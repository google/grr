#!/usr/bin/env python
from absl.testing import absltest

from grr_response_server.databases import db_blob_keys_test_lib
from grr_response_server.databases import mysql_test
from grr.test_lib import testing_startup


class MySQLBlobKeysTest(
    db_blob_keys_test_lib.DatabaseTestBlobKeysMixin,
    mysql_test.MysqlTestBase,
    absltest.TestCase,
):

  @classmethod
  def setUpClass(cls):
    testing_startup.TestInit()
    super().setUpClass()


if __name__ == "__main__":
  absltest.main()
