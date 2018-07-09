#!/usr/bin/env python
"""DB mixin for blobs-related methods."""

from grr.core.grr_response_core.lib import utils
from grr.server.grr_response_server import db


class _BlobRecord(object):

  def __init__(self):
    self._blob_refs = {}

  def AddBlobReference(self, blob_ref):
    self._blob_refs[blob_ref.offset] = blob_ref.Copy()

  def GetBlobReferences(self):
    return self._blob_refs.values()


class InMemoryDBBlobsMixin(object):
  """InMemoryDB mixin for blobs related functions."""

  @utils.Synchronized
  def WriteClientPathBlobReferences(self, references_by_client_path_id):
    """Writes blob references for given client path ids."""
    all_path_ids = self._AllPathIDs()

    for client_path_id, blob_refs in references_by_client_path_id.items():
      path_idx = (client_path_id.client_id, client_path_id.path_type,
                  client_path_id.path_id)

      if path_idx not in all_path_ids:
        raise db.AtLeastOneUnknownPathError(
            references_by_client_path_id.values())

      blob_record = self.blob_records.setdefault(path_idx, _BlobRecord())

      for blob_ref in blob_refs:
        blob_record.AddBlobReference(blob_ref)

  @utils.Synchronized
  def ReadClientPathBlobReferences(self, client_path_ids):
    """Reads blob references of given client path ids."""

    result = {}
    for cpid in client_path_ids:
      try:
        blob_record = self.blob_records[(cpid.client_id, cpid.path_type,
                                         cpid.path_id)]
        result[cpid] = blob_record.GetBlobReferences()
      except KeyError:
        result[cpid] = []

    return result

  @utils.Synchronized
  def WriteBlobs(self, blob_id_data_pairs):
    """Writes given blobs."""

    self.blobs.update(blob_id_data_pairs)

  @utils.Synchronized
  def ReadBlobs(self, blob_ids):
    """Reads given blobs."""

    result = {}
    for blob_id in blob_ids:
      result[blob_id] = self.blobs.get(blob_id, None)

    return result
