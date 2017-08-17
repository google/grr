#!/usr/bin/env python
"""Benchmark tests for the Cloud Bigtable data store."""


from grr.lib import flags
from grr.server import data_store_test
from grr.server.data_stores import cloud_bigtable_data_store_test
from grr.test_lib import test_lib


class CloudBigtableDataStoreBenchmarks(
    cloud_bigtable_data_store_test.CloudBigTableDataStoreMixin,
    data_store_test.DataStoreBenchmarks):
  """Performance test cloud bigtable."""


def main(argv):
  del argv  # Unused.
  test_lib.main()


if __name__ == "__main__":
  flags.StartMain(main)
