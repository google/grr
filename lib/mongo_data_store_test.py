#!/usr/bin/env python

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests the mongo data store abstraction."""



from grr.client import conf
from grr.client import conf as flags

# Support mongo storage
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import mongo_data_store

from grr.lib import test_lib

FLAGS = flags.FLAGS


class MongoDataStoreTest(data_store_test.DataStoreTest):
  """Test the mongo data store abstraction."""

  def setUp(self):
    self.token = data_store.ACLToken("test", "Running tests")
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
  FLAGS.storage = "MongoDataStore"
  FLAGS.mongo_db_name = "grr_test"
  test_lib.main(args)

if __name__ == "__main__":
  conf.StartMain(main)
