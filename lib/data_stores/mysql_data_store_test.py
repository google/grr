#!/usr/bin/env python
"""Tests the mysql data store."""



import unittest

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

import logging

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.data_stores import mysql_data_store


class MysqlTestMixin(object):

  def InitDatastore(self):
    self.token = access_control.ACLToken(username="test",
                                         reason="Running tests")
    # Use separate tables for benchmarks / tests so they can be run in parallel.
    config_lib.CONFIG.Set("Mysql.database_name", "grr_test_%s" %
                          self.__class__.__name__)
    config_lib.CONFIG.Set("Mysql.table_name", "aff4_test")

    try:
      data_store.DB = mysql_data_store.MySQLDataStore()
      data_store.DB.security_manager = test_lib.MockSecurityManager()
      data_store.DB.RecreateDataBase()
    except Exception as e:
      logging.debug("Error while connecting to MySQL db: %s.", e)
      raise unittest.SkipTest("Skipping since Mysql db is not reachable.")

  def DestroyDatastore(self):
    data_store.DB.DropDatabase()

  def testCorrectDataStore(self):
    self.assertTrue(isinstance(data_store.DB, mysql_data_store.MySQLDataStore))


class MysqlDataStoreTest(MysqlTestMixin, data_store_test._DataStoreTest):
  """Test the mysql data store abstraction."""


class MysqlDataStoreBenchmarks(MysqlTestMixin,
                               data_store_test.DataStoreBenchmarks):
  """Benchmark the mysql data store abstraction."""


class MysqlDataStoreCSVBenchmarks(MysqlTestMixin,
                                  data_store_test.DataStoreCSVBenchmarks):
  """Benchmark the mysql data store abstraction."""


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
