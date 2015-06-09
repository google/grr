#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""An implementation of a data store based on mysql."""


import logging
import Queue
import re
import thread
import threading
import time


import MySQLdb
from MySQLdb import cursors

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import utils


# pylint: disable=nonstandard-exception
class Error(data_store.Error):
  """Base class for all exceptions in this module."""
# pylint: enable=nonstandard-exception


class SafeQueue(Queue.Queue):
  """Queue with RLock instead of Lock."""

  def __init__(self, maxsize=0):
    # Queue is an old-style class so we can't use super()
    Queue.Queue.__init__(self, maxsize=maxsize)
    # This code is far from ideal as the Queue implementation makes it difficult
    # to replace Lock with RLock. Here we override the variables that use
    # self.mutex in the super class __init__.  If Queue.Queue.__init__
    # implementation changes this code could break.
    self.mutex = threading.RLock()
    self.not_empty = threading.Condition(self.mutex)
    self.not_full = threading.Condition(self.mutex)
    self.all_tasks_done = threading.Condition(self.mutex)


class MySQLConnection(object):
  """A Class to manage MySQL database connections."""

  def __init__(self):
    database = config_lib.CONFIG["Mysql.database_name"]
    try:
      self.dbh = self._MakeConnection(database=database)
      self.cursor = self.dbh.cursor()
      self.cursor.connection.autocommit(True)
    except MySQLdb.OperationalError as e:
      # Database does not exist
      if "Unknown database" in str(e):
        dbh = self._MakeConnection()
        cursor = dbh.cursor()
        cursor.connection.autocommit(True)
        cursor.execute("Create database `%s`" % database)
        cursor.close()
        dbh.close()

        self.dbh = self._MakeConnection(database=database)
        self.cursor = self.dbh.cursor()
        self.cursor.connection.autocommit(True)
      else:
        raise

  def _MakeConnection(self, database=""):
    try:
      connection_args = dict(
          user=config_lib.CONFIG["Mysql.database_username"],
          db=database, charset="utf8",
          passwd=config_lib.CONFIG["Mysql.database_password"],
          cursorclass=cursors.DictCursor,
          host=config_lib.CONFIG["Mysql.host"],
          port=config_lib.CONFIG["Mysql.port"])

      dbh = MySQLdb.connect(**connection_args)
      return dbh
    except MySQLdb.OperationalError as e:
      # This is a fatal error, we just raise the top level exception here.
      if "Access denied" in str(e):
        raise Error(str(e))
      raise


class ConnectionPool(object):
  """A pool of connections to the mysql server.

  Uses unfinished_tasks to track the number of open connections.
  """

  def __init__(self):
    self.connections = SafeQueue()
    self.pool_max_size = int(config_lib.CONFIG["Mysql.conn_pool_max"])
    self.pool_min_size = int(config_lib.CONFIG["Mysql.conn_pool_min"])
    for _ in range(self.pool_min_size):
      self.connections.put(MySQLConnection())

  def GetConnection(self):
    if self.connections.empty() and (self.connections.unfinished_tasks <
                                     self.pool_max_size):
      self.connections.put(MySQLConnection())
    connection = self.connections.get(block=True)
    return connection

  def PutConnection(self, connection):
    # If the pool is low on connections return this connection to the pool
    # Reduce the connection count and then put will increment again if the
    # connection is returned to the pool

    if self.connections.qsize() < self.pool_min_size:
      self.connections.task_done()
      self.connections.put(connection)
    else:
      self.DropConnection(connection)

  def DropConnection(self, connection):
    """Attempt to cleanly drop the connection."""
    try:
      connection.cursor.close()
    except MySQLdb.Error:
      pass

    try:
      connection.dbh.close()
    except MySQLdb.Error:
      pass
    # If a connection is going to be dropped we remove it from the count
    # of open connections.
    self.connections.task_done()


class MySQLAdvancedDataStore(data_store.DataStore):
  """A mysql based data store."""

  POOL = None

  def __init__(self):
    # Use the global connection pool.
    if MySQLAdvancedDataStore.POOL is None:
      MySQLAdvancedDataStore.POOL = ConnectionPool()
    self.pool = self.POOL

    self.to_insert = []
    self._CalculateAttributeStorageTypes()
    self.database_name = config_lib.CONFIG["Mysql.database_name"]
    self.lock = threading.Lock()

    super(MySQLAdvancedDataStore, self).__init__()

  def Initialize(self):
    try:
      self.ExecuteQuery("desc `aff4`")
    except MySQLdb.Error:
      self.RecreateTables()

  def DropTables(self):
    """Drop all existing tables."""

    rows = self.ExecuteQuery(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='%s'" % self.database_name)
    for row in rows:
      self.ExecuteQuery("DROP TABLE `%s`" % row["table_name"])

  def RecreateTables(self):
    """Drops the tables and creates a new ones."""
    self.DropTables()

    self._CreateTables()

  def Transaction(self, subject, lease_time=None, token=None):
    return MySQLTransaction(self, subject, lease_time=lease_time, token=token)

  def Size(self):
    query = ("SELECT table_schema, Sum(data_length + index_length) `size` "
             "FROM information_schema.tables "
             "WHERE table_schema = \"%s\" GROUP by table_schema" %
             self.database_name)

    result = self.ExecuteQuery(query, [])
    if len(result) != 1:
      return -1
    return int(result[0]["size"])

  def DeleteAttributes(self, subject, attributes, start=None, end=None,
                       sync=True, token=None):
    """Remove some attributes from a subject."""
    _ = sync  # Unused
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    if not attributes:
      return

    for attribute in attributes:
      timestamp = self._MakeTimestamp(start, end)
      attribute = utils.SmartUnicode(attribute)
      transaction = self._BuildDelete(subject, attribute, timestamp)
      self._ExecuteTransaction(transaction)

  def DeleteSubject(self, subject, sync=False, token=None):
    _ = sync
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    transaction = self._BuildDelete(subject)
    self._ExecuteTransaction(transaction)

  def ResolveMulti(self, subject, attributes, timestamp=None, limit=None,
                   token=None):
    """Resolves multiple attributes at once for one subject."""
    self.security_manager.CheckDataStoreAccess(
        token, [subject], self.GetRequiredResolveAccess(attributes))

    for attribute in attributes:
      query, args = self._BuildQuery(subject, attribute, timestamp, limit)
      result = self.ExecuteQuery(query, args)

      for row in result:
        value = self._Decode(attribute, row["value"])

        yield attribute, value, rdfvalue.RDFDatetime(row["timestamp"])

      if limit:
        limit -= len(result)

      if limit is not None and limit <= 0:
        break

  def MultiResolveRegex(self, subjects, attribute_regex, timestamp=None,
                        limit=None, token=None):
    """Result multiple subjects using one or more attribute regexps."""
    result = {}

    for subject in subjects:
      values = self.ResolveRegex(subject, attribute_regex, token=token,
                                 timestamp=timestamp, limit=limit)

      if values:
        result[subject] = values
        if limit:
          limit -= len(values)

      if limit is not None and limit <= 0:
        break

    return result.iteritems()

  def ResolveRegex(self, subject, attribute_regex, timestamp=None, limit=None,
                   token=None):
    """ResolveRegex."""
    self.security_manager.CheckDataStoreAccess(
        token, [subject], self.GetRequiredResolveAccess(attribute_regex))

    if isinstance(attribute_regex, basestring):
      attribute_regex = [attribute_regex]

    results = []

    for regex in attribute_regex:
      query, args = self._BuildQuery(subject, regex, timestamp, limit,
                                     is_regex=True)
      rows = self.ExecuteQuery(query, args)

      for row in rows:
        attribute = row["attribute"]
        value = self._Decode(attribute, row["value"])
        results.append((attribute, value, row["timestamp"]))

    return results

  def MultiSet(self, subject, values, timestamp=None, replace=True, sync=True,
               to_delete=None, token=None):
    """Set multiple attributes' values for this subject in one operation."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    to_delete = set(to_delete or [])
    if timestamp is None:
      timestamp = time.time() * 1e6

    # Prepare a bulk insert operation.
    subject = utils.SmartUnicode(subject)
    to_insert = []
    to_replace = []

    # Build a document for each unique timestamp.
    for attribute, sequence in values.items():
      for value in sequence:
        entry_timestamp = None

        if isinstance(value, tuple):
          value, entry_timestamp = value

        if entry_timestamp is None:
          entry_timestamp = timestamp

        attribute = utils.SmartUnicode(attribute)
        data = self._Encode(value)

        # Replacing means to delete all versions of the attribute first.
        if replace or attribute in to_delete:
          duplicates = self._CountDuplicateAttributes(subject, attribute)
          if duplicates > 1:
            to_delete.add(attribute)
            to_insert.append(
                [subject, attribute, data, int(entry_timestamp)])
          else:
            if attribute in to_delete:
              to_delete.remove(attribute)
            if duplicates == 0:
              to_insert.append(
                  [subject, attribute, data, int(entry_timestamp)])
            elif duplicates == 1:
              to_replace.append(
                  [subject, attribute, data, int(entry_timestamp)])
        else:
          to_insert.append(
              [subject, attribute, data, int(entry_timestamp)])

    if to_delete:
      self.DeleteAttributes(subject, to_delete, token=token)

    if to_replace:
      transaction = self._BuildReplaces(to_replace)
      self._ExecuteTransaction(transaction)

    if to_insert:
      if sync:
        transaction = self._BuildInserts(to_insert)
        self._ExecuteTransaction(transaction)
      else:
        with self.lock:
          self.to_insert.extend(to_insert)

  def Flush(self):
    with self.lock:
      to_insert = self.to_insert
      self.to_insert = []

    if to_insert:
      transaction = self._BuildInserts(to_insert)
      self._ExecuteTransaction(transaction)

  def _CountDuplicateAttributes(self, subject, attribute):
    query = ("SELECT count(*) AS total FROM aff4 "
             "WHERE subject_hash=unhex(md5(%s)) "
             "AND attribute_hash=unhex(md5(%s))")
    args = [subject, attribute]
    result = self.ExecuteQuery(query, args)
    return int(result[0]["total"])

  def _BuildReplaces(self, values):
    transaction = []

    for (subject, attribute, value, timestamp) in values:
      aff4_q = {}
      aff4_q["query"] = (
          "UPDATE aff4 SET value=%s, timestamp=%s "
          "WHERE subject_hash=unhex(md5(%s)) "
          "AND attribute_hash=unhex(md5(%s))")
      aff4_q["args"] = [value, timestamp, subject, attribute]
      transaction.append(aff4_q)
    return transaction

  def _BuildInserts(self, values):
    subjects_q = {}
    attributes_q = {}
    aff4_q = {}

    subjects_q["query"] = "INSERT IGNORE INTO subjects (hash, subject) VALUES"
    attributes_q["query"] = (
        "INSERT IGNORE INTO attributes (hash, attribute) VALUES")
    aff4_q["query"] = (
        "INSERT INTO aff4 (subject_hash, attribute_hash, "
        "timestamp, value) VALUES")

    subjects_q["args"] = []
    attributes_q["args"] = []
    aff4_q["args"] = []

    seen = {}
    seen["subjects"] = []
    seen["attributes"] = []

    for (subject, attribute, value, timestamp) in values:
      if subject not in seen["subjects"]:
        subjects_q["args"].extend([subject, subject])
        seen["subjects"].append(subject)
      if attribute not in seen["attributes"]:
        attributes_q["args"].extend([attribute, attribute])
        seen["attributes"].append(attribute)
      aff4_q["args"].extend([subject, attribute, timestamp, value])

    subjects_q["query"] += ", ".join(
        ["(unhex(md5(%s)), %s)"] * (len(subjects_q["args"]) / 2))
    attributes_q["query"] += ", ".join(
        ["(unhex(md5(%s)), %s)"] * (len(attributes_q["args"]) / 2))
    aff4_q["query"] += ", ".join(
        ["(unhex(md5(%s)), unhex(md5(%s)), %s, %s)"] * (
            len(aff4_q["args"]) / 4))

    return [aff4_q, subjects_q, attributes_q]

  def ExecuteQuery(self, query, args=None):
    """Get connection from pool and execute query."""
    retries = 10
    for attempt in range(1, retries + 1):
      connection = self.pool.GetConnection()
      try:
        connection.cursor.execute(query, args)
        results = connection.cursor.fetchall()
        break
      except MySQLdb.Error as e:
        # If there was an error attempt to clean up this connection and let it
        # drop
        logging.warn("Datastore query attempt %s failed with %s:",
                     attempt, str(e))
        time.sleep(.2)
        self.pool.DropConnection(connection)
        if attempt == 10:
          raise e
        else:
          continue
    self.pool.PutConnection(connection)
    return results

  def _ExecuteTransaction(self, transaction):
    """Get connection from pool and execute queries."""
    for query in transaction:
      self.ExecuteQuery(query["query"], query["args"])

  def _CalculateAttributeStorageTypes(self):
    """Build a mapping between column names and types."""
    self.attribute_types = {}

    for attribute in aff4.Attribute.PREDICATES.values():
      self.attribute_types[attribute.predicate] = (
          attribute.attribute_type.data_store_type)

  def _Encode(self, value):
    """Encode the value for the attribute."""
    try:
      return buffer(value.SerializeToString())
    except AttributeError:
      # Types "string" and "bytes" are stored as strings here.
      return buffer(utils.SmartStr(value))

  def _Decode(self, attribute, value):
    required_type = self.attribute_types.get(attribute, "bytes")
    if isinstance(value, buffer):
      value = str(value)
    if required_type in ("integer", "unsigned_integer"):
      return int(value)
    elif required_type == "string":
      return utils.SmartUnicode(value)
    else:
      return value

  def _BuildQuery(self, subject, attribute=None, timestamp=None,
                  limit=None, is_regex=False):
    """Build the SELECT query to be executed."""
    args = []
    fields = ""
    criteria = "WHERE aff4.subject_hash=unhex(md5(%s))"
    args.append(subject)
    sorting = ""
    tables = "FROM aff4"

    subject = utils.SmartUnicode(subject)

    # Set fields, tables, and criteria and append args
    if attribute is not None:
      if is_regex:
        tables += " JOIN attributes ON aff4.attribute_hash=attributes.hash"
        regex = re.match(r"(^[a-zA-Z0-9_\- /:]+)(.*)", attribute)
        if not regex:
          # If attribute has no prefix just rlike
          criteria += " AND attributes.attribute rlike %s"
          args.append(attribute)
        else:
          rlike = regex.groups()[1]

          if rlike:
             # If there is a regex component attempt to replace with like
            like = regex.groups()[0] + "%"
            criteria += " AND attributes.attribute like %s"
            args.append(like)

            # If the regex portion is not a match all regex then add rlike
            if not (rlike == ".*" or rlike == ".+"):
              criteria += " AND attributes.attribute rlike %s"
              args.append(rlike)
          else:
            # If no regex component then treat as full attribute
            criteria += " AND aff4.attribute_hash=unhex(md5(%s))"
            args.append(attribute)
      else:
        criteria += " AND aff4.attribute_hash=unhex(md5(%s))"
        args.append(attribute)

    # Limit to time range if specified
    if isinstance(timestamp, (tuple, list)):
      criteria += " AND aff4.timestamp >= %s AND aff4.timestamp <= %s"
      args.append(int(timestamp[0]))
      args.append(int(timestamp[1]))

    fields = "aff4.value, aff4.timestamp"
    if is_regex:
      fields += ", attributes.attribute"

    # Modify fields and sorting for timestamps.
    if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
      tables += (" JOIN (SELECT attribute_hash, MAX(timestamp) timestamp "
                 "%s %s GROUP BY attribute_hash) maxtime ON "
                 "aff4.attribute_hash=maxtime.attribute_hash AND "
                 "aff4.timestamp=maxtime.timestamp") % (tables, criteria)
      criteria = "WHERE aff4.subject_hash=unhex(md5(%s))"
      args.append(subject)
    else:
      # Always order results.
      sorting = "ORDER BY aff4.timestamp DESC"
    # Add limit if set.
    if limit:
      sorting += " LIMIT %s" % int(limit)

    query = " ".join(["SELECT", fields, tables, criteria, sorting])

    return (query, args)

  def _BuildDelete(self, subject, attribute=None, timestamp=None):
    """Build the DELETE query to be executed."""
    subjects_q = {}
    attributes_q = {}
    aff4_q = {}

    subjects_q["query"] = (
        "DELETE subjects FROM subjects WHERE hash=unhex(md5(%s))")
    subjects_q["args"] = [subject]

    aff4_q["query"] = "DELETE aff4 FROM aff4 WHERE subject_hash=unhex(md5(%s))"
    aff4_q["args"] = [subject]

    attributes_q["query"] = ""
    attributes_q["args"] = []

    if attribute:
      aff4_q["query"] += " AND attribute_hash=unhex(md5(%s))"
      aff4_q["args"].append(attribute)

      if isinstance(timestamp, (tuple, list)):
        aff4_q["query"] += " AND aff4.timestamp >= %s AND aff4.timestamp <= %s"
        aff4_q["args"].append(int(timestamp[0]))
        aff4_q["args"].append(int(timestamp[1]))

      subjects_q["query"] = (
          "DELETE subjects FROM subjects "
          "LEFT JOIN aff4 ON aff4.subject_hash=subjects.hash "
          "WHERE subjects.hash=unhex(md5(%s)) "
          "AND aff4.subject_hash IS NULL")

      attributes_q["query"] = (
          "DELETE attributes FROM attributes "
          "LEFT JOIN aff4 ON aff4.attribute_hash=attributes.hash "
          "WHERE attributes.hash=unhex(md5(%s)) "
          "AND aff4.attribute_hash IS NULL")
      attributes_q["args"].append(attribute)

      return [aff4_q, subjects_q, attributes_q]

    return [aff4_q, subjects_q]

  def _MakeTimestamp(self, start=None, end=None):
    """Create a timestamp using a start and end time.

    Args:
      start: Start timestamp.
      end: End timestamp.
    Returns:
      A tuple (start, end) of converted timestamps or None for all time.
    """
    mysql_unsigned_bigint_max = 18446744073709551615
    ts_start = int(start or 0)
    ts_end = int(end or mysql_unsigned_bigint_max)
    if ts_start == 0 and ts_end == mysql_unsigned_bigint_max:
      return None
    else:
      return (ts_start, ts_end)

  def _CreateTables(self):
    self.ExecuteQuery("""
    CREATE TABLE IF NOT EXISTS `subjects` (
      hash BINARY(16) PRIMARY KEY NOT NULL,
      subject TEXT CHARACTER SET utf8 NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT ='Table for storing subjects';
    """)

    self.ExecuteQuery("""
    CREATE TABLE IF NOT EXISTS `attributes` (
      hash BINARY(16) PRIMARY KEY NOT NULL,
      attribute VARCHAR(2048) CHARACTER SET utf8 DEFAULT NULL,
      KEY `attribute` (`attribute`(32))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT ='Table storing attributes';
    """)

    self.ExecuteQuery("""
    CREATE TABLE IF NOT EXISTS `aff4` (
      id BIGINT UNSIGNED PRIMARY KEY NOT NULL AUTO_INCREMENT,
      subject_hash BINARY(16) NOT NULL,
      attribute_hash BINARY(16) NOT NULL,
      timestamp BIGINT UNSIGNED DEFAULT NULL,
      value MEDIUMBLOB NULL,
      KEY `master` (`subject_hash`,`attribute_hash`,`timestamp`),
      KEY `attribute` (`attribute_hash`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8
    COMMENT ='Table representing AFF4 objects';
    """)

    self.ExecuteQuery("""
    CREATE TABLE IF NOT EXISTS `locks` (
      subject_hash BINARY(16) PRIMARY KEY NOT NULL,
      lock_owner BIGINT UNSIGNED DEFAULT NULL,
      lock_expiration BIGINT UNSIGNED DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8
    COMMENT ='Table representing locks on subjects';
    """)


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
    query = (
        "UPDATE locks SET lock_expiration=%s, lock_owner=%s "
        "WHERE subject_hash=unhex(md5(%s)) "
        "AND (lock_expiration < %s)")
    args = [self.expires_lock, self.lock_token, subject, time.time() * 1e6]
    self.store.ExecuteQuery(query, args)

    self._CheckForLock()

  def UpdateLease(self, lease_time):
    self.expires_lock = int((time.time() + lease_time) * 1e6)

    # This will take over the lock if the lock is too old.
    query = (
        "UPDATE locks SET lock_expiration=%s, lock_owner=%s "
        "WHERE subject_hash=unhex(md5(%s))")
    args = [self.expires_lock, self.lock_token, self.subject]
    self.store.ExecuteQuery(query, args)

  def CheckLease(self):
    return max(0, self.expires_lock / 1e6 - time.time())

  def Abort(self):
    self._RemoveLock()

  def Commit(self):
    super(MySQLTransaction, self).Commit()
    self._RemoveLock()

  def _CheckForLock(self):
    """Checks that the lock has stuck."""

    query = ("SELECT lock_expiration, lock_owner FROM locks "
             "WHERE subject_hash=unhex(md5(%s))")
    args = [self.subject]
    rows = self.store.ExecuteQuery(query, args)
    for row in rows:

      # We own this lock now.
      if (row["lock_expiration"] == self.expires_lock and
          row["lock_owner"] == self.lock_token):
        return

      else:
        # Someone else owns this lock.
        raise data_store.TransactionError("Subject %s is locked" % self.subject)

    # If we get here the row does not exist:
    query = ("INSERT IGNORE INTO locks "
             "SET lock_expiration=%s, lock_owner=%s, "
             "subject_hash=unhex(md5(%s))")
    args = [self.expires_lock, self.lock_token, self.subject]
    self.store.ExecuteQuery(query, args)

    self._CheckForLock()

  def _RemoveLock(self):
    # Remove the lock on the document. Note that this only resets the lock if
    # We actually hold it since lock_expiration == self.expires_lock and
    # lock_owner = self.lock_token.

    query = ("UPDATE locks SET lock_expiration=0, lock_owner=0 "
             "WHERE lock_expiration=%s "
             "AND lock_owner=%s "
             "AND subject_hash=unhex(md5(%s))")
    args = [self.expires_lock, self.lock_token, self.subject]
    self.store.ExecuteQuery(query, args)
