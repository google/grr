#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""An implementation of an in-memory data store for testing."""

import operator
import re
import threading
import time

from grr.lib import access_control
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils


# These are filters
class Filter(object):
  """Baseclass for filters.

  NOTE: Filters are not to be used on their own outside the data store
  module. They have no stable interface and do not have to implement their own
  abstraction. Users should only ever use filters from the data store
  implementation and only as args to the Query() method.

  This means that filters defined by the fake data store, and the mongo data
  store do not have to share any APIs.
  """

  __metaclass__ = registry.MetaclassRegistry

  # Automatically register plugins as class attributes
  include_plugins_as_attributes = True

  def FilterSubjects(self, subjects, token=None):
    data_store.DB.security_manager.CheckDataStoreAccess(token, subjects, "w")
    return subjects


class IdentityFilter(Filter):
  """A Filter which always returns true."""


class HasPredicateFilter(Filter):
  """Returns only the documents which have some value in the predicate."""

  def __init__(self, attribute_name):
    self.attribute_name = utils.SmartUnicode(attribute_name)
    Filter.__init__(self)

  def FilterSubjects(self, subjects, token=None):
    super(HasPredicateFilter, self).FilterSubjects(subjects, token)
    for subject, contents in subjects.items():
      if self.attribute_name in contents:
        yield utils.SmartUnicode(subject)


class AndFilter(Filter):
  """A Logical And operator."""

  def __init__(self, *parts):
    self.parts = parts
    Filter.__init__(self)

  def FilterSubjects(self, subjects, token=None):
    """Filter the subjects."""
    super(AndFilter, self).FilterSubjects(subjects, token)
    result = None
    for part in self.parts:
      part_set = set([subject for subject in part.FilterSubjects(
          subjects, token=token)])
      if result is None:
        result = part_set
      else:
        result = result.intersection(part_set)

    return result


class OrFilter(Filter):
  """A Logical Or operator."""

  def __init__(self, *parts):
    self.parts = parts
    Filter.__init__(self)

  def FilterSubjects(self, subjects, token=None):
    super(OrFilter, self).FilterSubjects(subjects, token)
    for part in self.parts:
      for subject in part.FilterSubjects(subjects, token=token):
        yield subject


class PredicateContainsFilter(Filter):
  """Applies a RegEx on the content of an attribute."""

  regex = None

  def __init__(self, attribute_name, regex):
    if regex:
      self.regex = re.compile(regex)

    self.attribute_name = utils.SmartUnicode(attribute_name)
    super(PredicateContainsFilter, self).__init__()

  def FilterSubjects(self, subjects, token=None):
    super(PredicateContainsFilter, self).FilterSubjects(subjects, token)
    for subject in subjects:
      # If the regex is empty, this is a passthrough.
      if self.regex is None:
        yield utils.SmartUnicode(subject)
      else:
        try:
          predicate_value = data_store.DB.Resolve(subject, self.attribute_name,
                                                  token=token)[0]
          if (predicate_value and
              self.regex.search(str(predicate_value))):
            yield utils.SmartUnicode(subject)
        except access_control.UnauthorizedAccess:
          pass


class PredicateLessThanFilter(Filter):
  """Filters attributes numerically less than a value."""

  _operator = operator.lt

  def __init__(self, attribute, value):
    self.value = long(value)
    self.attribute_name = utils.SmartUnicode(attribute)
    if getattr(attribute, "field_names", False):
      raise RuntimeError(
          "%s.%s: Filtering by subfields is not implemented yet." % (
              __name__, self.__class__.__name__))

    super(PredicateLessThanFilter, self).__init__()

  def FilterSubjects(self, subjects, token=None):
    super(PredicateLessThanFilter, self).FilterSubjects(subjects, token)
    for subject, values in subjects.items():
      try:
        # If the regex is empty, this is a passthrough.
        predicate_value, _ = values[self.attribute_name][0]
        if predicate_value is None: continue

        attribute = rdfvalue.RDFInteger(predicate_value)
        if self._operator(attribute, self.value):
          yield utils.SmartUnicode(subject)
      except (KeyError, ValueError):
        pass


class PredicateGreaterThanFilter(PredicateLessThanFilter):
  _operator = operator.gt


class PredicateGreaterEqualFilter(PredicateLessThanFilter):
  _operator = operator.ge


class PredicateNumericEqualFilter(Filter):
  """Filters attributes numerically equal than a value."""

  def __init__(self, attribute, value):
    self.value = value
    self.attribute_name = utils.SmartUnicode(attribute)
    if getattr(attribute, "field_names", False):
      raise RuntimeError(
          "%r: Filtering by subfields is not implemented yet." % self)

    super(PredicateNumericEqualFilter, self).__init__()

  def FilterSubjects(self, subjects, token=None):
    super(PredicateNumericEqualFilter, self).FilterSubjects(subjects, token)
    for subject in subjects:
      try:
        # If the regex is empty, this is a passthrough.
        predicate_value = data_store.DB.Resolve(subject, self.attribute_name)[0]
        attribute = self.attribute_name()
        attribute.ParseFromString(predicate_value)

        if attribute == self.value:
          yield utils.SmartUnicode(subject)
      except ValueError:
        pass


class SubjectContainsFilter(Filter):
  """Applies a RegEx to the subject name."""

  def __init__(self, regex):
    """Constructor.

    Args:
       regex: Must match the subject.
    """
    regex = utils.SmartUnicode(regex)
    self.regex = re.compile(regex)
    self.regex_text = regex
    super(SubjectContainsFilter, self).__init__()

  def FilterSubjects(self, subjects, token=None):
    super(SubjectContainsFilter, self).FilterSubjects(subjects, token)
    for subject in subjects:
      subject = utils.SmartUnicode(subject)
      if self.regex.search(subject):
        yield subject


class FakeTransaction(data_store.Transaction):
  """A fake transaction object for testing."""

  def __init__(self, store, subject, token=None):
    self.data_store = store
    self.subject = subject
    self.token = token
    self.locked = False

    with self.data_store.lock:
      if subject in store.transactions:
        raise data_store.TransactionError("Subject is locked")

      store.transactions.add(subject)
      self.locked = True

  def DeleteAttribute(self, attribute):
    self.data_store.DeleteAttributes(self.subject, [attribute],
                                     token=self.token)

  def ResolveRegex(self, predicate_regex,
                   decoder=None, timestamp=None):
    return self.data_store.ResolveRegex(self.subject, predicate_regex,
                                        decoder=decoder, timestamp=timestamp,
                                        token=self.token)

  def Set(self, predicate, value, timestamp=None, replace=True):
    self.data_store.Set(self.subject, predicate, value,
                        timestamp=timestamp, replace=replace,
                        token=self.token)

  def Resolve(self, predicate, decoder=None):
    return self.data_store.Resolve(self.subject, predicate, decoder=decoder,
                                   token=self.token)

  def Abort(self):
    # This is technically wrong - everything is always written. We do not have
    # code that depends on a working Abort right now.
    self.Unlock()

  def Commit(self):
    self.Unlock()

  def Unlock(self):
    with self.data_store.lock:
      if self.locked:
        self.data_store.transactions.remove(self.subject)
        self.locked = False

  def __del__(self):
    try:
      self.Abort()
    except Exception:  # This can raise on cleanup pylint: disable=broad-except
      pass


class FakeDataStore(data_store.DataStore):
  """A fake data store - Everything is in memory."""

  def __init__(self):
    super(FakeDataStore, self).__init__()
    self.subjects = {}
    self.filter = Filter
    # All access to the store must hold this lock.
    self.lock = threading.RLock()
    # The set of all transactions in flight.
    self.transactions = set()

  def Decode(self, value, decoder=None):
    result = super(FakeDataStore, self).Decode(value, decoder=decoder)
    if result is None:
      result = value

    return result

  def _Encode(self, value):
    """Encode the value into a Binary BSON object.

    The data store only supports the following values:
      -Integer
      -Unicode
      -Bytes (python string)

    We preserve integers and unicode objects, but serialize anything else.

    Args:
       value: The value to be encoded.

    Returns:
      An encoded value.
    """
    if isinstance(value, (basestring, int, float)):
      return value

    try:
      return value.SerializeToDataStore()
    except AttributeError:
      try:
        return value.SerializeToString()
      except AttributeError:
        return utils.SmartStr(value)

  @utils.Synchronized
  def DeleteSubject(self, subject, token=None):
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    try:
      del self.subjects[subject]
    except KeyError:
      pass

  def Flush(self):
    pass

  @utils.Synchronized
  def Clear(self):
    self.subjects = {}

  def Transaction(self, subject, token=None):
    return FakeTransaction(self, subject, token=token)

  @utils.Synchronized
  def Set(self, subject, attribute, value, timestamp=None, token=None,
          replace=True, sync=True):
    """Set the value into the data store."""
    _ = sync
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    subject = utils.SmartUnicode(subject)
    attribute = utils.SmartUnicode(attribute)

    if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
      timestamp = time.time() * 1000000

    if subject not in self.subjects:
      self.subjects[subject] = {}

    if replace or attribute not in self.subjects[subject]:
      self.subjects[subject][attribute] = []

    self.subjects[subject][attribute].append(
        [self._Encode(value), int(timestamp)])

  @utils.Synchronized
  def MultiSet(self, subject, values, timestamp=None, token=None,
               replace=True, sync=True, to_delete=None):
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    if to_delete:
      self.DeleteAttributes(subject, to_delete, token=token)

    for k, seq in values.items():
      for v in seq:
        try:
          v, element_timestamp = v
        except (TypeError, ValueError):
          element_timestamp = timestamp

        self.Set(subject, k, v, timestamp=element_timestamp, token=token,
                 replace=replace, sync=sync)

  @utils.Synchronized
  def DeleteAttributes(self, subject, attributes, start=None, end=None,
                       token=None, sync=None):
    _ = sync  # Unimplemented.
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    subject = utils.SmartUnicode(subject)
    try:
      record = self.subjects[subject]

      for attribute in attributes:
        if start and attribute[1] <= start:
          continue
        if end and attribute[1] >= end:
          continue
        del record[attribute]
    except KeyError:
      pass

  @utils.Synchronized
  def MultiResolveRegex(self, subjects, predicate_regex, token=None,
                        decoder=None, timestamp=None, limit=None):
    result = {}
    for subject in subjects:
      # If any of the subjects is forbidden we fail the entire request.
      self.security_manager.CheckDataStoreAccess(token, [subject], "r")

      values = self.ResolveRegex(subject, predicate_regex, token=token,
                                 decoder=decoder, timestamp=timestamp,
                                 limit=limit)

      if values:
        result[subject] = values
        if limit:
          limit -= len(values)

    return result

  @utils.Synchronized
  def ResolveMulti(self, subject, predicates, decoder=None, token=None,
                   timestamp=None):
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")
    # Does timestamp represent a range?
    try:
      start, end = timestamp
    except (ValueError, TypeError):
      start, end = -1, 1 << 65

    if isinstance(predicates, str):
      predicates = [predicates]

    subject = utils.SmartUnicode(subject)
    try:
      record = self.subjects[subject]
    except KeyError:
      return

    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = {}
    for predicate in predicates:
      for attribute, values in record.iteritems():
        if predicate == attribute:
          for value, ts in values:
            results_list = results.setdefault(attribute, [])
            # If we are always after the latest ts we clear older ones.
            if (results_list and timestamp == self.NEWEST_TIMESTAMP and
                results_list[0][1] < ts):
              results_list = []
              results[attribute] = results_list

            # Timestamp outside the range, drop it.
            elif ts < start or ts > end:
              continue

            results_list.append((attribute, ts, self.Decode(value, decoder)))

    # Return the results in the same order they requested.
    for predicate in predicates:
      for v in sorted(results.get(predicate, [])):
        yield (predicate, v[2], v[1])

  @utils.Synchronized
  def ResolveRegex(self, subject, predicate_regex, decoder=None, token=None,
                   timestamp=None, limit=None):
    """Resolve all predicates for a subject matching a regex."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")

    # Does timestamp represent a range?
    try:
      start, end = timestamp
    except (ValueError, TypeError):
      start, end = -1, 1 << 65

    if isinstance(predicate_regex, str):
      predicate_regex = [predicate_regex]

    subject = utils.SmartUnicode(subject)
    try:
      record = self.subjects[subject]
    except KeyError:
      return []

    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = {}
    nr_results = 0
    for regex in predicate_regex:
      regex = re.compile(regex)

      for attribute, values in record.iteritems():
        if limit and nr_results >= limit:
          break
        if regex.match(attribute):
          for value, ts in values:
            results_list = results.setdefault(attribute, [])
            # If we are always after the latest ts we clear older ones.
            if (results_list and timestamp == self.NEWEST_TIMESTAMP and
                results_list[0][1] < ts):
              results_list = []
              results[attribute] = results_list

            # Timestamp outside the range, drop it.
            elif ts < start or ts > end:
              continue

            results_list.append((attribute, ts, self.Decode(value, decoder)))
            nr_results += 1
            if limit and nr_results >= limit:
              break

    result = []
    for k, values in results.items():
      for v in sorted(values):
        result.append((k, v[2], v[1]))

    return result

  @utils.Synchronized
  def Query(self, attributes=None, filter_obj=None, subject_prefix="",
            token=None, subjects=None, limit=100,
            timestamp=data_store.DataStore.NEWEST_TIMESTAMP):
    """Retrieve subjects based on a filter."""
    # ACLs are enforced below.
    subject_prefix = utils.SmartUnicode(subject_prefix)

    if attributes is not None:
      attributes = [utils.SmartUnicode(x) for x in attributes]

    result_set = data_store.ResultSet()
    if filter_obj is None:
      filter_obj = Filter()

    # Filter the subjects according to the security_manager.
    if not subjects:
      subjects = self.subjects
    else:
      subjects = dict([(x, self.subjects[x])
                       for x in subjects if x in self.subjects])

    # Support limits if required
    try:
      start, length = limit
    except (TypeError, IndexError):
      start, length = 0, limit

    i = -1

    super_token = access_control.ACLToken()
    super_token.supervisor = True
    # Grab all the subjects which match the filter
    for subject in sorted(filter_obj.FilterSubjects(
        subjects, token=super_token)):
      if subject_prefix and not subject.startswith(subject_prefix):
        continue

      self.security_manager.CheckDataStoreAccess(token, [subject], "r")

      i += 1

      if i < start: continue
      if i >= start + length: break

      try:
        result = dict(subject=[(subject, 0)])
        for attribute in attributes or subjects[subject].keys():
          subject = utils.SmartUnicode(subject)
          attribute = utils.SmartUnicode(attribute)

          records = self.subjects.get(subject, {})
          values = records.get(attribute, [(None, 0)])

          if timestamp == data_store.DataStore.NEWEST_TIMESTAMP:
            values = values[-1:]
          elif timestamp == data_store.DataStore.ALL_TIMESTAMPS:
            pass
          else:
            try:
              start, end = timestamp
              values = [v for v in values if start <= v[1] <= end]
            except (TypeError, ValueError):
              raise RuntimeError("Invalid timestamp value.")

          result.setdefault(attribute, []).extend(
              [(self.Decode(value[0]), value[1])
               for value in values if value[0]])

        # Skip unauthorized results.
        self.security_manager.CheckDataStoreAccess(token, [subject], "rq")
        result_set.Append(result)
      except access_control.UnauthorizedAccess:
        continue

    result_set.total_count = len(result_set)

    return result_set
