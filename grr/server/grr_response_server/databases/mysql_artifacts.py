#!/usr/bin/env python
"""The MySQL database methods for handling artifacts."""

from collections.abc import Sequence
from typing import Optional

import MySQLdb
from MySQLdb.constants import ER as mysql_error_constants
import MySQLdb.cursors

from grr_response_proto import artifact_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils


def _RowToArtifact(row):
  return artifact_pb2.Artifact.FromString(row[0])


class MySQLDBArtifactsMixin(object):
  """An MySQL database mixin with artifact-related methods."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteArtifact(
      self,
      artifact: artifact_pb2.Artifact,
      cursor: Optional[MySQLdb.cursors.Cursor] = None,
  ):
    """Writes a new artifact to the database."""
    assert cursor is not None

    try:
      cursor.execute(
          "INSERT INTO artifacts (name, definition) VALUES (%s, %s)",
          [artifact.name, artifact.SerializeToString()],
      )
    except MySQLdb.IntegrityError as error:
      if error.args[0] == mysql_error_constants.DUP_ENTRY:
        raise db.DuplicatedArtifactError(artifact.name, cause=error)
      else:
        raise

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def ReadArtifact(
      self, name: str, cursor: Optional[MySQLdb.cursors.Cursor] = None
  ) -> artifact_pb2.Artifact:
    """Looks up an artifact with given name from the database."""
    assert cursor is not None
    cursor.execute("SELECT definition FROM artifacts WHERE name = %s", [name])

    row = cursor.fetchone()
    if row is None:
      raise db.UnknownArtifactError(name)
    else:
      return _RowToArtifact(row)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def ReadAllArtifacts(
      self, cursor: Optional[MySQLdb.cursors.Cursor] = None
  ) -> Sequence[artifact_pb2.Artifact]:
    """Lists all artifacts that are stored in the database."""
    assert cursor is not None
    cursor.execute("SELECT definition FROM artifacts")
    return [_RowToArtifact(row) for row in cursor.fetchall()]

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def DeleteArtifact(
      self, name: str, cursor: Optional[MySQLdb.cursors.Cursor] = None
  ) -> None:
    """Deletes an artifact with given name from the database."""
    assert cursor is not None
    cursor.execute("DELETE FROM artifacts WHERE name = %s", [name])

    if cursor.rowcount == 0:
      raise db.UnknownArtifactError(name)
