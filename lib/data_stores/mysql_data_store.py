#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""An implementation of a data store based on mysql."""


import Queue
import threading
import time
import MySQLdb
from MySQLdb import cursors

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils


config_lib.DEFINE_string("Mysql.database_name", default="grr",
                         help="Name of the database to use.")

config_lib.DEFINE_string("Mysql.table_name", default="aff4",
                         help="Name of the table to use.")

config_lib.DEFINE_string("Mysql.database_username", default="root",
                         help="The user to connect to the database.")

config_lib.DEFINE_string("Mysql.database_password", default="",
                         help="The password to connect to the database.")

config_lib.DEFINE_integer("Mysql.transaction_timeout", default=60,
                          help="How long do we wait for a transaction lock.")


# pylint: disable=nonstandard-exception
class Error(data_store.Error):
  """Base class for all exceptions in this module."""


class Filter(object):
  """The baseclass for filters."""
  __metaclass__ = registry.MetaclassRegistry

  # Automatically register plugins as class attributes
  include_plugins_as_attributes = True

  def Query(self):
    """Create a combined query for all our parts."""
    return ("", [])


class AndFilter(Filter):
  """A Logical And operator."""

  def __init__(self, *parts):
    self.parts = parts
    super(AndFilter, self).__init__()

  def Query(self):
    """Create a combined query for all our parts."""
    subqueries = []
    parameters = []
    for part in self.parts:
      subquery, subparams = part.Query()
      subqueries.append(subquery)
      parameters.extend(subparams)

    query = "select subject from `%s` where " % data_store.DB.table_name
    query += " and ".join(["subject in (%s)" % x for x in subqueries])
    query += " group by subject"

    return (query, parameters)


class SubjectContainsFilter(Filter):
  """Applies a RegEx to the subject name."""

  def __init__(self, regex):
    """Constructor.

    Args:
       regex: Must match the row name.
    """
    self.regex = regex
    super(SubjectContainsFilter, self).__init__()

  def Query(self):
    return ("select subject from `%s` where subject rlike %%s "
            "group by subject" % data_store.DB.table_name, [self.regex])


class OrFilter(AndFilter):
  """A Logical Or operator."""

  def Query(self):
    return (("select subject from `%s` where subject in " %
             data_store.DB.table_name) +
            " or ".join(["(%s)" % part.Query() for part in self.parts]) +
            "group by subject")


class HasPredicateFilter(Filter):

  def __init__(self, attribute_name):
    self.attribute_name = attribute_name
    Filter.__init__(self)

  def Query(self):
    return ("select subject from `%s` where attribute = %%s group by subject" %
            data_store.DB.table_name, [self.attribute_name])


class PredicateContainsFilter(Filter):
  """Applies a RegEx on the content of an attribute."""

  def __init__(self, attribute_name, regex):
    self.regex = regex
    self.attribute_name = attribute_name
    super(PredicateContainsFilter, self).__init__()

  def Query(self):
    return ("select subject from `%s` where attribute = %%s and value_string "
            "rlike %%s group by subject" % data_store.DB.table_name,
            [self.attribute_name, self.regex])


class PredicateGreaterThanFilter(Filter):
  """A filter to be applied to DataStore.Query.

  This filters all subjects which have this predicate greater than the value
  specified.
  """

  operator = ">"

  def __init__(self, attribute_name, value):
    """Constructor.

    Args:
       attribute_name: The attribute name must be set.
       value: The value that attribute must be greater than.
    """
    self.attribute_name = utils.SmartUnicode(attribute_name)
    self.value = value
    super(PredicateGreaterThanFilter, self).__init__()

  def Query(self):
    return ("select subject from `%s` where attribute=%%s and "
            "value_integer %s %%s" % (data_store.DB.table_name, self.operator),
            [self.attribute_name, self.value])


class PredicateGreaterEqualFilter(PredicateGreaterThanFilter):
  operator = ">="


class PredicateLessThanFilter(PredicateGreaterThanFilter):
  """A filter to be applied to DataStore.Query.

  This filters all subjects which have this predicate less than the value
  specified.
  """
  operator = "<"


class PredicateLessEqualFilter(PredicateGreaterThanFilter):
  operator = "<="


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
      self.dbh = MySQLdb.connect(
          user=config_lib.CONFIG["Mysql.database_username"],
          db=database, charset="utf8",
          passwd=config_lib.CONFIG["Mysql.database_password"],
          cursorclass=cursors.DictCursor)

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
      # If the connection becomes stale we reconnect.
      self._MakeConnection(database=config_lib.CONFIG["Mysql.database_name"])
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

  def __init__(self):
    super(MySQLDataStore, self).__init__()
    self.filter = Filter
    self.pool = ConnectionPool()
    self.lock = threading.Lock()
    self.to_set = []
    self.table_name = config_lib.CONFIG["Mysql.table_name"]

  def Initialize(self):
    with MySQLConnection() as connection:
      try:
        connection.Execute("desc `%s`" % self.table_name)
      except MySQLdb.Error:
        self.RecreateDataBase(connection)

  def RecreateDataBase(self, connection):
    """Drops the table and creates a new one."""
    try:
      connection.Execute("drop table `%s`" % self.table_name)
    except MySQLdb.OperationalError:
      pass
    connection.Execute("""
CREATE TABLE `%s` (
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

  def DeleteAttributes(self, subject, attributes, sync=None, token=None):
    """Remove some attributes from a subject."""
    _ = sync  # Unused

    self.security_manager.CheckDataStoreAccess(token, [subject], "w")
    with self.pool.GetConnection() as cursor:
      query = ("delete from `%s` where hash=md5(%%s) and "
               "subject=%%s and attribute in (%s) " % (
                   self.table_name,
                   ",".join(["%s"] * len(attributes))))

      args = [subject, subject] + list(attributes)
      cursor.Execute(query, args)

  def DeleteSubject(self, subject, token=None):
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

  def Escape(self, string):
    """Escape the string so it can be interpolated into an sql statement."""
    # This needs to come from a connection object so it is escaped according to
    # the current charset:
    with self.pool.GetConnection() as cursor:
      return cursor.dbh.escape(string)

  def ResolveMulti(self, subject, predicates, decoder=None, token=None,
                   timestamp=None):
    """Resolves multiple predicates at once for one subject."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "r")

    with self.pool.GetConnection() as cursor:
      query = ("select * from `%s` where hash = md5(%%s) and "
               "subject = %%s  and attribute in (%s) " % (
                   self.table_name,
                   ",".join(["%s"] * len(predicates)),
                   ))

      args = [subject, subject] + predicates[:]

      query += self._TimestampToQuery(timestamp, args)

      result = cursor.Execute(query, args)

    for row in result:
      subject = row["subject"]
      value = self.DecodeValue(row, decoder=decoder)

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

  def MultiResolveRegex(self, subjects, predicate_regex, token=None,
                        decoder=None, timestamp=None, limit=None):
    self.security_manager.CheckDataStoreAccess(token, subjects, "r")
    if not subjects:
      return {}

    with self.pool.GetConnection() as cursor:
      query = "select * from `%s` where hash in (%s) and subject in (%s) " % (
          self.table_name, ",".join(["md5(%s)"] * len(subjects)),
          ",".join(["%s"] * len(subjects)),
          )

      # Allow users to specify a single string here.
      if isinstance(predicate_regex, basestring):
        predicate_regex = [predicate_regex]

      query += "and (" + " or ".join(
          ["attribute rlike %s"] * len(predicate_regex)) + ")"

      args = subjects[:] + subjects[:] + predicate_regex

      query += self._TimestampToQuery(timestamp, args)

      seen = set()
      result = {}

      for row in cursor.Execute(query, args):
        subject = row["subject"]
        value = self.DecodeValue(row, decoder=decoder)

        # Only record the latest results. This is suboptimal since it always
        # returns all the results from the db. Can we do better with better SQL?
        if timestamp is None or timestamp == self.NEWEST_TIMESTAMP:
          if (row["attribute"], row["subject"]) in seen:
            continue
          else:
            seen.add((row["attribute"], row["subject"]))

        result.setdefault(subject, []).append((row["attribute"], value,
                                               row["age"]))

        if limit > 0 and len(result) > limit:
          break

      return result

  def MultiSet(self, subject, values, timestamp=None, token=None, replace=True,
               sync=True, to_delete=None):
    """Set multiple predicates' values for this subject in one operation."""
    self.security_manager.CheckDataStoreAccess(token, [subject], "w")

    if timestamp is None:
      timestamp = time.time() * 1e6

    # Prepare a bulk insert operation.
    subject = utils.SmartUnicode(subject)
    if to_delete:
      self.DeleteAttributes(subject, to_delete, token=token)

    to_set = []

    # Build a document for each unique timestamp.
    for attribute, sequence in values.items():
      for value in sequence:
        if isinstance(value, tuple):
          value, entry_timestamp = value
        else:
          entry_timestamp = timestamp

        predicate = utils.SmartUnicode(attribute)
        prefix = predicate.split(":", 1)[0]

        # Replacing means to delete all versions of the attribute first.
        if replace:
          self.DeleteAttributes(subject, [attribute], token=token)

        to_set.extend(
            [subject, subject, int(entry_timestamp), predicate, prefix] +
            self._Encode(attribute, value))

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
      elif attribute.attribute_type.data_store_type == "integer":
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
      elif attribute.attribute_type.data_store_type == "integer":
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

  def DecodeValue(self, row, decoder=None):
    """Decode the value from the row object."""
    value = row["value_string"]
    if value is None:
      value = row["value_integer"]

    if value is None:
      value = row["value_binary"]

    if value is not None and decoder:
      value = self.Decode(value, decoder=decoder)

    return value

  def Query(self, attributes=None, filter_obj=None, subject_prefix="",
            token=None, subjects=None, limit=100, timestamp=None):
    """Query the database according to the filter."""
    try:
      skip, limit = limit
    except TypeError:
      skip = 0

    if attributes is None: attributes = []

    if u"aff4:type" not in attributes:
      attributes.append(u"aff4:type")

    if filter_obj is None:
      filter_obj = Filter()

    with self.pool.GetConnection() as cursor:
      query = "select subject from `%s` where " % self.table_name
      parameters = []

      subquery, subparams = filter_obj.Query()
      if subquery:
        query += "subject in (%s)" % subquery
        parameters.extend(subparams)
      else:
        query += "1"

      if subjects:
        query += " and subject in (%s)" % (",".join(
            ["%s"] * len(subjects)))
        parameters.extend(subjects)

      elif subject_prefix:
        query += " and substring(subject, 1, %s) = %s"
        parameters.append(len(subject_prefix))
        parameters.append(subject_prefix)

      query += " group by subject order by subject limit %s, %s"
      parameters.extend((skip, limit))

      total_hits = sorted(
          (row["subject"] for row in cursor.Execute(query, parameters)))

      result_set = data_store.ResultSet()
      for subject, data in sorted(self.MultiResolveRegex(
          total_hits, attributes, token=token,
          timestamp=timestamp).items()):
        result = dict(subject=[(subject, 0)])
        for predicate, value, ts in data:
          result.setdefault(predicate, []).append((value, ts))

        try:
          self.security_manager.CheckDataStoreAccess(token, [subject], "rq")

          result_set.Append(result)
        except access_control.UnauthorizedAccess:
          continue

      result_set.total_count = len(total_hits)

      return result_set

  def Transaction(self, subject, token=None):
    return MySQLTransaction(self, subject, token=token)


class MySQLTransaction(data_store.Transaction):
  """The Mysql data store transaction object.

  This object does not aim to ensure ACID like consistently. We only ensure that
  two simultaneous locks can not be held on the same RDF subject.

  This means that the first thread which grabs the lock is considered the owner
  of the transaction. Any subsequent transactions on the same subject will fail
  immediately with data_store.TransactionError.

  A lock is considered expired after a certain time.
  """

  def __init__(self, store, subject, token=None):
    """Ensure we can take a lock on this subject."""
    self.store = store
    self.token = token
    self.subject = utils.SmartUnicode(subject)
    self.table_name = store.table_name
    with store.pool.GetConnection() as connection:
      self.current_lock = int(time.time() * 1e6)

      # This will take over the lock if the lock is too old.
      connection.Execute(
          "update `%s` set value_integer=%%s where "
          "attribute='transaction' and subject=%%s and hash=md5(%%s) and "
          "(value_integer < %%s)" % self.table_name,
          (self.current_lock, subject, subject,
           (time.time()-config_lib.CONFIG["Mysql.transaction_timeout"]) * 1e6))

      self.CheckForLock(connection, subject)

  def CheckForLock(self, connection, subject):
    """Checks that the lock has stuck."""

    for row in connection.Execute(
        "select * from `%s` where subject=%%s and hash=md5(%%s) and "
        "attribute='transaction'" % self.table_name, (subject, subject)):

      # We own this lock now.
      if row["value_integer"] == self.current_lock:
        return

      # Someone else owns this lock.
      else:
        raise data_store.TransactionError("Subject %s is locked" % subject)

    # If we get here the row does not exist:
    connection.Execute(
        "insert ignore into `%s` set value_integer=%%s, "
        "attribute='transaction', subject=%%s, hash=md5(%%s) " %
        self.table_name, (self.current_lock, self.subject, self.subject))

    self.CheckForLock(connection, subject)

  def DeleteAttribute(self, predicate):
    self.store.DeleteAttributes(self.subject, [predicate], sync=True,
                                token=self.token)

  def Resolve(self, predicate, decoder=None):
    return self.store.Resolve(self.subject, predicate, decoder=decoder,
                              token=self.token)

  def ResolveRegex(self, predicate_regex, decoder=None, timestamp=None):
    return self.store.ResolveRegex(self.subject, predicate_regex,
                                   decoder=decoder, token=self.token,
                                   timestamp=timestamp)

  def Set(self, predicate, value, timestamp=None, replace=True):
    self.store.Set(self.subject, predicate, value, timestamp=timestamp,
                   replace=replace, token=self.token)

  def Abort(self):
    self.Commit()

  def Commit(self):
    # Remove the lock on the document. Note that this only resets the lock if
    # we actually hold it (value_integer == self.current_lock).
    with self.store.pool.GetConnection() as connection:
      connection.Execute(
          "update `%s` set value_integer=0 where "
          "attribute='transaction' and value_integer=%%s and hash=md5(%%s) and "
          "subject=%%s" % self.table_name,
          (self.current_lock, self.subject, self.subject))

  def __del__(self):
    try:
      self.Abort()
    except Exception:  # This can raise on cleanup pylint: disable=broad-except
      pass
