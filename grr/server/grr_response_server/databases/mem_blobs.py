#!/usr/bin/env python
"""DB mixin for blobs-related methods."""

from grr.core.grr_response_core.lib import utils
from grr.server.grr_response_server import db


class InMemoryDBBlobsMixin(object):
  """InMemoryDB mixin for blobs related functions."""

  @utils.Synchronized
  def WriteClientPathBlobReferences(self, references_by_client_path_id):
    """Writes blob references for given client path ids."""

    for client_path_id, blob_refs in references_by_client_path_id.items():
      try:
        path_record = self.path_records[(client_path_id.client_id,
                                         client_path_id.path_type,
                                         client_path_id.path_id)]
      except KeyError:
        raise db.AtLeastOneUnknownPathError(
            references_by_client_path_id.values())

      for blob_ref in blob_refs:
        path_record.AddBlobReference(blob_ref)

  @utils.Synchronized
  def ReadClientPathBlobReferences(self, client_path_ids):
    """Reads blob references of given client path ids."""

    result = {}
    for cpid in client_path_ids:
      try:
        path_record = self.path_records[(cpid.client_id, cpid.path_type,
                                         cpid.path_id)]
        result[cpid] = path_record.GetBlobReferences()
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
