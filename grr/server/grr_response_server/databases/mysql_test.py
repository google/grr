#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import os
import random
import string
import threading
import unittest

from absl.testing import absltest
from builtins import range  # pylint: disable=redefined-builtin
import MySQLdb  # TODO(hanuszczak): This should be imported conditionally.

from grr_response_core.lib import flags
from grr_response_server import db_test_mixin
from grr_response_server.databases import mysql
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib


def _GetEnvironOrSkip(key):
  value = os.environ.get(key)
  if value is None:
    raise unittest.SkipTest("'%s' variable is not set" % key)
  return value


class TestMysqlDB(stats_test_lib.StatsTestMixin,
                  db_test_mixin.DatabaseTestMixin, absltest.TestCase):
  """Test the mysql.MysqlDB class.

  Most of the tests in this suite are general blackbox tests of the db.Database
  interface brought in by the db_test.DatabaseTestMixin.
  """

  flow_processing_req_func = "_WriteFlowProcessingRequests"

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

    conn = mysql.MysqlDB(
        host=host, port=port, user=user, passwd=passwd, db=dbname)

    def Fin():
      cursor.execute("DROP DATABASE " + dbname)
      cursor.close()
      connection.close()
      conn.Close()

    return conn, Fin
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
        1, "db_request_latency", fields=["ReadGRRUsers"]):
      self.db.ReadGRRUsers()

  # Tests that we don't expect to pass yet.

  # TODO(hanuszczak): Remove these once artifacts are supported in MySQL.

  def testReadArtifactThrowsForUnknownArtifacts(self):
    pass

  def testReadArtifactReadsWritten(self):
    pass

  def testReadArtifactReadsCopy(self):
    pass

  def testWriteArtifactThrowsForDuplicatedArtifacts(self):
    pass

  def testWriteArtifactThrowsForEmptyName(self):
    pass

  def testWriteArtifactWithSources(self):
    pass

  def testWriteArtifactMany(self):
    pass

  def testWriteArtifactWritesCopy(self):
    pass

  def testDeleteArtifactThrowsForUnknownArtifacts(self):
    pass

  def testDeleteArtifactDeletesSingle(self):
    pass

  def testDeleteArtifactDeletesMultiple(self):
    pass

  def testReadAllArtifactsEmpty(self):
    pass

  def testReadAllArtifactsReturnsAllArtifacts(self):
    pass

  def testReadAllArtifactsReturnsCopy(self):
    pass

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

  def testWritePathInfosHashAndStatEntry(self):
    pass

  def testWritePathInfoHashAndStatEntrySeparateWrites(self):
    pass

  def testReadPathInfoTimestampHashEntry(self):
    pass

  def testReadPathInfoTimestampStatAndHashEntry(self):
    pass

  def testReadingNonExistentBlobReturnsNone(self):
    pass

  def testSingleBlobCanBeWrittenAndThenRead(self):
    pass

  def testMultipleBlobsCanBeWrittenAndThenRead(self):
    pass

  def testWriting80MbOfBlobsWithSingleCallWorks(self):
    pass

  def testCheckBlobsExistCorrectlyReportsPresentAndMissingBlobs(self):
    pass

  def testHashBlobReferenceCanBeWrittenAndReadBack(self):
    pass

  def testReportsNonExistingHashesAsNone(self):
    pass

  def testCorrectlyHandlesRequestWithOneExistingAndOneMissingHash(self):
    pass

  def testMultipleHashBlobReferencesCanBeWrittenAndReadBack(self):
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

  def testWriteStatsStoreEntriesValidation(self):
    pass

  def testDuplicateStatsEntryWrite_SingleDimensional(self):
    pass

  def testDuplicateStatsEntryWrite_MultiDimensional(self):
    pass

  def testReadAllStatsEntries_UnknownPrefix(self):
    pass

  def testReadAllStatsEntries_UnknownMetric(self):
    pass

  def testReadAllStatsEntries_PrefixMatch(self):
    pass

  def testReadStatsEntriesLimitMaxResults(self):
    pass

  def testReadStatsEntriesLimitTimeRange(self):
    pass

  def testDeleteStatsEntries_HighLimit(self):
    pass

  def testDeleteStatsEntries_LowLimit(self):
    pass

  # TODO(user): implement hunts support for MySQL
  def testWritingAndReadingHuntObjectWorks(self):
    pass

  def testHuntObjectCanBeOverwritten(self):
    pass

  def testReadingNonExistentHuntObjectRaises(self):
    pass

  def testReadAllHuntObjectsReturnsEmptyListWhenNoHunts(self):
    pass

  def testReadAllHuntObjectsReturnsAllWrittenObjects(self):
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

  def testReadSignedBinaryReferences(self):
    pass

  def testUpdateSignedBinaryReferences(self):
    pass

  def testUnknownSignedBinary(self):
    pass

  def testReadIDsForAllSignedBinaries(self):
    pass

  def testDeleteSignedBinaryReferences(self):
    pass


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
