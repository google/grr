#!/usr/bin/env python
"""The InMemoryDB database methods for signed command handling."""

from collections.abc import Sequence

from grr_response_core.lib import utils
from grr_response_proto import signed_commands_pb2
from grr_response_server.databases import db


def PrimaryKey(
    command: signed_commands_pb2.SignedCommand,
) -> tuple[str, signed_commands_pb2.SignedCommand.OS]:
  return (command.id, command.operating_system)


class InMemoryDBSignedCommandsMixin:
  """InMemoryDB mixin for signed commands."""

  signed_commands: dict[
      tuple[str, signed_commands_pb2.SignedCommand.OS], bytes
  ] = {}

  @utils.Synchronized
  def WriteSignedCommands(
      self,
      signed_commands: Sequence[signed_commands_pb2.SignedCommand],
  ) -> None:
    """Writes signed commands to the database."""
    primary_keys = set(PrimaryKey(command) for command in signed_commands)
    # Inserting duplicate commands is not allowed.
    if len(primary_keys) < len(signed_commands):
      raise db.AtLeastOneDuplicatedSignedCommandError(signed_commands)

    # Inserting a command that already exists is not allowed.
    for signed_command in signed_commands:
      if PrimaryKey(signed_command) in self.signed_commands:
        raise db.AtLeastOneDuplicatedSignedCommandError(signed_commands)

    for signed_command in signed_commands:
      signed_command_bytes = signed_command.SerializeToString()
      self.signed_commands[PrimaryKey(signed_command)] = signed_command_bytes

  @utils.Synchronized
  def ReadSignedCommand(
      self,
      id_: str,
      operating_system: signed_commands_pb2.SignedCommand.OS,
  ) -> signed_commands_pb2.SignedCommand:
    """Reads signed command from the database."""
    stored_command = self.signed_commands.get((id_, operating_system))
    if not stored_command:
      raise db.UnknownSignedCommandError(id_, operating_system)

    command = signed_commands_pb2.SignedCommand()
    command.ParseFromString(stored_command)
    return command

  @utils.Synchronized
  def ReadSignedCommands(
      self,
  ) -> Sequence[signed_commands_pb2.SignedCommand]:
    """Reads all signed commands from the database."""
    commands = []
    for stored_command in self.signed_commands.values():
      command = signed_commands_pb2.SignedCommand()
      command.ParseFromString(stored_command)
      commands.append(command)
    return commands

  @utils.Synchronized
  def DeleteAllSignedCommands(
      self,
  ) -> None:
    """Deletes all signed commands from the database."""
    self.signed_commands.clear()
