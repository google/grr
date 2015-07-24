#!/usr/bin/env python
"""Benchmark tests for MySQL datastore."""


from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib

from grr.lib.data_stores import mysql_data_store_test


class MysqlDataStoreBenchmarks(mysql_data_store_test.MysqlTestMixin,
                               data_store_test.DataStoreBenchmarks):
  """Benchmark the mysql data store abstraction."""


class MysqlDataStoreCSVBenchmarks(mysql_data_store_test.MysqlTestMixin,
                                  data_store_test.DataStoreCSVBenchmarks):
  """Benchmark the mysql data store abstraction."""


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
