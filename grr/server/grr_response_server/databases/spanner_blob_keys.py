#!/usr/bin/env python
"""Blob encryption key methods of Spanner database implementation."""
import base64

from typing import Collection, Dict, Optional

from google.cloud import spanner as spanner_lib
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils
from grr_response_server.models import blobs as models_blobs


class BlobKeysMixin:
  """A Spanner mixin with implementation of blob encryption keys methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteBlobEncryptionKeys(
      self,
      key_names: Dict[models_blobs.BlobID, str],
  ) -> None:
    """Associates the specified blobs with the given encryption keys."""
    # A special case for empty list of blob identifiers to avoid issues with an
    # empty mutation.
    if not key_names:
      return

    def Mutation(mut) -> None:
      for blob_id, key_name in key_names.items():
        mut.insert(
          table="BlobEncryptionKeys",
          columns=("BlobId", "CreationTime", "KeyName"),
          values=[((base64.b64encode(bytes(blob_id))), spanner_lib.COMMIT_TIMESTAMP, key_name)]
        )

    self.db.Mutate(Mutation, txn_tag="WriteBlobEncryptionKeys")


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadBlobEncryptionKeys(
      self,
      blob_ids: Collection[models_blobs.BlobID],
  ) -> Dict[models_blobs.BlobID, Optional[str]]:
    """Retrieves encryption keys associated with blobs."""
    # A special case for empty list of blob identifiers to avoid syntax errors
    # in the query below.
    if not blob_ids:
      return {}

    param_placeholders = ", ".join([f"{{blobId{i}}}" for i in range(len(blob_ids))])

    params = {}
    for i, blob_id_bytes in enumerate(blob_ids):
      param_name = f"blobId{i}"
      params[param_name] = base64.b64encode(bytes(blob_id_bytes))

    query = f"""
    SELECT k.BlobId, k.KeyName
      FROM BlobEncryptionKeys AS k
        INNER JOIN (SELECT k.BlobId, MAX(k.CreationTime) AS MaxCreationTime
            FROM BlobEncryptionKeys AS k
          WHERE k.BlobId IN ({param_placeholders})
          GROUP BY k.BlobId) AS last_k
        ON k.BlobId = last_k.BlobId
        AND k.CreationTime = last_k.MaxCreationTime
    """

    results = {blob_id: None for blob_id in blob_ids}

    for blob_id_bytes, key_name in self.db.ParamQuery(
        query, params, txn_tag="ReadBlobEncryptionKeys"
    ):
      blob_id = models_blobs.BlobID(base64.b64decode(blob_id_bytes))
      results[blob_id] = key_name

    return results
