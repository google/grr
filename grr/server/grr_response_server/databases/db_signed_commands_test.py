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
    env_vars: Optional[dict[str, str]] = None,
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
    command.args_signed.extend(args)
  for name, value in (env_vars or {}).items():
    command.env_signed[name] = value

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
    command.args_signed.extend(["args1", "args2"])
    command.env_signed["env_var_1"] = "env_var_1_value"
    command.env_signed["env_var_2"] = "env_var_2_value"
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
    self.assertEqual(command.args_signed, ["arg1", "arg2", "arg3"])

  def testWriteReadSignedCommands_testEnvVars(self):
    signed_command = create_signed_command(
        "command",
        signed_commands_pb2.SignedCommand.OS.LINUX,
        env_vars={
            "name_1": "value_1",
            "name_2": "value_2",
        },
    )
    self.db.WriteSignedCommand(signed_command)

    read_command = self.db.ReadSignedCommand(
        "command", signed_commands_pb2.SignedCommand.OS.LINUX
    )
    command = rrg_execute_signed_command_pb2.Command()
    command.ParseFromString(read_command.command)
    self.assertEqual(
        command.env_signed,
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

  def testReadSignedCommand_UnknownCommand(self):
    with self.assertRaises(db.UnknownSignedCommandError) as context:
      self.db.ReadSignedCommand(
          "i_do_not_exist",
          signed_commands_pb2.SignedCommand.OS.LINUX,
      )

    self.assertEqual(
        context.exception.command_id,
        "i_do_not_exist",
    )
    self.assertEqual(
        context.exception.operating_system,
        signed_commands_pb2.SignedCommand.OS.LINUX,
    )

  def testReadSignedCommand_Source(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/true".encode("utf-8")

    command = signed_commands_pb2.SignedCommand()
    command.id = "true"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()
    command.source_path = "/home/quux/mycommands.textproto"

    self.db.WriteSignedCommand(command)

    command = self.db.ReadSignedCommand(
        "true",
        operating_system=signed_commands_pb2.SignedCommand.LINUX,
    )
    self.assertEqual(command.source_path, "/home/quux/mycommands.textproto")

  def testLookupSignedCommand_Match(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode("utf-8")
    rrg_command.args_signed.append("--bar")
    rrg_command.args_signed.append("--baz")

    command = signed_commands_pb2.SignedCommand()
    command.id = "foo"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()

    self.db.WriteSignedCommand(command)

    result = self.db.LookupSignedCommand(
        operating_system=signed_commands_pb2.SignedCommand.LINUX,
        path="/usr/bin/foo",
        args=["--bar", "--baz"],
    )
    self.assertEqual(result.id, "foo")

  def testLookupSignedCommand_Match_Args(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode("utf-8")
    rrg_command.args.add().signed = "--bar"
    rrg_command.args.add().signed = "--baz"

    command = signed_commands_pb2.SignedCommand()
    command.id = "foo"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()

    self.db.WriteSignedCommand(command)

    result = self.db.LookupSignedCommand(
        operating_system=signed_commands_pb2.SignedCommand.LINUX,
        path="/usr/bin/foo",
        args=["--bar", "--baz"],
    )
    self.assertEqual(result.id, "foo")

  def testLookupSignedCommand_Match_ArgsMixed(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode("utf-8")
    rrg_command.args_signed.append("--bar")
    rrg_command.args.add().signed = "--baz"

    command = signed_commands_pb2.SignedCommand()
    command.id = "foo"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()

    self.db.WriteSignedCommand(command)

    result = self.db.LookupSignedCommand(
        operating_system=signed_commands_pb2.SignedCommand.LINUX,
        path="/usr/bin/foo",
        args=["--bar", "--baz"],
    )
    self.assertEqual(result.id, "foo")

  def testLookupSignedCommand_Mismatch_OperatingSystem(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode("utf-8")
    rrg_command.args_signed.append("--bar")
    rrg_command.args_signed.append("--baz")

    command = signed_commands_pb2.SignedCommand()
    command.id = "foo"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()

    self.db.WriteSignedCommand(command)

    with self.assertRaises(db.NoMatchingSignedCommandError):
      self.db.LookupSignedCommand(
          operating_system=signed_commands_pb2.SignedCommand.MACOS,
          path="/usr/bin/foo",
          args=["--bar", "--baz"],
      )

  def testLookupSignedCommand_Mismatch_Path(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode("utf-8")
    rrg_command.args_signed.append("--bar")
    rrg_command.args_signed.append("--baz")

    command = signed_commands_pb2.SignedCommand()
    command.id = "foo"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()

    self.db.WriteSignedCommand(command)

    with self.assertRaises(db.NoMatchingSignedCommandError):
      self.db.LookupSignedCommand(
          operating_system=signed_commands_pb2.SignedCommand.MACOS,
          path="/usr/bin/bar",
          args=["--bar", "--baz"],
      )

  def testLookupSignedCommand_Mismatch_ArgsOrder(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode("utf-8")
    rrg_command.args_signed.append("--bar")
    rrg_command.args_signed.append("--baz")

    command = signed_commands_pb2.SignedCommand()
    command.id = "foo"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()

    self.db.WriteSignedCommand(command)

    with self.assertRaises(db.NoMatchingSignedCommandError):
      self.db.LookupSignedCommand(
          operating_system=signed_commands_pb2.SignedCommand.MACOS,
          path="/usr/bin/bar",
          args=["--baz", "--bar"],
      )

  def testLookupSignedCommand_Mismatch_ArgsUnsigned(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode("utf-8")
    rrg_command.args.add().signed = "--bar"
    rrg_command.args.add().unsigned_allowed = True
    rrg_command.args.add().signed = "--baz"

    command = signed_commands_pb2.SignedCommand()
    command.id = "foo"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()

    self.db.WriteSignedCommand(command)

    with self.assertRaises(db.NoMatchingSignedCommandError):
      self.db.LookupSignedCommand(
          operating_system=signed_commands_pb2.SignedCommand.MACOS,
          path="/usr/bin/bar",
          args=["--baz", "--quux", "--bar"],
      )

  def testLookupSignedCommand_Mismatch_Env(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode("utf-8")
    rrg_command.args_signed.append("--bar")
    rrg_command.args_signed.append("--baz")
    rrg_command.env_signed["quux"] = "blargh"

    command = signed_commands_pb2.SignedCommand()
    command.id = "foo"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()

    self.db.WriteSignedCommand(command)

    with self.assertRaises(db.NoMatchingSignedCommandError):
      self.db.LookupSignedCommand(
          operating_system=signed_commands_pb2.SignedCommand.LINUX,
          path="/usr/bin/foo",
          args=["--baz", "--bar"],
      )

  def testLookupSignedCommand_Mismatch_EnvUnsigned(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode("utf-8")
    rrg_command.env_unsigned_allowed.append("bar")

    command = signed_commands_pb2.SignedCommand()
    command.id = "foo"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()

    self.db.WriteSignedCommand(command)

    with self.assertRaises(db.NoMatchingSignedCommandError):
      self.db.LookupSignedCommand(
          operating_system=signed_commands_pb2.SignedCommand.LINUX,
          path="/usr/bin/foo",
          args=[],
      )

  def testLookupSignedCommand_Mismatch_SignedStdin(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode("utf-8")
    rrg_command.args_signed.append("--bar")
    rrg_command.args_signed.append("--baz")
    rrg_command.signed_stdin = b"lorem ipsum dolor sit amet"

    command = signed_commands_pb2.SignedCommand()
    command.id = "foo"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()

    self.db.WriteSignedCommand(command)

    with self.assertRaises(db.NoMatchingSignedCommandError):
      self.db.LookupSignedCommand(
          operating_system=signed_commands_pb2.SignedCommand.LINUX,
          path="/usr/bin/foo",
          args=["--baz", "--bar"],
      )

  def testLookupSignedCommand_Mismatch_UnsignedStdinAllowed(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "/usr/bin/foo".encode("utf-8")
    rrg_command.args_signed.append("--bar")
    rrg_command.args_signed.append("--baz")
    rrg_command.unsigned_stdin_allowed = True

    command = signed_commands_pb2.SignedCommand()
    command.id = "foo"
    command.operating_system = signed_commands_pb2.SignedCommand.LINUX
    command.ed25519_signature = os.urandom(64)
    command.command = rrg_command.SerializeToString()

    self.db.WriteSignedCommand(command)

    with self.assertRaises(db.NoMatchingSignedCommandError):
      self.db.LookupSignedCommand(
          operating_system=signed_commands_pb2.SignedCommand.LINUX,
          path="/usr/bin/foo",
          args=["--baz", "--bar"],
      )

  def testLookupSignedCommand_NoCommands(self):
    with self.assertRaises(db.NoMatchingSignedCommandError):
      self.db.LookupSignedCommand(
          operating_system=signed_commands_pb2.SignedCommand.MACOS,
          path="/usr/bin/bar",
          args=["--baz", "--bar"],
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
