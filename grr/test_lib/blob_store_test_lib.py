#!/usr/bin/env python
"""Test library for blob store-related code."""

from grr_response_core import config
from grr_response_core.lib.util import compatibility
from grr_response_server import blob_store
from grr_response_server.blob_stores import db_blob_store
from grr_response_server.blob_stores import memory_stream_bs


class TestBlobStore(blob_store.BlobStore):
  """Test blob store ensuring both REL_DB and legacy blob stores are tested."""

  def __init__(self):
    super(TestBlobStore, self).__init__()
    self.new = db_blob_store.DbBlobStore()
    self.legacy = memory_stream_bs.MemoryStreamBlobStore()

  def WriteBlobs(self, blob_id_data_map):
    self.new.WriteBlobs(blob_id_data_map)
    self.legacy.WriteBlobs(blob_id_data_map)

  def ReadBlobs(self, blob_ids):
    new_result = self.new.ReadBlobs(blob_ids)
    legacy_result = self.legacy.ReadBlobs(blob_ids)
    if new_result != legacy_result:
      raise RuntimeError("ReadBlobs regression detected: %r != %r" %
                         (legacy_result, new_result))

    return new_result

  def CheckBlobsExist(self, blob_ids):
    new_result = self.new.CheckBlobsExist(blob_ids)
    legacy_result = self.legacy.CheckBlobsExist(blob_ids)
    if new_result != legacy_result:
      raise RuntimeError("ReadBlobs regression detected: %r != %r" %
                         (legacy_result, new_result))

    return new_result


def UseTestBlobStore():
  config.CONFIG.Set("Blobstore.implementation",
                    compatibility.GetName(TestBlobStore))
  blob_store.REGISTRY[compatibility.GetName(TestBlobStore)] = TestBlobStore
