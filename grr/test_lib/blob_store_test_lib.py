#!/usr/bin/env python
"""Test library for blob store-related code."""

from __future__ import annotations

from collections.abc import Iterable

from grr_response_core import config
from grr_response_server import blob_store
from grr_response_server.blob_stores import db_blob_store
from grr_response_server.models import blobs as models_blobs


class TestBlobStore(blob_store.BlobStore):
  """Test blob store ensuring both REL_DB and legacy blob stores are tested."""

  def __init__(self):
    super().__init__()
    self.new = db_blob_store.DbBlobStore()

  def WriteBlobs(
      self, blob_id_data_map: dict[models_blobs.BlobID, bytes]
  ) -> None:
    self.new.WriteBlobs(blob_id_data_map)

  def ReadBlobs(
      self, blob_ids: Iterable[models_blobs.BlobID]
  ) -> dict[models_blobs.BlobID, bytes | None]:
    return self.new.ReadBlobs(blob_ids)

  def CheckBlobsExist(
      self, blob_ids: Iterable[models_blobs.BlobID]
  ) -> dict[models_blobs.BlobID, bool]:
    return self.new.CheckBlobsExist(blob_ids)


def UseTestBlobStore() -> None:
  config.CONFIG.Set("Blobstore.implementation", TestBlobStore.__name__)
  blob_store.REGISTRY[TestBlobStore.__name__] = TestBlobStore
