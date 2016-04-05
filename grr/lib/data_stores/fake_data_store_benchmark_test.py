#!/usr/bin/env python
"""The benchmark tests for the fake data store."""


from grr.lib import data_store_test
from grr.lib import flags
from grr.lib import test_lib


class FakeDataStoreBenchmarks(data_store_test.DataStoreBenchmarks):
  """Benchmark the fake data store."""


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
