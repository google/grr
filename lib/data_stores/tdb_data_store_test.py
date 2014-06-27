#!/usr/bin/env python
"""Tests the tdb data store - in memory implementation."""

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
from grr.lib.data_stores import tdb_data_store

# pylint: mode=test


class TDBTestMixin(object):

  def InitTable(self):
    self.token = access_control.ACLToken(username="test",
                                         reason="Running tests")
    config_lib.CONFIG.SetRaw("TDBDatastore.root_path",
                             "%s/tdb_test/" % self.temp_dir)

    try:
      shutil.rmtree(config_lib.CONFIG.Get("TDBDatastore.root_path"))
    except (OSError, IOError):
      pass

    data_store.DB = tdb_data_store.TDBDataStore()
    data_store.DB.security_manager = test_lib.MockSecurityManager()

  def testCorrectDataStore(self):
    self.assertTrue(isinstance(data_store.DB, tdb_data_store.TDBDataStore))


class TDBDataStoreTest(TDBTestMixin, data_store_test.DataStoreTest):
  """Test the tdb data store."""

  def setUp(self):
    super(TDBDataStoreTest, self).setUp()
    self.InitTable()


class TDBDataStoreBenchmarks(TDBTestMixin,
                             data_store_test.DataStoreBenchmarks):
  """Benchmark the TDB data store abstraction."""

  def setUp(self):
    super(TDBDataStoreBenchmarks, self).setUp()
    self.InitTable()


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
