#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import logging
import os
import threading
import unittest
import uuid
import warnings

from absl import app
from absl import flags
from absl.testing import absltest
from future import builtins
import MySQLdb  # TODO(hanuszczak): This should be imported conditionally.

from grr_response_server.databases import db_test_mixin
from grr_response_server.databases import mysql
from grr_response_server.databases import mysql_utils
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib


flags.DEFINE_string(
    "slow_query_log", "",
    "Filename. If given, generates a log of all queries not using an index.")


def _GetEnvironOrSkip(key):
  value = os.environ.get(key)
  if value is None:
    raise unittest.SkipTest("'%s' variable is not set" % key)
  return value


class MySQLDatabaseProviderMixin(db_test_mixin.DatabaseSetupMixin):

  @classmethod
  def _CreateDatabase(cls):

    user = _GetEnvironOrSkip("MYSQL_TEST_USER")
    host = _GetEnvironOrSkip("MYSQL_TEST_HOST")
    port = _GetEnvironOrSkip("MYSQL_TEST_PORT")
    password = _GetEnvironOrSkip("MYSQL_TEST_PASS")
    # Use dash character in database name to break queries that do not quote it.
    database = "test-{}".format(builtins.str(uuid.uuid4())[-10])

    conn = mysql.MysqlDB(
        host=host, port=port, user=user, password=password, database=database)
    logging.info("Created test database: %s", database)

    def _Drop(cursor):
      cursor.execute("DROP DATABASE `{}`".format(database))

    def Fin():
      conn._RunInTransaction(_Drop)
      conn.Close()

    return conn, Fin
    # pylint: enable=unreachable

  def CreateDatabase(self):
    return self.__class__._CreateDatabase()

  def CreateBlobStore(self):
    # Optimization: Since BlobStore and Database share the underlying MysqlDB
    # instance, there is no need to actually setup and destroy the BlobStore.
    # DatabaseTestMixin's setUp and tearDown do this implicitly for every test.
    return self.db.delegate, None


class MysqlTestBase(MySQLDatabaseProviderMixin):
  pass


class TestMysqlDB(stats_test_lib.StatsTestMixin,
                  db_test_mixin.DatabaseTestMixin, MysqlTestBase,
                  absltest.TestCase):
  """Test the mysql.MysqlDB class.

  Most of the tests in this suite are general blackbox tests of the db.Database
  interface brought in by the db_test.DatabaseTestMixin.
  """

  def testIsRetryable(self):
    self.assertFalse(mysql._IsRetryable(Exception("Some general error.")))
    self.assertFalse(
        mysql._IsRetryable(
            MySQLdb.OperationalError(
                1416, "Cannot get geometry object from data...")))
    self.assertTrue(
        mysql._IsRetryable(
            MySQLdb.OperationalError(
                1205, "Lock wait timeout exceeded; try restarting...")))
    self.assertTrue(
        mysql._IsRetryable(
            MySQLdb.OperationalError(
                1213,
                "Deadlock found when trying to get lock; try restarting...")))
    self.assertTrue(
        mysql._IsRetryable(
            MySQLdb.OperationalError(
                1637, "Too many active concurrent transactions")))

  def AddUser(self, connection, user, password):
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO grr_users (username, username_hash, password) "
        "VALUES (%s, %s, %s)", (user, mysql_utils.Hash(user), bytes(password)))
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
    self.assertEqual(users, ((u"AzureDiamond", "hunter2"),))

  def testRunInTransactionDeadlock(self):
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
          "SELECT password FROM grr_users WHERE username = 'user1' FOR UPDATE")
      t1_halfway.set()
      self.assertTrue(t2_halfway.wait(5))
      cursor.execute("UPDATE grr_users SET password = 'pw2-updated' "
                     "WHERE username = 'user2'")
      cursor.close()

    def Transaction2(connection):
      counts[1] += 1
      cursor = connection.cursor()
      cursor.execute(
          "SELECT password FROM grr_users WHERE username = 'user2' FOR UPDATE")
      t2_halfway.set()
      self.assertTrue(t1_halfway.wait(5))
      cursor.execute("UPDATE grr_users SET password = 'pw1-updated' "
                     "WHERE username = 'user1'")
      cursor.close()

    thread_1 = threading.Thread(
        target=lambda: self.db.delegate._RunInTransaction(Transaction1))
    thread_2 = threading.Thread(
        target=lambda: self.db.delegate._RunInTransaction(Transaction2))

    thread_1.start()
    thread_2.start()

    thread_1.join()
    thread_2.join()

    # Both transaction should have succeeded
    users = self.db.delegate._RunInTransaction(self.ListUsers, readonly=True)
    self.assertEqual(users,
                     ((u"user1", "pw1-updated"), (u"user2", "pw2-updated")))

    # At least one should have been retried.
    self.assertGreater(sum(counts), 2)

  def testSuccessfulCallsAreCorrectlyAccounted(self):
    with self.assertStatsCounterDelta(
        1, "db_request_latency", fields=["ReadGRRUsers"]):
      self.db.ReadGRRUsers()


if __name__ == "__main__":
  app.run(test_lib.main)
