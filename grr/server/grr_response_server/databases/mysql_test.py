#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib
import logging
import os
import random
import string
import threading
import unittest

from absl import app
from absl.testing import absltest
from future.builtins import range
import MySQLdb  # TODO(hanuszczak): This should be imported conditionally.

from grr_response_server import blob_store_test_mixin
from grr_response_server import db_test_mixin
from grr_response_server.databases import mysql
from grr_response_server.databases import mysql_utils
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib



def _GetEnvironOrSkip(key):
  value = os.environ.get(key)
  if value is None:
    raise unittest.SkipTest("'%s' variable is not set" % key)
  return value


class MySQLDatabaseProviderMixin(db_test_mixin.DatabaseProvider):

  def CreateDatabase(self):

    user = _GetEnvironOrSkip("MYSQL_TEST_USER")
    host = _GetEnvironOrSkip("MYSQL_TEST_HOST")
    port = _GetEnvironOrSkip("MYSQL_TEST_PORT")
    password = _GetEnvironOrSkip("MYSQL_TEST_PASS")
    database = "".join(
        random.choice(string.ascii_uppercase + string.digits)
        for _ in range(10))

    conn = mysql.MysqlDB(
        host=host, port=port, user=user, password=password, database=database)
    logging.info("Created test database: %s", database)

    def _Drop(cursor):
      cursor.execute("DROP DATABASE {}".format(database))

    def Fin():
      conn._RunInTransaction(_Drop)
      conn.Close()

    return conn, Fin
    # pylint: enable=unreachable

  def CreateBlobStore(self):
    # Optimization: Since BlobStore and Database share the underlying MysqlDB
    # instance, there is no need to actually setup and destroy the BlobStore.
    # DatabaseTestMixin's setUp and tearDown do this implicitly for every test.
    return self.db.delegate, None


class TestMysqlDB(stats_test_lib.StatsTestMixin,
                  db_test_mixin.DatabaseTestMixin, MySQLDatabaseProviderMixin,
                  blob_store_test_mixin.BlobStoreTestMixin, absltest.TestCase):
  """Test the mysql.MysqlDB class.

  Most of the tests in this suite are general blackbox tests of the db.Database
  interface brought in by the db_test.DatabaseTestMixin.
  """

  flow_processing_req_func = "_WriteFlowProcessingRequests"

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
        1, "db_request_latency", fields=["ReadGRRUsers"]):
      self.db.ReadGRRUsers()

  # Tests that we don't expect to pass yet.

  # TODO(user): Finish implementation and enable these tests.
  def testWritePathInfosRawValidates(self):
    pass

  def testWritePathInfosValidatesClient(self):
    pass

  def testWritePathInfosMetadata(self):
    pass

  def testWritePathInfosMetadataTimestampUpdate(self):
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

  def testMultiWritePathInfos(self):
    pass

  def testWriteStatHistory(self):
    pass

  def testWriteHashHistory(self):
    pass

  def testMultiWriteHistoryEmpty(self):
    pass

  def testMultiWriteHistoryStatAndHash(self):
    pass

  def testMultiWriteHistoryTwoPathTypes(self):
    pass

  def testMultiWriteHistoryTwoPaths(self):
    pass

  def testMultiWriteHistoryTwoClients(self):
    pass

  def testMultiWriteHistoryDoesNotAllowOverridingStat(self):
    pass

  def testMultiWriteHistoryDoesNotAllowOverridingHash(self):
    pass

  def testMultiWriteHistoryRaisesOnNonExistingPathsForStat(self):
    pass

  def testMultiWriteHistoryRaisesOnNonExistingPathForHash(self):
    pass

  def testReadPathInfosNonExistent(self):
    pass

  def testReadPathInfoNonExistent(self):
    pass

  def testReadPathInfoTimestampStatEntry(self):
    pass

  def testReadPathInfosMany(self):
    pass

  def testWritePathInfosDuplicatedData(self):
    pass

  def testWritePathInfosStoresCopy(self):
    pass

  def testListDescendentPathInfosEmptyResult(self):
    pass

  def testListDescendentPathInfosSingleResult(self):
    pass

  def testListDescendentPathInfosSingle(self):
    pass

  def testListDescendentPathInfosBranching(self):
    pass

  def testListDescendentPathInfosLimited(self):
    pass

  def testListDescendentPathInfosTypeSeparated(self):
    pass

  def testListDescendentPathInfosAll(self):
    pass

  def testListDescendentPathInfosLimitedDirectory(self):
    pass

  def testListDescendentPathInfosTimestampNow(self):
    pass

  def testListDescendentPathInfosTimestampMultiple(self):
    pass

  def testListDescendentPathInfosTimestampStatValue(self):
    pass

  def testListDescendentPathInfosTimestampHashValue(self):
    pass

  def testListChildPathInfosRoot(self):
    pass

  def testListChildPathInfosRootDeeper(self):
    pass

  def testListChildPathInfosDetails(self):
    pass

  def testListChildPathInfosDeepSorted(self):
    pass

  def testListChildPathInfosTimestamp(self):
    pass

  def testListChildPathInfosTimestampStatAndHashValue(self):
    pass

  # TODO(hanuszczak): Remove these once support for storing file hashes in
  # the MySQL backend is ready.

  def testWritePathInfosHashEntry(self):
    pass

  def testWriteMultiplePathInfosHashEntry(self):
    pass

  def testWritePathInfosHashAndStatEntry(self):
    pass

  def testWritePathInfoHashAndStatEntrySeparateWrites(self):
    pass

  def testReadPathInfoTimestampHashEntry(self):
    pass

  def testReadPathInfoTimestampStatAndHashEntry(self):
    pass

  def testReadPathInfoOlder(self):
    pass

  def testReadPathInfosHistoriesEmpty(self):
    pass

  def testReadPathInfosHistoriesDoesNotRaiseOnUnknownClient(self):
    pass

  def testReadPathInfosHistoriesWithSingleFileWithSingleHistoryItem(self):
    pass

  def testReadPathInfosHistoriesWithTwoFilesWithSingleHistoryItemEach(self):
    pass

  def testReadPathInfosHistoriesWithTwoFilesWithTwoHistoryItems(self):
    pass

  def testInitPathInfosValidatesClient(self):
    pass

  def testInitPathInfosEmpty(self):
    pass

  def testInitPathInfosWriteSingle(self):
    pass

  def testInitPathInfosWriteMany(self):
    pass

  def testInitPathInfosTree(self):
    pass

  def testInitPathInfosClearsStatHistory(self):
    pass

  def testInitPathInfosClearsHashHistory(self):
    pass

  def testInitPathInfosRetainsIndirectPathHistory(self):
    pass

  def testMultiInitPathInfos(self):
    pass

  def testMultiInitPathInfosEmptyDoesNotThrow(self):
    pass

  def testMultiInitPathInfosNoPathsDoesNotThrow(self):
    pass

  def testClearPathHistoryEmpty(self):
    pass

  def testClearPathHistorySingle(self):
    pass

  def testClearPathHistoryManyRecords(self):
    pass

  def testClearPathHistoryOnlyDirect(self):
    pass

  def testMultiClearPathHistoryEmptyDoesNotRaise(self):
    pass

  def testMultiClearPathHistoryNoPathsDoesNotRaise(self):
    pass

  def testMultiClearPathHistoryClearsMultipleHistories(self):
    pass

  def testWritesAndReadsSingleFlowResultOfSingleType(self):
    pass

  def testWritesAndReadsMultipleFlowResultsOfSingleType(self):
    pass

  def testWritesAndReadsMultipleFlowResultsWithDifferentTimestamps(self):
    pass

  def testWritesAndReadsMultipleFlowResultsOfMultipleTypes(self):
    pass

  def testReadFlowResultsCorrectlyAppliesOffsetAndCountFilters(self):
    pass

  def testReadFlowResultsCorrectlyAppliesWithTagFilter(self):
    pass

  def testReadFlowResultsCorrectlyAppliesWithTypeFilter(self):
    pass

  def testReadFlowResultsCorrectlyAppliesWithSubstringFilter(self):
    pass

  def testReadFlowResultsCorrectlyAppliesVariousCombinationsOfFilters(self):
    pass

  def testReadFlowResultsReturnsPayloadWithMissingTypeAsSpecialValue(self):
    pass

  def testCountFlowResultsReturnsCorrectResultsCount(self):
    pass

  def testCountFlowResultsCorrectlyAppliesWithTagFilter(self):
    pass

  def testCountFlowResultsCorrectlyAppliesWithTypeFilter(self):
    pass

  def testCountFlowResultsCorrectlyAppliesWithTagAndWithTypeFilters(self):
    pass

  def testWritesAndReadsSingleFlowLogEntry(self):
    pass

  def testWritesAndReadsMultipleFlowLogEntries(self):
    pass

  def testReadFlowLogEntriesCorrectlyAppliesOffsetAndCountFilters(self):
    pass

  def testReadFlowLogEntriesCorrectlyAppliesWithSubstringFilter(self):
    pass

  def testReadFlowLogEntriesCorrectlyAppliesVariousCombinationsOfFilters(self):
    pass

  def testCountFlowLogEntriesReturnsCorrectFlowLogEntriesCount(self):
    pass

  def testReadLatestPathInfosReturnsNothingForNonExistingPaths(self):
    pass

  def testFlowLogsAndErrorsForUnknownFlowsRaise(self):
    pass

  def testReadLatestPathInfosReturnsNothingWhenNoFilesCollected(self):
    pass

  def testReadLatestPathInfosFindsTwoCollectedFilesWhenTheyAreTheOnlyEntries(
      self):
    pass

  def testReadLatestPathInfosCorrectlyFindsCollectedFileWithNonLatestEntry(
      self):
    pass

  def testReadLatestPathInfosCorrectlyFindsLatestOfTwoCollectedFiles(self):
    pass

  def testReadLatestPathInfosCorrectlyFindsLatestCollectedFileBeforeTimestamp(
      self):
    pass

  def testReadLatestPathInfosIncludesStatEntryIfThereIsOneWithSameTimestamp(
      self):
    pass

  # TODO(user): implement hunts support for MySQL
  def testReadFlowForProcessingRaisesIfParentHuntIsStoppedOrCompleted(self):
    pass

  def testWritingAndReadingHuntObjectWorks(self):
    pass

  def testHuntObjectCanBeOverwritten(self):
    pass

  def testReadingNonExistentHuntObjectRaises(self):
    pass

  def testUpdateHuntObjectRaisesIfHuntDoesNotExist(self):
    pass

  def testUpdateHuntObjectCorrectlyUpdatesHuntObject(self):
    pass

  def testUpdateHuntObjectIsAtomic(self):
    pass

  def testUpdateHuntObjectPropagatesExceptions(self):
    pass

  def testUpdateHuntObjectIncrementsCountersWithoutOverridingThem(self):
    pass

  def testDeletingHuntObjectWorks(self):
    pass

  def testReadAllHuntObjectsReturnsEmptyListWhenNoHunts(self):
    pass

  def testReadAllHuntObjectsReturnsAllWrittenObjects(self):
    pass

  def testWritingAndReadingHuntOutputPluginsStatesWorks(self):
    pass

  def testReadingHuntOutputPluginsReturnsThemInOrderOfWriting(self):
    pass

  def testWritingHuntOutputStatesForZeroPlugins(self):
    pass

  def testWritingHuntOutputStatesForUnknownHuntRaises(self):
    pass

  def testReadingHuntOutputStatesForUnknownHuntRaises(self):
    pass

  def testUpdatingHuntOutputStateForUnknownHuntRaises(self):
    pass

  def testUpdatingHuntOutputStateWorksCorrectly(self):
    pass

  def testReadHuntLogEntriesReturnsEntryFromSingleHuntFlow(self):
    pass

  def testReadHuntLogEntriesReturnsEntryFromMultipleHuntFlows(self):
    pass

  def testReadHuntLogEntriesCorrectlyAppliesOffsetAndCountFilters(self):
    pass

  def testReadHuntLogEntriesCorrectlyAppliesWithSubstringFilter(self):
    pass

  def testReadHuntLogEntriesCorrectlyAppliesCombinationOfFilters(self):
    pass

  def testCountHuntLogEntriesReturnsCorrectHuntLogEntriesCount(self):
    pass

  def testReadHuntResultsReadsSingleResultOfSingleType(self):
    pass

  def testReadHuntResultsReadsMultipleResultOfSingleType(self):
    pass

  def testReadHuntResultsReadsMultipleResultOfMultipleTypes(self):
    pass

  def testReadHuntResultsCorrectlyAppliedOffsetAndCountFilters(self):
    pass

  def testReadHuntResultsCorrectlyAppliesWithTagFilter(self):
    pass

  def testReadHuntResultsCorrectlyAppliesWithTypeFilter(self):
    pass

  def testReadHuntResultsCorrectlyAppliesWithSubstringFilter(self):
    pass

  def testReadHuntResultsCorrectlyAppliesVariousCombinationsOfFilters(self):
    pass

  def testReadHuntResultsReturnsPayloadWithMissingTypeAsSpecialValue(self):
    pass

  def testCountHuntResultsReturnsCorrectResultsCount(self):
    pass

  def testCountHuntResultsCorrectlyAppliesWithTagFilter(self):
    pass

  def testCountHuntResultsCorrectlyAppliesWithTypeFilter(self):
    pass

  def testCountHuntResultsCorrectlyAppliesWithTagAndWithTypeFilters(self):
    pass

  def testCountHuntResultsCorrectlyAppliesWithTimestampFilter(self):
    pass

  def testCountHuntResultsByTypeGroupsResultsCorrectly(self):
    pass

  def testReadHuntFlowsReturnsEmptyListWhenNoFlows(self):
    pass

  def testReadHuntFlowsReturnsAllHuntFlowsWhenNoFilterCondition(self):
    pass

  def testReadHuntFlowsAppliesFilterConditionCorrectly(self):
    pass

  def testReadHuntFlowsCorrectlyAppliesOffsetAndCountFilters(self):
    pass

  def testCountHuntFlowsReturnsEmptyListWhenNoFlows(self):
    pass

  def testCountHuntFlowsReturnsAllHuntFlowsWhenNoFilterCondition(self):
    pass

  def testCountHuntFlowsAppliesFilterConditionCorrectly(self):
    pass

  # Flow/hunt output plugin tests.
  def testFlowOutputPluginLogEntriesCanBeWrittenAndThenRead(self):
    pass

  def testFlowOutputPluginLogEntryWith1MbMessageCanBeWrittenAndThenRead(self):
    pass

  def testFlowOutputPluginLogEntriesCanBeReadWithTypeFilter(self):
    pass

  def testReadFlowOutputPluginLogEntriesCorrectlyAppliesOffsetCounter(self):
    pass

  def testReadFlowOutputPluginLogEntriesAppliesOffsetCounterWithType(self):
    pass

  def testFlowOutputPluginLogEntriesCanBeCountedPerPlugin(self):
    pass

  def testCountFlowOutputPluginLogEntriesRespectsWithTypeFilter(self):
    pass

  def testReadHuntOutputPluginLogEntriesReturnsEntryFromSingleHuntFlow(self):
    pass

  def testReadHuntOutputPluginLogEntriesReturnsEntryFromMultipleHuntFlows(self):
    pass

  def testReadHuntOutputPluginLogEntriesCorrectlyAppliesOffsetAndCountFilters(
      self):
    pass

  def testReadHuntOutputPluginLogEntriesCorrectlyAppliesWithTypeFilter(self):
    pass

  def testReadHuntOutputPluginLogEntriesCorrectlyAppliesCombinationOfFilters(
      self):
    pass

  def testCountHuntOutputPluginLogEntriesReturnsCorrectCount(self):
    pass

  def testCountHuntOutputPluginLogEntriesRespectsWithTypeFilter(self):
    pass

  def testFlowStateUpdateUsingUpdateFlow(self):
    pass

  def testFlowStateUpdateUsingReturnProcessedFlow(self):
    pass

  def testReadHuntFlowsIgnoresSubflows(self):
    pass

  def testCountHuntFlowsIgnoresSubflows(self):
    pass

  def testReadHuntLogEntriesIgnoresNestedFlows(self):
    pass

  def testCountHuntLogEntriesIgnoresNestedFlows(self):
    pass

  def testReadHuntCountersCorrectlyAggregatesResultsAmongDifferentFlows(self):
    pass

  def testFlowRequestsWithStartTimeAreCorrectlyDelayed(self):
    pass


if __name__ == "__main__":
  app.run(test_lib.main)
