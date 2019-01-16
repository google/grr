#!/usr/bin/env python
"""MySQL implementation of the GRR relational database abstraction.

See grr/server/db.py for interface.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib
import logging
import math
import random
import time
import warnings

from builtins import range  # pylint: disable=redefined-builtin
import MySQLdb

from grr_response_core import config
from grr_response_server import db as db_module
from grr_response_server import threadpool
from grr_response_server.databases import mysql_artifacts
from grr_response_server.databases import mysql_blobs
from grr_response_server.databases import mysql_client_reports
from grr_response_server.databases import mysql_clients
from grr_response_server.databases import mysql_cronjobs
from grr_response_server.databases import mysql_ddl
from grr_response_server.databases import mysql_events
from grr_response_server.databases import mysql_flows
from grr_response_server.databases import mysql_foreman_rules
from grr_response_server.databases import mysql_hunts
from grr_response_server.databases import mysql_paths
from grr_response_server.databases import mysql_pool
from grr_response_server.databases import mysql_signed_binaries
from grr_response_server.databases import mysql_stats
from grr_response_server.databases import mysql_users

# Maximum retry count:
_MAX_RETRY_COUNT = 5

# MySQL error codes:
_RETRYABLE_ERRORS = {
    1205,  # ER_LOCK_WAIT_TIMEOUT
    1213,  # ER_LOCK_DEADLOCK
    1637,  # ER_TOO_MANY_CONCURRENT_TRXS
}

_ER_BAD_DB_ERROR = 1049

# Enforce sensible defaults for MySQL connection and database:
# Use utf8mb4_unicode_ci collation and utf8mb4 character set.
# Do not use what MySQL calls "utf8", it is only a limited subset of utf-8.
# Do not use utf8mb4_general_ci, it has minor differences to the UTF-8 spec.
CHARACTER_SET = "utf8mb4"
COLLATION = "utf8mb4_unicode_ci"
CREATE_DATABASE_QUERY = (
    "CREATE DATABASE {} CHARACTER SET {} COLLATE {};".format(
        "{}", CHARACTER_SET, COLLATION))  # Keep first placeholder for later.


def _IsRetryable(error):
  """Returns whether error is likely to be retryable."""
  if not isinstance(error, MySQLdb.OperationalError):
    return False
  if not error.args:
    return False
  code = error.args[0]
  return code in _RETRYABLE_ERRORS


def _ReadVariable(name, cursor):
  cursor.execute("SHOW VARIABLES LIKE %s", [name])
  row = cursor.fetchone()
  if row is None:
    return None
  else:
    return row[1]


def _EnforceEncoding(cursor):
  """Enforce a sane UTF-8 encoding for the DB cursor."""
  cursor.execute("SET NAMES '{}' COLLATE '{}'".format(CHARACTER_SET, COLLATION))

  collation_connection = _ReadVariable("collation_connection", cursor)
  if collation_connection != COLLATION:
    raise RuntimeError(
        "Require MySQL collation_connection of {}, got {}.".format(
            COLLATION, collation_connection))

  collation_database = _ReadVariable("collation_database", cursor)
  if collation_database != COLLATION:
    raise RuntimeError("Require MySQL collation_database of {}, got {}."
                       " To create your database, use: {}".format(
                           COLLATION, collation_database,
                           CREATE_DATABASE_QUERY))

  character_set_database = _ReadVariable("character_set_database", cursor)
  if character_set_database != CHARACTER_SET:
    raise RuntimeError("Require MySQL character_set_database of {}, got {}."
                       " To create your database, use: {}".format(
                           COLLATION, collation_connection,
                           CREATE_DATABASE_QUERY))

  character_set_connection = _ReadVariable("character_set_connection", cursor)
  if character_set_connection != CHARACTER_SET:
    raise RuntimeError(
        "Require MySQL character_set_connection of {}, got {}.".format(
            CHARACTER_SET, character_set_connection))


def CreateDatabase(host, port, user, passwd, db, **kwargs):
  """Connect to the given MySQL host and create a utf8mb4_unicode_ci database.

  Args:
    host: The hostname to connect to.
    port: The port to connect to.
    user: The username to connect as.
    passwd: The password to connect with.
    db: The database name to create.
    **kwargs: Further MySQL connection arguments.
  """
  con = MySQLdb.Connect(
      host=host, port=port, user=user, passwd=passwd, **kwargs)
  cursor = con.cursor()
  cursor.execute(CREATE_DATABASE_QUERY.format(db))
  cursor.close()
  con.close()


# pyformat: disable
class MysqlDB(mysql_artifacts.MySQLDBArtifactsMixin,
              mysql_blobs.MySQLDBBlobsMixin,
              mysql_client_reports.MySQLDBClientReportsMixin,
              mysql_clients.MySQLDBClientMixin,
              mysql_cronjobs.MySQLDBCronJobMixin,
              mysql_events.MySQLDBEventMixin,
              mysql_flows.MySQLDBFlowMixin,
              mysql_foreman_rules.MySQLDBForemanRulesMixin,
              mysql_hunts.MySQLDBHuntMixin,
              mysql_paths.MySQLDBPathMixin,
              mysql_signed_binaries.MySQLDBSignedBinariesMixin,
              mysql_stats.MySQLDBStatsMixin,
              mysql_users.MySQLDBUsersMixin,
              db_module.Database):
  """Implements db_module.Database using mysql.

  # pyformat: enable

  See server/db.py for a full description of the interface.
  """

  def __init__(self, host=None, port=None, user=None, passwd=None, db=None):
    """Creates a datastore implementation.

    Args:
      host: Passed to MySQLdb.Connect when creating a new connection.
      port: Passed to MySQLdb.Connect when creating a new connection.
      user: Passed to MySQLdb.Connect when creating a new connection.
      passwd: Passed to MySQLdb.Connect when creating a new connection.
      db: Passed to MySQLdb.Connect when creating a new connection.
    """

    # Turn all SQL warnings not mentioned below into exceptions.
    warnings.filterwarnings("error", category=MySQLdb.Warning)

    for message in [
        # We use INSERT IGNOREs which generate useless duplicate entry warnings.
        ".*Duplicate entry.*",
        # Same for CREATE TABLE IF NOT EXISTS.
        ".*Table '.*' already exists",
        # And CREATE INDEX IF NOT EXISTS.
        ".*Duplicate key name.*",
        ]:
      warnings.filterwarnings("ignore", category=MySQLdb.Warning,
                              message=message)

    def Connect():
      """Returns a MySQLdb connection and creates the db if it doesn't exist."""
      args = self._GetConnectionArgs(
          host=host, port=port, user=user, passwd=passwd, db=db)
      try:
        return MySQLdb.Connect(**args)
      except MySQLdb.Error as e:
        # Database does not exist
        if e[0] == _ER_BAD_DB_ERROR:
          CreateDatabase(**args)
          return MySQLdb.Connect(**args)
        else:
          raise

    self.pool = mysql_pool.Pool(Connect)
    with contextlib.closing(self.pool.get()) as connection:
      with contextlib.closing(connection.cursor()) as cursor:
        self._MariaDBCompatibility(cursor)
        self._SetBinlogFormat(cursor)
        self._InitializeSchema(cursor)
        self._CheckForSSL(cursor)
        _EnforceEncoding(cursor)
    self.handler_thread = None
    self.handler_stop = True

    self.flow_processing_request_handler_thread = None
    self.flow_processing_request_handler_stop = None
    self.flow_processing_request_handler_pool = (
        threadpool.ThreadPool.Factory(
            "flow_processing_pool", min_threads=2, max_threads=50))
    self.flow_processing_request_handler_pool.Start()

  def _GetConnectionArgs(self, host=None, port=None, user=None, passwd=None,
                         db=None):
    connection_args = dict(
        host=host,
        port=port,
        user=user,
        passwd=passwd,
        db=db,
        autocommit=False,
        use_unicode=True,
        charset=CHARACTER_SET
    )

    if host is None:
      connection_args["host"] = config.CONFIG["Mysql.host"]
    if port is None:
      connection_args["port"] = config.CONFIG["Mysql.port"]
    if user is None:
      connection_args["user"] = config.CONFIG["Mysql.database_username"]
    if passwd is None:
      connection_args["passwd"] = config.CONFIG["Mysql.database_password"]
    if db is None:
      connection_args["db"] = config.CONFIG["Mysql.rel_db_name"]

    key_path = config.CONFIG["Mysql.client_key_path"]
    if key_path:
      cert_path = config.CONFIG["Mysql.client_cert_path"]
      ca_cert_path = config.CONFIG["Mysql.ca_cert_path"]
      logging.debug("Client key file configured, trying to use SSL.")

      connection_args["ssl"] = {
          "key": key_path,
          "cert": cert_path,
          "ca": ca_cert_path,
      }
    return connection_args

  def Close(self):
    self.pool.close()

  def _CheckForMariaDB(self, cursor):
    """Checks if we are running against MariaDB."""
    for variable in ["version", "version_comment"]:
      cursor.execute("SHOW VARIABLES LIKE %s;", (variable,))
      version = cursor.fetchone()
      if version and "MariaDB" in version[1]:
        return True
    return False

  def _SetBinlogFormat(self, cursor):
    # We use some queries that are deemed unsafe for statement
    # based logging. MariaDB >= 10.2.4 has MIXED logging as a
    # default, for earlier versions we set it explicitly but that
    # requires SUPER privileges.
    if _ReadVariable("binlog_format", cursor) == "MIXED":
      return

    logging.info("Setting mysql server binlog_format to MIXED")
    cursor.execute("SET binlog_format=MIXED")

  def _MariaDBCompatibility(self, cursor):
    # MariaDB introduced raising warnings when INSERT IGNORE
    # encounters duplicate keys. This flag disables this behavior for
    # consistency.
    if self._CheckForMariaDB(cursor):
      cursor.execute("SET @@OLD_MODE = CONCAT(@@OLD_MODE, "
                     "',NO_DUP_KEY_WARNINGS_WITH_IGNORE');")

  def _CheckForSSL(self, cursor):
    key_path = config.CONFIG["Mysql.client_key_path"]
    if not key_path:
      # SSL not configured, nothing to do.
      return

    if _ReadVariable("have_ssl", cursor) == "YES":
      logging.debug("SSL enabled successfully")
    else:
      raise RuntimeError("Unable to establish SSL connection to MySQL.")

  def _InitializeSchema(self, cursor):
    """Initialize the database's schema."""
    for command in mysql_ddl.SCHEMA_SETUP:
      try:
        cursor.execute(command)
      except Exception:
        logging.error("Failed to execute DDL: %s", command)
        raise

  def _RunInTransaction(self, function, readonly=False):
    """Runs function within a transaction.

    Allocates a connection, begins a transaction on it and passes the connection
    to function.

    If function finishes without raising, the transaction is committed.

    If function raises, the transaction will be rolled back, if a retryable
    database error is raised, the operation may be repeated.

    Args:
      function: A function to be run, must accept a single MySQLdb.connection
        parameter.
      readonly: Indicates that only a readonly (snapshot) transaction is
        required.

    Returns:
      The value returned by the last call to function.

    Raises: Any exception raised by function.
    """
    start_query = "START TRANSACTION;"
    if readonly:
      start_query = "START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;"

    for retry_count in range(_MAX_RETRY_COUNT):
      with contextlib.closing(self.pool.get()) as connection:
        try:
          with contextlib.closing(connection.cursor()) as cursor:
            self._SetBinlogFormat(cursor)
            cursor.execute(start_query)

          ret = function(connection)

          if not readonly:
            connection.commit()
          return ret
        except MySQLdb.OperationalError as e:
          connection.rollback()
          # Re-raise if this was the last attempt.
          if retry_count >= _MAX_RETRY_COUNT or not _IsRetryable(e):
            raise
      # Simple delay, with jitter.
      #
      # TODO(user): Move to something more elegant, e.g. integrate a
      # general retry or backoff library.
      time.sleep(random.uniform(1.0, 2.0) * math.pow(1.5, retry_count))
    # Shouldn't happen, because we should have re-raised whatever caused the
    # last try to fail.
    raise Exception("Looped ended early - last exception swallowed.")  # pylint: disable=g-doc-exception
