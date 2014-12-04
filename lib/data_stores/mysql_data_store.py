#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""An implementation of a data store based on mysql."""


import Queue
import threading
import thread
import time
import MySQLdb

from MySQLdb import cursors

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.data_stores import common

from collections import defaultdict

# pylint: disable=nonstandard-exception
class Error(data_store.Error):
  """Base class for all exceptions in this module."""
# pylint: enable=nonstandard-exception


class MySQLConnection(object):
  """A Class to manage MySQL database connections."""

  def __init__(self, queue=None):
    self.queue = queue
    try:
      self._MakeConnection(database=config_lib.CONFIG["Mysql.database_name"])
    except MySQLdb.OperationalError as e:
      # Database does not exist
      if "Unknown database" in str(e):
        dbh = self._MakeConnection()
        cursor = dbh.cursor()
        cursor.execute("Create database `%s`" %
                       config_lib.CONFIG["Mysql.database_name"])
        dbh.commit()

        self._MakeConnection(database=config_lib.CONFIG["Mysql.database_name"])
      else:
        raise

  def _MakeConnection(self, database=""):
    try:
      connection_args = dict(
          user=config_lib.CONFIG["Mysql.database_username"],
          db=database, charset="utf8",
          passwd=config_lib.CONFIG["Mysql.database_password"],
          cursorclass=cursors.DictCursor)
      if config_lib.CONFIG["Mysql.host"]:
        connection_args["host"] = config_lib.CONFIG["Mysql.host"]
      if config_lib.CONFIG["Mysql.port"]:
        connection_args["port"] = config_lib.CONFIG["Mysql.port"]

      self.dbh = MySQLdb.connect(**connection_args)
      self.cursor = self.dbh.cursor()
      self.cursor.connection.autocommit(False)

      return self.dbh
    except MySQLdb.OperationalError as e:
      # This is a fatal error, we just raise the top level exception here.
      if "Access denied" in str(e):
        raise Error(str(e))
      raise

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    try:
      self.Commit()
    finally:
      # Return ourselves to the pool queue.
      if self.queue:
        self.queue.put(self)

  def Commit(self):
    self.dbh.commit()

  def Execute(self, *args):
    retries = 5

    for i in range(1, retries):
      try:
        self.cursor.execute(*args)
        return self.cursor.fetchall()
      except MySQLdb.Error:
        try:
          self._MakeConnection(database=config_lib.CONFIG["Mysql.database_name"])
        except MySQLdb.OperationalError:
          pass

    try:
      self.cursor.execute(*args)
      return self.cursor.fetchall()
    except MySQLdb.Error:
      raise

class ConnectionPool(object):
  """A pool of connections to the mysql server.

  Usage:

  with data_store.DB.pool.GetConnection() as connection:
    connection.Execute(.....)
  """

  def __init__(self, pool_size=5):
    self.connections = Queue.Queue()
    for _ in range(pool_size):
      self.connections.put(MySQLConnection(self.connections))

  def GetConnection(self):
    return self.connections.get(block=True)


class MySQLDataStore(data_store.DataStore):
  """A mysql based data store."""

  POOL = None
  LOCKS_TABLE = "locks"
  SYSTEM_TABLE = "system"

  def __init__(self):
    # Use the global connection pool.
    if MySQLDataStore.POOL is None:
      MySQLDataStore.POOL = ConnectionPool()
    self.pool = self.POOL

    self._CalculateAttributeStorageTypes()
    self.database_name = config_lib.CONFIG["Mysql.database_name"]
    self.lock = threading.Lock()

    super(MySQLDataStore, self).__init__()

  def Initialize(self):
    try:
      self._ExecuteQuery("desc `%s`" % self.SYSTEM_TABLE)
    except MySQLdb.Error:
      self.RecreateTables()

  def DropTables(self):
    #Drop all existing tables
    rows = self._ExecuteQuery("select table_name from information_schema.tables where table_schema='%s'" % self.database_name)
    for row in rows:
      self._ExecuteQuery("drop table `%s`" % row["table_name"])

  def RecreateTables(self):
    """Drops the tables and creates a new ones."""
    self.DropTables()

    #Create the system table
    self._CreateTable(self.SYSTEM_TABLE)

    # Create the locking table
    self._CreateTable(self.LOCKS_TABLE, schema="LOCKS")

  def Transaction(self, subject, lease_time=None, token=None):
    return MySQLTransaction(self, subject, lease_time=lease_time, token=token)

  def Size(self):
    query = ("SELECT table_schema, Sum(data_length + index_length) `size` "
             "FROM information_schema.tables "
             "WHERE table_schema = \"%s\" GROUP by table_schema" %
             self.database_name)

    result = self._ExecuteQuery(query, [])
    if len(result) != 1:
      return -1
    return int(result[0]["size"])

  def DeleteAttributes(self, subject, attributes, start=None, end=None, sync=None, token=None):
    """Remove some attributes from a subject."""
    _ = sync  # Unused

    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    if not attributes:
      return

    for attribute in attributes:
      timestamp = self._MakeTimestamp(start, end)
      action = "delete "
      query, args = self._BuildQuery(action, subject, str(attribute), timestamp)
      self._ExecuteQuery(query, args)

  def DeleteAttributesRegex(self, subject, regexes, token=None):
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    for regex in regexes:
      action = "delete "
      query, args = self._BuildQuery(action, subject, regex, is_regex=True)
      self._ExecuteQuery(query, args)

  def DeleteSubject(self, subject, token=None, sync=False):
    _ = sync
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    action = "delete "
    query, args = self._BuildQuery(action, subject)
    self._ExecuteQuery(query, args)

  def ResolveMulti(self, subject, predicates, token=None, timestamp=None):
    """Resolves multiple predicates at once for one subject."""
    self.security_manager.CheckDataStoreAccess(
        token, [subject], self.GetRequiredResolveAccess(predicates))

    for predicate in predicates:
      action = "select * "
      query, args = self._BuildQuery(action, subject, predicate, timestamp)
      result = self._ExecuteQuery(query, args)

      for row in result:
        attribute = row["attribute"]
        value = self._DecodeValue(attribute, row["value"])

        yield attribute, value, rdfvalue.RDFDatetime(row["timestamp"])

  def MultiResolveRegex(self, subjects, predicate_regex, token=None, timestamp=None, limit=None):
    """Result multiple subjects using one or more predicate regexps."""
    self.security_manager.CheckDataStoreAccess(
        token, subjects, self.GetRequiredResolveAccess(predicate_regex))

    result = {}

    for subject in subjects:
      values = self._ResolveRegex(subject, predicate_regex, token=token,
                                 timestamp=timestamp, limit=limit)

      if values:
        result[subject] = values
        if limit:
          limit -= len(values)

      if limit and limit <= 0:
        break

    return result.iteritems()

  def MultiSet(self, subject, values, timestamp=None, token=None, replace=True, sync=True, to_delete=None):
    """Set multiple predicates' values for this subject in one operation."""
    _ = sync  # Unused

    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    to_delete = set(to_delete or [])

    if timestamp is None:
      timestamp = time.time() * 1e6

    # Prepare a bulk insert operation.
    subject = utils.SmartUnicode(subject)
    to_set = []

    # Build a document for each unique timestamp.
    for attribute, sequence in values.items():
      for value in sequence:
        entry_timestamp = None

        if isinstance(value, tuple):
          value, entry_timestamp = value

        if entry_timestamp is None:
          entry_timestamp = timestamp

        predicate = utils.SmartUnicode(attribute)
        prefix = predicate.split(":", 1)[0]

        # Replacing means to delete all versions of the attribute first.
        if replace:
          to_delete.add(attribute)

        data = self._EncodeValue(value)
        to_set.extend(
            [subject, int(entry_timestamp), predicate, prefix, data])

    if to_delete:
      self.DeleteAttributes(subject, to_delete, token=token)

    if to_set:
      self._ResolveInsert(subject, to_set)

  def _ResolveInsert(self, subject, values):
      #Insert subject into locks table for tracking if not present
      query, args = self._BuildInsert(subject)
      self._ExecuteQuery(query, args)

      #Insert new data
      query, args = self._BuildInsert(subject, values)
      self._ExecuteQuery(query, args)

  def _BuildInsert(self, subject, values=None):
    args = []
    if values:
      query = ("insert into `%s` (hash, timestamp, attribute, prefix, "
             "value) values " %
             self.SYSTEM_TABLE)

      nr_items = len(values) / 5
      query += ", ".join(["(md5(%s), %s, %s, %s, %s)"] * nr_items)
      args = values
    else:
      query = "insert ignore into `%s` (hash, subject, lock_expiration, lock_owner) values (md5(%%s), %%s, 0, 0)" % self.LOCKS_TABLE
      args = [subject, subject]

    return (query, args)

  def _ResolveRegex(self, subject, predicate_regex, token=None, timestamp=None, limit=None):
    if limit and limit == 0:
      return []

    if isinstance(predicate_regex, str):
      predicate_regex = [predicate_regex]

    result = []
    seen = set()

    for regex in predicate_regex:
      action = "select * "
      query, args = self._BuildQuery(action, subject, regex, timestamp, limit, is_regex=True)
      rows = self._ExecuteQuery(query, args)

      for row in rows:
        attribute = row["attribute"]

        # Only record the latest results. This is suboptimal since it always
        # returns all the results from the db. Can we do better with better SQL?
        if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
          if (subject, attribute) in seen:
            continue
          else:
            seen.add((subject, attribute))

        value = self._DecodeValue(attribute, row["value"])
        result.append((attribute, value, row["timestamp"]))
        if limit:
          limit -= 1

    return result

  def _CalculateAttributeStorageTypes(self):
    """Build a mapping between column names and types."""
    self.attribute_types = {}

    for attribute in aff4.Attribute.PREDICATES.values():
      self.attribute_types[attribute.predicate] = (
          attribute.attribute_type.data_store_type)

  def _EncodeValue(self, value):
    """Encode the value for the attribute."""
    if hasattr(value, "SerializeToString"):
      return buffer(value.SerializeToString())
    else:
      # Types "string" and "bytes" are stored as strings here.
      return buffer(utils.SmartStr(value))

  def _DecodeValue(self, attribute, value):
    required_type = self.attribute_types.get(attribute, "bytes")
    if isinstance(value, buffer):
      value = str(value)
    if required_type in ("integer", "unsigned_integer"):
      return int(value)
    elif required_type == "string":
      return utils.SmartUnicode(value)
    else:
      return value

  def _BuildQuery(self, action, subject, predicate=None, timestamp=None, limit=None, is_regex=False):
    """Build the query to be executed"""
    args = []
    query = action

    #Select table
    query += "from `%s` " % self.SYSTEM_TABLE

    #Add subject
    query += "where hash=md5(%s) "
    args.append(subject)

    #Add predicate, splitting to use prefix when able and dropping regexes that would match all rows with that prefix
    if predicate:
      parts = predicate.split(":", 1)
      if len(parts) > 1:
        if is_regex:
          query += "and prefix=(%s) "
          args.append(parts[0])
          if parts[1] != ".*" and parts[1] != ".+":
            query += "and attribute rlike %s "
            args.append(predicate)
        else:
          query += "and attribute=(%s) "
          args.append(predicate)
      else:
        if is_regex:
          if parts[0] != ".*" and parts[0] != ".+":
            query += "and attribute rlike %s "
            args.append(predicate)
        else:
          query += "and attribute=(%s) "
          args.append(predicate)

      #Continue to add criteria if predicate is present
      #Add timestamp if in use
      if isinstance(timestamp, (tuple, list)):
        query += " and timestamp >= %s and timestamp <= %s "
        args.append(int(timestamp[0]))
        args.append(int(timestamp[1]))

      if action.startswith("select"):
        #Always order the results
        query += "order by timestamp desc "

        if limit:
          query += "limit %s" % int(limit)

    return (query, args)

  def _ExecuteQuery(self, *args):
    """Get connection from pool and execute query"""
    with self.pool.GetConnection() as cursor:
      result = cursor.Execute(*args)
    return result

  def _MakeTimestamp(self, start, end):
    """Create a timestamp using a start and end time.
    This will return None rather than creating a timestamp for all time"""
    if start or end:
      mysql_unsigned_bigint_max = 18446744073709551615
      start = int(start or 0)
      end = int(end or mysql_unsigned_bigint_max)
      if start == 0 and end == mysql_unsigned_bigint_max:
        return None
      else:
        return (start, end)

  def _CreateTable(self, table_name, schema="STANDARD"):
    if schema == "STANDARD":
      self._ExecuteQuery("""
CREATE TABLE IF NOT EXISTS `%s` (
  hash BINARY(32) DEFAULT NULL,
  prefix VARCHAR(16) CHARACTER SET utf8 DEFAULT NULL,
  attribute VARCHAR(1024) CHARACTER SET utf8 DEFAULT NULL,
  timestamp BIGINT(22) UNSIGNED DEFAULT NULL,
  value LONGBLOB NULL,
  KEY `master` (`hash`,`attribute`(255),`timestamp`),
  KEY `alternate` (`hash`,`prefix`,`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT ='Table representing AFF4 objects';
""" % table_name)

    elif schema == "LOCKS":
      self._ExecuteQuery("""
CREATE TABLE IF NOT EXISTS `%s` (
  hash BINARY(32) PRIMARY KEY NOT NULL,
  subject TEXT CHARACTER SET utf8 NULL,
  lock_owner BIGINT(22) UNSIGNED DEFAULT NULL,
  lock_expiration BIGINT(22) UNSIGNED DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT ='Table representing locks on subjects';
""" % table_name)

class MySQLTransaction(data_store.CommonTransaction):
  """The Mysql data store transaction object.

  This object does not aim to ensure ACID like consistently. We only ensure that
  two simultaneous locks can not be held on the same AFF4 subject.

  This means that the first thread which grabs the lock is considered the owner
  of the transaction. Any subsequent transactions on the same subject will fail
  immediately with data_store.TransactionError.

  A lock is considered expired after a certain time.
  """

  def __init__(self, store, subject, lease_time=None, token=None):
    """Ensure we can take a lock on this subject."""
    super(MySQLTransaction, self).__init__(store, subject,
                                           lease_time=lease_time, token=token)
    if lease_time is None:
      lease_time = config_lib.CONFIG["Datastore.transaction_timeout"]

    self.lock_token = thread.get_ident()
    self.lock_time = lease_time
    self.expires_lock = int((time.time() + self.lock_time) * 1e6)

    # This will take over the lock if the lock is too old.
    query = "update `%s` set lock_expiration=%%s, lock_owner=%%s where hash=md5(%%s) and (lock_expiration < %%s)" % self.store.LOCKS_TABLE
    args = [self.expires_lock, self.lock_token, subject, time.time() * 1e6]
    store._ExecuteQuery(query, args)

    self.CheckForLock()

  def UpdateLease(self, lease_time):
    self.expires_lock = int((time.time() + lease_time) * 1e6)

    # This will take over the lock if the lock is too old.
    query = "update `%s` set lock_expiration=%%s, lock_owner=%%s where hash=md5(%%s)" % self.store.LOCKS_TABLE
    args = [self.expires_lock, self.lock_token, self.subject]
    self.store._ExecuteQuery(query, args)

  def CheckLease(self):
    return max(0, self.expires_lock/1e6 - time.time())

  def CheckForLock(self):
    """Checks that the lock has stuck."""

    query = "select * from `%s` where hash=md5(%%s)" % self.store.LOCKS_TABLE
    args = [self.subject]
    rows = self.store._ExecuteQuery(query, args)
    for row in rows:

      # We own this lock now.
      if row["lock_expiration"] == self.expires_lock and row["lock_owner"] == self.lock_token:
        return

      # Someone else owns this lock.
      else:
        raise data_store.TransactionError("Subject %s is locked" % self.subject)

    # If we get here the row does not exist:
    query = "insert ignore into `%s` set lock_expiration=%%s, lock_owner=%%s, hash=md5(%%s), subject=%%s " % self.store.LOCKS_TABLE
    args = [self.expires_lock, self.lock_token, self.subject, self.subject]
    self.store._ExecuteQuery(query, args)

    self.CheckForLock()

  def Abort(self):
    self._RemoveLock()

  def Commit(self):
    super(MySQLTransaction, self).Commit()
    self._RemoveLock()

  def _RemoveLock(self):
    # Remove the lock on the document. Note that this only resets the lock if
    # we actually hold it (lock_expiration == self.expires_lock and lock_owner = self.lock_token).

    query = "update `%s` set lock_expiration=0, lock_owner=0 where lock_expiration=%%s and lock_owner=%%s and hash=md5(%%s) " % self.store.LOCKS_TABLE
    args = [self.expires_lock, self.lock_token, self.subject]
    self.store._ExecuteQuery(query, args)

