#!/usr/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
"""Tests the mysql data store."""


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.data_stores import mysql_data_store


class MysqlTestMixin(object):

  def InitTable(self):
    self.token = access_control.ACLToken("test", "Running tests")
    # Use separate tables for benchmarks / tests so they can be run in parallel.
    config_lib.CONFIG.Set("Mysql.database_name", "grr_test_%s" %
                          self.__class__.__name__)
    config_lib.CONFIG.Set("Mysql.table_name", "aff4_test")

    data_store.DB = mysql_data_store.MySQLDataStore()
    data_store.DB.security_manager = test_lib.MockSecurityManager()
    with mysql_data_store.MySQLConnection() as connection:
      data_store.DB.RecreateDataBase(connection)

  def testCorrectDataStore(self):
    self.assertTrue(isinstance(data_store.DB, mysql_data_store.MySQLDataStore))


class MysqlDataStoreTest(MysqlTestMixin, data_store_test.DataStoreTest):
  """Test the mysql data store abstraction."""

  def setUp(self):
    super(MysqlDataStoreTest, self).setUp()
    self.InitTable()


class MysqlDataStoreBenchmarks(MysqlTestMixin,
                               data_store_test.DataStoreBenchmarks):
  """Benchmark the mysql data store abstraction."""

  def setUp(self):
    super(MysqlDataStoreBenchmarks, self).setUp()
    self.InitTable()


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
