#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from absl.testing import absltest

from grr_response_server.databases import db_paths_test
from grr_response_server.databases import mysql_test
from grr.test_lib import test_lib


class MysqlPathsTest(db_paths_test.DatabaseTestPathsMixin,
                     mysql_test.MysqlTestBase, absltest.TestCase):

  # Tests that we don't expect to pass yet.

  # TODO(user): Finish implementation and enable these tests.

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

  # TODO(hanuszczak): Remove these once support for storing file hashes in
  # the MySQL backend is ready.

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


if __name__ == "__main__":
  app.run(test_lib.main)
