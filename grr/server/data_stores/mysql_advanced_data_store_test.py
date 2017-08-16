#!/usr/bin/env python
"""Tests the mysql data store."""

import logging

from grr.lib import flags
from grr.server import data_store
from grr.server import data_store_test
from grr.server.data_stores import mysql_advanced_data_store
from grr.test_lib import test_lib


class MysqlAdvancedTestMixin(object):

  disabled = False

  @classmethod
  def setUpClass(cls):
    super(MysqlAdvancedTestMixin, cls).setUpClass()
    try:
      data_store_cls = mysql_advanced_data_store.MySQLAdvancedDataStore
      data_store.DB = data_store_cls.SetupTestDB()
      data_store.DB.Initialize()
    except Exception as e:  # pylint: disable=broad-except
      logging.debug("Error while setting up MySQL data store: %s.", e)
      MysqlAdvancedTestMixin.disabled = True

  def testCorrectDataStore(self):
    self.assertTrue(
        isinstance(data_store.DB,
                   mysql_advanced_data_store.MySQLAdvancedDataStore))


class MysqlAdvancedDataStoreTest(MysqlAdvancedTestMixin,
                                 data_store_test._DataStoreTest):
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
