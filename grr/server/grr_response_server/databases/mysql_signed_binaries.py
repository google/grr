#!/usr/bin/env python
"""MySQL implementation of DB methods for handling signed binaries."""

from collections.abc import Sequence
from typing import Optional, cast

import MySQLdb
import MySQLdb.cursors

from grr_response_core.lib import rdfvalue
from grr_response_proto import objects_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils


class MySQLDBSignedBinariesMixin(object):
  """Mixin providing a MySQL implementation of signed binaries DB logic."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
      references: objects_pb2.BlobReferences,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ):
    """Writes blob references for a signed binary to the DB."""
    assert cursor is not None

    args = {
        "binary_type": int(binary_id.binary_type),
        "binary_path": binary_id.path,
        "binary_path_hash": mysql_utils.Hash(binary_id.path),
        "blob_references": references.SerializeToString(),
    }
    query = """
      INSERT INTO signed_binary_references {cols}
      VALUES {vals}
      ON DUPLICATE KEY UPDATE
        blob_references = VALUES(blob_references)
    """.format(
        cols=mysql_utils.Columns(args), vals=mysql_utils.NamedPlaceholders(args)
    )
    cursor.execute(query, args)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> tuple[objects_pb2.BlobReferences, rdfvalue.RDFDatetime]:
    """Reads blob references for the signed binary with the given id."""
    assert cursor is not None

    cursor.execute(
        """
      SELECT blob_references, UNIX_TIMESTAMP(timestamp)
      FROM signed_binary_references
      WHERE binary_type = %s AND binary_path_hash = %s
    """,
        [binary_id.binary_type, mysql_utils.Hash(binary_id.path)],
    )
    row = cursor.fetchone()

    if not row:
      raise db.UnknownSignedBinaryError(binary_id)

    raw_references, timestamp = row
    # TODO(hanuszczak): pytype does not understand overloads, so we have to cast
    # to a non-optional object.
    datetime = cast(
        rdfvalue.RDFDatetime, mysql_utils.TimestampToRDFDatetime(timestamp)
    )

    references = objects_pb2.BlobReferences()
    references.ParseFromString(raw_references)
    return references, datetime

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadIDsForAllSignedBinaries(
      self,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> Sequence[objects_pb2.SignedBinaryID]:
    """Returns ids for all signed binaries in the DB."""
    assert cursor is not None

    cursor.execute(
        "SELECT binary_type, binary_path FROM signed_binary_references"
    )
    return [
        objects_pb2.SignedBinaryID(binary_type=binary_type, path=binary_path)
        for binary_type, binary_path in cursor.fetchall()
    ]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def DeleteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ) -> None:
    """Deletes blob references for the given signed binary from the DB."""
    assert cursor is not None

    cursor.execute(
        """
      DELETE FROM signed_binary_references
      WHERE binary_type = %s AND binary_path_hash = %s
    """,
        [binary_id.binary_type, mysql_utils.Hash(binary_id.path)],
    )
