#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""An implementation of a data store based on mysql."""


import Queue
import threading
import thread
import time
import MySQLdb
import re

from MySQLdb import cursors

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.data_stores import common


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
      self.cursor.connection.autocommit(True)

      return self.dbh
    except MySQLdb.OperationalError as e:
      # This is a fatal error, we just raise the top level exception here.
      if "Access denied" in str(e):
        raise Error(str(e))
      raise

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    if self.queue:
      self.queue.put(self)

  def Execute(self, *args):
    retries = 10
    for i in range(1, retries):
      try:
        self.cursor.execute(*args)
        return self.cursor.fetchall()
      except MySQLdb.Error:
        time.sleep(.2)
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


class MySQLAdvancedDataStore(data_store.DataStore):
  """A mysql based data store."""

  POOL = None
  SYSTEM_TABLE = "system"

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
      self._ExecuteQuery("desc `aff4`")
    except MySQLdb.Error:
      self.RecreateTables()

  def DropTables(self):
    #Drop all existing tables
    rows = self._ExecuteQuery("select table_name from information_schema.tables "
                              "where table_schema='%s'" % self.database_name)
    for row in rows:
      self._ExecuteQuery("drop table `%s`" % row["table_name"])

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
      predicate = utils.SmartUnicode(attribute)
      transaction = self._BuildDelete(subject, predicate, timestamp)
      self._ExecuteTransaction(transaction)

  def DeleteSubject(self, subject, token=None, sync=False):
    _ = sync
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    transaction = self._BuildDelete(subject)
    self._ExecuteTransaction(transaction)

  def ResolveMulti(self, subject, predicates, token=None, timestamp=None):
    """Resolves multiple predicates at once for one subject."""
    self.security_manager.CheckDataStoreAccess(
        token, [subject], self.GetRequiredResolveAccess(predicates))

    for predicate in predicates:
      query, args = self._BuildQuery(subject, predicate, timestamp)
      result = self._ExecuteQuery(query, args)

      for row in result:
        value = self._Decode(predicate, row["value"])

        yield predicate, value, rdfvalue.RDFDatetime(row["timestamp"])

  def MultiResolveRegex(self, subjects, predicate_regex, token=None, timestamp=None, limit=None):
    """Result multiple subjects using one or more predicate regexps."""
    result = {}

    for subject in subjects:
      values = self.ResolveRegex(subject, predicate_regex, token=token,
                                 timestamp=timestamp, limit=limit)

      if values:
        result[subject] = values
        if limit:
          limit -= len(values)

      if limit is not None and limit <= 0:
        break

    return result.iteritems()

  def ResolveRegex(self, subject, predicate_regex, token=None, timestamp=None, limit=None):
    self.security_manager.CheckDataStoreAccess(
        token, subject, self.GetRequiredResolveAccess(predicate_regex))

    if isinstance(predicate_regex, basestring):
      predicate_regex = [predicate_regex]

    results = []
    seen = set()

    for regex in predicate_regex:
      query, args = self._BuildQuery(subject, regex, timestamp, limit, is_regex=True)
      rows = self._ExecuteQuery(query, args)

      for row in rows:
        attribute = row["attribute"]
        value = self._Decode(attribute, row["value"])
        results.append((attribute, value, row["timestamp"]))

    return results

  def MultiSet(self, subject, values, timestamp=None, token=None, replace=True,
               sync=True, to_delete=None):
    """Set multiple predicates' values for this subject in one operation."""
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

        predicate = utils.SmartUnicode(attribute)
        data = self._Encode(value)

        # Replacing means to delete all versions of the attribute first.
        if replace or attribute in to_delete:
          duplicates = self._CountDuplicateAttributes(subject, predicate)
          if duplicates > 1:
            to_delete.add(attribute)
            to_insert.append(
                [subject, predicate, data, int(entry_timestamp)])
          else:
            if attribute in to_delete:
              to_delete.remove(attribute)
            if duplicates == 0:
              to_insert.append(
                  [subject, predicate, data, int(entry_timestamp)])
            elif duplicates == 1:
              to_replace.append(
                  [subject, predicate, data, int(entry_timestamp)])
        else:
          to_insert.append(
              [subject, predicate, data, int(entry_timestamp)])

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

  def _CountDuplicateAttributes(self, subject, predicate):
    query = "SELECT count(*) AS total FROM aff4 WHERE \
subject_hash=unhex(md5(%s)) AND attribute_hash=unhex(md5(%s))"
    args = [subject, predicate]
    result = self._ExecuteQuery(query, args)
    return int(result[0]["total"])

  def _BuildReplaces(self, values):
    transaction = []

    for (subject, predicate, value, timestamp) in values:
      aff4 = {}
      aff4["query"] = "UPDATE aff4 SET value=%s, timestamp=%s WHERE \
subject_hash=unhex(md5(%s)) AND attribute_hash=unhex(md5(%s))"
      aff4["args"] = [value, timestamp, subject, predicate]
      transaction.append(aff4)
    return transaction

  def _BuildInserts(self, values):
    subjects = {}
    attributes = {}
    aff4 = {}

    subjects["query"] = "INSERT IGNORE INTO subjects (hash, subject) VALUES"
    attributes["query"] = "INSERT IGNORE INTO attributes (hash, attribute) VALUES"
    aff4["query"] = "INSERT INTO aff4 (subject_hash, attribute_hash, prefix, \
timestamp, value) VALUES"

    subjects["args"] = []
    attributes["args"] = []
    aff4["args"] = []

    seen = {}
    seen["subjects"] = []
    seen["attributes"] = []

    for (subject, predicate, value, timestamp) in values:
      if subject not in seen["subjects"]:
        subjects["args"].extend([subject, subject])
        seen["subjects"].append(subject)
      if predicate not in seen["attributes"]:
        attributes["args"].extend([predicate, predicate])
        seen["attributes"].append(predicate)
      prefix = predicate.split(":", 1)[0]
      aff4["args"].extend([subject, predicate, prefix, timestamp, value])

    subjects["query"] += ", ".join(["(unhex(md5(%s)), %s)"] * (len(subjects["args"]) / 2))
    attributes["query"] += ", ".join(["(unhex(md5(%s)), %s)"] * (len(attributes["args"]) / 2))
    aff4["query"] += ", ".join(
        ["(unhex(md5(%s)), unhex(md5(%s)), %s, %s, %s)"] * (
            len(aff4["args"]) / 5))

    return [subjects, attributes, aff4]

  def _ExecuteTransaction(self, transaction):
    """Get connection from pool and execute query"""
    for query in transaction:
      with self.pool.GetConnection() as cursor:
        cursor.Execute(query["query"], query["args"])

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

  def _BuildQuery(self, subject, predicate=None, timestamp=None,
                  limit=None, is_regex=False):
    """Build the SELECT query to be executed"""
    args = []
    fields = ""
    criteria = "WHERE aff4.subject_hash=unhex(md5(%s))"
    args.append(subject)
    sorting = ""
    tables = "FROM aff4"

    subject = utils.SmartUnicode(subject)

    #Set fields, tables, and criteria and append args
    if predicate is not None:
      if is_regex:
        tables += " JOIN attributes ON aff4.attribute_hash=attributes.hash"
        regex = re.match(r'(^[a-zA-Z0-9_]+:([a-zA-Z0-9_\-\. /:]*[a-zA-Z0-9_\- /:]+|[a-zA-Z0-9_\- /:]*))(.*)',
                         predicate)
        if not regex:
          #If predicate has no prefix just rlike
          criteria += " AND attributes.attribute rlike %s"
          args.append(predicate)
        elif regex.groups()[2]:
          prefix = predicate.split(":", 1)[0]
          like = regex.groups()[0] + "%"
          rlike = regex.groups()[2]

          #If predicate has prefix then use for query optimizations
          criteria += " AND aff4.prefix=(%s)"
          args.append(prefix)

          #If like component extends past prefix then include it
          #accounting for % and trailing :
          if len(like) > len(prefix) + 2:
            criteria += " AND attributes.attribute like %s"
            args.append(like)

          #If the regex portion is not a match all regex then break it
          #down into like and rlike components

          if not (rlike == ".*" or rlike == ".+"):
            criteria += " AND attributes.attribute rlike %s"
            args.append(rlike)
        else:
          criteria += " AND aff4.attribute_hash=unhex(md5(%s))"
          args.append(predicate)
      else:
          criteria += " AND aff4.attribute_hash=unhex(md5(%s))"
          args.append(predicate)

    #Limit to time range if specified
    if isinstance(timestamp, (tuple, list)):
      criteria += " AND aff4.timestamp >= %s AND aff4.timestamp <= %s"
      args.append(int(timestamp[0]))
      args.append(int(timestamp[1]))

    fields = "aff4.value, aff4.timestamp"
    if is_regex:
      fields += ", attributes.attribute"

    #Modify fields and sorting for timestamps
    if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
      tables += " JOIN (SELECT attribute_hash, MAX(timestamp) timestamp \
" + tables + " " + criteria + " GROUP BY attribute_hash) maxtime on \
aff4.attribute_hash=maxtime.attribute_hash and \
aff4.timestamp=maxtime.timestamp"
      criteria = "WHERE aff4.subject_hash=unhex(md5(%s))"
      args.append(subject)
    else:
      #Always order results
      sorting = "ORDER BY aff4.timestamp DESC"
    #Add limit if set
    if limit:
      sorting += " LIMIT %s" % int(limit)

    query = " ".join(["SELECT", fields, tables, criteria, sorting])

    return (query, args)

  def _BuildDelete(self, subject, predicate=None, timestamp=None):
    """Build the DELETE query to be executed"""
    subjects = {}
    attributes = {}
    aff4 = {}

    subjects["query"] = "DELETE subjects FROM subjects WHERE hash=unhex(md5(%s))"
    subjects["args"] = [subject]

    aff4["query"] = "DELETE aff4 FROM aff4 WHERE subject_hash=unhex(md5(%s))"
    aff4["args"] = [subject]

    attributes["query"] = ""
    attributes["args"] = []

    if predicate:
      aff4["query"] += " AND attribute_hash=unhex(md5(%s))"
      aff4["args"].append(predicate)

      if isinstance(timestamp, (tuple, list)):
        aff4["query"] += " AND aff4.timestamp >= %s AND aff4.timestamp <= %s"
        aff4["args"].append(int(timestamp[0]))
        aff4["args"].append(int(timestamp[1]))

      subjects["query"] = "DELETE subjects FROM subjects LEFT JOIN aff4 ON \
aff4.subject_hash=subjects.hash WHERE subjects.hash=unhex(md5(%s)) AND \
aff4.subject_hash IS NULL"

      attributes["query"] = "DELETE attributes FROM attributes LEFT JOIN aff4 \
ON aff4.attribute_hash=attributes.hash WHERE attributes.hash=unhex(md5(%s)) \
AND aff4.attribute_hash IS NULL"
      attributes["args"].append(predicate)

      return [aff4, subjects, attributes]

    return [aff4, subjects]

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

  def _CreateTables(self):
    self._ExecuteQuery("""
    CREATE TABLE IF NOT EXISTS `subjects` (
      hash BINARY(16) PRIMARY KEY NOT NULL,
      subject TEXT CHARACTER SET utf8 NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT ='Table for storing subjects';
    """)

    self._ExecuteQuery("""
    CREATE TABLE IF NOT EXISTS `attributes` (
      hash BINARY(16) PRIMARY KEY NOT NULL,
      attribute VARCHAR(2048) CHARACTER SET utf8 DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT ='Table storing attributes';
    """)

    self._ExecuteQuery("""
    CREATE TABLE IF NOT EXISTS `aff4` (
      subject_hash BINARY(16) NOT NULL,
      attribute_hash BINARY(16) NOT NULL,
      prefix VARCHAR(16) CHARACTER SET utf8 DEFAULT NULL,
      timestamp BIGINT(22) UNSIGNED DEFAULT NULL,
      value LONGBLOB NULL,
      KEY `master` (`subject_hash`,`attribute_hash`,`timestamp`),
      KEY `alternate` (`subject_hash`,`prefix`,`timestamp`),
      KEY `attribute` (`attribute_hash`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT ='Table representing AFF4 objects';
    """)

    self._ExecuteQuery("""
    CREATE TABLE IF NOT EXISTS `locks` (
      subject_hash BINARY(16) PRIMARY KEY NOT NULL,
      lock_owner BIGINT(22) UNSIGNED DEFAULT NULL,
      lock_expiration BIGINT(22) UNSIGNED DEFAULT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT ='Table representing locks on subjects';
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
    query = "UPDATE locks SET lock_expiration=%s, lock_owner=%s WHERE \
subject_hash=unhex(md5(%s)) AND (lock_expiration < %s)"
    args = [self.expires_lock, self.lock_token, subject, time.time() * 1e6]
    store._ExecuteQuery(query, args)

    self.CheckForLock()

  def UpdateLease(self, lease_time):
    self.expires_lock = int((time.time() + lease_time) * 1e6)

    # This will take over the lock if the lock is too old.
    query = "UPDATE locks SET lock_expiration=%s, lock_owner=%s WHERE subject_hash=unhex(md5(%s))"
    args = [self.expires_lock, self.lock_token, self.subject]
    self.store._ExecuteQuery(query, args)

  def CheckLease(self):
    return max(0, self.expires_lock / 1e6 - time.time())

  def CheckForLock(self):
    """Checks that the lock has stuck."""

    query = "SELECT lock_expiration, lock_owner FROM locks WHERE subject_hash=unhex(md5(%s))"
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
    query = "INSERT IGNORE INTO locks SET lock_expiration=%s, lock_owner=%s, \
subject_hash=unhex(md5(%s))"
    args = [self.expires_lock, self.lock_token, self.subject]
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

    query = "UPDATE locks SET lock_expiration=0, lock_owner=0 WHERE \
lock_expiration=%s AND lock_owner=%s AND subject_hash=unhex(md5(%s))"
    args = [self.expires_lock, self.lock_token, self.subject]
    self.store._ExecuteQuery(query, args)

