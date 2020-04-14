#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest

from grr_response_server.databases import db_yara_test_lib
from grr_response_server.databases import mem_test_base


class MemYaraTest(
    db_yara_test_lib.DatabaseTestYaraMixin,
    mem_test_base.MemoryDBTestBase,
    absltest.TestCase,
):
  pass


if __name__ == "__main__":
  absltest.main()
