#!/usr/bin/env python

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""An implementation of an in-memory data store for testing."""

import operator
import re
import threading
import time

from grr.lib import aff4
from grr.lib import data_store
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
    return subjects


class IdentityFilter(Filter):
  """A Filter which always returns true."""


class HasPredicateFilter(Filter):
  """Returns only the documents which have some value in the predicate."""

  def __init__(self, attribute_name):
    self.attribute_name = utils.SmartUnicode(attribute_name)
    Filter.__init__(self)

  def FilterSubjects(self, subjects, token=None):
    for subject, contents in subjects.items():
      if self.attribute_name in contents:
        yield utils.SmartUnicode(subject)


class AndFilter(Filter):
  """A Logical And operator."""

  def __init__(self, *parts):
    self.parts = parts
    Filter.__init__(self)

  def FilterSubjects(self, subjects, token=None):
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

  def FilterSubjects(self, subject, token=None):
    for part in self.parts:
      for subject in part.FilterSubjects(subject, token=token):
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
        except data_store.UnauthorizedAccess:
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
    for subject, values in subjects.items():
      try:
        # If the regex is empty, this is a passthrough.
        predicate_value, _ = values[self.attribute_name][0]
        if predicate_value is None: continue

        attribute = aff4.RDFInteger(predicate_value)
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
    pass

  def Commit(self):
    pass


class FakeDataStore(data_store.DataStore):
  """A fake data store - Everything is in memory."""

  def __init__(self):
    super(FakeDataStore, self).__init__()
    self.subjects = {}
    self.Filter = Filter
    # All access to the store must hold this lock.
    self.lock = threading.RLock()

  def _Decode(self, value, decoder=None):
    result = super(FakeDataStore, self)._Decode(value, decoder=decoder)
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

  def RetryWrapper(self, subject, callback, token=None, **kwargs):
    transaction = FakeTransaction(self, subject, token=token)
    return callback(transaction, **kwargs)

  @utils.Synchronized
  def Set(self, subject, attribute, value, timestamp=None, token=None,
          replace=True, sync=True):
    """Set the value into the data store."""
    self.security_manager.CheckAccess(token, [subject], "w")

    subject = utils.SmartUnicode(subject)
    attribute = utils.SmartUnicode(attribute)

    if timestamp is None:
      timestamp = time.time() * 1000000

    if subject not in self.subjects:
      self.subjects[subject] = {}

    if replace or attribute not in self.subjects[subject]:
      self.subjects[subject][attribute] = []

    self.subjects[subject][attribute].append(
        [self._Encode(value), timestamp])

  @utils.Synchronized
  def MultiSet(self, subject, values, timestamp=None, token=None,
               replace=True, sync=True, to_delete=None):
    self.security_manager.CheckAccess(token, [subject], "w")

    if to_delete:
      self.DeleteAttributes(subject, to_delete, token=token)

    for k, seq in values.items():
      for v in seq:
        try:
          v, element_timestamp = v
        except (TypeError, ValueError):
          element_timestamp = timestamp

        if element_timestamp is None:
          element_timestamp = time.time() * 1e6

        self.Set(subject, k, v, timestamp=element_timestamp, token=token,
                 replace=replace, sync=sync)

  @utils.Synchronized
  def DeleteAttributes(self, subject, attributes, token=None):
    self.security_manager.CheckAccess(token, [subject], "w")
    subject = utils.SmartUnicode(subject)
    try:
      record = self.subjects[subject]

      for attribute in attributes:
        del record[attribute]
    except KeyError:
      pass

  @utils.Synchronized
  def Resolve(self, subject, attribute, decoder=None, token=None):
    self.security_manager.CheckAccess(token, [subject], "r")
    subject = utils.SmartUnicode(subject)
    attribute = utils.SmartUnicode(attribute)

    records = self.subjects.get(subject, {})

    # Always get the newest timestamp.
    value = records.get(attribute, [(None, 0)])[-1]
    return self._Decode(value[0], decoder), value[1]

  @utils.Synchronized
  def MultiResolveRegex(self, subjects, predicate_regex, token=None,
                        decoder=None, timestamp=None, limit=None):
    result = {}
    for subject in subjects:
      # If any of the subjects is forbidden we fail the entire request.
      self.security_manager.CheckAccess(token, [subject], "r")

      values = self.ResolveRegex(subject, predicate_regex, token=token,
                                 decoder=decoder, timestamp=timestamp,
                                 limit=limit)
      if values:
        result[subject] = values

    return result

  @utils.Synchronized
  def ResolveMulti(self, subject, predicates, decoder=None, token=None,
                   timestamp=None):
    self.security_manager.CheckAccess(token, [subject], "r")
    if timestamp is not None:
      raise NotImplementedError("Timestamps not implemented in ResolveMulti")

    result = []
    for predicate in predicates:
      value, ts = self.Resolve(subject, predicate, decoder=decoder, token=token)
      if value:
        result.append((predicate, value, ts))

    return result

  @utils.Synchronized
  def ResolveRegex(self, subject, predicate_regex, decoder=None, token=None,
                   timestamp=None, limit=None):
    """Resolve all predicates for a subject matching a regex."""
    self.security_manager.CheckAccess(token, [subject], "r")

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
    for regex in predicate_regex:
      regex = re.compile(regex)

      for attribute, values in record.iteritems():
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

            results_list.append((attribute, ts, self._Decode(value, decoder)))
            if limit and len(results) >= limit:
              break

    result = []
    for k, values in results.items():
      for v in sorted(values):
        result.append((k, v[2], v[1]))

    return result

  @utils.Synchronized
  def Query(self, attributes=None, filter_obj=None, subject_prefix="",
            token=None, subjects=None, limit=100):
    """Retrieve subjects based on a filter."""
    # ACLs are enforced by the Resolve() call below.
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

    super_token = data_store.ACLToken()
    super_token.supervisor = True
    # Grab all the subjects which match the filter
    for subject in sorted(filter_obj.FilterSubjects(
        subjects, token=super_token)):
      if subject_prefix and not subject.startswith(subject_prefix):
        continue

      i += 1

      if i < start: continue
      if i >= start + length: break

      try:
        result = dict(subject=(subject, 0))
        for attribute in attributes or subjects[subject].keys():
          value_pair = self.Resolve(subject, attribute, token=token)
          if value_pair[0] is not None:
            result[attribute] = value_pair

        # Skip unauthorized results.
        self.security_manager.CheckAccess(token, [subject], "rq")
        result_set.Append(result)
      except data_store.UnauthorizedAccess:
        continue

    result_set.total_count = len(result_set)

    return result_set
