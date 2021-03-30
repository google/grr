#!/usr/bin/env python
"""Tests for the MySQL-based blob store."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from absl.testing import absltest

from grr_response_server import blob_store_test_mixin
from grr_response_server.blob_stores import db_blob_store
from grr_response_server.databases import mysql_test
from grr.test_lib import test_lib


class MySQLBlobStoreTest(blob_store_test_mixin.BlobStoreTestMixin,
                         mysql_test.MysqlTestBase, absltest.TestCase):

  def CreateBlobStore(self):
    db, db_cleanup_fn = self.CreateDatabase()
    return (db_blob_store.DbBlobStore(db), db_cleanup_fn)


if __name__ == "__main__":
  app.run(test_lib.main)
