#!/usr/bin/env python
"""Tests the fake data store - in memory implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_server import data_store_test
from grr.test_lib import test_lib


class FakeDataStoreTest(data_store_test.DataStoreTestMixin,
                        test_lib.GRRBaseTest):
  """Test the fake data store."""

  def testApi(self):
    """The fake datastore doesn't strictly conform to the api but this is ok."""


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
