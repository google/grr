#!/usr/bin/env python
"""The in-memory database methods for handling artifacts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future.utils import itervalues

from grr_response_server import db


class InMemoryDBArtifactsMixin(object):
  """An in-memory database mixin with artifact-related methods."""

  def WriteArtifact(self, artifact):
    """Writes new artifact to the database."""
    name = unicode(artifact.name)

    if name in self.artifacts:
      raise db.DuplicatedArtifactError(name)

    self.artifacts[name] = artifact.Copy()

  def ReadArtifact(self, name):
    """Looks up an artifact with given name from the database."""
    try:
      artifact = self.artifacts[name]
    except KeyError:
      raise db.UnknownArtifactError(name)

    return artifact.Copy()

  def ReadAllArtifacts(self):
    """Lists all artifacts that are stored in the database."""
    artifacts = []

    for artifact in itervalues(self.artifacts):
      artifacts.append(artifact.Copy())

    return artifacts

  def DeleteArtifact(self, name):
    """Deletes an artifact with given name from the database."""
    try:
      del self.artifacts[name]
    except KeyError:
      raise db.UnknownArtifactError(name)
