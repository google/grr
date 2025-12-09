#!/usr/bin/env python
"""A module with signed binaries methods of the Spanner backend."""

from typing import Sequence, Tuple

from google.api_core.exceptions import NotFound
from google.cloud import spanner as spanner_lib

from grr_response_core.lib import rdfvalue
from grr_response_proto import objects_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class SignedBinariesMixin:
  """A Spanner database mixin with implementation of signed binaries."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
      references: objects_pb2.BlobReferences,
  ) -> None:
    """Writes blob references for a signed binary to the DB.

    Args:
      binary_id: Signed binary id for the binary.
      references: Blob references for the given binary.
    """
    row = {
        "Type": int(binary_id.binary_type),
        "Path": binary_id.path,
        "BlobReferences": references,
        "CreationTime": spanner_lib.COMMIT_TIMESTAMP,
    }
    self.db.InsertOrUpdate(
        table="SignedBinaries", row=row, txn_tag="WriteSignedBinaryReferences"
    )


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadSignedBinaryReferences(
      self, binary_id: objects_pb2.SignedBinaryID
  ) -> Tuple[objects_pb2.BlobReferences, rdfvalue.RDFDatetime]:
    """Reads blob references for the signed binary with the given id.

    Args:
      binary_id: Signed binary id for the binary.

    Returns:
      A tuple of the signed binary's rdf_objects.BlobReferences and an
      RDFDatetime representing the time when the references were written to the
      DB.
    """
    binary_type = int(binary_id.binary_type)

    try:
      row = self.db.Read(
          table="SignedBinaries",
          key=(binary_type, binary_id.path),
          cols=("BlobReferences", "CreationTime"),
          txn_tag="ReadSignedBinaryReferences"
      )
    except NotFound as error:
      raise db.UnknownSignedBinaryError(binary_id) from error

    raw_references = row[0]
    creation_time = row[1]

    references = objects_pb2.BlobReferences()
    references.ParseFromString(raw_references)
    return references, rdfvalue.RDFDatetime.FromDatetime(creation_time)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadIDsForAllSignedBinaries(self) -> Sequence[objects_pb2.SignedBinaryID]:
    """Returns ids for all signed binaries in the DB."""
    results = []

    query = """
    SELECT sb.Type, sb.Path
      FROM SignedBinaries as sb
    """

    for [binary_type, binary_path] in self.db.Query(
        query, txn_tag="ReadIDsForAllSignedBinaries"
    ):
      binary_id = objects_pb2.SignedBinaryID(
          binary_type=binary_type, path=binary_path
      )
      results.append(binary_id)

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
  ) -> None:
    """Deletes blob references for the given signed binary from the DB.

    Does nothing if no entry with the given id exists in the DB.

    Args:
      binary_id: An id of the signed binary to delete.
    """
    def Mutation(mut: spanner_utils.Mutation) -> None:
      mut.delete("SignedBinaries", spanner_lib.KeySet(keys=[[binary_id.binary_type, binary_id.path]])
      )

    try:
      self.db.Mutate(Mutation, txn_tag="DeleteSignedBinaryReferences")
    except NotFound as error:
      raise db.UnknownSignedBinaryError(binary_id) from error