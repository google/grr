#!/usr/bin/env python
"""DB mixin for blobs-related methods."""

from typing import Collection, Mapping, Optional

from grr_response_core.lib import utils
from grr_response_proto import objects_pb2
from grr_response_server import blob_store
from grr_response_server.rdfvalues import objects as rdf_objects


class _BlobRecord(object):

  def __init__(self):
    self._blob_refs = {}

  def AddBlobReference(self, blob_ref):
    self._blob_refs[blob_ref.offset] = blob_ref.Copy()

  def GetBlobReferences(self):
    return list(self._blob_refs.values())


class InMemoryDBBlobsMixin(blob_store.BlobStore):
  """InMemoryDB mixin for blobs related functions."""

  blob_refs_by_hashes: dict[
      rdf_objects.SHA256HashID, list[objects_pb2.BlobReference]
  ]

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
  def WriteHashBlobReferences(
      self,
      references_by_hash: Mapping[
          rdf_objects.SHA256HashID, Collection[objects_pb2.BlobReference]
      ],
  ) -> None:
    for k, vs in references_by_hash.items():
      blob_refs = []

      for v in vs:
        blob_ref = objects_pb2.BlobReference()
        blob_ref.CopyFrom(v)

        blob_refs.append(blob_ref)

      self.blob_refs_by_hashes[k] = blob_refs

  @utils.Synchronized
  def ReadHashBlobReferences(
      self,
      hashes: Collection[rdf_objects.SHA256HashID],
  ) -> Mapping[
      rdf_objects.SHA256HashID, Optional[Collection[objects_pb2.BlobReference]]
  ]:
    result = {hash_id: None for hash_id in hashes}

    for hash_id in hashes:
      try:
        blob_refs = self.blob_refs_by_hashes[hash_id]
      except KeyError:
        continue

      blob_ref_copies = []
      for blob_ref in blob_refs:
        blob_ref_copy = objects_pb2.BlobReference()
        blob_ref_copy.CopyFrom(blob_ref)

        blob_ref_copies.append(blob_ref_copy)

      result[hash_id] = blob_ref_copies

    return result
