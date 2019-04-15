#!/usr/bin/env python
"""The MySQL database methods for handling artifacts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import MySQLdb
from MySQLdb.constants import ER as mysql_error_constants
from typing import Text

from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_server.databases import db
from grr_response_server.databases import mysql_utils


def _RowToArtifact(row):
  return rdf_artifacts.Artifact.FromSerializedString(row[0])


class MySQLDBArtifactsMixin(object):
  """An MySQL database mixin with artifact-related methods."""

  @mysql_utils.WithTransaction()
  def WriteArtifact(self, artifact, cursor=None):
    """Writes new artifact to the database."""
    name = Text(artifact.name)

    try:
      cursor.execute("INSERT INTO artifacts (name, definition) VALUES (%s, %s)",
                     [name, artifact.SerializeToString()])
    except MySQLdb.IntegrityError as error:
      if error.args[0] == mysql_error_constants.DUP_ENTRY:
        raise db.DuplicatedArtifactError(name, cause=error)
      else:
        raise

  @mysql_utils.WithTransaction()
  def ReadArtifact(self, name, cursor=None):
    """Looks up an artifact with given name from the database."""
    cursor.execute("SELECT definition FROM artifacts WHERE name = %s", [name])

    row = cursor.fetchone()
    if row is None:
      raise db.UnknownArtifactError(name)
    else:
      return _RowToArtifact(row)

  @mysql_utils.WithTransaction()
  def ReadAllArtifacts(self, cursor=None):
    """Lists all artifacts that are stored in the database."""
    cursor.execute("SELECT definition FROM artifacts")
    return [_RowToArtifact(row) for row in cursor.fetchall()]

  @mysql_utils.WithTransaction()
  def DeleteArtifact(self, name, cursor=None):
    """Deletes an artifact with given name from the database."""

    cursor.execute("DELETE FROM artifacts WHERE name = %s", [name])

    if cursor.rowcount == 0:
      raise db.UnknownArtifactError(name)
