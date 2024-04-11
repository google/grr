#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_server.databases import db_blob_references_test
from grr_response_server.databases import mysql_test
from grr.test_lib import test_lib


class MysqlBlobReferencesTest(
    db_blob_references_test.DatabaseTestBlobReferencesMixin,
    mysql_test.MysqlTestBase,
    absltest.TestCase,
):
  pass


if __name__ == "__main__":
  app.run(test_lib.main)
