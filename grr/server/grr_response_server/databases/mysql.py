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

from future.builtins import range

# Note: Please refer to server/setup.py for the MySQLdb version that is used.
# It is most likely not up-to-date because of our support for older OS.
import MySQLdb
from MySQLdb.constants import ER as mysql_error_constants

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
from grr_response_server.databases import mysql_users

# Maximum size of one SQL statement, including blob and protobuf data.
MAX_PACKET_SIZE = 20 << 20

# Maximum retry count:
_MAX_RETRY_COUNT = 5

# MySQL error codes:
_RETRYABLE_ERRORS = {
    mysql_error_constants.LOCK_WAIT_TIMEOUT,
    mysql_error_constants.LOCK_DEADLOCK,
    1637,  # TOO_MANY_CONCURRENT_TRXS, unavailable in MySQLdb 1.3.7
}

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


class Error(MySQLdb.Error):
  """Base Error for the MySQL datastore."""


class SchemaInitializationError(Error):
  """Raised when the setup of the MySQL schema fails."""


class EncodingEnforcementError(Error):
  """Raised when enforcing the UTF-8 encoding fails."""


def _CheckCollation(cursor):
  """Checks MySQL collation and warns if misconfigured."""

  # Do not fail for wrong collation, because changing it is harder than changing
  # the character set. Some providers only allow changing character set and then
  # use the default collation. Also, misconfigured collation is not expected to
  # have major negative impacts, since it only affects string sort order for
  # some locales.

  cur_collation_connection = _ReadVariable("collation_connection", cursor)
  if cur_collation_connection != COLLATION:
    logging.warning("Require MySQL collation_connection of %s, got %s.",
                    COLLATION, cur_collation_connection)

  cur_collation_database = _ReadVariable("collation_database", cursor)
  if cur_collation_database != COLLATION:
    logging.warning(
        "Require MySQL collation_database of %s, got %s."
        " To create your database, use: %s", COLLATION, cur_collation_database,
        CREATE_DATABASE_QUERY)


def _SetEncoding(cursor):
  """Sets MySQL encoding and collation for current connection."""
  cursor.execute("SET NAMES '{}' COLLATE '{}'".format(CHARACTER_SET, COLLATION))


def _CheckConnectionEncoding(cursor):
  """Enforces a sane UTF-8 encoding for the database connection."""
  cur_character_set = _ReadVariable("character_set_connection", cursor)
  if cur_character_set != CHARACTER_SET:
    raise EncodingEnforcementError(
        "Require MySQL character_set_connection of {}, got {}.".format(
            CHARACTER_SET, cur_character_set))


def _CheckDatabaseEncoding(cursor):
  """Enforces a sane UTF-8 encoding for the database."""
  cur_character_set = _ReadVariable("character_set_database", cursor)
  if cur_character_set != CHARACTER_SET:
    raise EncodingEnforcementError(
        "Require MySQL character_set_database of {}, got {}."
        " To create your database, use: {}".format(
            CHARACTER_SET, cur_character_set, CREATE_DATABASE_QUERY))


def _SetPacketSizeForFollowingConnections(cursor):
  """Sets max_allowed_packet globally for new connections (not current!)."""
  cur_packet_size = int(_ReadVariable("max_allowed_packet", cursor))

  if cur_packet_size < MAX_PACKET_SIZE:
    query = "SET GLOBAL max_allowed_packet={}".format(MAX_PACKET_SIZE)
    logging.warning(
        "MySQL max_allowed_packet of %d is required, got %d. Overwriting: %s",
        MAX_PACKET_SIZE, cur_packet_size, query)
    cursor.execute(query)


def _CheckPacketSize(cursor):
  """Checks that MySQL packet size is big enough for expected query size."""
  cur_packet_size = int(_ReadVariable("max_allowed_packet", cursor))
  if cur_packet_size < MAX_PACKET_SIZE:
    raise Error(
        "MySQL max_allowed_packet of {0} is required, got {1}. "
        "Please set max_allowed_packet={0} in your MySQL config.".format(
            MAX_PACKET_SIZE, cur_packet_size))


def _CheckLogFileSize(cursor):
  """Warns if MySQL log file size is not large enough for blob insertions."""

  # Do not fail, because users might not be able to change this for their
  # database. Instead, warn the user about the impacts.

  innodb_log_file_size = int(_ReadVariable("innodb_log_file_size", cursor))
  required_size = 10 * mysql_blobs.BLOB_CHUNK_SIZE
  if innodb_log_file_size < required_size:
    # See MySQL error 1118: The size of BLOB/TEXT data inserted in one
    # transaction is greater than 10% of redo log size. Increase the redo log
    # size using innodb_log_file_size.
    max_blob_size = innodb_log_file_size / 10
    max_blob_size_mib = max_blob_size / 2**20
    logging.warning(
        "MySQL innodb_log_file_size of %d is required, got %d. "
        "Storing Blobs bigger than %.4f MiB will fail.", required_size,
        innodb_log_file_size, max_blob_size_mib)


def _IsMariaDB(cursor):
  """Checks if we are running against MariaDB."""
  for variable in ["version", "version_comment"]:
    cursor.execute("SHOW VARIABLES LIKE %s;", (variable,))
    version = cursor.fetchone()
    if version and "MariaDB" in version[1]:
      return True
  return False


def _SetBinlogFormat(cursor):
  # We use some queries that are deemed unsafe for statement
  # based logging. MariaDB >= 10.2.4 has MIXED logging as a
  # default, for earlier versions we set it explicitly but that
  # requires SUPER privileges.
  if _ReadVariable("binlog_format", cursor) == "MIXED":
    return

  logging.info("Setting mysql server binlog_format to MIXED")
  cursor.execute("SET binlog_format = MIXED")


def _SetMariaDBMode(cursor):
  # MariaDB introduced raising warnings when INSERT IGNORE
  # encounters duplicate keys. This flag disables this behavior for
  # consistency.
  if _IsMariaDB(cursor):
    cursor.execute("SET @@OLD_MODE = CONCAT(@@OLD_MODE, "
                   "',NO_DUP_KEY_WARNINGS_WITH_IGNORE');")


def _CheckForSSL(cursor):
  key_path = config.CONFIG["Mysql.client_key_path"]
  if not key_path:
    # SSL not configured, nothing to do.
    return

  if _ReadVariable("have_ssl", cursor) == "YES":
    logging.info("SSL connection to MySQL enabled successfully.")
  else:
    raise RuntimeError("Unable to establish SSL connection to MySQL.")


def _InitializeSchema(cursor):
  """Initialize the database's schema."""
  for command in mysql_ddl.SCHEMA_SETUP:
    try:
      cursor.execute(command)
    except MySQLdb.MySQLError as e:
      raise SchemaInitializationError(
          "{}. Error occurred during execution of {}".format(
              e, command.strip()))


def _SetupDatabase(host, port, user, password, database, **kwargs):
  """Connect to the given MySQL host and create a utf8mb4_unicode_ci database.

  Args:
    host: The hostname to connect to.
    port: The port to connect to.
    user: The username to connect as.
    password: The password to connect with.
    database: The database name to create.
    **kwargs: Further MySQL connection arguments.
  """
  with contextlib.closing(
      MySQLdb.Connect(
          host=host, port=port, user=user, password=password,
          **kwargs)) as conn:
    with contextlib.closing(conn.cursor()) as cursor:
      _CheckForSSL(cursor)
      _SetMariaDBMode(cursor)
      _SetBinlogFormat(cursor)
      _SetPacketSizeForFollowingConnections(cursor)
      _SetEncoding(cursor)
      _CheckConnectionEncoding(cursor)
      _CheckLogFileSize(cursor)

      try:
        cursor.execute(CREATE_DATABASE_QUERY.format(database))
      except MySQLdb.MySQLError as e:
        #  Statement might fail if database exists, this is fine.
        if e.args[0] != mysql_error_constants.DB_CREATE_EXISTS:
          raise

      cursor.execute("USE {}".format(database))
      _CheckCollation(cursor)
      _InitializeSchema(cursor)


def _Connect(*args, **kwargs):
  """Connect to MySQL and check if server fulfills requirements."""
  conn = MySQLdb.Connect(*args, **kwargs)
  with contextlib.closing(conn.cursor()) as cursor:
    _CheckForSSL(cursor)
    _SetEncoding(cursor)
    _CheckConnectionEncoding(cursor)
    _CheckDatabaseEncoding(cursor)
    _SetMariaDBMode(cursor)
    _SetBinlogFormat(cursor)
    _CheckPacketSize(cursor)
  return conn


# pyformat: disable
class MysqlDB(mysql_artifacts.MySQLDBArtifactsMixin,
              mysql_blobs.MySQLDBBlobsMixin,  # Implements BlobStore.
              mysql_client_reports.MySQLDBClientReportsMixin,
              mysql_clients.MySQLDBClientMixin,
              mysql_cronjobs.MySQLDBCronJobMixin,
              mysql_events.MySQLDBEventMixin,
              mysql_flows.MySQLDBFlowMixin,
              mysql_foreman_rules.MySQLDBForemanRulesMixin,
              mysql_hunts.MySQLDBHuntMixin,
              mysql_paths.MySQLDBPathMixin,
              mysql_signed_binaries.MySQLDBSignedBinariesMixin,
              mysql_users.MySQLDBUsersMixin,
              db_module.Database):
  # pyformat: enable
  """Implements db.Database and blob_store.BlobStore using MySQL."""

  def ClearTestDB(self):
    # TODO(user): This is required because GRRBaseTest.setUp() calls it.
    # Refactor database test to provide their own logic of cleanup in tearDown.
    pass

  def __init__(self, host=None, port=None, user=None, password=None,
               database=None):
    """Creates a datastore implementation.

    Args:
      host: Passed to MySQLdb.Connect when creating a new connection.
      port: Passed to MySQLdb.Connect when creating a new connection.
      user: Passed to MySQLdb.Connect when creating a new connection.
      password: Passed to MySQLdb.Connect when creating a new connection.
      database: Passed to MySQLdb.Connect when creating a new connection.
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

    self._args = self._GetConnectionArgs(host=host, port=port, user=user,
                                         password=password, database=database)

    _SetupDatabase(**self._args)

    max_pool_size = config.CONFIG.Get("Mysql.conn_pool_max", 10)
    self.pool = mysql_pool.Pool(self._Connect, max_size=max_pool_size)

    self.handler_thread = None
    self.handler_stop = True

    self.flow_processing_request_handler_thread = None
    self.flow_processing_request_handler_stop = None
    self.flow_processing_request_handler_pool = (
        threadpool.ThreadPool.Factory(
            "flow_processing_pool", min_threads=2, max_threads=50))
    self.flow_processing_request_handler_pool.Start()

  def _Connect(self):
    return _Connect(**self._args)

  def _GetConnectionArgs(self, host=None, port=None, user=None, password=None,
                         database=None):
    connection_args = dict(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        autocommit=False,
        use_unicode=True,
        charset=CHARACTER_SET
    )

    if host is None:
      connection_args["host"] = config.CONFIG["Mysql.host"]
    if port is None:
      connection_args["port"] = config.CONFIG["Mysql.port"]
    if user is None:
      connection_args["user"] = config.CONFIG["Mysql.username"]
    if password is None:
      connection_args["password"] = config.CONFIG["Mysql.password"]
    if database is None:
      connection_args["database"] = config.CONFIG["Mysql.database"]

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
