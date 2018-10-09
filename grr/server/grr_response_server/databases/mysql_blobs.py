#!/usr/bin/env python
"""The MySQL database methods for blobs handling."""


class MySQLDBBlobsMixin(object):
  """MySQLDB mixin for blobs related functions."""

  def WriteBlobs(self, blob_id_data_map):
    raise NotImplementedError()

  def ReadBlobs(self, blob_ids):
    raise NotImplementedError()

  def CheckBlobsExist(self, blob_ids):
    raise NotImplementedError()

  def WriteHashBlobReferences(self, references_by_hash):
    raise NotImplementedError()

  def ReadHashBlobReferences(self, hashes):
    raise NotImplementedError()
