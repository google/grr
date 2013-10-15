#!/usr/bin/env python
"""An implementation of an in-memory data store for testing."""

import re
import threading
import time

from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import utils


class FakeTransaction(data_store.Transaction):
  """A fake transaction object for testing."""

  def __init__(self, store, subject, lease_time=None, token=None):
    self.data_store = store
    self.subject = subject
    self.token = token
    self.locked = False
    self.to_set = {}
    self.to_delete = []
    if lease_time is None:
      lease_time = config_lib.CONFIG["Datastore.transaction_timeout"]

    self.expires = time.time() + lease_time

    with self.data_store.lock:
      expires = store.transactions.get(subject)
      if expires and time.time() < expires:
        raise data_store.TransactionError("Subject is locked")

      # Check expiry time.
      store.transactions[subject] = self.expires

      self.locked = True

  def CheckLease(self):
    return max(0, self.expires - time.time())

  def UpdateLease(self, duration):
    self.expires = time.time() + duration
    self.data_store.transactions[self.subject] = self.expires

  def DeleteAttribute(self, predicate):
    self.to_delete.append(predicate)

  def ResolveRegex(self, predicate_regex, timestamp=None):
    return self.data_store.ResolveRegex(self.subject, predicate_regex,
                                        timestamp=timestamp,
                                        token=self.token)

  def Set(self, predicate, value, timestamp=None, replace=True):
    if replace:
      self.to_delete.append(predicate)

    if timestamp is None:
      timestamp = int(time.time() * 1e6)

    self.to_set.setdefault(predicate, []).append((value, timestamp))

  def Resolve(self, predicate):
    return self.data_store.Resolve(self.subject, predicate, token=self.token)

  def Abort(self):
    self.Unlock()

  def Commit(self):
    self.data_store.DeleteAttributes(self.subject, self.to_delete, sync=True,
                                     token=self.token)

    self.data_store.MultiSet(self.subject, self.to_set, token=self.token)

    self.Unlock()

  def Unlock(self):
    with self.data_store.lock:
      if self.locked:
        self.data_store.transactions.pop(self.subject, None)
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

    # All access to the store must hold this lock.
    self.lock = threading.RLock()
    # The set of all transactions in flight.
    self.transactions = {}

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
  def DeleteSubject(self, subject, sync=False, token=None):
    _ = sync
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

  def Transaction(self, subject, lease_time=None, token=None):
    return FakeTransaction(self, subject, lease_time=lease_time, token=token)

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
        if isinstance(v, (list, tuple)):
          v, element_timestamp = v
        else:
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

        record[attribute] = []
    except KeyError:
      pass

  @utils.Synchronized
  def DeleteAttributesRegex(self, subject, regexes, token=None):
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    for regex in regexes:
      regex_compiled = re.compile(regex)
      subject = utils.SmartUnicode(subject)
      try:
        record = self.subjects[subject]

        for attribute in list(record):
          if regex_compiled.match(utils.SmartStr(attribute)):
            record.pop(attribute)

      except KeyError:
        pass

  @utils.Synchronized
  def MultiResolveRegex(self, subjects, predicate_regex, token=None,
                        timestamp=None, limit=None):
    result = {}
    for subject in subjects:
      # If any of the subjects is forbidden we fail the entire request.
      self.security_manager.CheckDataStoreAccess(token, [subject], "r")

      values = self.ResolveRegex(subject, predicate_regex, token=token,
                                 timestamp=timestamp, limit=limit)

      if values:
        result[subject] = values
        if limit:
          limit -= len(values)

    return result.iteritems()

  @utils.Synchronized
  def ResolveMulti(self, subject, predicates, token=None, timestamp=None):
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")
    # Does timestamp represent a range?
    if isinstance(timestamp, (list, tuple)):
      start, end = timestamp
    else:
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

            results_list.append((attribute, ts, value))

    # Return the results in the same order they requested.
    for predicate in predicates:
      for v in sorted(results.get(predicate, [])):
        yield (predicate, v[2], v[1])

  @utils.Synchronized
  def ResolveRegex(self, subject, predicate_regex, token=None,
                   timestamp=None, limit=None):
    """Resolve all predicates for a subject matching a regex."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")
    # Does timestamp represent a range?
    if isinstance(timestamp, (list, tuple)):
      start, end = timestamp
    else:
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
        if regex.match(utils.SmartStr(attribute)):
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

            results_list.append((attribute, ts, value))
            nr_results += 1
            if limit and nr_results >= limit:
              break

    result = []
    for k, values in sorted(results.items()):
      for v in sorted(values):
        result.append((k, v[2], v[1]))
    return result
