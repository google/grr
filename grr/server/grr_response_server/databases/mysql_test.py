#!/usr/bin/env python
import contextlib
import logging
import os
import threading
import unittest
from unittest import mock
import uuid
import warnings

from absl import app
from absl import flags
from absl.testing import absltest
import MySQLdb  # TODO(hanuszczak): This should be imported conditionally.
from MySQLdb.constants import CR as mysql_conn_errors

from grr_response_server.databases import db_test_mixin
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql
from grr_response_server.databases import mysql_utils
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib

_SLOW_QUERY_LOG = flags.DEFINE_string(
    "slow_query_log",
    "",
    "Filename. If given, generates a log of all queries not using an index.",
)


def _GetEnvironOrSkip(key):
  value = os.environ.get(key)
  if value is None:
    raise unittest.SkipTest("'%s' variable is not set" % key)
  return value


class MySQLDatabaseProviderMixin(db_test_mixin.DatabaseSetupMixin):
  _conn: mysql.MysqlDB = None
  _warning_filters = None

  @classmethod
  def _Connect(cls):

    user = _GetEnvironOrSkip("MYSQL_TEST_USER")
    host = _GetEnvironOrSkip("MYSQL_TEST_HOST")
    port = _GetEnvironOrSkip("MYSQL_TEST_PORT")
    password = _GetEnvironOrSkip("MYSQL_TEST_PASS")
    # Use dash character in database name to break queries that do not quote it.
    database = "grr-test-{}".format(str(uuid.uuid4())[-10:])

    conn = mysql.MysqlDB(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
    )
    logging.info("Created test database: %s", database)

    return conn

  @classmethod
  def _DropTestDB(cls):

    def Drop(conn):
      with contextlib.closing(conn.cursor()) as cursor:
        cursor.execute("SELECT DATABASE()")
        dbname = cursor.fetchall()[0][0]
        cursor.execute(f"DROP DATABASE `{dbname}`")

    cls._conn._RunInTransaction(Drop)

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls._conn = cls._Connect()
    # The MySQL DB object sets some warning filters, and relies upon them.
    # Since filters are reset between tests, we'll keep them here and restore
    # them before each test run.
    cls._warning_filters = warnings.filters

  @classmethod
  def tearDownClass(cls):
    cls._DropTestDB()
    cls._conn.Close()
    super().tearDownClass()

  @classmethod
  def _EnableNonIndexedQueryLogging(cls, conn):
    with contextlib.closing(conn.cursor()) as cursor:
      print(
          "Generating log file of queries not using an index at %s."
          % _SLOW_QUERY_LOG.value
      )
      mysql._SetGlobalVariable("log_queries_not_using_indexes", True, cursor)
      mysql._SetSessionVariable("long_query_time", 100, cursor)
      mysql._SetGlobalVariable(
          "slow_query_log_file", _SLOW_QUERY_LOG.value, cursor
      )
      mysql._SetGlobalVariable("slow_query_log", True, cursor)

  @classmethod
  def _TruncateTables(cls, conn):
    with contextlib.closing(conn.cursor()) as cursor:
      cursor.execute("SELECT DATABASE()")
      dbname = cursor.fetchall()[0][0]
      cursor.execute(
          "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
          "WHERE table_schema = %s",
          [dbname],
      )
      tables = [r[0] for r in cursor.fetchall()]
      cursor.execute("SET FOREIGN_KEY_CHECKS=0")
      for table in tables:
        if table == "_migrations":
          continue
        cursor.execute(f"TRUNCATE TABLE `{table}`")
      cursor.execute("SET FOREIGN_KEY_CHECKS=1")

  def CreateDatabase(self):
    # Note: this is called by an upstream setUp() (i.e. before any individual
    # test run).
    # This returns a reusable DB object (stored as a class member). That object
    # relies on the warning filters it's set up during its construction. Since
    # pytest resets warning filters between tests, we restore them here.
    warnings.filters = self.__class__._warning_filters

    def Clean():
      self.__class__._conn._RunInTransaction(self.__class__._TruncateTables)

    return self._conn, Clean

  def CreateBlobStore(self):
    # Optimization: Since BlobStore and Database share the underlying MysqlDB
    # instance, there is no need to actually setup and destroy the BlobStore.
    # DatabaseTestMixin's setUp and tearDown do this implicitly for every test.
    return self.db.delegate, None


class MysqlTestBase(MySQLDatabaseProviderMixin):
  pass


class TestMysqlDB(
    stats_test_lib.StatsTestMixin,
    db_test_mixin.DatabaseTestMixin,
    MysqlTestBase,
    absltest.TestCase,
):
  """Test the mysql.MysqlDB class.

  Most of the tests in this suite are general blackbox tests of the db.Database
  interface brought in by the db_test.DatabaseTestMixin.
  """

  def testIsRetryable(self):
    self.assertFalse(mysql._IsRetryable(Exception("Some general error.")))
    self.assertFalse(
        mysql._IsRetryable(
            MySQLdb.OperationalError(
                1416, "Cannot get geometry object from data..."
            )
        )
    )
    self.assertTrue(
        mysql._IsRetryable(
            MySQLdb.OperationalError(
                1205, "Lock wait timeout exceeded; try restarting..."
            )
        )
    )
    self.assertTrue(
        mysql._IsRetryable(
            MySQLdb.OperationalError(
                1213,
                "Deadlock found when trying to get lock; try restarting...",
            )
        )
    )
    self.assertTrue(
        mysql._IsRetryable(
            MySQLdb.OperationalError(
                1637, "Too many active concurrent transactions"
            )
        )
    )

  def AddUser(self, connection, user, password):
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO grr_users (username, username_hash, password) "
        "VALUES (%s, %s, %s)",
        (user, mysql_utils.Hash(user), password.encode("utf-8")),
    )
    cursor.close()

  def ListUsers(self, connection):
    cursor = connection.cursor()
    cursor.execute("SELECT username, password FROM grr_users")
    ret = cursor.fetchall()
    cursor.close()
    return ret

  def testRunInTransaction(self):

    def AddUserFn(con):
      self.AddUser(con, "AzureDiamond", "hunter2")

    self.db.delegate._RunInTransaction(AddUserFn)

    users = self.db.delegate._RunInTransaction(self.ListUsers, readonly=True)
    self.assertEqual(users, (("AzureDiamond", b"hunter2"),))

  @mock.patch.object(mysql, "_SleepWithBackoff")
  def testRunInTransactionDeadlock(self, sleep_with_backoff_fn):
    """A deadlock error should be retried."""

    def AddUserFn1(con):
      self.AddUser(con, "user1", "pw1")

    def AddUserFn2(con):
      self.AddUser(con, "user2", "pw2")

    self.db.delegate._RunInTransaction(AddUserFn1)
    self.db.delegate._RunInTransaction(AddUserFn2)

    # We'll start two transactions which read/modify rows in different orders.
    # This should force (at least) one to fail with a deadlock, which should be
    # retried.
    t1_halfway = threading.Event()
    t2_halfway = threading.Event()

    # Number of times each transaction is attempted.
    counts = [0, 0]

    def Transaction1(connection):
      counts[0] += 1
      cursor = connection.cursor()
      cursor.execute(
          "SELECT password FROM grr_users WHERE username = 'user1' FOR UPDATE"
      )
      t1_halfway.set()
      self.assertTrue(t2_halfway.wait(5))
      cursor.execute(
          "UPDATE grr_users SET password = 'pw2-updated' "
          "WHERE username = 'user2'"
      )
      cursor.close()

    def Transaction2(connection):
      counts[1] += 1
      cursor = connection.cursor()
      cursor.execute(
          "SELECT password FROM grr_users WHERE username = 'user2' FOR UPDATE"
      )
      t2_halfway.set()
      self.assertTrue(t1_halfway.wait(5))
      cursor.execute(
          "UPDATE grr_users SET password = 'pw1-updated' "
          "WHERE username = 'user1'"
      )
      cursor.close()

    thread_1 = threading.Thread(
        target=lambda: self.db.delegate._RunInTransaction(Transaction1)
    )
    thread_2 = threading.Thread(
        target=lambda: self.db.delegate._RunInTransaction(Transaction2)
    )

    thread_1.start()
    thread_2.start()

    thread_1.join()
    thread_2.join()

    # Both transaction should have succeeded
    users = self.db.delegate._RunInTransaction(self.ListUsers, readonly=True)
    self.assertEqual(
        users, (("user1", b"pw1-updated"), ("user2", b"pw2-updated"))
    )

    # At least one should have been retried.
    self.assertGreater(sum(counts), 2)
    self.assertGreater(sleep_with_backoff_fn.call_count, 0)

  def testSuccessfulCallsAreCorrectlyAccounted(self):
    with self.assertStatsCounterDelta(
        1, db_utils.DB_REQUEST_LATENCY, fields=["ReadGRRUsers"]
    ):
      self.db.ReadGRRUsers()

  def testMaxAllowedPacketSettingIsOverriddenWhenTooLow(self):

    def SetMaxAllowedPacket(conn):
      with contextlib.closing(conn.cursor()) as cursor:
        mysql._SetGlobalVariable("max_allowed_packet", 20 << 10, cursor)

    def GetMaxAllowedPacket(conn):
      with contextlib.closing(conn.cursor()) as cursor:
        return mysql._ReadVariable("max_allowed_packet", cursor)

    # Lower packet size for future connections (i.e. set global var).
    self.db.delegate._RunInTransaction(SetMaxAllowedPacket)

    # Any new connection should fix the packet size (i.e. raise it back up).
    db = self.__class__._Connect()
    self.addCleanup(lambda db: db.Close(), db)

    self.assertEqual(
        db._RunInTransaction(GetMaxAllowedPacket), str(mysql.MAX_PACKET_SIZE)
    )

  def testMeaningfulErrorWhenNotEnoughPermissionsToOverrideGlobalVariable(self):

    def SetMaxAllowedPacket(conn):
      with contextlib.closing(conn.cursor()) as cursor:
        mysql._SetGlobalVariable("max_allowed_packet", 20 << 10, cursor)

    self.db.delegate._RunInTransaction(SetMaxAllowedPacket)

    # MaxAllowedPacketSettingTooLowError will be raised since
    # _SetGlobalVariable call will fail (via the mock). This way
    # we mimic the situation when _SetGlobalVariable fails due to
    # the lack of permissions.
    with mock.patch.object(
        mysql,
        "_SetGlobalVariable",
        side_effect=MySQLdb.OperationalError("SUPER privileges required"),
    ):
      with self.assertRaises(mysql.MaxAllowedPacketSettingTooLowError):
        self.__class__._Connect()

  @mock.patch.object(mysql, "_SleepWithBackoff")
  @mock.patch.object(mysql, "_MAX_RETRY_COUNT", 2)
  def testRetryOnServerGoneNoRollback(self, sleep_with_backoff_fn):
    expected_error_msg = "MySQL server has gone away"
    connections = []

    def RaiseServerGoneError(connection):
      # Wrap methods of the connection so we can check whether they get
      # called later.
      real_rollback_fn = connection.rollback
      real_close_fn = connection.close
      connection.rollback = mock.Mock(wraps=real_rollback_fn)
      connection.close = mock.Mock(wraps=real_close_fn)
      connections.append(connection)

      raise MySQLdb.OperationalError(
          mysql_conn_errors.SERVER_GONE_ERROR, expected_error_msg
      )

    with mock.patch.object(self.db.delegate, "_max_pool_size", 6):
      with self.assertRaises(MySQLdb.OperationalError) as context:
        self.db.delegate._RunInTransaction(RaiseServerGoneError)
      self.assertIn(expected_error_msg, str(context.exception))

      self.assertFalse(sleep_with_backoff_fn.called)
      # We expect all connections in the pool to be removed.
      self.assertLen(connections, 7)
      for connection in connections:
        self.assertFalse(connection.rollback.called)
        self.assertTrue(connection.close.called)

  @mock.patch.object(mysql, "_SleepWithBackoff", lambda _: None)
  def testRetryOnRetryableError(self):
    call_count = 0

    def RaisesRetryableError(connection):
      nonlocal call_count
      call_count += 1
      self.AddUser(connection, str(call_count), str(call_count))
      if call_count == 1:
        raise mysql_utils.RetryableError()

    self.db.delegate._RunInTransaction(RaisesRetryableError)
    self.assertEqual(call_count, 2)
    users = self.db.delegate._RunInTransaction(self.ListUsers, readonly=True)
    self.assertLen(users, 1)

  @mock.patch.object(mysql, "_SleepWithBackoff", lambda _: None)
  def testRetryOnRetryableError_maxRetries(self):

    def RaisesRetryableError(cursor):
      raise mysql_utils.RetryableError()

    with self.assertRaises(mysql_utils.RetryableError):
      self.db.delegate._RunInTransaction(RaisesRetryableError)

  @mock.patch.object(mysql, "_SleepWithBackoff")
  @mock.patch.object(mysql, "_MAX_RETRY_COUNT", 2)
  def testDoNotRetryPermanentErrors(self, sleep_with_backoff_fn):
    expected_error_msg = "Permanent error: Not implemented"
    connections = []

    def RaisePermanentError(connection):
      # Wrap methods of the connection so we can check whether they get
      # called later.
      real_rollback_fn = connection.rollback
      real_close_fn = connection.close
      connection.rollback = mock.Mock(wraps=real_rollback_fn)
      connection.close = mock.Mock(wraps=real_close_fn)
      connections.append(connection)

      raise MySQLdb.OperationalError(
          mysql_conn_errors.NOT_IMPLEMENTED, expected_error_msg
      )

    with self.assertRaises(MySQLdb.OperationalError) as context:
      self.db.delegate._RunInTransaction(RaisePermanentError)
    self.assertIn(expected_error_msg, str(context.exception))

    self.assertFalse(sleep_with_backoff_fn.called)
    self.assertLen(connections, 1)
    self.assertTrue(connections[0].rollback.called)
    self.assertTrue(connections[0].close.called)


if __name__ == "__main__":
  app.run(test_lib.main)
