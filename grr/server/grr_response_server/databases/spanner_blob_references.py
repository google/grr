#!/usr/bin/env python
"""A library with blob references methods of Spanner database implementation."""
import base64

from typing import Collection, Mapping, Optional

from google.cloud import spanner as spanner_lib

from grr_response_proto import objects_pb2
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils
from grr_response_server.rdfvalues import objects as rdf_objects


class BlobReferencesMixin:
  """A Spanner database mixin with implementation of blob references methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteHashBlobReferences(
      self,
      references_by_hash: Mapping[
          rdf_objects.SHA256HashID, Collection[objects_pb2.BlobReference]
      ],
  ) -> None:
    """Writes blob references for a given set of hashes."""
    def Mutation(mut) -> None:
      for hash_id, refs in references_by_hash.items():
        hash_id_b64 = base64.b64encode(bytes(hash_id.AsBytes()))
        key_range = spanner_lib.KeyRange(start_closed=[hash_id_b64,], end_closed=[hash_id_b64,])
        keyset = spanner_lib.KeySet(ranges=[key_range])
        # Make sure we delete any of the previously existing blob references.
        mut.delete("HashBlobReferences", keyset)

        for ref in refs:
          mut.insert(
              table="HashBlobReferences",
              columns=("HashId", "BlobId", "Offset", "Size",),
              values=[(hash_id_b64, base64.b64encode(bytes(ref.blob_id)), ref.offset, ref.size,)]
          )
  
    self.db.Mutate(Mutation, txn_tag="WriteHashBlobReferences")


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHashBlobReferences(
      self, hashes: Collection[rdf_objects.SHA256HashID]
  ) -> Mapping[
      rdf_objects.SHA256HashID, Optional[Collection[objects_pb2.BlobReference]]
  ]:
    """Reads blob references of a given set of hashes."""
    result = {}
    key_ranges = []
    
    for h in hashes:
      hash_id_b64 = base64.b64encode(bytes(h.AsBytes()))
      key_ranges.append(spanner_lib.KeyRange(start_closed=[hash_id_b64,], end_closed=[hash_id_b64,]))
      result[h] = []
  
    rows = spanner_lib.KeySet(ranges=key_ranges)

    hashes_left = set(hashes)
    for row in self.db.ReadSet(
        table="HashBlobReferences",
        rows=rows,
        cols=("HashId", "BlobId", "Offset", "Size"),
        txn_tag="ReadHashBlobReferences"
    ):
      hash_id = rdf_objects.SHA256HashID(base64.b64decode(row[0]))

      blob_ref = objects_pb2.BlobReference()
      blob_ref.blob_id = base64.b64decode(row[1])
      blob_ref.offset = row[2]
      blob_ref.size = row[3]

      result[hash_id].append(blob_ref)
      hashes_left.discard(hash_id)

    for h in hashes_left:
      result[h] = None

    return result
