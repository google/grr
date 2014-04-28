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
    self.index = set(self._value.split("\x00"))
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
      self._value = "\x00".join(self.index)
      self.context.Put(self._value, *self.parts)

  def __iter__(self):
    return iter(self.index)


class TDBContextCache(utils.FastStore):
  """A local cache of tdb context objects."""

  def KillObject(self, obj):
    obj.Close()

  def _ConvertSubjectToFilename(self, subject):
    """Converts a subject to a filesystem safe filename.

    For maximum compatibility we escape all chars which are not alphanumeric (in
    the unicode sense).

    Args:
     subject: a unicode subject.

    Returns:
      A safe filename with escaped special chars.
    """
    result = re.sub(
        r"\W", lambda x: "%%%02X" % ord(x.group(0)),
        utils.SmartUnicode(subject), flags=re.UNICODE).rstrip("/")

    # Some filesystems are not able to represent unicode chars.
    return utils.SmartStr(result)

  @utils.Synchronized
  def Get(self, subject):
    """This will create the object if needed so should not fail."""
    try:
      return super(TDBContextCache, self).Get(subject)
    except KeyError:
      subject_path = utils.JoinPath(config_lib.CONFIG["TDBDatastore.root_path"],
                                    self._ConvertSubjectToFilename(subject))
      filename = subject_path + ".tdb"
      try:
        context = TDBContext(filename)
      except IOError as e:
        if "No such file or directory" in str(e):
          dirname = os.path.dirname(subject_path)
          os.makedirs(dirname)

          context = TDBContext(filename)
        else:
          raise

      super(TDBContextCache, self).Put(subject, context)

      return context


# A cache of tdb contexts. It is slightly faster to reuse contexts than to open
# the tdb all the time.
TDB_CACHE = TDBContextCache(100)


class TDBContext(object):
  """A wrapper around the raw tdb context."""

  def __init__(self, filename):
    self.filename = filename
    self.context = tdb.open(utils.SmartStr(filename),
                            flags=os.O_CREAT|os.O_RDWR)
    self.lock = threading.RLock()

  @utils.Synchronized
  def Get(self, *parts):
    parts = [utils.SmartStr(part) for part in parts]

    # TDB can only handle strings here.
    return self.context.get("\x00".join(parts))

  @utils.Synchronized
  def Put(self, value, *parts):
    # TDB can only handle binary strings here.
    parts = [utils.SmartStr(x) for x in parts]
    self.context.store("\x00".join(parts), utils.SmartStr(value))

  def Delete(self, *parts):
    parts = [utils.SmartStr(part) for part in parts]
    try:
      # TDB can only handle strings here.
      self.context.delete("\x00".join(parts))
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


def TDBPrettyPrint(tdb_context):
  """Pretty print the entire tdb database."""
  for key in tdb_context.context:
    value = tdb_context.context.get(key)
    if value.endswith("index"):
      value = TDBIndex(value)

    print "Key: %s" % key
    print "Value: %s" % value
    print "-------------------------"


class TDBDataStore(data_store.DataStore):
  """A file based data store using the Samba project's trivial database."""
  INDEX_SUFFIX = "index"

  def __init__(self):
    self._CalculateAttributeStorageTypes()
    super(TDBDataStore, self).__init__()

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

  def MultiSet(self, subject, values, timestamp=None, token=None,
               replace=True, sync=True, to_delete=None):
    """Set multiple values at once."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    # All operations are synchronized.
    _ = sync
    if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
      timestamp = time.time() * 1000000

    if to_delete is None:
      to_delete = []

    with TDB_CACHE.Get(subject) as tdb_context:
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
              if isinstance(v, (list, tuple)):
                v, element_timestamp = v
              else:
                element_timestamp = timestamp

              element_timestamp = str(long(element_timestamp))
              timestamp_index.Add(element_timestamp)
              tdb_context.Put(self._Encode(v),
                              subject, attribute, element_timestamp)

  def DeleteAttributes(self, subject, attributes, sync=None, token=None):
    """Remove some attributes from a subject."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    _ = sync

    with TDB_CACHE.Get(subject) as tdb_context:
      with TDBIndex(subject, self.INDEX_SUFFIX,
                    context=tdb_context) as attribute_index:

        for attribute in list(attributes):
          attribute_index.Remove(attribute)
          self._DeleteAttribute(subject, attribute, tdb_context)

  def DeleteAttributesRegex(self, subject, regexes, token=None):
    """Deletes attributes using one or more regular expressions."""
    matching_attributes = []

    with TDB_CACHE.Get(subject) as tdb_context:
      with TDBIndex(subject, self.INDEX_SUFFIX,
                    context=tdb_context) as attribute_index:
        for regex in regexes:
          for attribute in attribute_index:
            if re.match(regex, attribute):
              matching_attributes.append(attribute)

    self.DeleteAttributes(subject, matching_attributes, token=token)

  def DeleteSubject(self, subject, token=None):
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    # Deleting the subject means removing the entire tdb file.
    with TDB_CACHE.Get(subject) as tdb_context:
      filename = tdb_context.filename
      TDB_CACHE.ExpireObject(subject)
      os.unlink(utils.SmartStr(filename))

  def MultiResolveRegex(self, subjects, predicate_regex, token=None,
                        timestamp=None, limit=None):
    """Result multiple subjects using one or more predicate regexps."""
    result = {}
    nr_results = 0

    for subject in subjects:
      values = self.ResolveRegex(subject, predicate_regex, token=token,
                                 timestamp=timestamp, limit=limit)

      if values:
        result[subject] = values
        nr_results += len(values)
        if limit:
          limit -= len(values)

      if limit and nr_results < 0:
        break

    return result.iteritems()

  def DumpTDBDatabase(self, subject, token=None):
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")
    with TDB_CACHE.Get(subject) as tdb_context:
      TDBPrettyPrint(tdb_context)

  def ResolveRegex(self, subject, predicate_regex, token=None,
                   timestamp=None, limit=None):
    """Resolve all predicates for a subject matching a regex."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")

    if isinstance(predicate_regex, str):
      predicate_regex = [predicate_regex]

    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = []

    with TDB_CACHE.Get(subject) as tdb_context:
      nr_results = 0
      for regex in predicate_regex:
        regex = re.compile(regex)

        attribute_index = TDBIndex(subject, self.INDEX_SUFFIX,
                                   context=tdb_context)

        for attribute in attribute_index:
          if limit and nr_results >= limit:
            break

          if regex.match(utils.SmartUnicode(attribute)):
            for result in self._GetTimestampsForAttribute(
                subject, attribute, timestamp, tdb_context):
              results.append(result[1:])

      return results

  def ResolveMulti(self, subject, predicates, token=None,
                   timestamp=None, limit=None):
    """Resolve all predicates for a subject matching a regex."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")

    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = []

    with TDB_CACHE.Get(subject) as tdb_context:
      attribute_index = TDBIndex(subject, self.INDEX_SUFFIX,
                                 context=tdb_context)
      for predicate in predicates:
        if predicate in attribute_index:
          for _, predicate, value, ts in self._GetTimestampsForAttribute(
              subject, predicate, timestamp, tdb_context):
            results.append((predicate, value, ts))

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
    timestamps = sorted(timestamp_index, reverse=True)
    results = []
    for matching_timestamp in timestamps:
      matching_timestamp = int(matching_timestamp)

      if (timestamp == self.ALL_TIMESTAMPS or
          (matching_timestamp >= timestamp[0] and
           matching_timestamp <= timestamp[1])):

        value = self._Decode(
            attribute, tdb_context.Get(subject, attribute, matching_timestamp))

        results.append((subject, attribute, value, int(matching_timestamp)))

    return results

  def Transaction(self, subject, lease_time=None, token=None):
    return Transaction(self, subject, lease_time=lease_time, token=token)


class Transaction(data_store.Transaction):
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
    self.store = store
    self.token = token
    self.subject = utils.SmartUnicode(subject)
    self.to_delete = []
    self.to_set = {}

    # Note that we have the luxury of real file locking here so this will block
    # until we obtain the lock.
    with TDB_CACHE.Get(self.subject) as tdb_context:
      locked_until = tdb_context.Get("lock")

      # This is currently locked by another thread.
      if locked_until and time.time() < float(locked_until):
        raise data_store.TransactionError("Subject %s is locked" % subject)

      # Subject is not locked, we take a lease on it.
      if lease_time is None:
        lease_time = config_lib.CONFIG["Datastore.transaction_timeout"]

      self.expires = time.time() + lease_time
      tdb_context.Put(self.expires, "lock")
      self.locked = True

  def CheckLease(self):
    return max(0, self.expires - time.time())

  def UpdateLease(self, duration):
    self.expires = time.time() + duration
    with TDB_CACHE.Get(self.subject) as tdb_context:
      self.expires = time.time() + duration
      tdb_context.Put(self.expires, "lock")

  def DeleteAttribute(self, predicate):
    self.to_delete.append(predicate)

  def Resolve(self, predicate):
    return self.store.Resolve(self.subject, predicate, token=self.token)

  def ResolveRegex(self, predicate_regex, timestamp=None):
    return self.store.ResolveRegex(self.subject, predicate_regex,
                                   token=self.token, timestamp=timestamp)

  def Set(self, predicate, value, timestamp=None, replace=None):
    if replace:
      self.to_delete.append(predicate)

    if timestamp is None:
      timestamp = int(time.time() * 1e6)

    self.to_set.setdefault(predicate, []).append((value, timestamp))

  def Abort(self):
    if self.locked:
      self._RemoveLock()

  def Commit(self):
    if self.locked:
      self.store.DeleteAttributes(self.subject, self.to_delete, sync=True,
                                  token=self.token)

      self.store.MultiSet(self.subject, self.to_set, token=self.token)
      self._RemoveLock()

  def _RemoveLock(self):
    with TDB_CACHE.Get(self.subject) as tdb_context:
      tdb_context.Delete("lock")

    self.locked = False

  def __del__(self):
    try:
      self.Abort()
    except Exception:  # This can raise on cleanup pylint: disable=broad-except
      pass
