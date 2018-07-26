#!/usr/bin/env python
"""The MySQL database methods for blobs handling."""


class MySQLDBBlobsMixin(object):
  """MySQLDB mixin for blobs related functions."""

  def WriteClientPathBlobReferences(self, references_by_path):
    raise NotImplementedError()

  def ReadClientPathBlobReferences(self, paths):
    raise NotImplementedError()

  def WriteBlobs(self, blob_id_data_pairs):
    raise NotImplementedError()

  def ReadBlobs(self, blob_ids):
    raise NotImplementedError()

  def CheckBlobsExist(self, blob_ids):
    raise NotImplementedError()
