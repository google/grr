#!/usr/bin/env python
"""The MySQL database methods for blobs handling."""

from collections.abc import Collection, Mapping
from typing import Optional

import MySQLdb.cursors

from grr_response_core.lib.util import precondition
from grr_response_proto import objects_pb2
from grr_response_server import blob_store
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import objects as rdf_objects

# Maximum size of one blob chunk, affected by MySQL configuration, especially
# innodb_log_file_size and max_allowed_packet.
BLOB_CHUNK_SIZE = 2**24  # MySQL MEDIUMBLOB, 16 MiB

CHUNKS_PER_INSERT = 100


def _Insert(cursor, table, values):
  """Inserts one or multiple rows into the given table.

  Args:
    cursor: The MySQL cursor to perform the insertion.
    table: The table name, where rows should be inserted.
    values: A list of dicts, associating column names to values.
  """
  assert cursor is not None
  precondition.AssertIterableType(values, dict)

  if not values:  # Nothing can be INSERTed with empty `values` list.
    return

  column_names = list(sorted(values[0]))
  for value_dict in values:
    if set(column_names) != set(value_dict):
      raise ValueError(
          "Given value dictionaries must have identical keys. "
          "Expecting columns {!r}, but got value {!r}".format(
              column_names, value_dict
          )
      )

  query = "INSERT IGNORE INTO %s {cols} VALUES {vals}" % table
  query = query.format(
      cols=mysql_utils.Columns(column_names),
      vals=mysql_utils.Placeholders(num=len(column_names), values=len(values)),
  )

  values_list = []
  for values_dict in values:
    values_list.extend(values_dict[column] for column in column_names)

  cursor.execute(query, values_list)


def _BlobToChunks(blob_id, blob):
  """Splits a Blob into chunks of size BLOB_CHUNK_SIZE."""
  #  In case of empty blob (with empty range), use [0].
  chunk_begins = list(range(0, len(blob), BLOB_CHUNK_SIZE)) or [0]
  chunks = []
  for i, chunk_begin in enumerate(chunk_begins):
    chunks.append({
        "blob_id": blob_id,
        "chunk_index": i,
        "blob_chunk": blob[chunk_begin : chunk_begin + BLOB_CHUNK_SIZE],
    })
  return chunks


def _PartitionChunks(chunks):
  """Groups chunks into partitions of size safe for a single INSERT."""
  partitions = [[]]
  partition_size = 0

  for chunk in chunks:
    cursize = len(chunk["blob_chunk"])
    if (
        cursize + partition_size > BLOB_CHUNK_SIZE
        or len(partitions[-1]) >= CHUNKS_PER_INSERT
    ):
      partitions.append([])
      partition_size = 0
    partitions[-1].append(chunk)
    partition_size += cursize

  return partitions


class MySQLDBBlobsMixin(blob_store.BlobStore):
  """MySQLDB mixin for blobs related functions."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def _WriteBlobsBatch(self, values, cursor=None):
    _Insert(cursor, "blobs", values)

  def WriteBlobs(self, blob_id_data_map):
    """Writes given blobs."""
    chunks = []
    for blob_id, blob in blob_id_data_map.items():
      chunks.extend(_BlobToChunks(bytes(blob_id), blob))
    for values in _PartitionChunks(chunks):
      self._WriteBlobsBatch(values)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadBlobs(
      self,
      blob_ids: list[models_blobs.BlobID],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> dict[models_blobs.BlobID, Optional[bytes]]:
    """Reads given blobs."""
    assert cursor is not None
    if not blob_ids:
      return {}

    query = (
        "SELECT blob_id, blob_chunk "
        "FROM blobs "
        "FORCE INDEX (PRIMARY) "
        "WHERE blob_id IN {} "
        "ORDER BY blob_id, chunk_index ASC"
    ).format(mysql_utils.Placeholders(len(blob_ids)))
    cursor.execute(query, [bytes(blob_id) for blob_id in blob_ids])
    results = {blob_id: None for blob_id in blob_ids}
    for blob_id_bytes, blob in cursor.fetchall():
      blob_id = models_blobs.BlobID(blob_id_bytes)
      if results[blob_id] is None:
        results[blob_id] = blob
      else:
        results[blob_id] += blob
    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def CheckBlobsExist(
      self,
      blob_ids: list[models_blobs.BlobID],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> dict[models_blobs.BlobID, bool]:
    """Checks if given blobs exist."""
    assert cursor is not None
    if not blob_ids:
      return {}

    exists = {blob_id: False for blob_id in blob_ids}
    query = (
        "SELECT blob_id "
        "FROM blobs "
        "FORCE INDEX (PRIMARY) "
        "WHERE blob_id IN {}".format(mysql_utils.Placeholders(len(blob_ids)))
    )
    cursor.execute(query, [bytes(blob_id) for blob_id in blob_ids])
    for (blob_id_bytes,) in cursor.fetchall():
      exists[models_blobs.BlobID(blob_id_bytes)] = True
    return exists

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteHashBlobReferences(
      self,
      references_by_hash: Mapping[
          rdf_objects.SHA256HashID, Collection[objects_pb2.BlobReference]
      ],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Writes blob references for a given set of hashes."""
    values = []
    for hash_id, blob_refs in references_by_hash.items():
      refs = objects_pb2.BlobReferences()
      for blob_ref in blob_refs:
        refs.items.append(blob_ref)
      values.append({
          "hash_id": hash_id.AsBytes(),
          "blob_references": refs.SerializeToString(),
      })
    _Insert(cursor, "hash_blob_references", values)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadHashBlobReferences(
      self,
      hashes: Collection[rdf_objects.SHA256HashID],
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Mapping[
      rdf_objects.SHA256HashID, Optional[Collection[objects_pb2.BlobReference]]
  ]:
    """Reads blob references of a given set of hashes."""
    assert cursor is not None
    if not hashes:
      return {}

    query = (
        "SELECT hash_id, blob_references FROM hash_blob_references WHERE "
        "hash_id IN {}"
    ).format(mysql_utils.Placeholders(len(hashes)))
    cursor.execute(query, [hash_id.AsBytes() for hash_id in hashes])
    results = {hash_id: None for hash_id in hashes}
    for hash_id, blob_references in cursor.fetchall():
      sha_hash_id = rdf_objects.SHA256HashID.FromSerializedBytes(hash_id)
      refs = objects_pb2.BlobReferences()
      refs.ParseFromString(blob_references)
      results[sha_hash_id] = list(refs.items)
    return results
