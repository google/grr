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

  def InitDatastore(self):
    self.token = access_control.ACLToken(username="test",
                                         reason="Running tests")
    config_lib.CONFIG.Set("Datastore.location", "%s/tdb_test/" % self.temp_dir)

    self.DestroyDatastore()

    data_store.DB = tdb_data_store.TDBDataStore()
    data_store.DB.security_manager = test_lib.MockSecurityManager()

  def testCorrectDataStore(self):
    self.assertTrue(isinstance(data_store.DB, tdb_data_store.TDBDataStore))

  def DestroyDatastore(self):
    try:
      shutil.rmtree(config_lib.CONFIG.Get("Datastore.location"))
    except (OSError, IOError):
      pass


class TDBDataStoreTest(TDBTestMixin, data_store_test._DataStoreTest):
  """Test the tdb data store."""


class TDBDataStoreBenchmarks(TDBTestMixin,
                             data_store_test.DataStoreBenchmarks):
  """Benchmark the TDB data store abstraction."""


class TDBDataStoreCSVBenchmarks(TDBTestMixin,
                                data_store_test.DataStoreCSVBenchmarks):
  """Benchmark the TDB data store abstraction."""


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
