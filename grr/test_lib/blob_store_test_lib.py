#!/usr/bin/env python
"""Test library for blob store-related code."""

from grr_response_core import config
from grr_response_core.lib.util import compatibility
from grr_response_server import blob_store
from grr_response_server.blob_stores import db_blob_store


class TestBlobStore(blob_store.BlobStore):
  """Test blob store ensuring both REL_DB and legacy blob stores are tested."""

  def __init__(self):
    super().__init__()
    self.new = db_blob_store.DbBlobStore()

  def WriteBlobs(self, blob_id_data_map):
    self.new.WriteBlobs(blob_id_data_map)

  def ReadBlobs(self, blob_ids):
    return self.new.ReadBlobs(blob_ids)

  def CheckBlobsExist(self, blob_ids):
    return self.new.CheckBlobsExist(blob_ids)


def UseTestBlobStore():
  config.CONFIG.Set("Blobstore.implementation",
                    compatibility.GetName(TestBlobStore))
  blob_store.REGISTRY[compatibility.GetName(TestBlobStore)] = TestBlobStore
