#!/usr/bin/env python
"""DB mixin for blobs-related methods."""
from grr_response_core.lib import utils
from grr_response_server import blob_store


class _BlobRecord(object):

  def __init__(self):
    self._blob_refs = {}

  def AddBlobReference(self, blob_ref):
    self._blob_refs[blob_ref.offset] = blob_ref.Copy()

  def GetBlobReferences(self):
    return list(self._blob_refs.values())


class InMemoryDBBlobsMixin(blob_store.BlobStore):
  """InMemoryDB mixin for blobs related functions."""

  @utils.Synchronized
  def WriteBlobs(self, blob_id_data_map):
    """Writes given blobs."""
    self.blobs.update(blob_id_data_map)

  @utils.Synchronized
  def ReadBlobs(self, blob_ids):
    """Reads given blobs."""

    result = {}
    for blob_id in blob_ids:
      result[blob_id] = self.blobs.get(blob_id, None)

    return result

  @utils.Synchronized
  def CheckBlobsExist(self, blob_ids):
    """Checks if given blobs exit."""

    result = {}
    for blob_id in blob_ids:
      result[blob_id] = blob_id in self.blobs

    return result

  @utils.Synchronized
  def WriteHashBlobReferences(self, references_by_hash):
    for k, vs in references_by_hash.items():
      self.blob_refs_by_hashes[k] = [v.Copy() for v in vs]

  @utils.Synchronized
  def ReadHashBlobReferences(self, hashes):
    result = {}
    for hash_id in hashes:
      try:
        result[hash_id] = [v.Copy() for v in self.blob_refs_by_hashes[hash_id]]
      except KeyError:
        result[hash_id] = None

    return result
