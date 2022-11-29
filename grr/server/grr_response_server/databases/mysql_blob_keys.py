#!/usr/bin/env python
"""A module with MySQL implementation of blobstore encryption keys methods."""
from __future__ import annotations

from typing import Collection
from typing import Dict
from typing import Optional

import MySQLdb

from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import objects as rdf_objects


class MySQLDBBlobKeysMixin(object):
  """A MySQL database mixin class with blobstore encryption keys methods."""

  @mysql_utils.WithTransaction()
  def WriteBlobEncryptionKeys(
      self,
      keys: Dict[rdf_objects.BlobID, abstract_db.EncryptionKey],
      cursor: MySQLdb.cursors.Cursor,
  ) -> None:
    """Associates the specified blobs with the given encryption keys."""
    query = """
    INSERT
      INTO blob_encryption_keys(blob_id, key_id, nonce)
    VALUES (%s, %s, %s)
    """

    args = []
    for blob_id, key in keys.items():
      args.append((blob_id.AsBytes(), key.key_id, key.nonce))

    cursor.executemany(query, args)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadBlobEncryptionKeys(
      self,
      blob_ids: Collection[rdf_objects.BlobID],
      cursor: MySQLdb.cursors.Cursor,
  ) -> Dict[rdf_objects.BlobID, Optional[abstract_db.EncryptionKey]]:
    """Retrieves encryption keys associated with blobs."""
    # A special case for empty list of blob identifiers to avoid syntax errors
    # in the query below.
    if not blob_ids:
      return {}

    blob_ids_bytes = [blob_id.AsBytes() for blob_id in blob_ids]

    query = """
    SELECT k.blob_id, k.key_id, k.nonce
      FROM blob_encryption_keys AS k
INNER JOIN (SELECT blob_id, MAX(timestamp) AS max_timestamp
              FROM blob_encryption_keys
             WHERE blob_id IN ({})
             GROUP BY blob_id) AS last_k
        ON k.blob_id = last_k.blob_id
       AND k.timestamp = last_k.max_timestamp
    """.format(",".join(["%s"] * len(blob_ids_bytes)))

    results = {blob_id: None for blob_id in blob_ids}

    cursor.execute(query, blob_ids_bytes)
    for blob_id_bytes, key_id, nonce in cursor.fetchall():
      blob_id = rdf_objects.BlobID(blob_id_bytes)
      results[blob_id] = abstract_db.EncryptionKey(key_id=key_id, nonce=nonce)

    return results
