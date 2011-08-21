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


import re
import time

from google.protobuf import message
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


class HasPredicateFilter(Filter):
  """Returns only the documents which have some value in the predicate."""

  def __init__(self, attribute_name):
    self.attribute_name = attribute_name
    Filter.__init__(self)

  def Filter(self, subjects):
    for subject, contents in subjects.items():
      if self.attribute_name in contents:
        yield utils.SmartUnicode(subject)


class AndFilter(Filter):
  """A Logical And operator."""

  def __init__(self, *parts):
    self.parts = parts
    Filter.__init__(self)

  def Filter(self, subjects):
    result = None
    for part in self.parts:
      part_set = set([subject for subject in part.Filter(subjects)])
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

  def Filter(self, subject):
    for part in self.parts:
      for subject in part.Filter(subject):
        yield subject


class PredicateContainsFilter(Filter):
  """Applies a RegEx on the content of an attribute."""

  regex = None

  def __init__(self, attribute_name, regex):
    if regex:
      self.regex = re.compile(regex)

    self.attribute_name = attribute_name
    super(PredicateContainsFilter, self).__init__()

  def Filter(self, subjects):
    for subject in subjects:
      # If the regex is empty, this is a passthrough.
      if self.regex is None:
        yield utils.SmartUnicode(subject)
      else:
        predicate_value = data_store.DB.Resolve(subject, self.attribute_name)[0]
        if (predicate_value and
            self.regex.search(str(predicate_value))):
          yield utils.SmartUnicode(subject)


class SubjectContainsFilter(Filter):
  """Applies a RegEx to the subject name."""

  def __init__(self, regex):
    """Constructor.

    Args:
       regex: Must match the subject.
    """
    self.regex = re.compile(regex)
    self.regex_text = regex
    super(SubjectContainsFilter, self).__init__()

  def Filter(self, subjects):
    for subject in subjects:
      if self.regex.search(subject):
        yield utils.SmartUnicode(subject)


class FakeTransaction(data_store.Transaction):
  """A fake transaction object for testing."""

  def __init__(self, store, subject):
    self.data_store = store
    self.subject = subject

  def DeleteSubject(self):
    del self.data_store.subjects[self.subject]

  def DeleteAttribute(self, attribute):
    self.data_store.DeleteAttributes(self.subject, [attribute])

  def ResolveRegex(self, predicate_regex,
                   decoder=None, timestamp=None):
    return self.data_store.ResolveRegex(self.subject, predicate_regex,
                                        decoder=decoder, timestamp=timestamp)

  def ResolveMulti(self, predicates, decoder=None):
    for predicate in predicates:
      try:
        cell, ts = self.data_store.Resolve(self.subject, predicate, decoder)
        yield predicate, cell, ts
      except KeyError: pass

  def Set(self, predicate, value, timestamp=None, replace=True):
    self.data_store.Set(self.subject, predicate, value,
                        timestamp=timestamp, replace=replace)

  def Resolve(self, predicate, decoder=None):
    return self.data_store.Resolve(self.subject, predicate, decoder=decoder)

  def Abort(self):
    # This is technically wrong - everything is always written. We do not have
    # code that depends on a working Abort right now.
    pass

  def Commit(self):
    pass


class FakeDataStore(data_store.DataStore):
  """A fake data store - Everything is in memory."""

  def __init__(self):
    self.subjects = {}
    self.Filter = Filter

  def Flush(self):
    self.subjects = {}

  def Transaction(self, subject):
    return FakeTransaction(self, subject)

  def RetryWrapper(self, subject, callback, **kwargs):
    transaction = FakeTransaction(self, subject)
    return callback(transaction, **kwargs)

  def Set(self, subject, attribute, value, timestamp=None,
          replace=True, sync=True):
    """Set the value into the data store."""
    if timestamp is None:
      timestamp = time.time() * 1e6

    subject = utils.SmartUnicode(subject)
    attribute = utils.SmartUnicode(attribute)

    if subject not in self.subjects:
      self.subjects[subject] = {}

    if replace or attribute not in self.subjects[subject]:
      self.subjects[subject][attribute] = []

    self.subjects[subject][attribute].append((_Encode(value), timestamp))

  def MultiSet(self, subject, values, timestamp=None,
               replace=True, sync=True):
    for k, v in values.items():
      self.Set(subject, k, v, timestamp=timestamp,
               replace=replace, sync=sync)

  def DeleteAttributes(self, subject, attributes):
    subject = utils.SmartUnicode(subject)
    try:
      record = self.subjects[subject]

      for attribute in attributes:
        del record[attribute]
    except KeyError: pass

  def Resolve(self, subject, attribute, decoder=None):
    subject = utils.SmartUnicode(subject)
    attribute = utils.SmartUnicode(attribute)

    records = self.subjects.get(subject, {})
    value = records.get(attribute, [(None, 0)])[0]
    return _Decode(value[0], decoder), value[1]

  def MultiResolveRegex(self, subjects, predicate_regex,
                        decoder=None, timestamp=None):
    result = {}
    for subject in subjects:
      result[subject] = self.ResolveRegex(subject, predicate_regex,
                                          decoder=decoder, timestamp=timestamp)

    return result

  def ResolveRegex(self, subject, predicate_regex, decoder=None,
                   timestamp=None):
    """Resolve all predicates for a subject matching a regex."""
    if isinstance(predicate_regex, str):
      predicate_regex = [predicate_regex]

    subject = utils.SmartUnicode(subject)
    try:
      record = self.subjects[subject]
    except KeyError: return []

    results = []
    for regex in predicate_regex:
      regex = re.compile(regex)

      for attribute, values in record.iteritems():
        if regex.match(attribute):
          for value, ts in values:
            results.append((attribute, _Decode(value, decoder), ts))

    results.sort(key=lambda x: x[0])

    if results and timestamp == data_store.NEWEST_TIMESTAMP:
      return [results[0]]

    try:
      start, end = timestamp

      return [x for x in results if x[2] > start and x[2] <= end]

    except (ValueError, TypeError): pass

    return results

  def Query(self, attributes, filter_obj="", subject_prefix="", limit=100):
    """Retrieve subjects based on a filter."""
    if attributes is None: attributes = []
    attributes = [str(x) for x in attributes]

    # Grab all the subjects which match the filter
    for subject in filter_obj.Filter(self.subjects):
      if subject_prefix and not subject.startswith(subject_prefix):
        continue

      result = dict(subject=(subject, 0))
      for attribute in attributes:
        value_pair = self.Resolve(subject, attribute)
        if value_pair[0] is not None:
          result[attribute] = value_pair

      yield result


def _Decode(value, decoder=None):
  """Decode from a value using the protobuf specified."""
  if value and decoder:
    result = decoder()
    try:
      result.ParseFromString(utils.SmartStr(value))
    except message.DecodeError: pass

    return result

  return value


def _Encode(value):
  """Encode the value into a Binary BSON object."""
  try:
    return value.SerializeToString()
  except AttributeError:
    if isinstance(value, str) or isinstance(value, unicode):
      return value
    else:
      return str(value)
