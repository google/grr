#!/usr/bin/env python
"""Benchmark tests for sqlite datastore."""


from grr.lib import flags
from grr.server.grr_response_server import data_store_test
from grr.server.grr_response_server.data_stores import sqlite_data_store_test

from grr.test_lib import test_lib


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
