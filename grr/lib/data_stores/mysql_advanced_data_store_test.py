#!/usr/bin/env python
"""Tests the mysql data store."""

import unittest

import logging

from grr.lib import access_control
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.data_stores import mysql_advanced_data_store


class MysqlAdvancedTestMixin(object):

  disabled = False

  def InitDatastore(self):
    if self.disabled:
      raise unittest.SkipTest("Skipping since Mysql db is not reachable.")

    self.token = access_control.ACLToken(username="test",
                                         reason="Running tests")
    # Use separate tables for benchmarks / tests so they can be run in parallel.
    with test_lib.ConfigOverrider({
        "Mysql.database_name": "grr_test_%s" % self.__class__.__name__,
        "Mysql.max_connect_wait": 2
    }):
      try:
        data_store.DB = mysql_advanced_data_store.MySQLAdvancedDataStore()
        data_store.DB.Initialize()
        data_store.DB.flusher_thread.Stop()
        data_store.DB.security_manager = test_lib.MockSecurityManager()
        data_store.DB.RecreateTables()
      except Exception as e:
        logging.debug("Error while connecting to MySQL db: %s.", e)
        MysqlAdvancedTestMixin.disabled = True
        raise unittest.SkipTest("Skipping since Mysql db is not reachable.")

  def DestroyDatastore(self):
    data_store.DB.DropTables()

  def testCorrectDataStore(self):
    self.assertTrue(isinstance(
        data_store.DB, mysql_advanced_data_store.MySQLAdvancedDataStore))


class MysqlAdvancedDataStoreTest(MysqlAdvancedTestMixin,
                                 data_store_test._DataStoreTest):
  """Test the mysql data store abstraction."""

  def testMultiSet(self):
    cursor = data_store.DB.ExecuteQuery("select @@version")
    version = cursor[0]["@@version"]
    # Extract ["5", "5", "..."] for "5.5.46-0ubuntu0.14.04.2".
    version_major, version_minor = version.split(".", 2)[:2]
    if (int(version_major) < 5 or
        (int(version_major) == 5 and int(version_minor) <= 5)):
      self.skipTest("This test needs MySQL >= 5.6")
    else:
      super(MysqlAdvancedDataStoreTest, self).testMultiSet()


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
