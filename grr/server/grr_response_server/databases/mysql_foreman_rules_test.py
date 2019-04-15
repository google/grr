#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from absl.testing import absltest

from grr_response_server.databases import db_foreman_rules_test
from grr_response_server.databases import mysql_test
from grr.test_lib import test_lib


class MysqlForemanRulesTest(db_foreman_rules_test.DatabaseTestForemanRulesMixin,
                            mysql_test.MysqlTestBase, absltest.TestCase):
  pass


if __name__ == "__main__":
  app.run(test_lib.main)
