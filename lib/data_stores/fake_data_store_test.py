#!/usr/bin/env python
"""Tests the fake data store - in memory implementation."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib


class FakeDataStoreTest(data_store_test._DataStoreTest):
  """Test the fake data store."""

  def testApi(self):
    """The fake datastore doesn't strictly conform to the api but this is ok."""


class FakeDataStoreBenchmarks(data_store_test.DataStoreBenchmarks):
  """Benchmark the fake data store.

  This gives an upper bound on data store performance - since the fake data
  store is the most trivial data store and therefore the fastest.
  """


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
