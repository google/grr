#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib

from absl import app
from absl.testing import absltest

import MySQLdb

from grr_response_server.databases import db_paths_test
from grr_response_server.databases import db_test_utils
from grr_response_server.databases import mysql_test
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class MysqlPathsTest(db_paths_test.DatabaseTestPathsMixin,
                     mysql_test.MysqlTestBase, absltest.TestCase):

  def testTemporaryTableIsRemovedIfMultiWritePathInfosFails(self):
    client_id = db_test_utils.InitializeClient(self.db)

    path_info = rdf_objects.PathInfo.OS(components=["foo", "bar"])
    path_info.stat_entry.st_size = 42

    # We have to pass the cursor explicitly, since MySQL database
    # implementation keeps the pool of connections and provides no
    # guarantees as to which connection will be used for a particular call.
    with contextlib.closing(self.db.delegate.pool.get()) as connection:
      with self.assertRaisesRegexp(MySQLdb.IntegrityError, "Duplicate entry"):
        self.db.delegate._MultiWritePathInfos(
            {client_id: [path_info, path_info]}, connection=connection)

      # This call shouldn't fail: even though previous call failed mid-way
      # the client_path_infos temporary table should have been removed.
      self.db.delegate._MultiWritePathInfos({client_id: [path_info]},
                                            connection=connection)

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
