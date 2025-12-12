#!/usr/bin/env python
"""A module with artifacts methods of the Spanner backend."""

from typing import Optional, Sequence

from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import spanner as spanner_lib

from grr_response_proto import artifact_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class ArtifactsMixin:
  """A Spanner database mixin with implementation of artifacts."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteArtifact(self, artifact: artifact_pb2.Artifact) -> None:
    """Writes new artifact to the database.

    Args:
      artifact: Artifact to be stored.

    Raises:
      DuplicatedArtifactError: when the artifact already exists.
    """
    name = str(artifact.name)
    row = {
        "Name": name,
        "Platforms": list(artifact.supported_os),
        "Payload": artifact,
    }
    try:
      self.db.Insert(table="Artifacts", row=row, txn_tag="WriteArtifact")
    except AlreadyExists as error:
      raise db.DuplicatedArtifactError(name) from error

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadArtifact(self, name: str) -> Optional[artifact_pb2.Artifact]:
    """Looks up an artifact with given name from the database.

    Args:
      name: Name of the artifact to be read.

    Returns:
      The artifact object read from the database.

    Raises:
      UnknownArtifactError: when the artifact does not exist.
    """
    try:
      row = self.db.Read("Artifacts",
                         key=[name],
                         cols=("Platforms", "Payload"),
                         txn_tag="ReadArtifacts")
    except NotFound as error:
      raise db.UnknownArtifactError(name) from error

    artifact = artifact_pb2.Artifact.FromString(row[1])
    artifact.name = name
    artifact.supported_os[:] = row[0]
    return artifact

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadAllArtifacts(self) -> Sequence[artifact_pb2.Artifact]:
    """Lists all artifacts that are stored in the database."""
    result = []

    query = """
    SELECT a.Name, a.Platforms, a.Payload
      FROM Artifacts AS a
    """
    for [name, supported_os, payload] in self.db.Query(query):
      artifact = artifact_pb2.Artifact.FromString(payload)
      artifact.name = name
      artifact.supported_os[:] = supported_os
      result.append(artifact)

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteArtifact(self, name: str) -> None:
    """Deletes an artifact with given name from the database.

    Args:
      name: Name of the artifact to be deleted.

    Raises:
      UnknownArtifactError when the artifact does not exist.
    """
    def Transaction(txn) -> None:
      # Spanner does not raise if we attempt to delete a non-existing row so
      # we check it exists ourselves.
      keyset = spanner_lib.KeySet(keys=[[name],])

      try:
        txn.read(table="Artifacts", columns=("Name",), keyset=keyset).one()
      except NotFound as error:
        raise db.UnknownArtifactError(name) from error

      txn.delete("Artifacts", keyset)

    self.db.Transact(Transaction, txn_tag="DeleteArtifact")
