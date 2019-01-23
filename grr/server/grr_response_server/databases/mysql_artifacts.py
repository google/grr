#!/usr/bin/env python
"""The MySQL database methods for handling artifacts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future.builtins import str

import MySQLdb
from MySQLdb.constants import ER as mysql_error_constants

from grr_response_core.lib.rdfvalues import artifacts as rdf_artifacts
from grr_response_server import db
from grr_response_server.databases import mysql_utils


def _RowToArtifact(row):
  return rdf_artifacts.Artifact.FromSerializedString(row[0])


class MySQLDBArtifactsMixin(object):
  """An MySQL database mixin with artifact-related methods.

  The artifact name is a globally unique string identifier, that has to be used
  as primary key. Since MySQL/InnoDB has an index size limit of 767 bytes, we
  cannot use the raw artifact name. Hashing is preferrable (e.g. over using
  truncated prefixes), because the only operation required is equality
  comparison.
  """

  @mysql_utils.WithTransaction()
  def WriteArtifact(self, artifact, cursor=None):
    """Writes new artifact to the database."""
    name = str(artifact.name)

    try:
      cursor.execute(
          "INSERT INTO artifacts (name_hash, definition) VALUES (%s, %s)",
          [mysql_utils.Hash(name),
           artifact.SerializeToString()])
    except MySQLdb.IntegrityError as error:
      if error.args[0] == mysql_error_constants.DUP_ENTRY:
        raise db.DuplicatedArtifactError(name, cause=error)
      else:
        raise

  @mysql_utils.WithTransaction()
  def ReadArtifact(self, name, cursor=None):
    """Looks up an artifact with given name from the database."""
    cursor.execute("SELECT definition FROM artifacts WHERE name_hash = %s",
                   [mysql_utils.Hash(name)])

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

    cursor.execute("DELETE FROM artifacts WHERE name_hash = %s",
                   [mysql_utils.Hash(name)])

    if cursor.rowcount == 0:
      raise db.UnknownArtifactError(name)
