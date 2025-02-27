#!/usr/bin/env python
import os
from typing import Optional

from grr_response_proto import signed_commands_pb2
from grr_response_server.databases import db
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


def create_signed_command(
    id_: str,
    operating_system: signed_commands_pb2.SignedCommand.OS,
    path: str = "test_path",
    signature: bytes = None,
    args: Optional[list[str]] = None,
    unsigned_stdin_allowed: bool = False,
    signed_stdin: Optional[bytes] = None,
    env_vars: Optional[list[signed_commands_pb2.Command.EnvVar]] = None,
) -> signed_commands_pb2.SignedCommand:
  """Creates a signed command for testing."""
  signed_command = signed_commands_pb2.SignedCommand()
  signed_command.id = id_
  signed_command.operating_system = operating_system

  command = rrg_execute_signed_command_pb2.Command()
  command.path.raw_bytes = path.encode("utf-8")

  if not signature:
    signature = os.urandom(64)
  signed_command.ed25519_signature = signature

  if args:
    command.args.extend(args)
  if env_vars:
    for env_var in env_vars:
      command.env[env_var.name] = env_var.value

  command.unsigned_stdin_allowed = unsigned_stdin_allowed
  if signed_stdin:
    command.signed_stdin = signed_stdin

  signed_command.command = command.SerializeToString()
  return signed_command


class DatabaseTestSignedCommandsMixin:
  """An abstract class for testing db.Database implementations."""

  def testWriteReadSignedCommands_allFields(self):
    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "ID"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.OS.MACOS
    signed_command.ed25519_signature = b"test_signature" + 50 * b"-"  # 64 bytes

    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "test_path".encode("utf-8")
    command.args.extend(["args1", "args2"])
    command.env["env_var_1"] = "env_var_1_value"
    command.env["env_var_2"] = "env_var_2_value"
    command.signed_stdin = b"signed_stdin"
    command.unsigned_stdin_allowed = False

    signed_command.command = command.SerializeToString()

    self.db.WriteSignedCommands([signed_command])
    result = self.db.ReadSignedCommand(
        "ID", signed_commands_pb2.SignedCommand.OS.MACOS
    )
    self.assertEqual(result, signed_command)

  def testWriteReadSignedCommands_multipleCommands(self):
    one_linux = create_signed_command(
        "one", signed_commands_pb2.SignedCommand.OS.LINUX
    )
    two_linux = create_signed_command(
        "two", signed_commands_pb2.SignedCommand.OS.LINUX
    )
    two_macos = create_signed_command(
        "two", signed_commands_pb2.SignedCommand.OS.MACOS
    )
    self.db.WriteSignedCommands([one_linux, two_linux, two_macos])

    read_one_linux = self.db.ReadSignedCommand(
        "one", signed_commands_pb2.SignedCommand.OS.LINUX
    )
    read_two_linux = self.db.ReadSignedCommand(
        "two", signed_commands_pb2.SignedCommand.OS.LINUX
    )
    read_two_macos = self.db.ReadSignedCommand(
        "two", signed_commands_pb2.SignedCommand.OS.MACOS
    )
    self.assertEqual(read_one_linux, one_linux)
    self.assertEqual(read_two_linux, two_linux)
    self.assertEqual(read_two_macos, two_macos)

  def testWriteReadSignedCommands_testPositionalArgsKeepOrder(self):
    signed_command = create_signed_command(
        "command",
        signed_commands_pb2.SignedCommand.OS.LINUX,
        args=["arg1", "arg2", "arg3"],
    )
    self.db.WriteSignedCommand(signed_command)

    read_command = self.db.ReadSignedCommand(
        "command", signed_commands_pb2.SignedCommand.OS.LINUX
    )
    command = rrg_execute_signed_command_pb2.Command()
    command.ParseFromString(read_command.command)
    self.assertEqual(command.args, ["arg1", "arg2", "arg3"])

  def testWriteReadSignedCommands_testEnvVars(self):
    signed_command = create_signed_command(
        "command",
        signed_commands_pb2.SignedCommand.OS.LINUX,
        env_vars=[
            signed_commands_pb2.Command.EnvVar(name="name_1", value="value_1"),
            signed_commands_pb2.Command.EnvVar(name="name_2", value="value_2"),
        ],
    )
    self.db.WriteSignedCommand(signed_command)

    read_command = self.db.ReadSignedCommand(
        "command", signed_commands_pb2.SignedCommand.OS.LINUX
    )
    command = rrg_execute_signed_command_pb2.Command()
    command.ParseFromString(read_command.command)
    self.assertEqual(
        command.env,
        {
            "name_2": "value_2",
            "name_1": "value_1",
        },
    )

  def testWriteSignedCommand_CannotOverwrite(self):
    initial_command = create_signed_command(
        "attemt_overwrite", signed_commands_pb2.SignedCommand.OS.LINUX
    )
    self.db.WriteSignedCommand(initial_command)

    updated_command = signed_commands_pb2.SignedCommand()
    updated_command.CopyFrom(initial_command)
    updated_command.ed25519_signature = b"new_signature" + 51 * b"="  # 64 bytes

    new_command = create_signed_command(
        "new_command", signed_commands_pb2.SignedCommand.OS.LINUX
    )
    with self.assertRaises(db.AtLeastOneDuplicatedSignedCommandError):
      self.db.WriteSignedCommands([updated_command, new_command])

    attemtped_overwrite = self.db.ReadSignedCommand(
        "attemt_overwrite", signed_commands_pb2.SignedCommand.OS.LINUX
    )
    self.assertEqual(attemtped_overwrite, initial_command)

    # If one command fails to be written, the whole transaction should be
    # rolled back.
    with self.assertRaises(db.NotFoundError):
      self.db.ReadSignedCommand(
          "new_command", signed_commands_pb2.SignedCommand.OS.WINDOWS
      )

  def testWriteSignedCommands_CannotInsertDuplicateSignedCommands(self):
    command = create_signed_command(
        "duplicate", signed_commands_pb2.SignedCommand.OS.LINUX
    )

    copy = signed_commands_pb2.SignedCommand()
    copy.CopyFrom(command)

    with self.assertRaises(db.AtLeastOneDuplicatedSignedCommandError):
      self.db.WriteSignedCommands([command, copy])

    # If one command fails to be written, the whole transaction should be
    # rolled back.
    with self.assertRaises(db.NotFoundError):
      self.db.ReadSignedCommand(
          "duplicate", signed_commands_pb2.SignedCommand.OS.LINUX
      )

  def testWriteSignedCommand_InputValidationInvalidEd25519Signature(self):
    signed_command = create_signed_command(
        "command",
        signed_commands_pb2.SignedCommand.OS.LINUX,
        signature=b"invalid_signature",
    )
    with self.assertRaises(ValueError):
      self.db.WriteSignedCommand(signed_command)

  def testWriteSignedCommand_InputValidationMissingPath(self):
    signed_command = create_signed_command(
        "command", signed_commands_pb2.SignedCommand.OS.LINUX, path=""
    )
    with self.assertRaises(ValueError):
      self.db.WriteSignedCommand(signed_command)

  def testWriteSignedCommand_InputValidationInvalidId(self):
    signed_command = create_signed_command(
        100 * "too_long_id", signed_commands_pb2.SignedCommand.OS.LINUX
    )
    with self.assertRaises(ValueError):
      self.db.WriteSignedCommand(signed_command)

  def testReadSignedCommands(self):
    signed_command_1 = create_signed_command(
        id_="command_1",
        operating_system=signed_commands_pb2.SignedCommand.OS.LINUX,
    )
    signed_command_2 = create_signed_command(
        id_="command_2",
        operating_system=signed_commands_pb2.SignedCommand.OS.WINDOWS,
    )
    self.db.WriteSignedCommands([signed_command_1, signed_command_2])

    read_signed_commands = self.db.ReadSignedCommands()
    self.assertLen(read_signed_commands, 2)
    self.assertCountEqual(
        read_signed_commands, [signed_command_1, signed_command_2]
    )

  def testDeleteAllSignedCommands(self):
    signed_command_1 = create_signed_command(
        id_="command_1",
        operating_system=signed_commands_pb2.SignedCommand.OS.LINUX,
    )
    signed_command_2 = create_signed_command(
        id_="command_2",
        operating_system=signed_commands_pb2.SignedCommand.OS.WINDOWS,
    )
    self.db.WriteSignedCommands([signed_command_1, signed_command_2])

    self.assertLen(self.db.ReadSignedCommands(), 2)

    self.db.DeleteAllSignedCommands()
    self.assertEmpty(self.db.ReadSignedCommands())

  def testDeleteAllSignedCommands_NoCommandsDoesNotFail(self):
    read_signed_commands = self.db.ReadSignedCommands()
    self.assertEmpty(read_signed_commands)

    # Deleting 0 rows should not fail.
    self.db.DeleteAllSignedCommands()


# This file is a test library and thus does not require a __main__ block.
