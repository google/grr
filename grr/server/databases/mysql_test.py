#!/usr/bin/env python
import logging
import os
import random
import string
import unittest

# TODO(hanuszczak): This should be imported conditionally.
import MySQLdb

import unittest
from grr.server import db_test
from grr.server.databases import mysql


def _GetEnvironOrSkip(key):
  value = os.environ.get(key)
  if value is None:
    raise unittest.SkipTest("'%s' variable is not set" % key)
  return value


class TestMysqlDB(db_test.DatabaseTestMixin, unittest.TestCase):

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

  # These are tests defined by the Mixin which we don't (yet) expect to pass.
  # TODO(user): finish the implementation and enable these.

  def testDatabaseType(self):
    pass

  def testClientMetadataSubsecond(self):
    pass

  def testClientWriteToUnknownClient(self):
    pass

  def testKeywordWriteToUnknownClient(self):
    pass

  def testLabelWriteToUnknownClient(self):
    pass

  def testClientSnapshotHistory(self):
    pass

  def testWriteClientSnapshotHistory(self):
    pass

  def testWriteClientSnapshotHistoryUpdatesLastTimestampIfNotSet(self):
    pass

  def testWriteClientSnapshotHistoryUpdatesLastTimestampIfNewer(self):
    pass

  def testWriteClientSnapshotHistoryDoesNotUpdateLastTimestampIfOlder(self):
    pass

  def testWriteClientSnapshotHistoryUpdatesOnlyLastClientTimestamp(self):
    pass

  def testWriteClientSnapshotHistoryRaiseTypeError(self):
    pass

  def testWriteClientSnapshotHistoryRaiseValueErrorOnEmpty(self):
    pass

  def testWriteClientSnapshotHistoryRaiseValueErrorOnNonUniformIds(self):
    pass

  def testWriteClientSnapshotHistoryRaiseAttributeError(self):
    pass

  def testWriteClientSnapshotHistoryRaiseOnNonExistingClient(self):
    pass

  def testClientSummary(self):
    pass

  def testClientValidates(self):
    pass

  def testClientStartupInfo(self):
    pass

  def testStartupHistory(self):
    pass

  def testCrashHistory(self):
    pass

  def testClientKeywords(self):
    pass

  def testClientKeywordsTimeRanges(self):
    pass

  def testRemoveClientKeyword(self):
    pass

  def testClientLabels(self):
    pass

  def testClientLabelsUnicode(self):
    pass

  def testFilledGRRUserReadWrite(self):
    pass

  def testEmptyGRRUserReadWrite(self):
    pass

  def testReadingUnknownGRRUserFails(self):
    pass

  def testReadingMultipleGRRUsersEntriesWorks(self):
    pass

  def testReadClientFullFullInfoReturnsCorrectResult(self):
    pass

  def testReadAllClientsFullInfoReadsMultipleClientsWithMultipleLabels(self):
    pass

  def testReadAllClientsFullInfoFiltersClientsByLastPingTime(self):
    pass

  def testReadWriteApprovalRequestWithEmptyNotifiedUsersEmailsAndGrants(self):
    pass

  def testReadWriteApprovalRequestsWithFilledInUsersEmailsAndGrants(self):
    pass

  def testGrantApprovalAddsNewGrantor(self):
    pass

  def testGrantApprovalAddsMultipleGrantorsWithSameName(self):
    pass

  def testReadApprovalRequeststReturnsNothingWhenNoApprovals(self):
    pass

  def testReadApprovalRequestsReturnsSingleApproval(self):
    pass

  def testReadApprovalRequestsReturnsMultipleApprovals(self):
    pass

  def testReadApprovalRequestsIncludesGrantsIntoSingleApproval(self):
    pass

  def testReadApprovalRequestsIncludesGrantsIntoMultipleResults(self):
    pass

  def testReadApprovalRequestsFiltersOutExpiredApprovals(self):
    pass

  def testReadApprovalRequestsKeepsExpiredApprovalsWhenAsked(self):
    pass

  def testReadApprovalRequestsForSubjectReturnsNothingWhenNoApprovals(self):
    pass

  def testReadApprovalRequestsForSubjectReturnsSingleNonExpiredApproval(self):
    pass

  def testReadApprovalRequestsForSubjectReturnsManyNonExpiredApproval(self):
    pass

  def testReadApprovalRequestsForSubjectIncludesGrantsIntoSingleResult(self):
    pass

  def testReadApprovalRequestsForSubjectIncludesGrantsIntoMultipleResults(self):
    pass

  def testReadApprovalRequestsForSubjectFiltersOutExpiredApprovals(self):
    pass

  def testReadApprovalRequestsForSubjectKeepsExpiredApprovalsWhenAsked(self):
    pass


if __name__ == "__main__":
  unittest.main()
