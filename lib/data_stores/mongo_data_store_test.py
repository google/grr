#!/usr/bin/env python
"""Tests the mongo data store abstraction."""



from grr.client import conf

from grr.lib import access_control
from grr.lib import data_store
from grr.lib import data_store_test

from grr.lib import test_lib
from grr.lib.data_stores import mongo_data_store


class MongoDataStoreTest(data_store_test.DataStoreTest):
  """Test the mongo data store abstraction."""

  def setUp(self):
    super(MongoDataStoreTest, self).setUp()

    self.token = access_control.ACLToken("test", "Running tests")
    data_store.DB = mongo_data_store.MongoDataStore()
    data_store.DB.security_manager = test_lib.MockSecurityManager()

    # Drop the collection.
    data_store.DB.db_handle.drop_collection(data_store.DB.latest_collection)
    data_store.DB.db_handle.drop_collection(data_store.DB.versioned_collection)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  conf.StartMain(main)
