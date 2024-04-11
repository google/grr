#!/usr/bin/env python
"""Tests for REL_DB-based blob store."""

from absl import app

from grr_response_server import blob_store_test_mixin
from grr_response_server.blob_stores import db_blob_store
from grr.test_lib import test_lib


class DbBlobStoreTest(
    blob_store_test_mixin.BlobStoreTestMixin, test_lib.GRRBaseTest
):

  def CreateBlobStore(self):
    return (db_blob_store.DbBlobStore(), lambda: None)


if __name__ == "__main__":
  app.run(test_lib.main)
