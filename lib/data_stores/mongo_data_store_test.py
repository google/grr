#!/usr/bin/env python
"""Tests the mongo data store abstraction."""



from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.data_stores import mongo_data_store


class MongoTestMixin(object):

  def InitTable(self):
    self.token = access_control.ACLToken("test", "Running tests")
    config_lib.CONFIG.Set("Mongo.db_name", "grr_test_%s" %
                          self.__class__.__name__)
    data_store.DB = mongo_data_store.MongoDataStore()
    data_store.DB.security_manager = test_lib.MockSecurityManager()

    # Drop the collection.
    data_store.DB.db_handle.drop_collection(data_store.DB.latest_collection)
    data_store.DB.db_handle.drop_collection(data_store.DB.versioned_collection)

  def testCorrectDataStore(self):
    self.assertTrue(isinstance(data_store.DB, mongo_data_store.MongoDataStore))


class MongoDataStoreTest(MongoTestMixin, data_store_test.DataStoreTest):
  """Test the mongo data store abstraction."""

  def setUp(self):
    super(MongoDataStoreTest, self).setUp()
    self.InitTable()


class MongoDataStoreBenchmarks(MongoTestMixin,
                               data_store_test.DataStoreBenchmarks):
  """Benchmark the mongo data store abstraction."""

  # Mongo is really slow at this, make sure that the test doesn't run too long.
  # 500 is standard for other data stores.
  files_per_dir = 50

  def setUp(self):
    super(MongoDataStoreBenchmarks, self).setUp()
    self.InitTable()


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
