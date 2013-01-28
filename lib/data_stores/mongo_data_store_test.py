#!/usr/bin/env python
"""Tests the mongo data store abstraction."""



from grr.client import conf
from grr.client import conf as flags

from grr.lib import data_store
from grr.lib import data_store_test

from grr.lib import test_lib

FLAGS = flags.FLAGS


class MongoDataStoreTest(data_store_test.DataStoreTest):
  """Test the mongo data store abstraction."""

  def setUp(self):
    self.token = data_store.ACLToken("test", "Running tests")
    FLAGS.test_data_store = "MongoDataStore"
    FLAGS.mongo_db_name = "grr_test"
    super(MongoDataStoreTest, self).setUp()

    data_store.DB.security_manager = test_lib.MockSecurityManager()

    # Drop the collection.
    data_store.DB.db_handle.drop_collection(data_store.DB.latest_collection)
    data_store.DB.db_handle.drop_collection(data_store.DB.versioned_collection)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  conf.StartMain(main)
