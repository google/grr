#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from absl.testing import absltest

from grr_response_server.databases import db_cronjob_test
from grr_response_server.databases import mem_test_base
from grr.test_lib import test_lib


class MemoryDBCronJobTest(db_cronjob_test.DatabaseTestCronJobMixin,
                          mem_test_base.MemoryDBTestBase, absltest.TestCase):
  pass


if __name__ == "__main__":
  app.run(test_lib.main)
