#!/usr/bin/env python
"""The MySQL database methods for signed command handling."""

from collections.abc import Sequence
from typing import Optional

import MySQLdb
from MySQLdb import cursors
from MySQLdb.constants import ER as mysql_errors

from grr_response_proto import signed_commands_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import mysql_utils


class MySQLDBSignedCommandsMixin:
  """MySQLDB mixin for signed commands."""

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def WriteSignedCommands(
      self,
      signed_commands: Sequence[signed_commands_pb2.SignedCommand],
      cursor: Optional[cursors.Cursor] = None,
  ):
    """Writes a signed command to the database."""
    assert cursor is not None

    query = """
      INSERT INTO signed_commands (
        id, operating_system, ed25519_signature, command, source_path
      ) VALUES (
        %s, %s, %s, %s, %s
      )
    """

    rows = []
    for signed_command in signed_commands:
      rows.append((
          signed_command.id,
          int(signed_command.operating_system),
          signed_command.ed25519_signature,
          signed_command.command,
          signed_command.source_path,
      ))
    try:
      cursor.executemany(query, rows)
    except MySQLdb.IntegrityError as e:
      if e.args[0] == mysql_errors.DUP_ENTRY:
        raise db.AtLeastOneDuplicatedSignedCommandError(signed_commands) from e
      raise

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadSignedCommand(
      self,
      id_: str,
      operating_system: signed_commands_pb2.SignedCommand.OS,
      cursor: Optional[cursors.Cursor] = None,
  ) -> signed_commands_pb2.SignedCommand:
    """Reads a signed command from the database."""
    assert cursor is not None

    query_signed_command = """
      SELECT
        ed25519_signature, command, source_path
      FROM
        signed_commands
      WHERE
        id = %s
      AND
        operating_system = %s
    """
    cursor.execute(query_signed_command, [id_, operating_system])
    signed_command_row = cursor.fetchone()
    if not signed_command_row:
      raise db.UnknownSignedCommandError(id_, operating_system)
    (ed25519_signature, command_bytes, source_path) = signed_command_row
    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = id_
    signed_command.operating_system = operating_system
    signed_command.ed25519_signature = ed25519_signature
    signed_command.command = command_bytes

    if source_path:
      signed_command.source_path = source_path

    return signed_command

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction(readonly=True)
  def ReadSignedCommands(
      self,
      cursor: Optional[cursors.Cursor] = None,
  ) -> Sequence[signed_commands_pb2.SignedCommand]:
    """Reads all signed commands from the database."""
    assert cursor is not None

    query_signed_command = """
      SELECT
        id, operating_system, ed25519_signature, command, source_path
      FROM
        signed_commands
    """
    cursor.execute(query_signed_command)
    signed_commands = []
    for (
        id_,
        operating_system,
        ed25519_signature,
        command_bytes,
        source_path,
    ) in cursor.fetchall():
      signed_command = signed_commands_pb2.SignedCommand()
      signed_command.id = id_
      signed_command.operating_system = operating_system
      signed_command.ed25519_signature = ed25519_signature
      signed_command.command = command_bytes

      if source_path:
        signed_command.source_path = source_path

      signed_commands.append(signed_command)

    return signed_commands

  @db_utils.CallLogged
  @db_utils.CallAccounted
  @mysql_utils.WithTransaction()
  def DeleteAllSignedCommands(
      self,
      cursor: Optional[cursors.Cursor] = None,
  ) -> None:
    """Deletes all signed commands from the database."""
    assert cursor is not None

    cursor.execute("DELETE FROM signed_commands")
