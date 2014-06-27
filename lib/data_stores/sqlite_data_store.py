#!/usr/bin/env python
"""A file based data store based on the SQLite database.

SQLite database files are created by taking the root of each AFF4 object.
"""



import os
import re
import tempfile
import threading
import time

import sqlite3

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import utils
from grr.lib.data_stores import common

SQLITE_EXTENSION = "sqlite"


class SqliteConnectionCache(utils.FastStore):
  """A local cache of SQLite connection objects."""

  # Contents of the database that are written initially to a database file.
  template = None

  def _CreateModelDatabase(self):
    # Create model database file.
    root_path = config_lib.CONFIG["SqliteDatastore.root_path"]
    if not os.path.isdir(root_path):
      os.makedirs(root_path)
    fd, model = tempfile.mkstemp(dir=root_path)
    os.close(fd)
    conn = sqlite3.connect(model, 5.0, sqlite3.PARSE_DECLTYPES |
                           sqlite3.PARSE_COLNAMES,
                           "EXCLUSIVE", False)
    cursor = conn.cursor()
    query = """CREATE TABLE IF NOT EXISTS tbl (
              subject VARCHAR(512) NOT NULL,
              predicate VARCHAR(512) NOT NULL,
              timestamp BIG INTEGER NOT NULL,
              value BLOB)"""
    cursor.execute(query)
    query = """CREATE TABLE IF NOT EXISTS lock (
               subject VARCHAR(512) PRIMARY KEY NOT NULL,
               expires BIG INTEGER NOT NULL)"""
    cursor.execute(query)
    query = "CREATE INDEX tbl_index ON tbl (subject, predicate, timestamp)"
    cursor.execute(query)
    cursor.execute("PRAGMA journal_mode = MEMORY")
    cursor.execute("PRAGMA count_changes = OFF")
    cursor.execute("PRAGMA cache_size = 10000")
    # Make sure the database is fully written to disk.
    cursor.execute("PRAGMA synchronous = ON")
    conn.commit()
    cursor.close()
    conn.close()
    with open(model, "rb") as model_file:
      self.template = model_file.read()
    os.unlink(model)

  def _CopyModelDatabase(self, target_path):
    with open(target_path, "wb") as target_file:
      target_file.write(self.template)

  def __init__(self, max_size):
    super(SqliteConnectionCache, self).__init__(max_size)
    self._CreateModelDatabase()

  def KillObject(self, conn):
    conn.Close()

  @utils.Synchronized
  def Get(self, subject):
    """This will create the connection if needed so should not fail."""
    subject = common.ResolveSubjectDestination(subject)

    try:
      return super(SqliteConnectionCache, self).Get(subject)
    except KeyError:
      path = utils.JoinPath(config_lib.CONFIG["SqliteDatastore.root_path"],
                            common.ConvertStringToFilename(subject))
      filename = path + "." + SQLITE_EXTENSION
      assert os.path.isdir(os.path.dirname(filename))
      self._CopyModelDatabase(filename)
      # Open database.
      connection = SqliteConnection(filename)

      super(SqliteConnectionCache, self).Put(subject, connection)

      return connection


def SqliteRegexpFunction(expr, item):
  reg = re.compile(expr)
  return reg.search(item) is not None


class SqliteConnection(object):
  """A wrapper around the raw SQLite connection."""

  def __init__(self, filename):
    self.filename = filename
    self.conn = sqlite3.connect(filename, 5.0, sqlite3.PARSE_DECLTYPES |
                                sqlite3.PARSE_COLNAMES, "EXCLUSIVE", False)
    self.conn.text_factory = sqlite3.OptimizedUnicode
    self.conn.create_function("REGEXP", 2, SqliteRegexpFunction)
    self.cursor = self.conn.cursor()
    self.cursor.execute("PRAGMA synchronous = OFF")
    self.cursor.execute("PRAGMA journal_mode = MEMORY")
    self.cursor.execute("PRAGMA count_changes = OFF")
    self.cursor.execute("PRAGMA cache_size = 10000")
    self.lock = threading.RLock()

  def Filename(self):
    return self.filename

  @utils.Synchronized
  def GetLock(self, subject):
    """Gets the expiration time for a given subject."""
    subject = utils.SmartUnicode(subject)
    query = "SELECT expires FROM lock WHERE subject = ?"
    data = self.cursor.execute(query, (subject,)).fetchone()

    if data:
      return data[0]
    else:
      return None

  @utils.Synchronized
  def SetLock(self, subject, expires):
    """Locks a subject."""
    subject = utils.SmartUnicode(subject)
    query = "INSERT OR REPLACE INTO lock VALUES(?, ?)"
    self.cursor.execute(query, (subject, expires))

  @utils.Synchronized
  def RemoveLock(self, subject):
    """Removes the lock from a subject."""
    subject = utils.SmartUnicode(subject)
    query = "DELETE FROM lock WHERE subject = ?"
    self.cursor.execute(query, (subject,))

  @utils.Synchronized
  def GetNewestValue(self, subject, predicate):
    """Returns the newest value for subject/predicate."""
    subject = utils.SmartUnicode(subject)
    predicate = utils.SmartUnicode(predicate)
    query = """SELECT value, timestamp FROM tbl
               WHERE subject = ? AND predicate = ?
               ORDER BY timestamp DESC
               LIMIT 1"""
    data = self.cursor.execute(query, (subject, predicate)).fetchone()

    if data:
      return (data[0], data[1])
    else:
      return None

  @utils.Synchronized
  def GetNewestFromRegex(self, subject, regex, limit=None):
    """Returns the newest values for predicates that match 'regex'.

    Args:
     subject: The subject.
     regex: The predicate regex.
     limit: The maximum number of records to return.

    Returns:
     A list of the form (predicate, value, timestamp).
    """
    subject = utils.SmartUnicode(subject)
    query = """SELECT predicate, MAX(timestamp), value FROM tbl
               WHERE subject = ? AND predicate REGEXP ?
               GROUP BY predicate"""

    if limit:
      query += " LIMIT ?"
      args = (subject, regex, limit)
    else:
      args = (subject, regex)

    # Reorder columns.
    data = self.cursor.execute(query, args).fetchall()
    return [(pred, val, ts) for pred, ts, val in data]

  @utils.Synchronized
  def GetValuesFromRegex(self, subject, regex, start, end, limit=None):
    """Returns the values of the predicates that match 'regex'.

    Args:
     subject: The subject.
     regex: The predicate regex.
     start: The start timestamp.
     end: The end timestamp.
     limit: The maximum number of values to return.

    Returns:
     A list of the form (predicate, value, timestamp).
    """
    subject = utils.SmartUnicode(subject)
    query = """SELECT predicate, value, timestamp FROM tbl
               WHERE subject = ? AND predicate REGEXP ?
                     AND timestamp >= ? AND timestamp <= ?"""
    if limit:
      query += " LIMIT ?"
      args = (subject, regex, start, end, limit)
    else:
      args = (subject, regex, start, end)

    data = self.cursor.execute(query, args).fetchall()
    return data

  @utils.Synchronized
  def GetValues(self, subject, predicate, start, end, limit=None):
    """Returns the values of the predicate between 'start' and 'end'.

    Args:
     subject: The subject.
     predicate: The predicate.
     start: The start timestamp.
     end: The end timestamp.
     limit: The maximum number of values to return.

    Returns:
     A list of the form (value, timestamp).
    """
    subject = utils.SmartUnicode(subject)
    predicate = utils.SmartUnicode(predicate)
    query = """SELECT value, timestamp FROM tbl
               WHERE subject = ? AND predicate = ? AND
                     timestamp >= ? AND timestamp <= ?
               ORDER BY timestamp"""
    if limit:
      query += " LIMIT ?"
      args = (subject, predicate, start, end, limit)
    else:
      args = (subject, predicate, start, end)
    data = self.cursor.execute(query, args).fetchall()
    return data

  @utils.Synchronized
  def DeleteAttribute(self, subject, predicate):
    """Deletes all values for the given subject/predicate."""
    subject = utils.SmartUnicode(subject)
    predicate = utils.SmartUnicode(predicate)
    query = "DELETE FROM tbl WHERE subject = ? AND predicate = ?"
    self.cursor.execute(query, (subject, predicate))

  @utils.Synchronized
  def SetAttribute(self, subject, predicate, value, timestamp):
    """Sets subject's predicate value with the given timestamp."""
    subject = utils.SmartUnicode(subject)
    predicate = utils.SmartUnicode(predicate)
    query = "INSERT INTO tbl VALUES (?, ?, ?, ?)"
    self.cursor.execute(query, (subject, predicate, timestamp, value))

  @utils.Synchronized
  def DeleteAttributeRange(self, subject, predicate, start, end):
    """Deletes all values of a predicate within the range [start, end]."""
    subject = utils.SmartUnicode(subject)
    predicate = utils.SmartUnicode(predicate)
    query = """DELETE FROM tbl WHERE subject = ? AND predicate = ?
               AND timestamp >= ? AND timestamp <= ?"""
    self.cursor.execute(query, (subject, predicate, start, end))

  @utils.Synchronized
  def DeleteAttributesRegex(self, subject, regex):
    """Deletes all predicates that match 'regex'."""
    subject = utils.SmartUnicode(subject)
    query = "DELETE FROM tbl WHERE subject = ? AND predicate REGEXP ?"
    self.cursor.execute(query, (subject, regex))

  @utils.Synchronized
  def DeleteSubject(self, subject):
    """Deletes subject information."""
    subject = utils.SmartUnicode(subject)
    query = "DELETE FROM tbl WHERE subject = ?"
    self.cursor.execute(query, (subject,))

  def PrettyPrint(self):
    """Print the SQLite database."""
    query = "SELECT subject, predicate, timestamp, value FROM tbl"
    for sub, pred, ts, val in self.cursor.execute(query):
      print "(%s, %s, %s) = %s" % (sub, pred, ts, val)
    print "---------------------------------"

  def __enter__(self):
    self.lock.acquire()
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.lock.release()

  @utils.Synchronized
  def Flush(self):
    """Flush the database."""
    if self.conn:
      try:
        self.conn.commit()
      except sqlite3.OperationalError:
        # Transaction not active.
        pass

  @utils.Synchronized
  def Close(self):
    """Flush and close connection."""
    self.Flush()
    self.cursor.close()
    self.conn.close()
    self.conn = None
    self.cursor = None


class SqliteDataStore(data_store.DataStore):
  """A file based data store using the SQLite database."""

  # A cache of SQLite connections.
  cache = None

  def __init__(self):
    self._CalculateAttributeStorageTypes()
    super(SqliteDataStore, self).__init__()
    self.cache = SqliteConnectionCache(1000)

  def _CalculateAttributeStorageTypes(self):
    """Build a mapping between column names and types."""
    self._attribute_types = {}

    for attribute in aff4.Attribute.PREDICATES.values():
      self._attribute_types[attribute.predicate] = (
          attribute.attribute_type.data_store_type)

  def _Encode(self, attribute, value):
    """Encode the value for the attribute."""
    if isinstance(value, int):
      return str(value)
    elif isinstance(value, unicode):
      return value
    else:
      try:
        if attribute.attribute_type.data_store_type in (
            "integer", "unsigned_integer"):
          return str(value)
        elif attribute.attribute_type.data_store_type == "string":
          return utils.SmartUnicode(value)
        elif attribute.attribute_type.data_store_type == "bytes":
          return utils.SmartUnicode(value)
      except AttributeError:
        try:
          return utils.SmartUnicode(value.SerializeToString())
        except AttributeError:
          return utils.SmartUnicode(value)

  def _Decode(self, attribute, value):
    required_type = self._attribute_types.get(attribute, "bytes")
    if required_type in ("integer", "unsigned_integer"):
      return int(value)
    elif required_type == "unicode":
      return value
    elif required_type == "string":
      return value
    elif required_type == "bytes":
      return utils.SmartStr(value)
    else:
      return utils.SmartStr(value)

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

    with self.cache.Get(subject) as sqlite_connection:
      if replace:
        to_delete.extend(values.keys())

      # Delete attribute if needed.
      if to_delete:
        for attribute in to_delete:
          sqlite_connection.DeleteAttribute(subject, attribute)

      for attribute, seq in values.items():
        for v in seq:
          element_timestamp = None
          if isinstance(v, (list, tuple)):
            v, element_timestamp = v
          if element_timestamp is None:
            element_timestamp = timestamp

          element_timestamp = long(element_timestamp)
          value = self._Encode(attribute, v)
          sqlite_connection.SetAttribute(subject, attribute, value,
                                         element_timestamp)

  def DeleteAttributes(self, subject, attributes, start=None, end=None,
                       sync=None, token=None):
    """Remove some attributes from a subject."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    _ = sync

    with self.cache.Get(subject) as sqlite_connection:
      if start is None and end is None:
        # This is done when we delete all attributes at once without
        # caring about timestamps.
        for attribute in list(attributes):
          sqlite_connection.DeleteAttribute(subject, attribute)
      else:
        # This code path is taken when we have a timestamp range.
        start = start or 0
        if end is None:
          end = (2 ** 63) - 1  # sys.maxint
        for attribute in list(attributes):
          sqlite_connection.DeleteAttributeRange(subject, attribute, start,
                                                 end)

  def DeleteAttributesRegex(self, subject, regexes, token=None):
    """Deletes attributes using one or more regular expressions."""
    with self.cache.Get(subject) as sqlite_connection:
      for regex in regexes:
        sqlite_connection.DeleteAttributesRegex(subject, regex)

  def DeleteSubject(self, subject, token=None):
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    with self.cache.Get(subject) as sqlite_connection:
      sqlite_connection.DeleteSubject(subject)

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

  def _GetStartEndTimestamp(self, timestamp):
    if timestamp == self.ALL_TIMESTAMPS or timestamp is None:
      return 0, (2 ** 63) - 1
    elif timestamp == self.NEWEST_TIMESTAMP:
      return -1, -1
    else:
      try:
        start, end = timestamp
        return start, end
      except ValueError:
        return timestamp, timestamp

  def ResolveRegex(self, subject, predicate_regex, token=None,
                   timestamp=None, limit=None):
    """Resolve all predicates for a subject matching a regex."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")

    if limit and limit == 0:
      return []

    if isinstance(predicate_regex, str):
      predicate_regex = [predicate_regex]

    start, end = self._GetStartEndTimestamp(timestamp)

    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = []

    with self.cache.Get(subject) as sqlite_connection:
      for regex in predicate_regex:
        nr_results = len(results)
        if limit and nr_results >= limit:
          break
        new_limit = limit
        if new_limit:
          new_limit -= nr_results
        if timestamp == self.NEWEST_TIMESTAMP:
          data = sqlite_connection.GetNewestFromRegex(subject, regex, new_limit)
          for predicate, value, ts in data:
            value = self._Decode(predicate, value)
            results.append((predicate, value, ts))
        else:
          data = sqlite_connection.GetValuesFromRegex(subject, regex, start,
                                                      end, new_limit)
          for predicate, value, ts in data:
            value = self._Decode(predicate, value)
            results.append((predicate, value, ts))

      return results

  def ResolveMulti(self, subject, predicates, token=None,
                   timestamp=None, limit=None):
    """Resolve all predicates for a subject matching a regex."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")

    if limit and limit == 0:
      return []

    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = []
    start, end = self._GetStartEndTimestamp(timestamp)

    with self.cache.Get(subject) as sqlite_connection:
      for predicate in predicates:
        if timestamp == self.NEWEST_TIMESTAMP:
          ret = sqlite_connection.GetNewestValue(subject, predicate)
          if ret:
            value, ts = ret
            value = self._Decode(predicate, value)
            results.append((predicate, value, ts))
            if limit and len(results) >= limit:
              break
        else:
          new_limit = limit
          if new_limit:
            new_limit = limit - len(results)
          values = sqlite_connection.GetValues(subject, predicate, start, end,
                                               new_limit)
          for value, ts in values:
            value = self._Decode(predicate, value)
            results.append((predicate, value, ts))
        if limit and len(results) >= limit:
          break

    return results

  def DumpDatabase(self, token=None):
    self.security_manager.CheckDataStoreAccess(token, [], "r")
    for _, sql_connection in self.cache:
      sql_connection.PrettyPrint()

  def Flush(self):
    if not self.cache:
      return
    for _, sql_connection in self.cache:
      sql_connection.Flush()

  def Size(self):
    root_path = config_lib.CONFIG["SqliteDatastore.root_path"]
    if not os.path.exists(root_path):
      # Database does not exist yet.
      return 0
    if not os.path.isdir(root_path):
      # Database should be a directory.
      raise IOError("expected SQLite directory %s to be a directory" %
                    root_path)
    total_size = os.path.getsize(root_path)
    for subject in os.listdir(root_path):
      subject_path = os.path.join(root_path, subject)
      if os.path.isfile(subject_path):
        total_size += os.path.getsize(subject_path)
      else:
        # Only files are allowed in this directory.
        raise IOError("only regular files are allowed in SQLite directory %s" %
                      root_path)
    return total_size

  def Transaction(self, subject, lease_time=None, token=None):
    return SqliteTransaction(self, subject, lease_time=lease_time, token=token)


class SqliteTransaction(data_store.CommonTransaction):
  """The SQLite data store transaction object.

  We only ensure that two simultaneous locks can not be held on the
  same subject.

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
    super(SqliteTransaction, self).__init__(store, utils.SmartUnicode(subject),
                                            lease_time=lease_time, token=token)

    # Note that we have the luxury of real file locking here so this will block
    # until we obtain the lock.
    with store.cache.Get(self.subject) as sqlite_connection:
      locked_until = sqlite_connection.GetLock(subject)

      # This is currently locked by another thread.
      if locked_until and time.time() < float(locked_until):
        raise data_store.TransactionError("Subject %s is locked" % subject)

      # Subject is not locked, we take a lease on it.
      if lease_time is None:
        lease_time = config_lib.CONFIG["Datastore.transaction_timeout"]

      self.expires = time.time() + lease_time
      sqlite_connection.SetLock(subject, self.expires)
      self.locked = True

  def CheckLease(self):
    return max(0, self.expires - time.time())

  def UpdateLease(self, duration):
    self.expires = time.time() + duration
    with self.store.cache.Get(self.subject) as sqlite_connection:
      self.expires = time.time() + duration
      sqlite_connection.SetLock(self.subject, self.expires)

  def Abort(self):
    if self.locked:
      self._RemoveLock()

  def Commit(self):
    if self.locked:
      super(SqliteTransaction, self).Commit()
      self._RemoveLock()

  def _RemoveLock(self):
    with self.store.cache.Get(self.subject) as sqlite_connection:
      sqlite_connection.RemoveLock(self.subject)

    self.locked = False
