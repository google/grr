#!/usr/bin/env python
"""The benchmark tests for the fake data store."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_server import data_store_test
from grr.test_lib import test_lib


class FakeDataStoreBenchmarks(data_store_test.DataStoreBenchmarks):
  """Benchmark the fake data store."""


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
