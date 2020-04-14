#!/usr/bin/env python
# Lint as: python3
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest

from grr_response_server.databases import db_yara_test_lib
from grr_response_server.databases import mysql_test
from grr.test_lib import testing_startup


class MySQLYaraTest(
    db_yara_test_lib.DatabaseTestYaraMixin,
    mysql_test.MysqlTestBase,
    absltest.TestCase,
):

  @classmethod
  def setUpClass(cls):
    testing_startup.TestInit()
    super(MySQLYaraTest, cls).setUpClass()


if __name__ == "__main__":
  absltest.main()
