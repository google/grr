#!/usr/bin/env python
"""MySQL implementation of the GRR relational database abstraction.

See grr/server/db.py for interface.
"""

from collections.abc import Callable
import contextlib
import logging
import math
import random
import time
from typing import Union
import warnings

# Note: Please refer to server/setup.py for the MySQLdb version that is used.
# It is most likely not up-to-date because of our support for older OS.
import MySQLdb
from MySQLdb.constants import CR as mysql_conn_errors
from MySQLdb.constants import ER as mysql_errors

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_server import threadpool
from grr_response_server.databases import db as db_module
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_artifacts
from grr_response_server.databases import mysql_blob_keys
from grr_response_server.databases import mysql_blobs
from grr_response_server.databases import mysql_clients
from grr_response_server.databases import mysql_cronjobs
from grr_response_server.databases import mysql_events
from grr_response_server.databases import mysql_flows
from grr_response_server.databases import mysql_foreman_rules
from grr_response_server.databases import mysql_hunts
from grr_response_server.databases import mysql_migration
from grr_response_server.databases import mysql_paths
from grr_response_server.databases import mysql_pool
from grr_response_server.databases import mysql_signed_binaries
from grr_response_server.databases import mysql_signed_commands
from grr_response_server.databases import mysql_users
from grr_response_server.databases import mysql_utils
from grr_response_server.databases import mysql_yara

# Maximum size of one SQL statement, including blob and protobuf data.
MAX_PACKET_SIZE = 20 << 21

# Maximum retry count:
_MAX_RETRY_COUNT = 5

# MySQL error codes:
_RETRYABLE_ERRORS = frozenset([
    mysql_conn_errors.SERVER_GONE_ERROR,
    mysql_errors.LOCK_WAIT_TIMEOUT,
    mysql_errors.LOCK_DEADLOCK,
    1637,  # TOO_MANY_CONCURRENT_TRXS, unavailable in MySQLdb 1.3.7
    mysql_conn_errors.CONN_HOST_ERROR,
    mysql_conn_errors.SERVER_LOST,
])

# Enforce sensible defaults for MySQL connection and database:
# Use utf8mb4_unicode_ci collation and utf8mb4 character set.
# Do not use what MySQL calls "utf8", it is only a limited subset of utf-8.
# Do not use utf8mb4_general_ci, it has minor differences to the UTF-8 spec.
CHARACTER_SET = "utf8mb4"
COLLATION = "utf8mb4_unicode_ci"
CREATE_DATABASE_QUERY = (
    "CREATE DATABASE `{}` CHARACTER SET {} COLLATE {}".format(
        "{}", CHARACTER_SET, COLLATION
    )  # Keep first placeholder for later.
)


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


def _SetGlobalVariable(name, value, cursor):
  cursor.execute("SET GLOBAL {}=%s".format(name), [value])


def _SetSessionVariable(name, value, cursor):
  cursor.execute("SET {}=%s".format(name), [value])


class Error(MySQLdb.Error):
  """Base Error for the MySQL datastore."""


class SchemaInitializationError(Error):
  """Raised when the setup of the MySQL schema fails."""


class EncodingEnforcementError(Error):
  """Raised when enforcing the UTF-8 encoding fails."""


class MaxAllowedPacketSettingTooLowError(Error):
  """Raises when MySQL's max_allowed_packet setting is too low."""


def _CheckCollation(cursor):
  """Checks MySQL collation and warns if misconfigured."""

  # Do not fail for wrong collation, because changing it is harder than changing
  # the character set. Some providers only allow changing character set and then
  # use the default collation. Also, misconfigured collation is not expected to
  # have major negative impacts, since it only affects string sort order for
  # some locales.

  cur_collation_connection = _ReadVariable("collation_connection", cursor)
  if cur_collation_connection != COLLATION:
    logging.warning(
        "Require MySQL collation_connection of %s, got %s.",
        COLLATION,
        cur_collation_connection,
    )

  cur_collation_database = _ReadVariable("collation_database", cursor)
  if cur_collation_database != COLLATION:
    logging.warning(
        "Require MySQL collation_database of %s, got %s."
        " To create your database, use: %s",
        COLLATION,
        cur_collation_database,
        CREATE_DATABASE_QUERY,
    )


def _SetEncoding(cursor):
  """Sets MySQL encoding and collation for current connection."""
  cursor.execute("SET NAMES '{}' COLLATE '{}'".format(CHARACTER_SET, COLLATION))


def _SetSqlMode(cursor):
  """Sets session-level sql_mode variable to a well defined value."""
  incompatible_modes = [
      "NO_ZERO_IN_DATE",
      "NO_ZERO_DATE",
      "ERROR_FOR_DIVISION_BY_ZERO",
      "STRICT_TRANS_TABLES",
  ]

  sql_mode = _ReadVariable("sql_mode", cursor)
  if sql_mode is None:
    raise Error("Unable to read sql_mode variable.")

  components = [x.strip() for x in sql_mode.split(",")]
  filtered_components = [
      x for x in components if x.upper() not in incompatible_modes
  ]
  cursor.execute("SET SESSION sql_mode = %s", [",".join(filtered_components)])


def _CheckConnectionEncoding(cursor):
  """Enforces a sane UTF-8 encoding for the database connection."""
  cur_character_set = _ReadVariable("character_set_connection", cursor)
  if cur_character_set != CHARACTER_SET:
    raise EncodingEnforcementError(
        "Require MySQL character_set_connection of {}, got {}.".format(
            CHARACTER_SET, cur_character_set
        )
    )


def _CheckDatabaseEncoding(cursor):
  """Enforces a sane UTF-8 encoding for the database."""
  cur_character_set = _ReadVariable("character_set_database", cursor)
  if cur_character_set != CHARACTER_SET:
    raise EncodingEnforcementError(
        "Require MySQL character_set_database of {}, got {}."
        " To create your database, use: {}".format(
            CHARACTER_SET, cur_character_set, CREATE_DATABASE_QUERY
        )
    )


def _SetPacketSizeForFollowingConnections(cursor):
  """Sets max_allowed_packet globally for new connections (not current!)."""
  cur_packet_size = int(_ReadVariable("max_allowed_packet", cursor))

  if cur_packet_size < MAX_PACKET_SIZE:
    logging.warning(
        "MySQL max_allowed_packet of %d is required, got %d. Overwriting.",
        MAX_PACKET_SIZE,
        cur_packet_size,
    )
    try:
      _SetGlobalVariable("max_allowed_packet", MAX_PACKET_SIZE, cursor)
    except MySQLdb.OperationalError as e:
      logging.error(e)

      msg = (
          "Failed to override max_allowed_packet setting. "
          "max_allowed_packet must be < %d. Please update MySQL "
          "configuration or grant GRR sufficient privileges to "
          "override global variables." % MAX_PACKET_SIZE
      )
      logging.error(msg)
      raise MaxAllowedPacketSettingTooLowError(msg)


def _CheckPacketSize(cursor):
  """Checks that MySQL packet size is big enough for expected query size."""
  cur_packet_size = int(_ReadVariable("max_allowed_packet", cursor))
  if cur_packet_size < MAX_PACKET_SIZE:
    raise Error(
        "MySQL max_allowed_packet of {0} is required, got {1}. "
        "Please set max_allowed_packet={0} in your MySQL config.".format(
            MAX_PACKET_SIZE, cur_packet_size
        )
    )


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
        "Storing Blobs bigger than %.4f MiB will fail.",
        required_size,
        innodb_log_file_size,
        max_blob_size_mib,
    )


def _IsMariaDB(cursor):
  """Checks if we are running against MariaDB."""
  for variable in ["version", "version_comment"]:
    cursor.execute("SHOW VARIABLES LIKE %s", (variable,))
    version = cursor.fetchone()
    if version and "MariaDB" in version[1]:
      return True
  return False


def _SetBinlogFormat(cursor):
  """Sets database's binlog_format, if needed."""
  # We use some queries that are deemed unsafe for statement based logging.
  # MariaDB >= 10.2.4 has MIXED logging as a default, CloudSQL has ROW
  # logging preconfigured (and that can't be changed).
  #
  # If neither MIXED nor ROW logging is used, we set binlog_format explicitly
  # (requires SUPER privileges).
  if _ReadVariable("binlog_format", cursor) in ["MIXED", "ROW"]:
    return

  logging.info("Setting mysql server binlog_format to MIXED")
  cursor.execute("SET binlog_format = MIXED")


def _SetMariaDBMode(cursor):
  # MariaDB introduced raising warnings when INSERT IGNORE
  # encounters duplicate keys. This flag disables this behavior for
  # consistency.
  if _IsMariaDB(cursor):
    cursor.execute(
        "SET @@OLD_MODE = CONCAT(@@OLD_MODE, "
        "',NO_DUP_KEY_WARNINGS_WITH_IGNORE')"
    )


def _CheckForSSL(cursor):
  key_path = config.CONFIG["Mysql.client_key_path"]
  if not key_path:
    # SSL not configured, nothing to do.
    return

  if _ReadVariable("have_ssl", cursor) == "YES":
    logging.info("SSL connection to MySQL enabled successfully.")
  else:
    raise RuntimeError("Unable to establish SSL connection to MySQL.")


def _SetupDatabase(
    host=None,
    port=None,
    user=None,
    password=None,
    database=None,
    client_key_path=None,
    client_cert_path=None,
    ca_cert_path=None,
):
  """Connect to the given MySQL host and create a utf8mb4_unicode_ci database.

  Args:
    host: The hostname to connect to.
    port: The port to connect to.
    user: The username to connect as.
    password: The password to connect with.
    database: The database name to create.
    client_key_path: The path of the client private key file.
    client_cert_path: The path of the client public key certificate file.
    ca_cert_path: The path of the Certificate Authority (CA) certificate file.
  """
  with contextlib.closing(
      _Connect(
          host=host,
          port=port,
          user=user,
          password=password,
          # No database should be specified in a connection that intends
          # to create a database.
          database=None,
          client_key_path=client_key_path,
          client_cert_path=client_cert_path,
          ca_cert_path=ca_cert_path,
      )
  ) as conn:
    with contextlib.closing(conn.cursor()) as cursor:
      try:
        cursor.execute(CREATE_DATABASE_QUERY.format(database))
      except MySQLdb.MySQLError as e:
        #  Statement might fail if database exists, this is fine.
        if e.args[0] != mysql_errors.DB_CREATE_EXISTS:
          raise

      cursor.execute("USE `{}`".format(database))
      _CheckCollation(cursor)

  def _MigrationConnect():
    return _Connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        client_key_path=client_key_path,
        client_cert_path=client_cert_path,
        ca_cert_path=ca_cert_path,
    )

  mysql_migration.ProcessMigrations(
      _MigrationConnect, config.CONFIG["Mysql.migrations_dir"]
  )


def _GetConnectionArgs(
    host=None,
    port=None,
    user=None,
    password=None,
    database=None,
    client_key_path=None,
    client_cert_path=None,
    ca_cert_path=None,
):
  """Builds connection arguments for MySQLdb.Connect function."""
  connection_args = dict(
      autocommit=False,
      use_unicode=True,
      charset=CHARACTER_SET,
  )

  if host is not None:
    connection_args["host"] = host

  if port is not None:
    connection_args["port"] = port

  if user is not None:
    connection_args["user"] = user

  if password is not None:
    connection_args["passwd"] = password

  if database is not None:
    connection_args["db"] = database

  if client_key_path is not None:
    connection_args["ssl"] = {
        "key": client_key_path,
        "cert": client_cert_path,
        "ca": ca_cert_path,
    }

  return connection_args


def _Connect(
    host=None,
    port=None,
    user=None,
    password=None,
    database=None,
    client_key_path=None,
    client_cert_path=None,
    ca_cert_path=None,
):
  """Connect to MySQL and check if server fulfills requirements."""
  connection_args = _GetConnectionArgs(
      host=host,
      port=port,
      user=user,
      password=password,
      database=database,
      client_key_path=client_key_path,
      client_cert_path=client_cert_path,
      ca_cert_path=ca_cert_path,
  )

  conn = MySQLdb.Connect(**connection_args)
  with contextlib.closing(conn.cursor()) as cursor:
    _CheckForSSL(cursor)
    _SetMariaDBMode(cursor)
    _SetBinlogFormat(cursor)
    _SetPacketSizeForFollowingConnections(cursor)
    _SetEncoding(cursor)
    _CheckConnectionEncoding(cursor)
    _CheckLogFileSize(cursor)
    _SetSqlMode(cursor)

  return conn


_TXN_RETRY_JITTER_MIN = 1.0
_TXN_RETRY_JITTER_MAX = 2.0
_TXN_RETRY_BACKOFF_BASE = 1.5


def _SleepWithBackoff(exponent):
  """Simple function for sleeping with exponential backoff.

  With the defaults given above, and a max-number-of-attempts value of 5,
  this function will sleep for the following sequence of periods (seconds):
    Best case: [1.0, 1.5, 2.25, 3.375, 5.0625]
    Worst case: [2.0, 3.0, 4.5, 6.75, 10.125]

  Args:
    exponent: The exponent in the exponential backoff function, which specifies
      how many RETRIES (not attempts) have occurred so far.
  """
  jitter = random.uniform(_TXN_RETRY_JITTER_MIN, _TXN_RETRY_JITTER_MAX)
  time.sleep(jitter * math.pow(_TXN_RETRY_BACKOFF_BASE, exponent))


class MysqlDB(
    mysql_artifacts.MySQLDBArtifactsMixin,
    mysql_blobs.MySQLDBBlobsMixin,  # Implements BlobStore.
    mysql_blob_keys.MySQLDBBlobKeysMixin,
    mysql_clients.MySQLDBClientMixin,
    mysql_cronjobs.MySQLDBCronJobMixin,
    mysql_events.MySQLDBEventMixin,
    mysql_flows.MySQLDBFlowMixin,
    mysql_foreman_rules.MySQLDBForemanRulesMixin,
    mysql_hunts.MySQLDBHuntMixin,
    mysql_paths.MySQLDBPathMixin,
    mysql_signed_binaries.MySQLDBSignedBinariesMixin,
    mysql_signed_commands.MySQLDBSignedCommandsMixin,
    mysql_users.MySQLDBUsersMixin,
    mysql_yara.MySQLDBYaraMixin,
    db_module.Database,
):
  """Implements db.Database and blob_store.BlobStore using MySQL."""

  def ClearTestDB(self):
    # This is required because GRRBaseTest.setUp() calls it.
    pass

  _WRITE_ROWS_BATCH_SIZE = 10000
  _DELETE_ROWS_BATCH_SIZE = 5000

  def __init__(
      self, host=None, port=None, user=None, password=None, database=None
  ):
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
        # TODO: this is caused by an old version of the MySQLdb
        # library that doesn't wrap bytes SQL arguments with the _binary()
        # type hint. This issue should go away when a new version of the
        # MySQLdb is used with Python 3.
        ".*Invalid.*character string.*",
    ]:
      warnings.filterwarnings(
          "ignore", category=MySQLdb.Warning, message=message
      )

    self._connect_args = dict(
        host=host or config.CONFIG["Mysql.host"],
        port=port or config.CONFIG["Mysql.port"],
        user=user or config.CONFIG["Mysql.username"],
        password=password or config.CONFIG["Mysql.password"],
        database=database or config.CONFIG["Mysql.database"],
    )

    client_key_path = config.CONFIG["Mysql.client_key_path"]
    if client_key_path:
      logging.debug("Client key file configured, trying to use SSL.")
      self._connect_args["client_key_path"] = client_key_path
      self._connect_args["client_cert_path"] = config.CONFIG[
          "Mysql.client_cert_path"
      ]
      self._connect_args["ca_cert_path"] = config.CONFIG["Mysql.ca_cert_path"]

    _SetupDatabase(**self._connect_args)

    self._max_pool_size = config.CONFIG["Mysql.conn_pool_max"]
    self.pool = mysql_pool.Pool(self._Connect, max_size=self._max_pool_size)

    self.handler_thread = None
    self.handler_stop = True

    self.flow_processing_request_handler_thread = None
    self.flow_processing_request_handler_stop = None
    self.flow_processing_request_handler_pool = threadpool.ThreadPool.Factory(
        "flow_processing_pool",
        min_threads=config.CONFIG["Mysql.flow_processing_threads_min"],
        max_threads=config.CONFIG["Mysql.flow_processing_threads_max"],
    )

  def _Connect(self):
    return _Connect(**self._connect_args)

  def Close(self):
    self.pool.close()

  def _RunInTransaction(
      self,
      function: Callable[
          [Union[MySQLdb.connections.Connection, mysql_pool._ConnectionProxy]],
          None,
      ],
      readonly: bool = False,
  ) -> None:
    """Runs function within a transaction.

    Allocates a connection, begins a transaction on it and passes the connection
    to function.

    If function finishes without raising, the transaction is committed.

    If function raises, the transaction will be rolled back, if a retryable
    database error is raised, the operation may be repeated.

    Args:
      function: A function to be run.
      readonly: Indicates that only a readonly (snapshot) transaction is
        required.

    Returns:
      The value returned by the last call to function.

    Raises: Any exception raised by function.
    """
    start_query = "START TRANSACTION"
    if readonly:
      start_query = "START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY"

    broken_connections_seen = 0
    txn_execution_attempts = 0
    while True:
      with contextlib.closing(self.pool.get()) as connection:
        try:
          with contextlib.closing(connection.cursor()) as cursor:
            cursor.execute(start_query)

          result = function(connection)

          if not readonly:
            connection.commit()
          return result
        except mysql_utils.RetryableError:
          connection.rollback()
          if txn_execution_attempts < _MAX_RETRY_COUNT:
            _SleepWithBackoff(txn_execution_attempts)
            txn_execution_attempts += 1
          else:
            raise
        except MySQLdb.OperationalError as e:
          if e.args[0] in [
              mysql_conn_errors.SERVER_GONE_ERROR,
              mysql_conn_errors.SERVER_LOST,
          ]:
            # The connection to the MySQL server is broken. That might be
            # the case with other existing connections in the pool. We will
            # retry with all connections in the pool, expecting that they
            # will get removed from the pool when they error out. Eventually,
            # the pool will create new connections.
            broken_connections_seen += 1
            if broken_connections_seen > self._max_pool_size:
              # All existing connections in the pool have been exhausted, and
              # we have tried to create at least one new connection.
              raise
            # Retry immediately.
          else:
            connection.rollback()
            if _IsRetryable(e) and txn_execution_attempts < _MAX_RETRY_COUNT:
              _SleepWithBackoff(txn_execution_attempts)
              txn_execution_attempts += 1
            else:
              raise

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def Now(self, cursor: MySQLdb.cursors.Cursor) -> rdfvalue.RDFDatetime:
    cursor.execute("SELECT UNIX_TIMESTAMP(NOW(6))")
    [(timestamp,)] = cursor.fetchall()

    return mysql_utils.TimestampToRDFDatetime(timestamp)

  def MinTimestamp(self) -> rdfvalue.RDFDatetime:
    # Per https://dev.mysql.com/doc/refman/8.0/en/datetime.html:
    # "the range for TIMESTAMP values is '1970-01-01 00:00:01.000000' to
    # '2038-01-19 03:14:07.999999'".
    return rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1)
