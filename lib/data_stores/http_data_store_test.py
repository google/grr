#!/usr/bin/env python
"""Tests the HTTP remote data store abstraction."""


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.data_stores import http_data_store


class HTTPDataStoreMixin(object):

  def InitDatastore(self):
    config_lib.CONFIG.Set("HTTPDataStore.username", "testuser")
    config_lib.CONFIG.Set("HTTPDataStore.password", "testpass")
    config_lib.CONFIG.Set("Dataserver.server_list", ["http://127.0.0.1:7000",
                                                     "http://127.0.0.1:7001"])
    data_store.DB = http_data_store.HTTPDataStore()

  def DestroyDatastore(self):
    pass


class HTTPDataStoreTest(HTTPDataStoreMixin,
                        data_store_test.DataStoreTest):
  """Test the remote data store."""


class HTTPDataStoreBenchmarks(HTTPDataStoreMixin,
                              data_store_test.DataStoreBenchmarks):
  """Benchmark the HTTP remote data store abstraction."""


class HTTPDataStoreCSVBenchmarks(HTTPDataStoreMixin,
                                 data_store_test.DataStoreCSVBenchmarks):
  """Benchmark the HTTP remote data store."""


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
