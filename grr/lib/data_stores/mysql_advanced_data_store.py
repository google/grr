#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""An implementation of a data store based on mysql."""

import logging
import Queue
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

  def __init__(self, database_name):
    try:
      self.dbh = self._MakeConnection(database=database_name)
      self.cursor = self.dbh.cursor()
      self.cursor.connection.autocommit(True)
      self.cursor.execute("SET NAMES binary")
    except MySQLdb.OperationalError as e:
      # Database does not exist
      if "Unknown database" in str(e):
        dbh = self._MakeConnection()
        cursor = dbh.cursor()
        cursor.connection.autocommit(True)
        cursor.execute("Create database `%s`" % database_name)
        cursor.close()
        dbh.close()

        self.dbh = self._MakeConnection(database=database_name)
        self.cursor = self.dbh.cursor()
        self.cursor.connection.autocommit(True)
        self.cursor.execute("SET NAMES binary")
      else:
        raise

  def _MakeConnection(self, database=""):
    """Repeat connection attempts to server until we get a valid connection."""
    first_attempt_time = time.time()
    wait_time = config_lib.CONFIG["Mysql.max_connect_wait"]
    while wait_time == 0 or time.time() - first_attempt_time < wait_time:
      try:
        connection_args = dict(
            user=config_lib.CONFIG["Mysql.database_username"],
            db=database,
            charset="utf8",
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

        if "Can't connect" in str(e):
          logging.warning("Datastore connection retrying after failed with %s.",
                          str(e))
          time.sleep(.5)
          continue
        raise

    raise IOError("Unable to connect to Mysql database.")


class ConnectionPool(object):
  """A pool of connections to the mysql server.

  Uses unfinished_tasks to track the number of open connections.
  """

  def __init__(self, database_name):
    self.connections = SafeQueue()
    self.database_name = database_name
    self.pool_max_size = int(config_lib.CONFIG["Mysql.conn_pool_max"])
    self.pool_min_size = int(config_lib.CONFIG["Mysql.conn_pool_min"])
    for _ in range(self.pool_min_size):
      self.connections.put(MySQLConnection(self.database_name))

  def GetConnection(self):
    if self.connections.empty() and (
        self.connections.unfinished_tasks < self.pool_max_size):
      self.connections.put(MySQLConnection(self.database_name))
    connection = self.connections.get(block=True)
    return connection

  def PutConnection(self, connection):
    # If the pool is low on connections return this connection to the pool

    if self.connections.qsize() < self.pool_min_size:
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


class MySQLAdvancedDataStore(data_store.DataStore):
  """A mysql based data store."""

  POOL = None

  def __init__(self):
    self.database_name = config_lib.CONFIG["Mysql.database_name"]
    # Use the global connection pool.
    if MySQLAdvancedDataStore.POOL is None:
      MySQLAdvancedDataStore.POOL = ConnectionPool(self.database_name)
    self.pool = self.POOL

    self.to_replace = []
    self.to_insert = []
    self._CalculateAttributeStorageTypes()
    self.database_name = config_lib.CONFIG["Mysql.database_name"]
    self.buffer_lock = threading.RLock()
    self.lock = threading.RLock()

    super(MySQLAdvancedDataStore, self).__init__()

  def Initialize(self):
    super(MySQLAdvancedDataStore, self).Initialize()
    try:
      self.ExecuteQuery("desc `aff4`")
    except MySQLdb.Error:
      logging.debug("Recreating Tables")
      self.RecreateTables()

  def DropTables(self):
    """Drop all existing tables."""

    rows = self.ExecuteQuery("SELECT table_name FROM information_schema.tables "
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

  def DeleteAttributes(self,
                       subject,
                       attributes,
                       start=None,
                       end=None,
                       sync=True,
                       token=None):
    """Remove some attributes from a subject."""
    _ = sync  # Unused
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    if not attributes:
      return

    if isinstance(attributes, basestring):
      raise ValueError(
          "String passed to DeleteAttributes (non string iterable expected).")

    for attribute in attributes:
      timestamp = self._MakeTimestamp(start, end)
      attribute = utils.SmartUnicode(attribute)
      queries = self._BuildDelete(subject, attribute, timestamp)
      self._ExecuteQueries(queries)

  def DeleteSubject(self, subject, sync=False, token=None):
    _ = sync
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    queries = self._BuildDelete(subject)
    self._ExecuteQueries(queries)

  def ResolveMulti(self,
                   subject,
                   attributes,
                   timestamp=None,
                   limit=None,
                   token=None):
    """Resolves multiple attributes at once for one subject."""
    self.security_manager.CheckDataStoreAccess(
        token, [subject], self.GetRequiredResolveAccess(attributes))

    for attribute in attributes:
      query, args = self._BuildQuery(subject, attribute, timestamp, limit)
      result = self.ExecuteQuery(query, args)

      for row in result:
        value = self._Decode(attribute, row["value"])

        yield (attribute, value, row["timestamp"])

      if limit:
        limit -= len(result)

      if limit is not None and limit <= 0:
        break

  def MultiResolvePrefix(self,
                         subjects,
                         attribute_prefix,
                         timestamp=None,
                         limit=None,
                         token=None):
    """Result multiple subjects using one or more attribute regexps."""
    result = {}

    for subject in subjects:
      values = self.ResolvePrefix(subject,
                                  attribute_prefix,
                                  token=token,
                                  timestamp=timestamp,
                                  limit=limit)

      if values:
        result[subject] = values
        if limit:
          limit -= len(values)

      if limit is not None and limit <= 0:
        break

    return result.iteritems()

  def ResolvePrefix(self,
                    subject,
                    attribute_prefix,
                    timestamp=None,
                    limit=None,
                    token=None):
    """ResolvePrefix."""
    self.security_manager.CheckDataStoreAccess(
        token, [subject], self.GetRequiredResolveAccess(attribute_prefix))

    if isinstance(attribute_prefix, basestring):
      attribute_prefix = [attribute_prefix]

    results = []

    for prefix in attribute_prefix:
      query, args = self._BuildQuery(subject,
                                     prefix,
                                     timestamp,
                                     limit,
                                     is_prefix=True)
      rows = self.ExecuteQuery(query, args)

      for row in rows:
        attribute = row["attribute"]
        value = self._Decode(attribute, row["value"])
        results.append((attribute, value, row["timestamp"]))

    return results

  def _ScanAttribute(self,
                     subject_prefix,
                     attribute,
                     after_urn=None,
                     limit=None,
                     token=None):
    self.security_manager.CheckDataStoreAccess(token, [subject_prefix], "qr")

    subject_prefix = utils.SmartStr(rdfvalue.RDFURN(subject_prefix))
    if subject_prefix[-1] != "/":
      subject_prefix += "/"
    subject_prefix += "%"

    query = """
    SELECT aff4.value, aff4.timestamp, subjects.subject
      FROM aff4
      JOIN subjects ON aff4.subject_hash=subjects.hash
      JOIN (
            SELECT subject_hash, MAX(timestamp) timestamp
            FROM aff4
            JOIN subjects ON aff4.subject_hash=subjects.hash
            WHERE aff4.attribute_hash=unhex(md5(%s))
                  AND subjects.subject like %s
                  AND subjects.subject > %s
            GROUP BY subject_hash
            ) maxtime ON aff4.subject_hash=maxtime.subject_hash
                  AND aff4.timestamp=maxtime.timestamp
      WHERE aff4.attribute_hash=unhex(md5(%s))
    """
    args = [attribute, subject_prefix, after_urn, attribute]

    if limit:
      query += " LIMIT %s"
      args.append(limit)

    results = self.ExecuteQuery(query, args)
    return results

  def ScanAttributes(self,
                     subject_prefix,
                     attributes,
                     after_urn=None,
                     max_records=None,
                     token=None,
                     relaxed_order=False):
    _ = relaxed_order  # Unused

    if after_urn:
      after_urn = utils.SmartStr(after_urn)
    else:
      after_urn = ""

    results = {}

    for attribute in attributes:
      attribute_results = self._ScanAttribute(subject_prefix, attribute,
                                              after_urn, max_records, token)

      for row in attribute_results:
        subject = row["subject"]
        timestamp = row["timestamp"]
        value = self._Decode(attribute, row["value"])
        if subject in results:
          results[subject][attribute] = (timestamp, value)
        else:
          results[subject] = {attribute: (timestamp, value)}

    result_count = 0
    for subject in sorted(results):
      yield (subject, results[subject])
      result_count += 1
      if max_records and result_count >= max_records:
        return

  def MultiSet(self,
               subject,
               values,
               timestamp=None,
               replace=True,
               sync=True,
               to_delete=None,
               token=None):
    """Set multiple attributes' values for this subject in one operation."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    to_delete = set(to_delete or [])

    # Prepare a bulk insert operation.
    subject = utils.SmartUnicode(subject)
    to_insert = []
    to_replace = []
    transaction = []

    # Build a document for each unique timestamp.
    for attribute, sequence in values.items():
      for value in sequence:

        if isinstance(value, tuple):
          value, entry_timestamp = value
        else:
          entry_timestamp = timestamp

        if entry_timestamp is None:
          entry_timestamp = timestamp

        if entry_timestamp is not None:
          entry_timestamp = int(entry_timestamp)

        attribute = utils.SmartUnicode(attribute)
        data = self._Encode(value)

        # Replacing means to delete all versions of the attribute first.
        if replace or attribute in to_delete:
          existing = self._CountExistingRows(subject, attribute)
          if existing:
            to_replace.append([subject, attribute, data, entry_timestamp])
          else:
            to_insert.append([subject, attribute, data, entry_timestamp])
          if attribute in to_delete:
            to_delete.remove(attribute)

        else:
          to_insert.append([subject, attribute, data, entry_timestamp])

    if to_delete:
      self.DeleteAttributes(subject, to_delete, token=token)

    if sync:
      if to_replace:
        transaction.extend(self._BuildReplaces(to_replace))
      if to_insert:
        transaction.extend(self._BuildInserts(to_insert))
      if transaction:
        self._ExecuteTransaction(transaction)
    else:
      if to_replace:
        with self.buffer_lock:
          self.to_replace.extend(to_replace)
      if to_insert:
        with self.buffer_lock:
          self.to_insert.extend(to_insert)

  def _CountExistingRows(self, subject, attribute):
    query = ("SELECT count(*) AS total FROM aff4 "
             "WHERE subject_hash=unhex(md5(%s)) "
             "AND attribute_hash=unhex(md5(%s))")
    args = [subject, attribute]
    result = self.ExecuteQuery(query, args)
    return int(result[0]["total"])

  @utils.Synchronized
  def Flush(self):
    # TODO(user): There is a race condition here. The locking only
    # applies to the data to be written later so what could happen is:
    # - Thread a writes lots of important messages with sync=False, they end up
    #   in the lists.
    # - Thread b calls Flush() and empties the lists. The transaction takes a
    #   long time though since the server is heavily loaded.
    # - Meanwhile, Thread a calls Flush(). The lists are all empty so Flush()
    #   returns immediately. Thread a carries on with live assuming the data has
    #   been written but it actually hasn't yet so things go wrong.
    #
    # This is not easy to fix - except by taking a huge performance hit and
    # locking the whole Flush() method. Long term, we should stop flushing the
    # data store and use MutationPools everywhere.
    super(MySQLAdvancedDataStore, self).Flush()
    with self.buffer_lock:
      to_insert = self.to_insert
      to_replace = self.to_replace
      self.to_replace = []
      self.to_insert = []

    transaction = []
    if to_replace:
      transaction.extend(self._BuildReplaces(to_replace))
    if to_insert:
      transaction.extend(self._BuildInserts(to_insert))
    if transaction:
      self._ExecuteTransaction(transaction)

  def _BuildReplaces(self, values):
    transaction = []
    updates = {}
    to_insert = []

    for (subject, attribute, data, timestamp) in values:
      updates.setdefault(subject, {})[attribute] = [data, timestamp]

    for subject in updates:
      for attribute in updates[subject]:
        data = updates[subject][attribute][0]
        timestamp = updates[subject][attribute][1]
        to_insert.append([subject, attribute, data, timestamp])
        delete_q = self._BuildDelete(subject, attribute)[0]
        transaction.append(delete_q)
    transaction.extend(self._BuildInserts(to_insert))
    return transaction

  def _BuildInserts(self, values):
    subjects_q = {}
    attributes_q = {}
    aff4_q = {}

    subjects_q["query"] = "INSERT IGNORE INTO subjects (hash, subject) VALUES"
    attributes_q["query"] = (
        "INSERT IGNORE INTO attributes (hash, attribute) VALUES")
    aff4_q["query"] = ("INSERT INTO aff4 (subject_hash, attribute_hash, "
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
      aff4_q["args"].extend([subject, attribute, timestamp, timestamp, value])

    subjects_q["query"] += ", ".join(["(unhex(md5(%s)), %s)"] *
                                     (len(subjects_q["args"]) / 2))
    attributes_q["query"] += ", ".join(["(unhex(md5(%s)), %s)"] *
                                       (len(attributes_q["args"]) / 2))
    aff4_q["query"] += ", ".join(
        ["(unhex(md5(%s)), unhex(md5(%s)), "
         "if(%s is NULL,floor(unix_timestamp(now(6))*1000000),%s), "
         "unhex(%s))"] * (len(aff4_q["args"]) / 5))

    return [aff4_q, attributes_q, subjects_q]

  def ExecuteQuery(self, query, args=None):
    """Get connection from pool and execute query."""
    while True:
      # Connectivity issues and deadlocks should not cause threads to die and
      # create inconsistency.  Any MySQL errors here should be temporary in
      # nature and GRR should be able to recover when the server is available or
      # deadlocks have been resolved.
      connection = self.pool.GetConnection()
      try:
        connection.cursor.execute(query, args)
        results = connection.cursor.fetchall()
        self.pool.PutConnection(connection)
        return results
      except MySQLdb.Error as e:
        # If there was an error attempt to clean up this connection and let it
        # drop
        self.pool.DropConnection(connection)
        if "doesn't exist" in str(e):
          # This should indicate missing tables and raise immediately
          raise e
        else:
          logging.warning("Datastore query retrying after failed with %s.",
                          str(e))
          # Most errors encountered here need a reasonable backoff time to
          # resolve.
          time.sleep(1)
      finally:
        # Reduce the open connection count by calling task_done. This will
        # increment again if the connection is returned to the pool.
        self.pool.connections.task_done()

  def _ExecuteQueries(self, queries):
    """Get connection from pool and execute queries."""
    for query in queries:
      self.ExecuteQuery(query["query"], query["args"])

  def _ExecuteTransaction(self, transaction):
    """Get connection from pool and execute transaction."""
    while True:
      # Connectivity issues and deadlocks should not cause threads to die and
      # create inconsistency.  Any MySQL errors here should be temporary in
      # nature and GRR should be able to recover when the server is available or
      # deadlocks have been resolved.
      connection = self.pool.GetConnection()
      try:
        connection.cursor.execute("START TRANSACTION")
        for query in transaction:
          connection.cursor.execute(query["query"], query["args"])
        connection.cursor.execute("COMMIT")
        results = connection.cursor.fetchall()
        self.pool.PutConnection(connection)
        return results
      except MySQLdb.Error as e:
        # If there was an error attempt to clean up this connection and let it
        # drop
        self.pool.DropConnection(connection)
        if "doesn't exist" in str(e):
          # This should indicate missing tables and raise immediately
          raise e
        else:
          logging.warning("Datastore query retrying after failed with %s.",
                          str(e))
          # Most errors encountered here need a reasonable backoff time to
          # resolve.
          time.sleep(1)
      finally:
        # Reduce the open connection count by calling task_done. This will
        # increment again if the connection is returned to the pool.
        self.pool.connections.task_done()

  def _CalculateAttributeStorageTypes(self):
    """Build a mapping between column names and types."""
    self.attribute_types = {}

    for attribute in aff4.Attribute.PREDICATES.values():
      self.attribute_types[attribute.predicate] = (
          attribute.attribute_type.data_store_type)

  def _Encode(self, value):
    """Encode the value for the attribute."""
    try:
      return value.SerializeToString().encode("hex")
    except AttributeError:
      if isinstance(value, (int, long)):
        return str(value).encode("hex")
      else:
        # Types "string" and "bytes" are stored as strings here.
        return utils.SmartStr(value).encode("hex")

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

  def _BuildQuery(self,
                  subject,
                  attribute=None,
                  timestamp=None,
                  limit=None,
                  is_prefix=False):
    """Build the SELECT query to be executed."""
    args = []
    subject = utils.SmartUnicode(subject)
    criteria = "WHERE aff4.subject_hash=unhex(md5(%s))"
    args.append(subject)
    sorting = ""
    tables = "FROM aff4"

    # Set fields, tables, and criteria and append args
    if attribute is not None:
      if is_prefix:
        tables += " JOIN attributes ON aff4.attribute_hash=attributes.hash"
        prefix = attribute + "%"
        criteria += " AND attributes.attribute like %s"
        args.append(prefix)
      else:
        criteria += " AND aff4.attribute_hash=unhex(md5(%s))"
        args.append(attribute)

    # Limit to time range if specified
    if isinstance(timestamp, (tuple, list)):
      criteria += " AND aff4.timestamp >= %s AND aff4.timestamp <= %s"
      args.append(int(timestamp[0]))
      args.append(int(timestamp[1]))

    fields = "aff4.value, aff4.timestamp"
    if is_prefix:
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
    subjects_q = {
        "query": "DELETE subjects FROM subjects WHERE hash=unhex(md5(%s))",
        "args": [subject]
    }

    aff4_q = {
        "query": "DELETE aff4 FROM aff4 WHERE subject_hash=unhex(md5(%s))",
        "args": [subject]
    }

    locks_q = {
        "query": "DELETE locks FROM locks WHERE subject_hash=unhex(md5(%s))",
        "args": [subject]
    }

    if attribute:
      aff4_q["query"] += " AND attribute_hash=unhex(md5(%s))"
      aff4_q["args"].append(attribute)

      if isinstance(timestamp, (tuple, list)):
        aff4_q["query"] += " AND aff4.timestamp >= %s AND aff4.timestamp <= %s"
        aff4_q["args"].append(int(timestamp[0]))
        aff4_q["args"].append(int(timestamp[1]))

      attributes_q = {
          "query": "DELETE attributes FROM attributes LEFT JOIN aff4 ON "
                   "aff4.attribute_hash=attributes.hash "
                   "WHERE attributes.hash=unhex(md5(%s)) "
                   "AND aff4.attribute_hash IS NULL",
          "args": [attribute]
      }
      # If only attribute is being deleted we will not check to clean up
      # subject and lock tables.
      return [aff4_q, attributes_q]
    # If a subject is being deleted we clean up the locks and subjects table
    # but assume it has attributes that are common to other subjects

    return [aff4_q, locks_q, subjects_q]

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
    if end is None:
      ts_end = mysql_unsigned_bigint_max
    else:
      ts_end = int(end)
    if ts_start == 0 and ts_end == mysql_unsigned_bigint_max:
      return None
    else:
      return (ts_start, ts_end)

  def _CreateTables(self):
    self.ExecuteQuery("""
    CREATE TABLE IF NOT EXISTS `subjects` (
      hash BINARY(16) PRIMARY KEY NOT NULL,
      subject TEXT CHARACTER SET utf8 NULL,
      KEY `subject` (`subject`(96))
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
    super(MySQLTransaction, self).__init__(store,
                                           subject,
                                           lease_time=lease_time,
                                           token=token)
    if lease_time is None:
      lease_time = config_lib.CONFIG["Datastore.transaction_timeout"]

    self.lock_token = thread.get_ident()
    self.lock_time = lease_time
    self.expires_lock = int((time.time() + self.lock_time) * 1e6)

    # This will take over the lock if the lock is too old.
    query = ("UPDATE locks SET lock_expiration=%s, lock_owner=%s "
             "WHERE subject_hash=unhex(md5(%s)) "
             "AND (lock_expiration < %s)")
    args = [self.expires_lock, self.lock_token, subject, time.time() * 1e6]
    self.store.ExecuteQuery(query, args)

    self._CheckForLock()

  def UpdateLease(self, lease_time):
    self.expires_lock = int((time.time() + lease_time) * 1e6)

    # This will take over the lock if the lock is too old.
    query = ("UPDATE locks SET lock_expiration=%s, lock_owner=%s "
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
