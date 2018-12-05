#!/usr/bin/env python
"""An implementation of an in-memory data store for testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
import threading
import time


from future.utils import iteritems
from future.utils import string_types

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.util import precondition
from grr_response_server import aff4
from grr_response_server import data_store


class FakeDBSubjectLock(data_store.DBSubjectLock):
  """A fake transaction object for testing."""

  def _Acquire(self, lease_time):
    self.expires = int((time.time() + lease_time) * 1e6)
    with self.store.lock:
      expires = self.store.transactions.get(self.subject)
      if expires and (time.time() * 1e6) < expires:
        raise data_store.DBSubjectLockError("Subject is locked")
      self.store.transactions[self.subject] = self.expires
      self.locked = True

  def UpdateLease(self, duration):
    self.expires = int((time.time() + duration) * 1e6)
    self.store.transactions[self.subject] = self.expires

  def Release(self):
    with self.store.lock:
      if self.locked:
        self.store.transactions.pop(self.subject, None)
        self.locked = False


class FakeDataStore(data_store.DataStore):
  """A fake data store - Everything is in memory."""

  def __init__(self):
    super(FakeDataStore, self).__init__()
    self.subjects = {}

    # All access to the store must hold this lock.
    self.lock = threading.RLock()
    # The set of all transactions in flight.
    self.transactions = {}

    self._value_converter = aff4.ValueConverter()

  @utils.Synchronized
  def DeleteSubject(self, subject, sync=False):
    _ = sync
    subject = utils.SmartUnicode(subject)
    try:
      del self.subjects[subject]
    except KeyError:
      pass

  @utils.Synchronized
  def ClearTestDB(self):
    self.subjects = {}

  def DBSubjectLock(self, subject, lease_time=None):
    return FakeDBSubjectLock(self, subject, lease_time=lease_time)

  @utils.Synchronized
  def Set(self,
          subject,
          attribute,
          value,
          timestamp=None,
          replace=True,
          sync=True):
    """Set the value into the data store."""
    subject = utils.SmartUnicode(subject)

    _ = sync
    attribute = utils.SmartUnicode(attribute)

    if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
      timestamp = time.time() * 1000000

    if subject not in self.subjects:
      self.subjects[subject] = {}

    if replace or attribute not in self.subjects[subject]:
      self.subjects[subject][attribute] = []

    encoded_value = self._value_converter.Encode(attribute, value)
    self.subjects[subject][attribute].append([encoded_value, int(timestamp)])
    self.subjects[subject][attribute].sort(key=lambda x: x[1])

  @utils.Synchronized
  def MultiSet(self,
               subject,
               values,
               timestamp=None,
               replace=True,
               sync=True,
               to_delete=None):
    subject = utils.SmartUnicode(subject)
    if to_delete:
      self.DeleteAttributes(subject, to_delete, sync=sync)

    for k, seq in iteritems(values):
      for v in seq:
        if isinstance(v, (list, tuple)):
          v, element_timestamp = v
        else:
          element_timestamp = timestamp

        self.Set(
            subject,
            k,
            v,
            timestamp=element_timestamp,
            replace=replace,
            sync=sync)

  @utils.Synchronized
  def DeleteAttributes(self,
                       subject,
                       attributes,
                       start=None,
                       end=None,
                       sync=None):
    _ = sync  # Unimplemented.
    if isinstance(attributes, string_types):
      raise ValueError(
          "String passed to DeleteAttributes (non string iterable expected).")

    subject = utils.SmartUnicode(subject)
    try:
      record = self.subjects[subject]
      keys_to_delete = []
      for name, values in iteritems(record):
        if name not in attributes:
          continue

        start = start or 0
        if end is None:
          end = (2**63) - 1  # sys.maxsize
        new_values = []
        for value, timestamp in values:
          if not start <= timestamp <= end:
            new_values.append((value, int(timestamp)))

        if new_values:
          record[name] = new_values
        else:
          keys_to_delete.append(name)

      for key in keys_to_delete:
        record.pop(key)
    except KeyError:
      pass

  @utils.Synchronized
  def ScanAttributes(self,
                     subject_prefix,
                     attributes,
                     after_urn="",
                     max_records=None,
                     relaxed_order=False):
    precondition.AssertType(subject_prefix, unicode)
    precondition.AssertIterableType(attributes, unicode)

    subject_prefix = utils.SmartStr(rdfvalue.RDFURN(subject_prefix))
    if subject_prefix[-1] != "/":
      subject_prefix += "/"
    if after_urn:
      after_urn = utils.SmartUnicode(after_urn)
    subjects = []
    for s in self.subjects:
      if s.startswith(subject_prefix) and s > after_urn:
        subjects.append(s)
    subjects.sort()

    return_count = 0
    for s in subjects:
      if max_records and return_count >= max_records:
        break
      r = self.subjects[s]
      results = {}
      for attribute in attributes:
        attribute_list = r.get(attribute)
        if attribute_list:
          encoded_value, timestamp = attribute_list[-1]
          value = self._value_converter.Decode(attribute, encoded_value)
          results[attribute] = (timestamp, value)
      if results:
        return_count += 1
        yield (s, results)

  @utils.Synchronized
  def ResolveMulti(self, subject, attributes, timestamp=None, limit=None):
    subject = utils.SmartUnicode(subject)

    # Does timestamp represent a range?
    if isinstance(timestamp, (list, tuple)):
      start, end = timestamp  # pylint: disable=unpacking-non-sequence
    else:
      start, end = -1, 1 << 65

    start = int(start)
    end = int(end)

    if isinstance(attributes, str):
      attributes = [attributes]

    try:
      record = self.subjects[subject]
    except KeyError:
      return

    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = {}
    for attribute in attributes:
      for attr, values in iteritems(record):
        if attr == attribute:
          for encoded_value, ts in values:
            results_list = results.setdefault(attribute, [])
            # If we are always after the latest ts we clear older ones.
            if (results_list and timestamp == self.NEWEST_TIMESTAMP and
                results_list[0][1] < ts):
              results_list = []
              results[attribute] = results_list

            # Timestamp outside the range, drop it.
            elif ts < start or ts > end:
              continue

            value = self._value_converter.Decode(attribute, encoded_value)
            results_list.append((attribute, ts, value))

    # Return the results in the same order they requested.
    remaining_limit = limit
    for attribute in attributes:
      # This returns triples of (attribute_name, timestamp, data). We want to
      # sort by timestamp.
      for _, ts, data in sorted(
          results.get(attribute, []), key=lambda x: x[1], reverse=True):
        if remaining_limit:
          remaining_limit -= 1
          if remaining_limit == 0:
            yield (attribute, data, ts)
            return

        yield (attribute, data, ts)

  @utils.Synchronized
  def MultiResolvePrefix(self,
                         subjects,
                         attribute_prefix,
                         timestamp=None,
                         limit=None):
    unicode_to_orig = {utils.SmartUnicode(s): s for s in subjects}
    result = {}
    for unicode_subject, orig_subject in iteritems(unicode_to_orig):

      values = self.ResolvePrefix(
          unicode_subject, attribute_prefix, timestamp=timestamp, limit=limit)

      if not values:
        continue

      if limit:
        if limit < len(values):
          values = values[:limit]
        result[orig_subject] = values
        limit -= len(values)
        if limit <= 0:
          return iteritems(result)
      else:
        result[orig_subject] = values

    return iteritems(result)

  def Flush(self):
    pass

  @utils.Synchronized
  def ResolvePrefix(self, subject, attribute_prefix, timestamp=None,
                    limit=None):
    """Resolve all attributes for a subject starting with a prefix."""
    subject = utils.SmartUnicode(subject)

    if timestamp in [None, self.NEWEST_TIMESTAMP, self.ALL_TIMESTAMPS]:
      start, end = 0, (2**63) - 1
    # Does timestamp represent a range?
    elif isinstance(timestamp, (list, tuple)):
      start, end = timestamp  # pylint: disable=unpacking-non-sequence
    else:
      raise ValueError("Invalid timestamp: %s" % timestamp)

    start = int(start)
    end = int(end)

    # TODO(hanuszczak): Make this function accept only one attribute prefix and
    # only a unicode object.
    if isinstance(attribute_prefix, string_types):
      attribute_prefix = [attribute_prefix]

    try:
      record = self.subjects[subject]
    except KeyError:
      return []

    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = {}
    nr_results = 0
    for prefix in attribute_prefix:
      for attribute, values in iteritems(record):
        if limit and nr_results >= limit:
          break
        # TODO(hanuszczak): After resolving the TODO comment above this call to
        # `unicode` should be redundant.
        if unicode(attribute).startswith(prefix):
          for encoded_value, ts in values:
            results_list = results.setdefault(attribute, [])
            # If we are always after the latest ts we clear older ones.
            if (results_list and timestamp in [self.NEWEST_TIMESTAMP, None] and
                results_list[0][1] < ts):
              results_list = []
              results[attribute] = results_list

            # Timestamp outside the range, drop it.
            elif ts < start or ts > end:
              continue

            value = self._value_converter.Decode(attribute, encoded_value)
            results_list.append((attribute, ts, value))
            nr_results += 1
            if limit and nr_results >= limit:
              break

    result = []
    for attribute_name, values in sorted(iteritems(results)):
      # Values are triples of (attribute_name, timestamp, data). We want to
      # sort by timestamp.
      for _, ts, data in sorted(values, key=lambda x: x[1], reverse=True):
        # Return triples (attribute_name, data, timestamp).
        result.append((attribute_name, data, ts))
    return result

  def Size(self):
    total_size = sys.getsizeof(self.subjects)
    for subject, record in iteritems(self.subjects):
      total_size += sys.getsizeof(subject)
      total_size += sys.getsizeof(record)
      for attribute, values in iteritems(record):
        total_size += sys.getsizeof(attribute)
        total_size += sys.getsizeof(values)
        for value, timestamp in values:
          total_size += sys.getsizeof(value)
          total_size += sys.getsizeof(timestamp)
    return total_size

  def PrintSubjects(self, literal=None):
    for s in sorted(self.subjects):
      if literal and literal not in s:
        continue
      print(s)
