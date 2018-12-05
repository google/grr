#!/usr/bin/env python
"""Tests the mysql data store."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_server import data_store
from grr_response_server import data_store_test
from grr_response_server.data_stores import mysql_advanced_data_store
from grr.test_lib import test_lib


class MysqlAdvancedTestMixin(object):

  @classmethod
  def setUpClass(cls):
    super(MysqlAdvancedTestMixin, cls).setUpClass()
    data_store_cls = mysql_advanced_data_store.MySQLAdvancedDataStore
    data_store.DB = data_store_cls.SetupTestDB()
    data_store.DB.Initialize()

  def testCorrectDataStore(self):
    self.assertIsInstance(data_store.DB,
                          mysql_advanced_data_store.MySQLAdvancedDataStore)


class MysqlAdvancedDataStoreTest(data_store_test.DataStoreTestMixin,
                                 MysqlAdvancedTestMixin, test_lib.GRRBaseTest):
  """Test the mysql data store abstraction."""

  def testMysqlVersion(self):
    results, _ = data_store.DB.ExecuteQuery("select @@version")
    version = results[0]["@@version"]
    # Extract ["5", "5", "..."] for "5.5.46-0ubuntu0.14.04.2".
    version_major, version_minor = version.split(".", 2)[:2]
    if (int(version_major) < 5 or
        (int(version_major) == 5 and int(version_minor) <= 5)):
      self.fail("GRR needs MySQL >= 5.6")


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
