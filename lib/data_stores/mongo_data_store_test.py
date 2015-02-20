#!/usr/bin/env python
"""Tests the mongo data store abstraction."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.data_stores import mongo_data_store

# pylint: mode=test


class MongoTestMixin(object):
  """A mixin for Mongo tests."""

  def InitDatastore(self):
    """Initializes the data store."""
    self.token = access_control.ACLToken(username="test",
                                         reason="Running tests")
    config_lib.CONFIG.Set("Mongo.db_name", "grr_test_%s" %
                          self.__class__.__name__)
    data_store.DB = mongo_data_store.MongoDataStore()
    data_store.DB.security_manager = test_lib.MockSecurityManager()

    self.DestroyDatastore()

  def DestroyDatastore(self):
    # Drop the collection.
    data_store.DB.db_handle.drop_collection(data_store.DB.latest_collection)
    data_store.DB.db_handle.drop_collection(data_store.DB.versioned_collection)

  def testCorrectDataStore(self):
    """Makes sure the correct implementation is tested."""
    self.assertTrue(isinstance(data_store.DB, mongo_data_store.MongoDataStore))


class MongoDataStoreTest(MongoTestMixin, data_store_test._DataStoreTest):
  """Test the mongo data store abstraction."""


class MongoDataStoreBenchmarks(MongoTestMixin,
                               data_store_test.DataStoreBenchmarks):
  """Benchmark the mongo data store abstraction."""

  # Mongo is really slow at this, make sure that the test doesn't run too long.
  # 500 is standard for other data stores.
  files_per_dir = 50


class MongoDataStoreCSVBenchmarks(MongoTestMixin,
                                  data_store_test.DataStoreCSVBenchmarks):
  """Benchmark the mongo data store abstraction."""


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
