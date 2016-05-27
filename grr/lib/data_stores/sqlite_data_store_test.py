#!/usr/bin/env python
"""Tests the SQLite data store."""

import shutil


from grr.lib import access_control
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib
from grr.lib import utils

from grr.lib.data_stores import sqlite_data_store

# pylint: mode=test


class SqliteTestMixin(object):

  def InitDatastore(self):
    self.token = access_control.ACLToken(username="test",
                                         reason="Running tests")
    self.root_path = utils.SmartStr("%s/sqlite_test/" % self.temp_dir)

    with test_lib.ConfigOverrider({"Datastore.location": self.root_path}):

      self.DestroyDatastore()

      data_store.DB = sqlite_data_store.SqliteDataStore()
      data_store.DB.Initialize()
      data_store.DB.security_manager = test_lib.MockSecurityManager()

  def testCorrectDataStore(self):
    self.assertTrue(isinstance(data_store.DB,
                               sqlite_data_store.SqliteDataStore))

  def DestroyDatastore(self):
    try:
      data_store.DB.cache.Flush()
    except AttributeError:
      pass
    try:
      if self.root_path:
        shutil.rmtree(self.root_path)
    except (OSError, IOError):
      pass


class SqliteDataStoreTest(SqliteTestMixin, data_store_test._DataStoreTest):
  """Test the sqlite data store."""


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
