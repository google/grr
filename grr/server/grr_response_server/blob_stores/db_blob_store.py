#!/usr/bin/env python
"""REL_DB blobstore implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server import blob_store
from grr_response_server import data_store


class DbBlobStore(blob_store.BlobStore):
  """A REL_DB-based blob store implementation."""

  def WriteBlobs(self, blob_id_data_map):
    data_store.REL_DB.WriteBlobs(blob_id_data_map)

  def ReadBlobs(self, blob_ids):
    return data_store.REL_DB.ReadBlobs(blob_ids)

  def CheckBlobsExist(self, blob_ids):
    return data_store.REL_DB.CheckBlobsExist(blob_ids)
