#!/usr/bin/env python
"""MySQL implementation of DB methods for handling signed binaries."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from typing import cast, Sequence, Tuple

from grr_response_core.lib import rdfvalue
from grr_response_server.databases import db
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import objects as rdf_objects


class MySQLDBSignedBinariesMixin(object):
  """Mixin providing a MySQL implementation of signed binaries DB logic."""

  @mysql_utils.WithTransaction()
  def WriteSignedBinaryReferences(self,
                                  binary_id,
                                  references,
                                  cursor=None):
    """Writes blob references for a signed binary to the DB."""
    args = {
        "binary_type":
            binary_id.binary_type.SerializeToDataStore(),
        "binary_path":
            binary_id.path,
        "binary_path_hash":
            mysql_utils.Hash(binary_id.path),
        "blob_references":
            references.SerializeToString()
    }
    query = """
      INSERT INTO signed_binary_references {cols}
      VALUES {vals}
      ON DUPLICATE KEY UPDATE
        blob_references = VALUES(blob_references)
    """.format(
        cols=mysql_utils.Columns(args),
        vals=mysql_utils.NamedPlaceholders(args))
    cursor.execute(query, args)

  @mysql_utils.WithTransaction(readonly=True)
  def ReadSignedBinaryReferences(
      self, binary_id,
      cursor=None):
    """Reads blob references for the signed binary with the given id."""
    cursor.execute(
        """
      SELECT blob_references, UNIX_TIMESTAMP(timestamp)
      FROM signed_binary_references
      WHERE binary_type = %s AND binary_path_hash = %s
    """, [
        binary_id.binary_type.SerializeToDataStore(),
        mysql_utils.Hash(binary_id.path)
    ])
    row = cursor.fetchone()

    if not row:
      raise db.UnknownSignedBinaryError(binary_id)

    raw_references, timestamp = row
    # TODO(hanuszczak): pytype does not understand overloads, so we have to cast
    # to a non-optional object.
    datetime = cast(rdfvalue.RDFDatetime,
                    mysql_utils.TimestampToRDFDatetime(timestamp))

    references = rdf_objects.BlobReferences.FromSerializedString(raw_references)
    return references, datetime

  @mysql_utils.WithTransaction(readonly=True)
  def ReadIDsForAllSignedBinaries(self, cursor=None
                                 ):
    """Returns ids for all signed binaries in the DB."""
    cursor.execute(
        "SELECT binary_type, binary_path FROM signed_binary_references")
    return [
        rdf_objects.SignedBinaryID(binary_type=binary_type, path=binary_path)
        for binary_type, binary_path in cursor.fetchall()
    ]

  @mysql_utils.WithTransaction()
  def DeleteSignedBinaryReferences(self,
                                   binary_id,
                                   cursor=None):
    """Deletes blob references for the given signed binary from the DB."""
    cursor.execute(
        """
      DELETE FROM signed_binary_references
      WHERE binary_type = %s AND binary_path_hash = %s
    """, [
        binary_id.binary_type.SerializeToDataStore(),
        mysql_utils.Hash(binary_id.path)
    ])
