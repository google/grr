#!/usr/bin/env python
"""A file based data store based on the SQLite database.

SQLite database files are created by taking the root of each AFF4 object.
"""


import itertools
import logging
import os
import re
import shutil
import stat
import tempfile
import thread
import threading
import time

import sqlite3

from grr import config
from grr.lib import utils
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server.data_stores import common

SQLITE_EXTENSION = ".sqlite"
SQLITE_TIMEOUT = 600.0
SQLITE_ISOLATION = "DEFERRED"
SQLITE_SUBJECT_SPEC = "TEXT"
SQLITE_DETECT_TYPES = 0
SQLITE_FACTORY = sqlite3.Connection
SQLITE_CACHED_STATEMENTS = 20
SQLITE_PAGE_SIZE = 1024


class SqliteConnectionCache(utils.FastStore):
  """A local cache of SQLite connection objects."""

  # Contents of the database that are written initially to a database file.
  template = None

  def _CreateModelDatabase(self):
    # Create model database file.
    try:
      if not os.path.isdir(self.root_path):
        os.makedirs(self.root_path)
    except OSError:
      # Directory was created after the if.
      pass
    fd, model = tempfile.mkstemp(dir=self.root_path)
    os.close(fd)
    conn = sqlite3.connect(model, SQLITE_TIMEOUT, SQLITE_DETECT_TYPES,
                           SQLITE_ISOLATION, False, SQLITE_FACTORY,
                           SQLITE_CACHED_STATEMENTS)
    cursor = conn.cursor()
    cursor.execute("PRAGMA count_changes = OFF")
    cursor.execute("PRAGMA cache_size = 10000")
    cursor.execute("PRAGMA page_size = %d" % SQLITE_PAGE_SIZE)
    # It is not possible to change page_size in WAL mode.
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    # The linter and pyformat can't agree on how to format this
    # pylint: disable=bad-continuation
    query = """CREATE TABLE IF NOT EXISTS tbl (
              subject %(subject)s NOT NULL,
              predicate TEXT NOT NULL,
              timestamp BIG INTEGER NOT NULL,
              value BLOB)""" % {
                  "subject": SQLITE_SUBJECT_SPEC
              }
    cursor.execute(query)
    query = """CREATE TABLE IF NOT EXISTS lock (
               subject %(subject)s PRIMARY KEY NOT NULL,
               expires BIG INTEGER NOT NULL,
               token BIG INTEGER NOT NULL)""" % {
                   "subject": SQLITE_SUBJECT_SPEC
               }
    cursor.execute(query)
    query = """CREATE TABLE IF NOT EXISTS statistics (
               name TEXT PRIMARY KEY NOT NULL,
               value BLOB)"""
    cursor.execute(query)
    query = """CREATE INDEX IF NOT EXISTS tbl_index
              ON tbl (subject, predicate, timestamp)"""
    # pylint: enable=bad-continuation
    cursor.execute(query)
    conn.commit()
    cursor.close()
    conn.close()
    with open(model, "rb") as model_file:
      self.template = model_file.read()
    os.unlink(model)

  def _WaitUntilReadable(self, target_path):
    start_time = time.time()
    # We will loop for 3 seconds until the file becomes readable.
    # If we cannot get read access to the file, we simply give up.
    while True:
      if os.access(target_path, os.R_OK):
        return
      # Sleep a little bit.
      time.sleep(0.001)
      if time.time() - start_time >= 3.0:
        raise IOError("database file %s cannot be read" % target_path)

  def _EnsureDatabaseExists(self, target_path):
    # Check if file already exists.
    if os.path.exists(target_path):
      self._WaitUntilReadable(target_path)
      return
    # Copy database file to a file that has no read permissions.
    umask_original = os.umask(0)
    write_permissions = stat.S_IWUSR | stat.S_IWGRP
    read_permissions = stat.S_IRUSR | stat.S_IRGRP
    try:
      fd = os.open(target_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                   write_permissions)
      os.close(fd)
      with open(target_path, "wb") as target_file:
        target_file.write(self.template)
      os.chmod(target_path, write_permissions | read_permissions)
    except OSError:
      # Failed to create file
      if os.path.exists(target_path):
        # Failed because file was created in the meantime (race condition)
        self._WaitUntilReadable(target_path)
      else:
        logging.error("Could not create database file. Make sure "
                      "GRR has write access to the target_path "
                      "directory to create the file '%s'", target_path)
    finally:
      os.umask(umask_original)

  def __init__(self, max_size, path):
    super(SqliteConnectionCache, self).__init__(max_size=max_size)
    self.root_path = path or config.CONFIG.Get("Datastore.location")
    self._CreateModelDatabase()
    self.RecreatePathing()

  def RecreatePathing(self, pathing=None):
    if not pathing:
      pathing = config.CONFIG.Get("Datastore.pathing")
    try:
      self.path_regexes = [re.compile(path) for path in pathing]
      self.pathing = pathing
    except re.error:
      raise data_store.Error("Invalid regular expression in Datastore.pathing")

  def RootPath(self):
    return self.root_path

  def KillObject(self, conn):
    conn.Close()

  @utils.Synchronized
  def Get(self, subject):
    """This will create the connection if needed so should not fail."""
    filename, directory = common.ResolveSubjectDestination(
        subject, self.path_regexes)
    key = common.MakeDestinationKey(directory, filename)
    try:
      return super(SqliteConnectionCache, self).Get(key)
    except KeyError:
      dirname = utils.JoinPath(self.root_path, directory)
      path = utils.JoinPath(dirname, filename) + SQLITE_EXTENSION
      dirname = utils.SmartStr(dirname)
      path = utils.SmartStr(path)

      # Make sure directory exists.
      if not os.path.isdir(dirname):
        try:
          os.makedirs(dirname)
        except OSError:
          pass
      self._EnsureDatabaseExists(path)
      connection = SqliteConnection(path)

      super(SqliteConnectionCache, self).Put(key, connection)

      return connection

  def GetPrefix(self, subject_prefix):
    """Return list of databases matching subject_prefix."""

    components = common.Components(subject_prefix)

    components = [common.ConvertStringToFilename(x) for x in components]
    path_prefix = utils.JoinPath(*components)
    if path_prefix == "/":
      path_prefix = ""
    for regex in self.path_regexes:
      result = common.EvaluatePrefix(path_prefix, regex)
      if result == "MATCH":
        yield self.Get(subject_prefix)
        return
      if result == "POSSIBLE":
        for conn in self.DatabasesByPath(path_prefix):
          yield conn
        return
    yield self.Get(subject_prefix)

  def DatabasesInDir(self, directory):
    """Returns a list of the database files in directory."""
    for (path, dirs, files) in os.walk(directory, topdown=True):
      dirs.sort()  # controls os.walk recurse order!
      files.sort()
      for f in files:
        if f.endswith(SQLITE_EXTENSION):
          f = f[:-len(SQLITE_EXTENSION)]
          yield utils.JoinPath(path, f)

  @utils.Synchronized
  def DatabasesByPath(self, path_prefix):
    """Yields connections which might contain data prefixed by path_prefix."""

    # We are looking for database files which start with this prefix, or
    # which could be extended to match this prefix.
    dir_prefix = utils.JoinPath(self.root_path, path_prefix)

    # Shortened path_prefix - we will shorten it one component at a time
    # checking directories for databases of interest as we go.
    shortened_path_prefix = path_prefix

    databases_found = set()
    while True:
      shortened_path = utils.JoinPath(self.root_path, shortened_path_prefix)
      if os.path.isdir(shortened_path):
        for db in self.DatabasesInDir(shortened_path):
          if db in databases_found:
            continue
          mod_db = db
          if mod_db == utils.JoinPath(self.root_path, "aff4"):
            mod_db = self.root_path
          if mod_db.startswith(dir_prefix) or dir_prefix.startswith(mod_db):
            databases_found.add(db)
            yield SqliteConnection(db + SQLITE_EXTENSION)
      if not shortened_path_prefix:
        break
      components = shortened_path_prefix.split(os.path.sep)
      shortened_path_prefix = utils.JoinPath(*(components[:-1]))
      if shortened_path_prefix == "/":
        shortened_path_prefix = ""


class SqliteConnection(object):
  """A wrapper around the raw SQLite connection."""

  def __init__(self, filename):
    self.filename = filename
    self.conn = sqlite3.connect(filename, SQLITE_TIMEOUT, SQLITE_DETECT_TYPES,
                                SQLITE_ISOLATION, False, SQLITE_FACTORY,
                                SQLITE_CACHED_STATEMENTS)
    self.conn.text_factory = str
    self.cursor = self.conn.cursor()
    self.Execute("PRAGMA synchronous = NORMAL")
    self.Execute("PRAGMA journal_mode = WAL")
    self.Execute("PRAGMA count_changes = OFF")
    self.Execute("PRAGMA cache_size = 10000")
    self.lock = threading.RLock()
    self.dirty = False
    # Counter for vacuuming purposes.
    self.deleted = 0
    self.next_vacuum_check = config.CONFIG["SqliteDatastore.vacuum_check"]

  def Filename(self):
    return self.filename

  def Execute(self, *args):
    try:
      return self.cursor.execute(*args)
    except sqlite3.DatabaseError:
      logging.exception("DB error in file: %s for query: %s", self.filename,
                        args)
      raise

  @utils.Synchronized
  def GetLock(self, subject):
    """Gets the expiration time for a given subject."""
    subject = utils.SmartStr(subject)
    query = "SELECT expires, token FROM lock WHERE subject = ?"
    args = (subject,)
    data = self.Execute(query, args).fetchone()

    if data:
      return data[0], data[1]
    else:
      return None, None

  @utils.Synchronized
  def SetLock(self, subject, expires, token):
    """Locks a subject."""
    subject = utils.SmartStr(subject)
    query = "INSERT OR REPLACE INTO lock VALUES(?, ?, ?)"
    args = (subject, expires, token)
    self.Execute(query, args)
    self.dirty = True

  @utils.Synchronized
  def RemoveLock(self, subject):
    """Removes the lock from a subject."""
    subject = utils.SmartStr(subject)
    query = "DELETE FROM lock WHERE subject = ?"
    args = (subject,)
    self.Execute(query, args)
    self.dirty = True

  @utils.Synchronized
  def GetNewestValue(self, subject, attribute):
    """Returns the newest value for subject/attribute."""
    subject = utils.SmartStr(subject)
    attribute = utils.SmartStr(attribute)
    query = """SELECT value, timestamp FROM tbl
               WHERE subject = ? AND predicate = ?
               ORDER BY timestamp DESC
               LIMIT 1"""
    args = (subject, attribute)
    data = self.Execute(query, args).fetchone()

    if data:
      return (data[0], data[1])
    else:
      return None

  @utils.Synchronized
  def GetNewestFromPrefix(self, subject, prefix, limit=None):
    """Returns the newest values for attributes that match 'prefix'.

    Args:
     subject: The subject.
     prefix: The attribute prefix.
     limit: The maximum number of records to return.

    Returns:
     A list of the form (attribute, value, timestamp).
    """
    pattern = prefix + "%"
    subject = utils.SmartStr(subject)
    query = """SELECT predicate, MAX(timestamp), value FROM tbl
               WHERE subject = ? AND predicate LIKE ?
               GROUP BY predicate"""

    if limit:
      query += " LIMIT ?"
      args = (subject, pattern, limit)
    else:
      args = (subject, pattern)

    # Reorder columns.
    data = self.Execute(query, args).fetchall()
    return [(pred, val, ts) for pred, ts, val in data]

  @utils.Synchronized
  def GetValuesFromPrefix(self, subject, prefix, start, end, limit=None):
    """Returns the values of the attributes that match 'prefix'.

    Args:
     subject: The subject.
     prefix: The attribute prefix.
     start: The start timestamp.
     end: The end timestamp.
     limit: The maximum number of values to return.

    Returns:
     A list of the form (attribute, value, timestamp).
    """
    pattern = prefix + "%"
    subject = utils.SmartStr(subject)
    query = """SELECT predicate, value, timestamp FROM tbl
               WHERE subject = ? AND predicate LIKE ?
                     AND timestamp >= ? AND timestamp <= ?
                     ORDER BY timestamp DESC"""
    if limit:
      query += " LIMIT ?"
      args = (subject, pattern, start, end, limit)
    else:
      args = (subject, pattern, start, end)

    data = self.Execute(query, args).fetchall()
    return data

  @utils.Synchronized
  def GetValues(self, subject, attribute, start, end, limit=None):
    """Returns the values of the attribute between 'start' and 'end'.

    Args:
     subject: The subject.
     attribute: The attribute.
     start: The start timestamp.
     end: The end timestamp.
     limit: The maximum number of values to return.

    Returns:
     A list of the form (value, timestamp).
    """
    subject = utils.SmartStr(subject)
    attribute = utils.SmartStr(attribute)
    query = """SELECT value, timestamp FROM tbl
               WHERE subject = ? AND predicate = ? AND
                     timestamp >= ? AND timestamp <= ?
               ORDER BY timestamp"""
    if limit:
      query += " LIMIT ?"
      args = (subject, attribute, start, end, limit)
    else:
      args = (subject, attribute, start, end)
    data = self.Execute(query, args).fetchall()
    return data

  def ScanAttributes(self,
                     subject_prefix,
                     attributes,
                     after_urn=None,
                     max_records=None):
    """Yields the values of attribute for a range of subjexts.

    Args:
     subject_prefix: Returns records for all subjects which begin with
       subject_prefix.
     attributes: A list of the attributes of interest.
     after_urn: If set, restrict to records which come after.
     max_records: The maximum number of values to return.

    Yields:
     Records of the form (subject, timestamp, value).
    """

    # A generator cannot really be synchronized, and in any case, this might be
    # long running. So we just make our own cursor.
    cursor = self.conn.cursor()
    cursor.execute("PRAGMA synchronous = OFF")
    cursor.execute("PRAGMA cache_size = 10000")

    query = """SELECT t1.subject, t1.predicate, t1.timestamp, t1.value
               FROM tbl AS t1,
                    (SELECT subject, predicate,
                            MAX(timestamp) AS max_ts FROM tbl
                       WHERE subject LIKE ? AND subject > ?
                         AND predicate in (%s)
                       GROUP BY subject, predicate) AS t2
               WHERE t1.subject = t2.subject AND
                     t1.timestamp = t2.max_ts AND
                     t1.predicate = t2.predicate
               ORDER BY t1.subject
            """ % ",".join("?" * len(attributes))
    subject_prefix = utils.SmartStr(subject_prefix)
    if after_urn:
      after_urn = utils.SmartStr(after_urn)
    else:
      after_urn = ""

    args = [subject_prefix + "%", after_urn] + attributes

    if max_records:
      query += " LIMIT ?"
      args.append(max_records * len(attributes))

    cursor.execute(query, args)

    for r in cursor:
      yield r

  @utils.Synchronized
  def DeleteAttribute(self, subject, attribute):
    """Deletes all values for the given subject/attribute."""
    subject = utils.SmartStr(subject)
    attribute = utils.SmartStr(attribute)
    query = "DELETE FROM tbl WHERE subject = ? AND predicate = ?"
    args = (subject, attribute)
    self.Execute(query, args)
    self.dirty = True
    self.deleted += self.cursor.rowcount

  @utils.Synchronized
  def SetAttribute(self, subject, attribute, value, timestamp):
    """Sets subject's attribute value with the given timestamp."""
    subject = utils.SmartStr(subject)
    attribute = utils.SmartStr(attribute)
    query = "INSERT INTO tbl VALUES (?, ?, ?, ?)"
    args = (subject, attribute, timestamp, value)
    self.Execute(query, args)
    self.dirty = True
    self.deleted = max(0, self.deleted - self.cursor.rowcount)

  @utils.Synchronized
  def DeleteAttributeRange(self, subject, attribute, start, end):
    """Deletes all values of a attribute within the range [start, end]."""
    subject = utils.SmartStr(subject)
    attribute = utils.SmartStr(attribute)
    query = """DELETE FROM tbl WHERE subject = ? AND predicate = ?
               AND timestamp >= ? AND timestamp <= ?"""
    args = (subject, attribute, int(start), int(end))
    self.Execute(query, args)
    self.dirty = True
    self.deleted += self.cursor.rowcount

  @utils.Synchronized
  def DeleteSubject(self, subject):
    """Deletes subject information."""
    subject = utils.SmartStr(subject)
    query = "DELETE FROM tbl WHERE subject = ?"
    args = (subject,)
    self.Execute(query, args)
    self.dirty = True
    self.deleted += self.cursor.rowcount

  def PrettyPrint(self):
    """Print the SQLite database."""
    query = "SELECT subject, predicate, timestamp, value FROM tbl"
    for sub, pred, ts, val in self.Execute(query):
      print "(%s, %s, %s) = %s" % (sub, pred, ts, val)
    print "---------------------------------"

  def __enter__(self):
    self.lock.acquire()
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if self.dirty:
      self.Flush()
    self.dirty = False
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

    if self.deleted >= self.next_vacuum_check:
      if self._NeedsVacuum() and not self._HasRecentVacuum():
        self.Vacuum()
        self.deleted = 0
        self.next_vacuum_check = max(
            config.CONFIG["SqliteDatastore.vacuum_check"],
            self.next_vacuum_check / 2)
      else:
        # Back-off a bit.
        self.next_vacuum_check *= 2

  def _NeedsVacuum(self):
    """Check if there are too many free pages."""
    pages_result = self.Execute("PRAGMA page_count").fetchone()
    if not pages_result:
      return False
    pages = int(pages_result[0])
    vacuum_minsize = config.CONFIG["SqliteDatastore.vacuum_minsize"]
    if pages * SQLITE_PAGE_SIZE < vacuum_minsize:
      # Too few pages to worry about.
      return False
    free_pages_result = self.Execute("PRAGMA freelist_count").fetchone()
    if not free_pages_result:
      return False
    free_pages = int(free_pages_result[0])
    # Return true if ratio of free pages is high enough.
    vacuum_ratio = config.CONFIG["SqliteDatastore.vacuum_ratio"]
    return 100.0 * float(free_pages) / float(pages) >= vacuum_ratio

  def _HasRecentVacuum(self):
    """Check if a vacuum operation has been performed recently."""
    query = "SELECT value FROM statistics WHERE name = 'vacuum_time'"
    data = self.Execute(query).fetchone()
    if not data:
      return False
    try:
      last_vacuum = int(str(data[0]))
      vacuum_frequency = config.CONFIG["SqliteDatastore.vacuum_frequency"]
      return time.time() - last_vacuum < vacuum_frequency
    except ValueError:
      # Should not happen.
      return False

  def Vacuum(self):
    """Vacuum the database."""
    now = time.time()

    logging.debug("Vacuuming database.")

    self.Execute("VACUUM")
    # Write time of the vacuum operation.
    query = "INSERT OR REPLACE INTO statistics VALUES('vacuum_time', ?)"
    args = (str(int(now)),)
    self.Execute(query, args)
    try:
      self.conn.commit()
    except sqlite3.OperationalError:
      pass

  @utils.Synchronized
  def Close(self):
    """Flush and close connection."""
    if self.dirty:
      self.Flush()
    self.cursor.close()
    self.conn.close()
    self.conn = None
    self.cursor = None


class SqliteDataStore(data_store.DataStore):
  """A file based data store using the SQLite database."""

  # A cache of SQLite connections.
  cache = None

  def __init__(self, path=None):
    self._CalculateAttributeStorageTypes()
    super(SqliteDataStore, self).__init__()
    self.cache = SqliteConnectionCache(
        config.CONFIG["SqliteDatastore.connection_cache_size"], path)

  def RecreatePathing(self, pathing):
    self.cache.RecreatePathing(pathing)

  def _CalculateAttributeStorageTypes(self):
    """Build a mapping between column names and types."""
    self._attribute_types = {}

    for attribute in aff4.Attribute.PREDICATES.values():
      self._attribute_types[attribute.predicate] = (
          attribute.attribute_type.data_store_type)

  def _Encode(self, value):
    """Encode the value for the attribute."""
    try:
      return buffer(value.SerializeToString())
    except AttributeError:
      if isinstance(value, (int, long)):
        return value
      else:
        # Types "string" and "bytes" are stored as strings here.
        return buffer(utils.SmartStr(value))

  def _Decode(self, attribute, value):
    required_type = self._attribute_types.get(attribute, "bytes")
    if isinstance(value, buffer):
      value = str(value)
    if required_type in ("integer", "unsigned_integer"):
      return int(value)
    elif required_type == "string":
      return utils.SmartUnicode(value)
    else:
      return value

  def MultiSet(self,
               subject,
               values,
               timestamp=None,
               replace=True,
               sync=True,
               to_delete=None):
    """Set multiple values at once."""
    # All operations are synchronized.
    _ = sync
    if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
      timestamp = time.time() * 1000000

    to_delete = set(to_delete or [])

    with self.cache.Get(subject) as sqlite_connection:
      if replace:
        to_delete.update(values.keys())

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
          value = self._Encode(v)
          sqlite_connection.SetAttribute(subject, attribute, value,
                                         element_timestamp)

  def DeleteAttributes(self,
                       subject,
                       attributes,
                       start=None,
                       end=None,
                       sync=True):
    """Remove some attributes from a subject."""
    _ = sync

    if isinstance(attributes, basestring):
      raise ValueError(
          "String passed to DeleteAttributes (non string iterable expected).")

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
          end = (2**63) - 1  # sys.maxint
        for attribute in list(attributes):
          sqlite_connection.DeleteAttributeRange(subject, attribute, start, end)

  def DeleteSubject(self, subject, sync=False):
    _ = sync

    with self.cache.Get(subject) as sqlite_connection:
      sqlite_connection.DeleteSubject(subject)

  def MultiResolvePrefix(self,
                         subjects,
                         attribute_prefix,
                         timestamp=None,
                         limit=None):
    """Result multiple subjects using one or more attribute prefixes."""
    result = {}

    remaining_limit = limit
    for subject in subjects:
      values = self.ResolvePrefix(
          subject, attribute_prefix, timestamp=timestamp, limit=remaining_limit)

      if values:
        if limit:
          if len(values) >= remaining_limit:
            result[subject] = values[:remaining_limit]
            return result.iteritems()
          remaining_limit -= len(values)
        result[subject] = values

    return result.iteritems()

  def _GetStartEndTimestamp(self, timestamp):
    if timestamp == self.ALL_TIMESTAMPS or timestamp is None:
      return 0, (2**63) - 1
    elif timestamp == self.NEWEST_TIMESTAMP:
      return -1, -1
    elif isinstance(timestamp, int):
      return timestamp, timestamp
    else:
      try:
        start, end = timestamp
        return int(start), int(end)
      except ValueError:
        return timestamp, timestamp

  def ResolvePrefix(self, subject, attribute_prefix, timestamp=None,
                    limit=None):
    """Resolve all attributes for a subject matching a prefix."""
    if isinstance(attribute_prefix, str):
      attribute_prefix = [attribute_prefix]

    start, end = self._GetStartEndTimestamp(timestamp)

    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = {}

    with self.cache.Get(subject) as sqlite_connection:
      for prefix in attribute_prefix:
        if limit and len(results) >= limit:
          break
        if timestamp == self.NEWEST_TIMESTAMP:
          data = sqlite_connection.GetNewestFromPrefix(subject, prefix)
          for attribute, value, ts in data:
            value = self._Decode(attribute, value)
            results.setdefault(attribute, []).append((value, ts))
        else:
          data = sqlite_connection.GetValuesFromPrefix(subject, prefix, start,
                                                       end)
          for attribute, value, ts in data:
            value = self._Decode(attribute, value)
            results.setdefault(attribute, []).append((value, ts))

      res = []
      for attribute, values in sorted(results.items()):
        values.sort(key=lambda x: x[1], reverse=True)
        for value, ts in values:
          res.append((attribute, value, ts))
        if limit and len(res) >= limit:
          return res
      return res

  def _GroupSubjects(self, collection, max_records):
    """Group results by subject and convert to ScanAttribute output format."""
    record_count = 0
    current_subject = None
    current_results = {}
    for subject, attribute, timestamp, value in collection:
      if not current_subject:
        current_subject = subject
      if current_subject != subject:
        yield (current_subject, current_results)
        record_count += 1
        if max_records and record_count >= max_records:
          return
        current_results = {}
        current_subject = subject
      current_results[attribute] = (timestamp, self._Decode(attribute, value))
    if current_results:
      yield (current_subject, current_results)

  def ScanAttributes(self,
                     subject_prefix,
                     attributes,
                     after_urn=None,
                     max_records=None,
                     relaxed_order=False):
    subject_prefix = self._CleanSubjectPrefix(subject_prefix)
    after_urn = self._CleanAfterURN(after_urn, subject_prefix)

    connection_iter = self.cache.GetPrefix(subject_prefix)
    if relaxed_order:
      for sqlite_connection in connection_iter:
        with sqlite_connection:
          for r in self._GroupSubjects(
              list(
                  sqlite_connection.ScanAttributes(
                      subject_prefix,
                      attributes,
                      after_urn=after_urn,
                      max_records=max_records)), max_records):
            yield r
      return
    first_connections = []
    try:
      first_connections.append(connection_iter.next())
      first_connections.append(connection_iter.next())
    except StopIteration:
      pass
    if not first_connections:
      return
    if len(first_connections) == 1:
      with first_connections[0] as sqlite_connection:
        for r in self._GroupSubjects(
            list(
                sqlite_connection.ScanAttributes(
                    subject_prefix,
                    attributes,
                    after_urn=after_urn,
                    max_records=max_records)), max_records):
          yield r
      return
    raw_results = []
    for sqlite_connection in itertools.chain(first_connections,
                                             connection_iter):
      for record in sqlite_connection.ScanAttributes(
          subject_prefix,
          attributes,
          after_urn=after_urn,
          max_records=max_records):
        raw_results.append(record)
    for r in self._GroupSubjects(
        sorted(raw_results, key=lambda x: x[0]), max_records):
      yield r

  def ResolveMulti(self, subject, attributes, timestamp=None, limit=None):
    """Resolve multiple attributes for a subject."""
    # Holds all the attributes which matched. Keys are attribute names, values
    # are lists of timestamped data.
    results = []
    start, end = self._GetStartEndTimestamp(timestamp)

    with self.cache.Get(subject) as sqlite_connection:
      for attribute in attributes:
        if timestamp == self.NEWEST_TIMESTAMP:
          ret = sqlite_connection.GetNewestValue(subject, attribute)
          if ret:
            value, ts = ret
            value = self._Decode(attribute, value)
            results.append((attribute, value, ts))
            if limit and len(results) >= limit:
              break
        else:
          new_limit = limit
          if new_limit:
            new_limit = limit - len(results)
          values = sqlite_connection.GetValues(subject, attribute, start, end,
                                               new_limit)
          for value, ts in values:
            value = self._Decode(attribute, value)
            results.append((attribute, value, ts))
        if limit and len(results) >= limit:
          break

    return results

  def DumpDatabase(self):
    for _, sql_connection in self.cache:
      sql_connection.PrettyPrint()

  def Size(self):
    root_path = self.Location()
    if not os.path.exists(root_path):
      # Database does not exist yet.
      return 0
    if not os.path.isdir(root_path):
      # Database should be a directory.
      raise IOError(
          "expected SQLite directory %s to be a directory" % root_path)
    size, _ = common.DatabaseDirectorySize(root_path, self.FileExtension())
    return size

  @staticmethod
  def FileExtension():
    return SQLITE_EXTENSION

  def Location(self):
    """Get location of the data store."""
    return self.cache.RootPath()

  def Flush(self):
    pass

  def DBSubjectLock(self, subject, lease_time=None):
    return SqliteDBSubjectLock(self, subject, lease_time=lease_time)

  @classmethod
  def SetupTestDB(cls):
    super(SqliteDataStore, cls).SetupTestDB()
    temp_dir = tempfile.mkdtemp()
    db = SqliteDataStore(os.path.join(temp_dir, "sqlite_test"))
    db.temp_dir = temp_dir
    return db

  def ClearTestDB(self):
    root_path = self.cache.RootPath()
    if (not hasattr(self, "temp_dir") or
        not root_path.startswith(self.temp_dir)):
      raise ValueError(
          "No test DB found, using root %s" % self.cache.RootPath())
    shutil.rmtree(root_path)
    os.makedirs(root_path)
    # This closes all SQLite connections in the cache. If we don't
    # close them, subsequent access to SQLite files with the same name
    # might fail randomly.
    self.cache.Flush()
    self.cache = SqliteConnectionCache(
        config.CONFIG["SqliteDatastore.connection_cache_size"], root_path)

  def DestroyTestDB(self):
    if (not hasattr(self, "temp_dir") or
        not self.cache.RootPath().startswith(self.temp_dir)):
      raise ValueError(
          "No test DB found, using root %s" % self.cache.RootPath())
    try:
      shutil.rmtree(self.temp_dir)
    except OSError:
      pass


class SqliteDBSubjectLock(data_store.DBSubjectLock):
  """The SQLite data store transaction object.

  We only ensure that two simultaneous locks can not be held on the
  same subject.

  This means that the first thread which grabs the lock is considered the owner
  of the transaction. Any subsequent transactions on the same subject will fail
  immediately with data_store.DBSubjectLockError. NOTE that it is still possible
  to manipulate the row without a transaction - this is a design feature!

  A lock is considered expired after a certain time.
  """
  locked = False

  def _Acquire(self, lease_time):
    self.lock_token = thread.get_ident()
    sqlite_connection = self.store.cache.Get(self.subject)

    # We first check if there is a lock on the subject.
    # Next we set our lease time and lock_token as identification.
    with sqlite_connection:
      locked_until, stored_token = sqlite_connection.GetLock(self.subject)

      # This is currently locked by another thread.
      if locked_until and (time.time() * 1e6) < float(locked_until):
        raise data_store.DBSubjectLockError(
            "Subject %s is locked" % self.subject)

      # Subject is not locked, we take a lease on it.
      self.expires = int((time.time() + lease_time) * 1e6)
      sqlite_connection.SetLock(self.subject, self.expires, self.lock_token)

    # TODO(user): This shouldn't really be necessary, and seems fragile. We
    # should be able to use an UPDATE WHERE lock_expiration < now inside a
    # transaction and check that we changed one row.
    # Check if the lock stuck. If the stored token is not ours
    # then probably someone was able to grab it before us.
    locked_until, stored_token = sqlite_connection.GetLock(self.subject)
    if stored_token != self.lock_token:
      raise data_store.DBSubjectLockError(
          "Unable to lock subject %s" % self.subject)

    self.locked = True

  def UpdateLease(self, duration):
    with self.store.cache.Get(self.subject) as sqlite_connection:
      self.expires = int((time.time() + duration) * 1e6)
      sqlite_connection.SetLock(self.subject, self.expires, self.lock_token)

  def Release(self):
    if self.locked:
      with self.store.cache.Get(self.subject) as sqlite_connection:
        sqlite_connection.RemoveLock(self.subject)
        self.locked = False
