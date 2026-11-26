#!/usr/bin/env python
"""rdf value representation for artifact collector parameters."""

from __future__ import annotations

from grr_response_proto import artifact_pb2


class ConditionError(Exception):
  """An invalid artifact condition was specified."""


class ArtifactDefinitionError(Exception):
  """An exception class thrown upon encountering malformed artifact.

  Args:
    target: A string representing object for which the error was encountered.
    details: A string with more details about the problem.
    cause: An optional exception that triggered the exception.
  """

  def __init__(
      self, target: object, details: str, cause: Exception | str | None = None
  ):
    message = "%s: %s" % (target, details)
    if cause:
      message += ": %s" % cause

    super().__init__(message)


class ArtifactSyntaxError(ArtifactDefinitionError):
  """An exception class representing syntax errors in artifact definition.

  Args:
    artifact: An artifact object for which the error was encountered.
    details: A string with more details about syntax problems.
    cause: An optional exception that triggered the syntax error.
  """

  def __init__(
      self,
      artifact: artifact_pb2.Artifact,
      details: str,
      cause: Exception | str | None = None,
  ):
    super().__init__(artifact.name, details, cause)


class ArtifactDependencyError(ArtifactDefinitionError):
  """An exception class representing dependency errors in artifact definition.

  Args:
    artifact: An artifact object for which the error was encountered.
    details: A string with more details about dependency problems.
    cause: An optional exception that triggered the dependency error.
  """

  def __init__(
      self,
      artifact: artifact_pb2.Artifact,
      details: str,
      cause: Exception | str | None = None,
  ):
    super().__init__(artifact.name, details, cause)


class ArtifactSourceSyntaxError(ArtifactDefinitionError):
  """An exception class representing syntax errors in artifact sources.

  Args:
    source: An artifact source object for which the error was encountered.
    details: A string with more details about syntax problems.
  """

  def __init__(self, source: artifact_pb2.ArtifactSource, details: str):
    super().__init__(source.type, details)


class ArtifactNotRegisteredError(Exception):
  """Artifact is not present in the registry."""
