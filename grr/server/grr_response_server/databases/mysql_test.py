#!/usr/bin/env python
import logging
import os
import random
import string
import threading
import unittest

# TODO(hanuszczak): This should be imported conditionally.
import MySQLdb

import unittest
from grr.server.grr_response_server import db_test_mixin
from grr.server.grr_response_server import db_utils
from grr.server.grr_response_server.databases import mysql
from grr.test_lib import stats_test_lib


def _GetEnvironOrSkip(key):
  value = os.environ.get(key)
  if value is None:
    raise unittest.SkipTest("'%s' variable is not set" % key)
  return value


class TestMysqlDB(stats_test_lib.StatsTestMixin,
                  db_test_mixin.DatabaseTestMixin, unittest.TestCase):
  """Test the mysql.MysqlDB class.

  Most of the tests in this suite are general blackbox tests of the db.Database
  interface brought in by the db_test.DatabaseTestMixin.
  """

  def CreateDatabase(self):
    # pylint: disable=unreachable
    user = _GetEnvironOrSkip("MYSQL_TEST_USER")
    host = _GetEnvironOrSkip("MYSQL_TEST_HOST")
    port = _GetEnvironOrSkip("MYSQL_TEST_PORT")
    passwd = _GetEnvironOrSkip("MYSQL_TEST_PASS")
    dbname = "".join(
        random.choice(string.ascii_uppercase + string.digits)
        for _ in range(10))

    connection = MySQLdb.Connect(host=host, port=port, user=user, passwd=passwd)
    cursor = connection.cursor()
    cursor.execute("CREATE DATABASE " + dbname)
    logging.info("Created test database: %s", dbname)

    def Fin():
      cursor.execute("DROP DATABASE " + dbname)
      cursor.close()
      connection.close()

    return mysql.MysqlDB(
        host=host, port=port, user=user, passwd=passwd, db=dbname), Fin
    # pylint: enable=unreachable

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

  def AddUser(self, connection, user, passwd):
    cursor = connection.cursor()
    cursor.execute("INSERT INTO grr_users (username, password) VALUES (%s, %s)",
                   (user, bytes(passwd)))
    cursor.close()

  def ListUsers(self, connection):
    cursor = connection.cursor()
    cursor.execute("SELECT username, password FROM grr_users")
    ret = cursor.fetchall()
    cursor.close()
    return ret

  def setUp(self):
    super(TestMysqlDB, self).setUp()
    db_utils.DBMetricsInit().RunOnce()

  def testRunInTransaction(self):
    self.db.delegate._RunInTransaction(
        lambda con: self.AddUser(con, "AzureDiamond", "hunter2"))

    users = self.db.delegate._RunInTransaction(self.ListUsers, readonly=True)
    self.assertEqual(users, ((u"AzureDiamond", "hunter2"),))

  def testRunInTransactionDeadlock(self):
    """A deadlock error should be retried."""

    self.db.delegate._RunInTransaction(
        lambda con: self.AddUser(con, "user1", "pw1"))
    self.db.delegate._RunInTransaction(
        lambda con: self.AddUser(con, "user2", "pw2"))

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
          "SELECT password FROM grr_users WHERE username = 'user1' FOR UPDATE;")
      t1_halfway.set()
      self.assertTrue(t2_halfway.wait(5))
      cursor.execute("UPDATE grr_users SET password = 'pw2-updated' "
                     "WHERE username = 'user2';")
      cursor.close()

    def Transaction2(connection):
      counts[1] += 1
      cursor = connection.cursor()
      cursor.execute(
          "SELECT password FROM grr_users WHERE username = 'user2' FOR UPDATE;")
      t2_halfway.set()
      self.assertTrue(t1_halfway.wait(5))
      cursor.execute("UPDATE grr_users SET password = 'pw1-updated' "
                     "WHERE username = 'user1';")
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
    self.assertEqual(users, ((u"user1", "pw1-updated"),
                             (u"user2", "pw2-updated")))

    # At least one should have been retried.
    self.assertGreater(sum(counts), 2)

  def testSuccessfulCallsAreCorrectlyAccounted(self):
    with self.assertStatsCounterDelta(
        1, "db_request_latency", fields=["ReadAllGRRUsers"]):
      self.db.ReadAllGRRUsers()

  # Tests that we don't expect to pass yet.
  # TODO(user): Finish implementation and enable these tests.
  def testWritePathInfosRawValidates(self):
    pass

  def testWritePathInfosValidatesClient(self):
    pass

  def testWritePathInfosMetadata(self):
    pass

  def testWritePathInfosStatEntry(self):
    pass

  def testWritePathInfosExpansion(self):
    pass

  def testWritePathInfosTypeSeparated(self):
    pass

  def testWritePathInfosUpdates(self):
    pass

  def testWritePathInfosUpdatesAncestors(self):
    pass

  def testFindPathInfosByPathIDsNonExistent(self):
    pass

  def testFindPathInfoByPathIDNonExistent(self):
    pass

  def testFindPathInfoByPathIDTimestamp(self):
    pass

  def testWritePathInfosDuplicatedData(self):
    pass

  def testFindDescendentPathIDsEmptyResult(self):
    pass

  def testFindDescendentPathIDsSingleResult(self):
    pass

  def testFindDescendentPathIDsSingle(self):
    pass

  def testFindDescendentPathIDsBranching(self):
    pass

  def testFindDescendentPathIDsLimited(self):
    pass

  def testFindDescendentPathIDsTypeSeparated(self):
    pass

  def testFindDescendentPathIDsAll(self):
    pass


if __name__ == "__main__":
  unittest.main()
