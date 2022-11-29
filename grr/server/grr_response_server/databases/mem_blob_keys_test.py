#!/usr/bin/env python
from absl.testing import absltest

from grr_response_server.databases import db_blob_keys_test_lib
from grr_response_server.databases import mem_test_base


class InMemoryDBBlobKeysTest(
    db_blob_keys_test_lib.DatabaseTestBlobKeysMixin,
    mem_test_base.MemoryDBTestBase,
    absltest.TestCase,
):
  pass  # Test methods are defined in the base mixin class.


if __name__ == "__main__":
  absltest.main()
