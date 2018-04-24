#!/usr/bin/env python
"""Tests the SQLite data store."""


from grr.lib import flags
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import data_store_test
from grr.server.grr_response_server.data_stores import sqlite_data_store

from grr.test_lib import test_lib

# pylint: mode=test


class SqliteTestMixin(object):

  @classmethod
  def setUpClass(cls):
    super(SqliteTestMixin, cls).setUpClass()
    data_store.DB = sqlite_data_store.SqliteDataStore.SetupTestDB()
    data_store.DB.Initialize()

  def testCorrectDataStore(self):
    self.assertTrue(
        isinstance(data_store.DB, sqlite_data_store.SqliteDataStore))


class SqliteDataStoreTest(data_store_test.DataStoreTestMixin, SqliteTestMixin,
                          test_lib.GRRBaseTest):
  """Test the sqlite data store."""


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
