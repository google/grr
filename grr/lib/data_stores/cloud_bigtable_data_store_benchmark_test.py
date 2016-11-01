#!/usr/bin/env python
"""Benchmark tests for the Cloud Bigtable data store."""


from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.data_stores import cloud_bigtable_data_store_test


class CloudBigtableDataStoreBenchmarks(
    cloud_bigtable_data_store_test.CloudBigTableDataStoreMixin,
    data_store_test.DataStoreBenchmarks):
  """Performance test cloud bigtable."""


def main(argv):
  test_lib.main(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
