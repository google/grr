#!/usr/bin/env python
# Copyright 2013 Google Inc. All Rights Reserved.
"""Tests the mysql data store."""


from grr.client import conf

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import test_lib
from grr.lib.data_stores import mysql_data_store


class MysqlDataStoreTest(data_store_test.DataStoreTest):
  """Test the mysql data store abstraction."""

  def setUp(self):
    super(MysqlDataStoreTest, self).setUp()

    self.token = access_control.ACLToken("test", "Running tests")
    config_lib.CONFIG.Set("Mysql.database_name", "grr_test")

    data_store.DB = mysql_data_store.MySQLDataStore()
    data_store.DB.security_manager = test_lib.MockSecurityManager()

    # Drop the test database - it will be recreated by the init hook.
    with mysql_data_store.MySQLConnection() as connection:
      connection.Execute(
          "drop database `%s`" % config_lib.CONFIG["Mysql.database_name"])
      connection.Execute(
          "create database `%s`" % config_lib.CONFIG["Mysql.database_name"])

      mysql_data_store.MySQLEnsureDatabase.RecreateDataBase(connection)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  conf.StartMain(main)
