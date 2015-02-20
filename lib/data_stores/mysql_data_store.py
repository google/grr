#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""An implementation of a data store based on mysql."""


import Queue
import threading
import time
import MySQLdb
from MySQLdb import cursors

from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import utils


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
    try:
      self.cursor.execute(*args)
      return self.cursor.fetchall()
    except MySQLdb.Error:
      self._MakeConnection(database=config_lib.CONFIG["Mysql.database_name"])
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

  def __init__(self):
    # Use the global connection pool.
    if MySQLDataStore.POOL is None:
      MySQLDataStore.POOL = ConnectionPool()

    self.pool = self.POOL

    self.lock = threading.Lock()
    self.to_set = []
    self.table_name = config_lib.CONFIG["Mysql.table_name"]
    super(MySQLDataStore, self).__init__()

  def Initialize(self):
    with self.pool.GetConnection() as connection:
      try:
        connection.Execute("desc `%s`" % self.table_name)
      except MySQLdb.Error:
        self.RecreateDataBase()

  def DropDatabase(self):
    """Drops the database table."""
    with self.pool.GetConnection() as connection:
      try:
        connection.Execute("drop table `%s`" % self.table_name)
      except MySQLdb.OperationalError:
        pass

  def RecreateDataBase(self):
    """Drops the table and creates a new one."""
    self.DropDatabase()
    with self.pool.GetConnection() as connection:
      connection.Execute("""
  CREATE TABLE IF NOT EXISTS `%s` (
    hash BINARY(32) DEFAULT NULL,
    subject VARCHAR(4096) CHARACTER SET utf8 DEFAULT NULL,
    prefix VARCHAR(256) CHARACTER SET utf8 DEFAULT NULL,
    attribute VARCHAR(4096) CHARACTER SET utf8 DEFAULT NULL,
    age BIGINT(22) UNSIGNED DEFAULT NULL,
    value_string TEXT CHARACTER SET utf8 NULL,
    value_binary LONGBLOB NULL,
    value_integer BIGINT(22) UNSIGNED DEFAULT NULL,

    KEY `hash` (`hash`),
    KEY `prefix` (`prefix`)
  ) ENGINE=MyISAM DEFAULT CHARSET=utf8 COMMENT ='Table representing AFF4 objects';
  """ % config_lib.CONFIG["Mysql.table_name"])
      connection.Execute("CREATE INDEX attribute ON `%s` (attribute(300));" %
                         config_lib.CONFIG["Mysql.table_name"])

  def DeleteAttributes(self, subject, attributes, start=None, end=None,
                       sync=True, token=None):
    """Remove some attributes from a subject."""
    _ = sync  # Unused

    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    if not attributes:
      return

    with self.pool.GetConnection() as cursor:
      query = ("delete from `%s` where hash=md5(%%s) and "
               "subject=%%s and attribute in (%s) " % (
                   self.table_name,
                   ",".join(["%s"] * len(attributes))))
      args = [subject, subject] + list(attributes)

      if start or end:
        query += " and age >= %s and age <= %s"
        args.append(int(start or 0))
        mysql_unsigned_bigint_max = 18446744073709551615
        if end is None:
          end = mysql_unsigned_bigint_max
        args.append(int(end))

      cursor.Execute(query, args)

  def DeleteSubject(self, subject, sync=False, token=None):
    _ = sync
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    with self.pool.GetConnection() as cursor:
      query = ("delete from `%s` where hash=md5(%%s) and subject=%%s  " %
               self.table_name)
      args = [subject, subject]

      cursor.Execute(query, args)

  def Flush(self):
    with self.lock:
      to_set = self.to_set
      self.to_set = []

    self._MultiSet(to_set)

  def Size(self):
    database_name = config_lib.CONFIG["Mysql.database_name"]
    query = ("SELECT table_schema, Sum(data_length + index_length) `size` "
             "FROM information_schema.tables "
             "WHERE table_schema = \"%s\" GROUP by table_schema" %
             database_name)
    with self.pool.GetConnection() as cursor:
      result = cursor.Execute(query, [])
      if len(result) != 1:
        return -1
      return int(result[0]["size"])

  def Escape(self, string):
    """Escape the string so it can be interpolated into an sql statement."""
    # This needs to come from a connection object so it is escaped according to
    # the current charset:
    with self.pool.GetConnection() as cursor:
      return cursor.dbh.escape(string)

  def ResolveMulti(self, subject, attributes, timestamp=None, limit=None,
                   token=None):
    """Resolves multiple attributes at once for one subject."""
    self.security_manager.CheckDataStoreAccess(
        token, [subject], self.GetRequiredResolveAccess(attributes))

    with self.pool.GetConnection() as cursor:
      query = ("select * from `%s` where hash = md5(%%s) and "
               "subject = %%s  and attribute in (%s) " % (
                   self.table_name,
                   ",".join(["%s"] * len(attributes)),
               ))

      args = [subject, subject] + attributes[:]

      query += self._TimestampToQuery(timestamp, args)

      if limit:
        query += " LIMIT %d" % limit

      result = cursor.Execute(query, args)

    for row in result:
      subject = row["subject"]
      value = self.DecodeValue(row)

      yield row["attribute"], value, rdfvalue.RDFDatetime(row["age"])

  def _TimestampToQuery(self, timestamp, args):
    """Convert the timestamp to a query fragment and add args."""
    if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
      query = " order by age desc "
    elif timestamp == self.ALL_TIMESTAMPS:
      query = " order by age desc "
    elif isinstance(timestamp, (tuple, list)):
      query = " and age >= %s and age <= %s order by age desc "
      args.append(int(timestamp[0]))
      args.append(int(timestamp[1]))

    return query

  def MultiResolveRegex(self, subjects, attribute_regex, timestamp=None,
                        limit=None, token=None):
    self.security_manager.CheckDataStoreAccess(
        token, subjects, self.GetRequiredResolveAccess(attribute_regex))

    if not subjects:
      return {}

    with self.pool.GetConnection() as cursor:
      query = "select * from `%s` where hash in (%s) and subject in (%s) " % (
          self.table_name, ",".join(["md5(%s)"] * len(subjects)),
          ",".join(["%s"] * len(subjects)),
      )

      # Allow users to specify a single string here.
      if isinstance(attribute_regex, basestring):
        attribute_regex = [attribute_regex]

      query += "and (" + " or ".join(
          ["attribute rlike %s"] * len(attribute_regex)) + ")"

      args = list(subjects) + list(subjects) + attribute_regex

      query += self._TimestampToQuery(timestamp, args)

      seen = set()
      result = {}

      remaining_limit = limit
      for row in cursor.Execute(query, args):
        subject = row["subject"]
        value = self.DecodeValue(row)

        # Only record the latest results. This is suboptimal since it always
        # returns all the results from the db. Can we do better with better SQL?
        if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
          if (row["attribute"], row["subject"]) in seen:
            continue
          else:
            seen.add((row["attribute"], row["subject"]))

        result.setdefault(subject, []).append((row["attribute"], value,
                                               row["age"]))
        if remaining_limit:
          remaining_limit -= 1
          if remaining_limit == 0:
            break

      return result.iteritems()

  def MultiSet(self, subject, values, timestamp=None, replace=True,
               sync=True, to_delete=None, token=None):
    """Set multiple attributes' values for this subject in one operation."""
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

        attribute = utils.SmartUnicode(attribute)
        prefix = attribute.split(":", 1)[0]

        # Replacing means to delete all versions of the attribute first.
        if replace:
          to_delete.add(attribute)

        to_set.extend(
            [subject, subject, int(entry_timestamp), attribute, prefix] +
            self._Encode(attribute, value))

    if to_delete:
      self.DeleteAttributes(subject, to_delete, token=token)

    if to_set:
      if sync:
        self._MultiSet(to_set)
      else:
        with self.lock:
          self.to_set.extend(to_set)

  def _MultiSet(self, values):
    if not values:
      return
    query = ("insert into `%s` (hash, subject, age, attribute, prefix, "
             "value_string, value_integer, value_binary) values " %
             self.table_name)

    nr_items = len(values) / 8
    query += ", ".join(["(md5(%s), %s, %s, %s, %s, %s, %s, %s)"] * nr_items)

    with self.pool.GetConnection() as cursor:
      cursor.Execute(query, values)

  def _Encode(self, attribute, value):
    """Return a list encoding this value."""
    try:
      if isinstance(value, int):
        return [None, value, None]
      elif isinstance(value, unicode):
        return [value, None, None]
      elif attribute.attribute_type.data_store_type in (
          "integer", "unsigned_integer"):
        return [None, int(value), None]
      elif attribute.attribute_type.data_store_type == "string":
        return [utils.SmartUnicode(value), None, None]
      elif attribute.attribute_type.data_store_type == "bytes":
        return [None, None, utils.SmartStr(value)]
    except AttributeError:
      try:
        return [None, None, value.SerializeToString()]
      except AttributeError:
        return [None, None, utils.SmartStr(value)]

  def EncodeValue(self, attribute, value):
    """Returns the value encoded into the correct fields."""
    result = {}
    try:
      if isinstance(value, int):
        result["value_integer"] = value
      elif isinstance(value, unicode):
        result["value_string"] = value
      elif attribute.attribute_type.data_store_type in (
          "integer", "unsigned_integer"):
        result["value_integer"] = int(value)
      elif attribute.attribute_type.data_store_type == "string":
        result["value_string"] = utils.SmartUnicode(value)
      elif attribute.attribute_type.data_store_type == "bytes":
        result["value_binary"] = utils.SmartStr(value)
    except AttributeError:
      try:
        result["value_binary"] = value.SerializeToString()
      except AttributeError:
        result["value_binary"] = utils.SmartStr(value)

    return result

  def DecodeValue(self, row):
    """Decode the value from the row object."""
    value = row["value_string"]
    if value is None:
      value = row["value_integer"]

    if value is None:
      value = row["value_binary"]

    return value

  def Transaction(self, subject, lease_time=None, token=None):
    return MySQLTransaction(self, subject, lease_time=lease_time, token=token)


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

    self.lock_time = lease_time
    self.table_name = store.table_name
    with store.pool.GetConnection() as connection:
      self.expires_lock = int((time.time() + self.lock_time) * 1e6)

      # This will take over the lock if the lock is too old.
      connection.Execute(
          "update `%s` set value_integer=%%s where "
          "attribute='transaction' and subject=%%s and hash=md5(%%s) and "
          "(value_integer < %%s)" % self.table_name,
          (self.expires_lock, subject, subject, time.time() * 1e6))

      self.CheckForLock(connection, subject)

  def UpdateLease(self, lease_time):
    self.expires_lock = int((time.time() + lease_time) * 1e6)
    with self.store.pool.GetConnection() as connection:
      # This will take over the lock if the lock is too old.
      connection.Execute(
          "update `%s` set value_integer=%%s where "
          "attribute='transaction' and subject=%%s and hash=md5(%%s)" %
          self.table_name, (self.expires_lock, self.subject, self.subject))

  def CheckLease(self):
    return max(0, self.expires_lock / 1e6 - time.time())

  def CheckForLock(self, connection, subject):
    """Checks that the lock has stuck."""

    for row in connection.Execute(
        "select * from `%s` where subject=%%s and hash=md5(%%s) and "
        "attribute='transaction'" % self.table_name, (subject, subject)):

      # We own this lock now.
      if row["value_integer"] == self.expires_lock:
        return

      # Someone else owns this lock.
      else:
        raise data_store.TransactionError("Subject %s is locked" % subject)

    # If we get here the row does not exist:
    connection.Execute(
        "insert ignore into `%s` set value_integer=%%s, "
        "attribute='transaction', subject=%%s, hash=md5(%%s) " %
        self.table_name, (self.expires_lock, self.subject, self.subject))

    self.CheckForLock(connection, subject)

  def Abort(self):
    self._RemoveLock()

  def Commit(self):
    super(MySQLTransaction, self).Commit()
    self._RemoveLock()

  def _RemoveLock(self):
    # Remove the lock on the document. Note that this only resets the lock if
    # we actually hold it (value_integer == self.expires_lock).
    with self.store.pool.GetConnection() as connection:
      connection.Execute(
          "update `%s` set value_integer=0 where "
          "attribute='transaction' and value_integer=%%s and hash=md5(%%s) and "
          "subject=%%s" % self.table_name,
          (self.expires_lock, self.subject, self.subject))
