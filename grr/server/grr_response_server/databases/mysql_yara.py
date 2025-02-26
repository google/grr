#!/usr/bin/env python
"""A module with MySQL implementation of YARA-related database methods."""

import MySQLdb

from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils
from grr_response_server.models import blobs as models_blobs


class MySQLDBYaraMixin(object):
  """A MySQL database mixin class with YARA-related methods."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteYaraSignatureReference(
      self,
      blob_id: models_blobs.BlobID,
      username: str,
      cursor: MySQLdb.cursors.Cursor,
  ) -> None:
    """Marks specified blob id as a YARA signature."""
    query = """
    INSERT IGNORE INTO yara_signature_references
    VALUES (%(blob_id)s, %(username_hash)s, NOW(6))
    """
    args = {
        "blob_id": bytes(blob_id),
        "username_hash": mysql_utils.Hash(username),
    }

    try:
      cursor.execute(query, args)
    except MySQLdb.IntegrityError:
      raise db.UnknownGRRUserError(username=username)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def VerifyYaraSignatureReference(
      self,
      blob_id: models_blobs.BlobID,
      cursor: MySQLdb.cursors.Cursor,
  ) -> bool:
    """Verifies whether specified blob is a YARA signature."""
    query = """
    SELECT 1
      FROM yara_signature_references
     WHERE blob_id = %(blob_id)s
    """
    cursor.execute(query, {"blob_id": bytes(blob_id)})

    return len(cursor.fetchall()) == 1
