#!/usr/bin/env python
"""Benchmark tests for HTTP datastore."""

from grr.lib import flags
from grr.server import data_store_test
from grr.server.data_stores import http_data_store_test
from grr.test_lib import test_lib


class HTTPDataStoreBenchmarks(http_data_store_test.HTTPDataStoreMixin,
                              data_store_test.DataStoreBenchmarks):
  """Benchmark the HTTP remote data store abstraction."""


class HTTPDataStoreCSVBenchmarks(http_data_store_test.HTTPDataStoreMixin,
                                 data_store_test.DataStoreCSVBenchmarks):
  """Benchmark the HTTP remote data store."""


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
