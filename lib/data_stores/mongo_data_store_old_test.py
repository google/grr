#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Tests the mongo data store abstraction."""



# pylint: disable=unused-import
# Support mongo storage
from grr.lib import access_control
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.data_stores import mongo_data_store_old
# pylint: enable=unused-import


class MongoDataStoreV1Test(data_store_test.DataStoreTest):
  """Test the mongo data store abstraction."""

  def setUp(self):
    super(MongoDataStoreV1Test, self).setUp()

    self.token = access_control.ACLToken("test", "Running tests")
    data_store.DB = mongo_data_store_old.MongoDataStoreV1()
    data_store.DB.security_manager = test_lib.MockSecurityManager()

    # Drop the collection.
    data_store.DB.db_handle.drop_collection(data_store.DB.collection)

  def testNewestTimestamps(self):
    """This test is switched off in the mongo data store.

    This test essentially checks that specifying age=NEWEST_TIME is honored by
    the data store. The purpose of this flag is to allow the data store to do
    less work as its only fetching the latest version of each attribute. Due to
    the current data model we use in mongo, we fetch all versions of each
    attribute anyway because everything is stored in the same document. This
    means that the database is actually always doing all the work, and
    transferring all the data. This is suboptimal and should be fixed by
    redesigning the mongo data store data model. Until then there is no point
    implementing the age parameter properly since it would incur more work
    (i.e. fetch all the versions, and then filter the newest one).

    Hence for now we switch off this test.
    """


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
