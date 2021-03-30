#!/usr/bin/env python
"""REL_DB blobstore implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_server import blob_store
from grr_response_server import data_store


class DbBlobStore(blob_store.BlobStore):
  """A REL_DB-based blob store implementation."""

  def __init__(self, delegate=None):
    self._delegate = delegate

  # TODO(user): REL_DB can be None, because initialization is happening at some
  # early but nondeterministic time. Once REL_DB is guaranteed to be not None,
  # perform type checking that REL_DB.delegate is a BlobStore..
  @property
  def delegate(self):
    return self._delegate or data_store.REL_DB.delegate

  def WriteBlobs(self, blob_id_data_map):
    return self.delegate.WriteBlobs(blob_id_data_map)

  def ReadBlobs(self, blob_ids):
    return self.delegate.ReadBlobs(blob_ids)

  def CheckBlobsExist(self, blob_ids):
    return self.delegate.CheckBlobsExist(blob_ids)
