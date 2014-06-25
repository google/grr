#!/usr/bin/env python
"""Tests the SQLite data store - in memory implementation."""

import shutil


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.data_stores import sqlite_data_store

# pylint: mode=test


class SqliteTestMixin(object):

  def InitTable(self):
    self.token = access_control.ACLToken(username="test",
                                         reason="Running tests")

    config_lib.CONFIG.SetRaw("SqliteDatastore.root_path",
                             "%s/sqlite_test/" % self.temp_dir)

    try:
      shutil.rmtree(config_lib.CONFIG.Get("SqliteDatastore.root_path"))
    except (OSError, IOError):
      pass

    data_store.DB = sqlite_data_store.SqliteDataStore()
    data_store.DB.security_manager = test_lib.MockSecurityManager()

  def testCorrectDataStore(self):
    self.assertTrue(isinstance(data_store.DB,
                               sqlite_data_store.SqliteDataStore))


class SqliteDataStoreTest(SqliteTestMixin, data_store_test.DataStoreTest):
  """Test the sqlite data store."""

  def setUp(self):
    super(SqliteDataStoreTest, self).setUp()
    self.InitTable()


class SqliteDataStoreBenchmarks(SqliteTestMixin,
                                data_store_test.DataStoreBenchmarks):
  """Benchmark the SQLite data store abstraction."""

  def setUp(self):
    super(SqliteDataStoreBenchmarks, self).setUp()
    self.InitTable()


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
