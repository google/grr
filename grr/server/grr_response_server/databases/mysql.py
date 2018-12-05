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

from grr_response_server import db as db_module
from grr_response_server import threadpool
from grr_response_server.databases import mysql_artifacts
from grr_response_server.databases import mysql_blobs
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


def _IsRetryable(error):
  """Returns whether error is likely to be retryable."""
  if not isinstance(error, MySQLdb.OperationalError):
    return False
  if not error.args:
    return False
  code = error.args[0]
  return code in _RETRYABLE_ERRORS


# pyformat: disable
class MysqlDB(mysql_artifacts.MySQLDBArtifactsMixin,
              mysql_blobs.MySQLDBBlobsMixin,
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

    # Turn all SQL warnings into exceptions.
    warnings.filterwarnings("error", category=MySQLdb.Warning)

    def Connect():
      return MySQLdb.Connect(
          host=host,
          port=port,
          user=user,
          passwd=passwd,
          db=db,
          autocommit=False,
          use_unicode=True,
          charset="utf8")

    self.pool = mysql_pool.Pool(Connect)
    with contextlib.closing(self.pool.get()) as connection:
      with contextlib.closing(connection.cursor()) as cursor:
        self._MariaDBCompatibility(cursor)
        self._SetBinlogFormat(cursor)
        self._InitializeSchema(cursor)
    self.handler_thread = None
    self.handler_stop = True

    self.flow_processing_request_handler_thread = None
    self.flow_processing_request_handler_stop = None
    self.flow_processing_request_handler_pool = (
        threadpool.ThreadPool.Factory(
            "flow_processing_pool", min_threads=2, max_threads=50))
    self.flow_processing_request_handler_pool.Start()

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
    cursor.execute("show variables like 'binlog_format'")
    _, log_format = cursor.fetchone()
    if log_format == "MIXED":
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
