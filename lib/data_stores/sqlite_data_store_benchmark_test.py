#!/usr/bin/env python
"""Benchmark tests for sqlite datastore."""


from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib

from grr.lib.data_stores import sqlite_data_store_test


class SqliteDataStoreBenchmarks(sqlite_data_store_test.SqliteTestMixin,
                                data_store_test.DataStoreBenchmarks):
  """Benchmark the SQLite data store abstraction."""


class SqliteDataStoreCSVBenchmarks(sqlite_data_store_test.SqliteTestMixin,
                                   data_store_test.DataStoreCSVBenchmarks):
  """Benchmark the SQLite data store abstraction."""


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
