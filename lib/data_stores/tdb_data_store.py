#!/usr/bin/env python
"""A file based data store based on the trivial database.

TDB is part of the Samba project: http://tdb.samba.org/

NOTE: We only support tdb version 1.2.12 and latest. Please download it from:
http://www.samba.org/ftp/tdb/

This data store has the following properties:

- Very fast for local, single database machine systems

- Produces an aff4 mapping on the filesystem that is easily understandable by
  humans

- May work on networked filesystems as long as locking is supported, but this is
  untested
"""
import os
import re
import threading
import time

import tdb

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.data_stores import common

TDB_SEPARATOR = "\x00"
TDB_EXTENSION = "tdb"


class TDBIndex(rdfvalue.RDFBytes):
  """An index for columns or timestamps."""

  def __init__(self, *parts, **kwargs):
    self.parts = parts
    self.context = kwargs.pop("context", None)
    if parts:
      kwargs["initializer"] = self.context.Get(*parts)

    super(TDBIndex, self).__init__(**kwargs)

    # The index is always a byte string, but we read and write unicode objects
    # to it.
    self.index = set(self._value.split(TDB_SEPARATOR))
    self.index.discard("")
    self._dirty = False

  def __contains__(self, other):
    return utils.SmartStr(other) in self.index

  def Add(self, value):
    self.index.add(utils.SmartStr(value))
    self._dirty = True

  def Remove(self, value):
    self.index.discard(utils.SmartStr(value))
    self._dirty = True

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if self._dirty:
      self._value = TDB_SEPARATOR.join(self.index)
      self.context.Put(self._value, *self.parts)

  def __len__(self):
    return len(self.index)

  def __iter__(self):
    return iter(self.index)


class TDBContextCache(utils.FastStore):
  """A local cache of tdb context objects."""

  def __init__(self, size):
    super(TDBContextCache, self).__init__(max_size=size)
    self.root_path = config_lib.CONFIG.Get("Datastore.location")
    self.RecreatePathing()

  def RecreatePathing(self, pathing=None):
    if not pathing:
      pathing = config_lib.CONFIG.Get("Datastore.pathing")
    try:
      self.path_regexes = [re.compile(path) for path in pathing]
    except re.error:
      raise data_store.Error("Invalid regular expression in Datastore.pathing")

  def KillObject(self, obj):
    obj.Close()

  def RootPath(self):
    return self.root_path

  @utils.Synchronized
  def Get(self, subject):
    """This will create the object if needed so should not fail."""
    filename, directory = common.ResolveSubjectDestination(subject,
                                                           self.path_regexes)
    key = common.MakeDestinationKey(directory, filename)
    try:
      return super(TDBContextCache, self).Get(key)
    except KeyError:
      root_path = self.RootPath()
      dirname = utils.JoinPath(root_path, directory)
      path = utils.JoinPath(dirname, filename) + "." + TDB_EXTENSION
      dirname = utils.SmartStr(dirname)
      path = utils.SmartStr(path)

      # Make sure directory exists.
      if not os.path.isdir(dirname):
        try:
          os.makedirs(dirname)
        except OSError:
          pass

      context = TDBContext(path)

      super(TDBContextCache, self).Put(key, context)

      return context


class TDBContext(object):
  """A wrapper around the raw tdb context."""

  def __init__(self, filename):
    self.filename = filename
    self.context = tdb.open(utils.SmartStr(filename),
                            flags=os.O_CREAT | os.O_RDWR)
    self.lock = threading.RLock()

  def _MakeKey(self, parts):
    # TDB can only handle strings here.
    return TDB_SEPARATOR.join([utils.SmartStr(part) for part in parts])

  @utils.Synchronized
  def Get(self, *parts):
    return self.context.get(self._MakeKey(parts))

  @utils.Synchronized
  def Put(self, value, *parts):
    # TDB can only handle binary strings here.
    self.context.store(self._MakeKey(parts), utils.SmartStr(value))

  @utils.Synchronized
  def Delete(self, *parts):
    try:
      self.context.delete(self._MakeKey(parts))
    except RuntimeError:
      pass

  def __enter__(self):
    self.lock.acquire()
    self.context.lock_all()

    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if self.context:
      self.context.unlock_all()
    self.lock.release()

  def Close(self):
    self.context.close()
    self.context = None

  def PrettyPrint(self):
    """Pretty print the entire tdb database."""
    for key in self.context:
      value = self.context.get(key)
      if value.endswith("index"):
        value = TDBIndex(value)

      print "Key: %s" % key
      print "Value: %s" % value
      print "-------------------------"


class TDBDataStore(data_store.DataStore):
  """A file based data store using the Samba project's trivial database."""
  INDEX_SUFFIX = "index"

  cache = None

  def __init__(self):
    self._CalculateAttributeStorageTypes()
    super(TDBDataStore, self).__init__()
    # A cache of tdb contexts. It is slightly faster to reuse contexts than
    # to open the tdb all the time.
    self.cache = TDBContextCache(100)

  def RecreatePathing(self, pathing):
    self.cache.RecreatePathing(pathing)

  def _CalculateAttributeStorageTypes(self):
    """Build a mapping between column names and types.

    Since TDB only stores strings, we need to record the basic types that are
    required to be stored for each column.
    """
    self._attribute_types = {}

    for attribute in aff4.Attribute.PREDICATES.values():
      self._attribute_types[attribute.predicate] = (
          attribute.attribute_type.data_store_type)

  def _Encode(self, value):
    """Encode the value for the attribute."""
    if hasattr(value, "SerializeToString"):
      return value.SerializeToString()
    else:
      # Types "string" and "bytes" are stored as strings here.
      return utils.SmartStr(value)

  def _Decode(self, attribute, value):
    """Decode the value to the required type."""
    required_type = self._attribute_types.get(attribute, "bytes")
    if required_type in ("integer", "unsigned_integer"):
      return int(value)
    elif required_type == "string":
      return utils.SmartUnicode(value)
    else:
      return value

  def MultiSet(self, subject, values, timestamp=None,
               replace=True, sync=True, to_delete=None, token=None):
    """Set multiple values at once."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    # All operations are synchronized.
    _ = sync
    if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
      timestamp = time.time() * 1000000

    if to_delete is None:
      to_delete = []

    with self.cache.Get(subject) as tdb_context:
      with TDBIndex(subject, self.INDEX_SUFFIX,
                    context=tdb_context) as attribute_index:

        if replace:
          to_delete.extend(values.keys())

        # Delete attribute if needed.
        if to_delete:
          for attribute in to_delete:
            attribute_index.Remove(attribute)
            self._DeleteAttribute(subject, attribute, tdb_context)

        for attribute, seq in values.items():
          attribute_index.Add(attribute)
          with TDBIndex(subject, attribute,
                        self.INDEX_SUFFIX,
                        context=tdb_context) as timestamp_index:
            for v in seq:
              element_timestamp = None
              if isinstance(v, (list, tuple)):
                v, element_timestamp = v

              if element_timestamp is None:
                element_timestamp = timestamp

              element_timestamp = str(long(element_timestamp))
              timestamp_index.Add(element_timestamp)
              tdb_context.Put(self._Encode(v),
                              subject, attribute, element_timestamp)

  def DeleteAttributes(self, subject, attributes, start=None, end=None,
                       sync=True, token=None):
    """Remove some attributes from a subject."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    _ = sync

    with self.cache.Get(subject) as tdb_context:
      with TDBIndex(subject, self.INDEX_SUFFIX,
                    context=tdb_context) as attribute_index:
        if start is None and end is None:
          # This is done when we delete all attributes at once without
          # caring about timestamps.
          for attribute in list(attributes):
            attribute_index.Remove(attribute)
            self._DeleteAttribute(subject, attribute, tdb_context)
        else:
          # This code path is taken when we have a timestamp range - we
          # first enumerate all existing timestamps and then remove
          # the ones that fall in that range.
          start = start or 0
          if end is None:
            end = (2 ** 63) - 1  # sys.maxint
          for attribute in list(attributes):
            attribute_removed = False
            with TDBIndex(subject, attribute,
                          self.INDEX_SUFFIX,
                          context=tdb_context) as timestamp_index:
              filtered_ts = [x for x in timestamp_index
                             if start <= int(x) <= end]
              attribute_removed = (len(filtered_ts) == len(timestamp_index))
              for timestamp in filtered_ts:
                tdb_context.Delete(subject, attribute, timestamp)
                timestamp_index.Remove(timestamp)
            if attribute_removed:
              attribute_index.Remove(attribute)
              # Also delete the timestamp index.
              tdb_context.Delete(subject, attribute, self.INDEX_SUFFIX)

  def DeleteSubject(self, subject, sync=False, token=None):
    _ = sync
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    with self.cache.Get(subject) as tdb_context:
      with TDBIndex(subject, self.INDEX_SUFFIX,
                    context=tdb_context) as attribute_index:
        for attribute in attribute_index:
          self._DeleteAttribute(subject, attribute, tdb_context)
        # Delete attribute index.
        tdb_context.Delete(subject, self.INDEX_SUFFIX)

  def MultiResolveRegex(self, subjects, attribute_regex,
                        timestamp=None, limit=None, token=None):
    """Result multiple subjects using one or more attribute regexps."""
    result = {}

    remaining_limit = limit
    for subject in subjects:
      values = self.ResolveRegex(subject, attribute_regex, token=token,
                                 timestamp=timestamp, limit=remaining_limit)

      if values:
        if remaining_limit:
          if len(values) >= remaining_limit:
            result[subject] = values[:remaining_limit]
            return result.iteritems()
          else:
            remaining_limit -= len(values)

        result[subject] = values

    return result.iteritems()

  def DumpTDBDatabase(self, subject, token=None):
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")
    with self.cache.Get(subject) as tdb_context:
      tdb_context.PrettyPrint()

  def ResolveRegex(self, subject, attribute_regex,
                   timestamp=None, limit=None, token=None):
    """Resolve all attributes for a subject matching a regex."""
    self.security_manager.CheckDataStoreAccess(
        token, [subject], self.GetRequiredResolveAccess(attribute_regex))

    if isinstance(attribute_regex, str):
      attribute_regex = [attribute_regex]

    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = []

    with self.cache.Get(subject) as tdb_context:
      remaining_limit = limit
      for regex in attribute_regex:
        regex = re.compile(regex)

        attribute_index = TDBIndex(subject, self.INDEX_SUFFIX,
                                   context=tdb_context)

        for attribute in attribute_index:

          if regex.match(utils.SmartUnicode(attribute)):
            for result in self._GetTimestampsForAttribute(
                subject, attribute, timestamp, tdb_context):
              results.append(result[1:])
              if remaining_limit:
                remaining_limit -= 1
                if remaining_limit == 0:
                  return results

      return results

  def ResolveMulti(self, subject, attributes,
                   timestamp=None, limit=None, token=None):
    """Resolve all attributes for a subject matching a regex."""
    self.security_manager.CheckDataStoreAccess(
        token, [subject], self.GetRequiredResolveAccess(attributes))

    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = []

    with self.cache.Get(subject) as tdb_context:
      attribute_index = TDBIndex(subject, self.INDEX_SUFFIX,
                                 context=tdb_context)
      for attribute in attributes:
        if attribute in attribute_index:
          for _, attribute, value, ts in self._GetTimestampsForAttribute(
              subject, attribute, timestamp, tdb_context):
            results.append((attribute, value, ts))

        if limit and len(results) >= limit:
          break

      return results

  def _DeleteAttribute(self, subject, attribute, tdb_context):
    # Find the matching timestamps through the index.
    timestamp_index = TDBIndex(subject, attribute, self.INDEX_SUFFIX,
                               context=tdb_context)

    # Remove all timestamps.
    for timestamp in timestamp_index:
      tdb_context.Delete(subject, attribute, timestamp)

    tdb_context.Delete(subject, attribute, self.INDEX_SUFFIX)

  def _GetTimestampsForAttribute(self, subject, attribute, timestamp,
                                 tdb_context):
    """Use the timestamp index to select ranges of timestamps."""
    # Find the matching timestamps through the index.
    timestamp_index = TDBIndex(subject, attribute, self.INDEX_SUFFIX,
                               context=tdb_context)

    if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
      # We only care about the latest timestamp.
      matching_timestamp = max(timestamp_index)
      value = self._Decode(
          attribute, tdb_context.Get(subject, attribute, matching_timestamp))

      return [(subject, attribute, value, int(matching_timestamp))]

    # Timestamps are a range or ALL_TIMESTAMPS.
    timestamps = sorted([int(t) for t in timestamp_index],
                        reverse=True)
    results = []
    for matching_timestamp in timestamps:
      if (timestamp == self.ALL_TIMESTAMPS or
          (matching_timestamp >= timestamp[0] and
           matching_timestamp <= timestamp[1])):

        value = self._Decode(
            attribute, tdb_context.Get(subject, attribute, matching_timestamp))

        results.append((subject, attribute, value, matching_timestamp))

    return results

  def Size(self):
    root_path = self.Location()
    if not os.path.exists(root_path):
      # Database does not exist yet.
      return 0
    if not os.path.isdir(root_path):
      # Database should be a directory.
      raise IOError("expected TDB directory %s to be a directory" % root_path)
    size, _ = common.DatabaseDirectorySize(root_path, self.FileExtension())
    return size

  @staticmethod
  def FileExtension():
    return TDB_EXTENSION

  def Location(self):
    """Get location of the data store."""
    return self.cache.RootPath()

  def Transaction(self, subject, lease_time=None, token=None):
    return TDBTransaction(self, subject, lease_time=lease_time, token=token)


class TDBTransaction(data_store.CommonTransaction):
  """The TDB data store transaction object.

  This does not aim to ensure ACID like consistently. We only ensure that two
  simultaneous locks can not be held on the same subject.

  This means that the first thread which grabs the lock is considered the owner
  of the transaction. Any subsequent transactions on the same subject will fail
  immediately with data_store.TransactionError. NOTE that it is still possible
  to manipulate the row without a transaction - this is a design feature!

  A lock is considered expired after a certain time.
  """

  lock_creation_lock = threading.Lock()

  locked = False

  def __init__(self, store, subject, lease_time=None, token=None):
    """Ensure we can take a lock on this subject."""
    super(TDBTransaction, self).__init__(store, utils.SmartUnicode(subject),
                                         lease_time=lease_time, token=token)

    self.lock_key = utils.SmartUnicode(self.subject) + "_lock"
    if lease_time is None:
      lease_time = config_lib.CONFIG["Datastore.transaction_timeout"]

    # Note that we have the luxury of real file locking here so this will block
    # until we obtain the lock.
    with store.cache.Get(self.subject) as tdb_context:
      locked_until = tdb_context.Get(self.lock_key)

      # This is currently locked by another thread.
      if locked_until and time.time() < float(locked_until):
        raise data_store.TransactionError("Subject %s is locked" % subject)

      # Subject is not locked, we take a lease on it.
      self.expires = time.time() + lease_time
      tdb_context.Put(self.expires, self.lock_key)
      self.locked = True

  def UpdateLease(self, duration):
    self.expires = time.time() + duration
    with self.store.cache.Get(self.subject) as tdb_context:
      self.expires = time.time() + duration
      tdb_context.Put(self.expires, self.lock_key)

  def Abort(self):
    if self.locked:
      self._RemoveLock()

  def Commit(self):
    if self.locked:
      super(TDBTransaction, self).Commit()
      self._RemoveLock()

  def _RemoveLock(self):
    with self.store.cache.Get(self.subject) as tdb_context:
      tdb_context.Delete(self.lock_key)

    self.locked = False
