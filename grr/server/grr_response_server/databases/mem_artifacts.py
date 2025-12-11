#!/usr/bin/env python
"""The in-memory database methods for handling artifacts."""

from collections.abc import Sequence

from grr_response_proto import artifact_pb2
from grr_response_server.databases import db


class InMemoryDBArtifactsMixin(object):
  """An in-memory database mixin with artifact-related methods."""

  artifacts: dict[str, artifact_pb2.Artifact]

  def WriteArtifact(self, artifact: artifact_pb2.Artifact) -> None:
    """Writes new artifact to the database."""
    if artifact.name in self.artifacts:
      raise db.DuplicatedArtifactError(artifact.name)

    artifact_copy = artifact_pb2.Artifact()
    artifact_copy.CopyFrom(artifact)
    self.artifacts[artifact.name] = artifact_copy

  def ReadArtifact(self, name: str) -> artifact_pb2.Artifact:
    """Looks up an artifact with given name from the database."""
    try:
      artifact = self.artifacts[name]
    except KeyError as e:
      raise db.UnknownArtifactError(name) from e

    artifact_copy = artifact_pb2.Artifact()
    artifact_copy.CopyFrom(artifact)
    return artifact_copy

  def ReadAllArtifacts(self) -> Sequence[artifact_pb2.Artifact]:
    """Lists all artifacts that are stored in the database."""
    artifacts = []

    for artifact in self.artifacts.values():
      artifact_copy = artifact_pb2.Artifact()
      artifact_copy.CopyFrom(artifact)
      artifacts.append(artifact_copy)

    return artifacts

  def DeleteArtifact(self, name: str) -> None:
    """Deletes an artifact with given name from the database."""
    try:
      del self.artifacts[name]
    except KeyError as e:
      raise db.UnknownArtifactError(name) from e
