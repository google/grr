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
  # Generate them with the following IPython snippet:
  #
  # from grr.server import db_test
  # methods = dir(db_test.DatabaseTestMixin)
  # for m in methods:
  #   if not m.startswith("test"):
  #     continue
  #   print "  def %s(self):\n    pass\n" % m
  #
  # TODO(user): finish the implementation and enable these.

  def testClientKeywords(self):
    pass

  def testClientKeywordsTimeRanges(self):
    pass

  def testClientLabels(self):
    pass

  def testClientLabelsUnicode(self):
    pass

  def testClientStartupInfo(self):
    pass

  def testCrashHistory(self):
    pass

  def testDatabaseType(self):
    pass

  def testEmptyGRRUserReadWrite(self):
    pass

  def testFilledGRRUserReadWrite(self):
    pass

  def testGrantApprovalAddsMultipleGrantorsWithSameName(self):
    pass

  def testGrantApprovalAddsNewGrantor(self):
    pass

  def testKeywordWriteToUnknownClient(self):
    pass

  def testLabelWriteToUnknownClient(self):
    pass

  def testReadAllClientsFullInfoFiltersClientsByLastPingTime(self):
    pass

  def testReadAllClientsFullInfoReadsMultipleClientsWithMultipleLabels(self):
    pass

  def testReadApprovalRequestsFiltersOutExpiredApprovals(self):
    pass

  def testReadApprovalRequestsForSubjectFiltersOutExpiredApprovals(self):
    pass

  def testReadApprovalRequestsForSubjectIncludesGrantsIntoMultipleResults(self):
    pass

  def testReadApprovalRequestsForSubjectIncludesGrantsIntoSingleResult(self):
    pass

  def testReadApprovalRequestsForSubjectKeepsExpiredApprovalsWhenAsked(self):
    pass

  def testReadApprovalRequestsForSubjectReturnsManyNonExpiredApproval(self):
    pass

  def testReadApprovalRequestsForSubjectReturnsNothingWhenNoApprovals(self):
    pass

  def testReadApprovalRequestsForSubjectReturnsSingleNonExpiredApproval(self):
    pass

  def testReadApprovalRequestsIncludesGrantsIntoMultipleResults(self):
    pass

  def testReadApprovalRequestsIncludesGrantsIntoSingleApproval(self):
    pass

  def testReadApprovalRequestsKeepsExpiredApprovalsWhenAsked(self):
    pass

  def testReadApprovalRequestsReturnsMultipleApprovals(self):
    pass

  def testReadApprovalRequestsReturnsSingleApproval(self):
    pass

  def testReadApprovalRequeststReturnsNothingWhenNoApprovals(self):
    pass

  def testReadClientFullFullInfoReturnsCorrectResult(self):
    pass

  def testReadClientStartupInfoHistory(self):
    pass

  def testReadClientStartupInfoHistoryWithEmptyTimerange(self):
    pass

  def testReadClientStartupInfoHistoryWithTimerangeEdgeCases(self):
    pass

  def testReadClientStartupInfoHistoryWithTimerangeWithBothFromTo(self):
    pass

  def testReadClientStartupInfoHistoryWithTimerangeWithFromOnly(self):
    pass

  def testReadClientStartupInfoHistoryWithTimerangeWithToOnly(self):
    pass

  def testReadWriteApprovalRequestWithEmptyNotifiedUsersEmailsAndGrants(self):
    pass

  def testReadWriteApprovalRequestsWithFilledInUsersEmailsAndGrants(self):
    pass

  def testReadingMultipleGRRUsersEntriesWorks(self):
    pass

  def testReadingUnknownGRRUserFails(self):
    pass

  def testRemoveClientKeyword(self):
    pass

  def testWriteClientSnapshotHistory(self):
    pass

  def testWriteClientSnapshotHistoryDoesNotUpdateLastTimestampIfOlder(self):
    pass

  def testWriteClientSnapshotHistoryRaiseAttributeError(self):
    pass

  def testWriteClientSnapshotHistoryRaiseOnNonExistingClient(self):
    pass

  def testWriteClientSnapshotHistoryRaiseTypeError(self):
    pass

  def testWriteClientSnapshotHistoryRaiseValueErrorOnEmpty(self):
    pass

  def testWriteClientSnapshotHistoryRaiseValueErrorOnNonUniformIds(self):
    pass

  def testWriteClientSnapshotHistoryUpdatesLastTimestampIfNewer(self):
    pass

  def testWriteClientSnapshotHistoryUpdatesLastTimestampIfNotSet(self):
    pass

  def testWriteClientSnapshotHistoryUpdatesOnlyLastClientTimestamp(self):
    pass


if __name__ == "__main__":
  unittest.main()
