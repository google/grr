#!/usr/bin/env python
"""Benchmark tests for MySQL advanced data store."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_server import data_store_test
from grr_response_server.data_stores import mysql_advanced_data_store_test
from grr.test_lib import test_lib


class MysqlAdvancedDataStoreBenchmarks(
    mysql_advanced_data_store_test.MysqlAdvancedTestMixin,
    data_store_test.DataStoreBenchmarks):
  """Benchmark the mysql data store abstraction."""


class MysqlAdvancedDataStoreCSVBenchmarks(
    mysql_advanced_data_store_test.MysqlAdvancedTestMixin,
    data_store_test.DataStoreCSVBenchmarks):
  """Benchmark the mysql data store abstraction."""


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
