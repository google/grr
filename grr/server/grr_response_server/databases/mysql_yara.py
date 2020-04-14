#!/usr/bin/env python
# Lint as: python3
"""A module with MySQL implementation of YARA-related database methods."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Text

import MySQLdb

from grr_response_server.databases import db
from grr_response_server.databases import mysql_utils
from grr_response_server.rdfvalues import objects as rdf_objects


class MySQLDBYaraMixin(object):
  """A MySQL database mixin class with YARA-related methods."""

  @mysql_utils.WithTransaction()
  def WriteYaraSignatureReference(
      self,
      blob_id: rdf_objects.BlobID,
      username: Text,
      cursor: MySQLdb.cursors.Cursor,
  ) -> None:
    """Marks specified blob id as a YARA signature."""
    query = """
    INSERT IGNORE INTO yara_signature_references
    VALUES (%(blob_id)s, %(username_hash)s, NOW(6))
    """
    args = {
        "blob_id": blob_id.AsBytes(),
        "username_hash": mysql_utils.Hash(username),
    }

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError:
      raise db.UnknownGRRUserError(username=username)

  @mysql_utils.WithTransaction(readonly=True)
  def VerifyYaraSignatureReference(
      self,
      blob_id: rdf_objects.BlobID,
      cursor: MySQLdb.cursors.Cursor,
  ) -> bool:
    """Verifies whether specified blob is a YARA signature."""
    query = """
    SELECT 1
      FROM yara_signature_references
     WHERE blob_id = %(blob_id)s
    """
    cursor.execute(query, {"blob_id": blob_id.AsBytes()})

    return len(cursor.fetchall()) == 1
