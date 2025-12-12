#!/usr/bin/env python
import os

from absl.testing import absltest

from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_server import data_store
from grr_response_server.databases import db
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import signed_commands as api_signed_commands
from grr.test_lib import testing_startup
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


def create_signed_command(
    command_id: str,
    operating_system: api_signed_commands_pb2.ApiSignedCommand.OS = api_signed_commands_pb2.ApiSignedCommand.OS.WINDOWS,
) -> api_signed_commands_pb2.ApiSignedCommand:
  """Creates a signed command."""
  signed_command = api_signed_commands_pb2.ApiSignedCommand()
  signed_command.id = command_id
  signed_command.operating_system = operating_system
  signed_command.ed25519_signature = os.urandom(64)
  command = rrg_execute_signed_command_pb2.Command()
  command.path.raw_bytes = "/foo/bar".encode("utf-8")
  command.signed_stdin = b"stdin"
  signed_command.command = command.SerializeToString()

  return signed_command


class ApiCreateSignedCommandsTest(api_test_lib.ApiCallHandlerTest):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  def setUp(self):
    super().setUp()
    self.handler = api_signed_commands.ApiCreateSignedCommandsHandler()

  def testCreateSignedCommands_AllFieldsGetWrittenToDatabase(self):
    signed_command = api_signed_commands_pb2.ApiSignedCommand()
    signed_command.id = "foo"
    signed_command.operating_system = (
        api_signed_commands_pb2.ApiSignedCommand.OS.WINDOWS
    )
    signed_command.ed25519_signature = b"test-signature" + 50 * b"-"  # 64 bytes
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = "/foo/bar".encode("utf-8")
    command.args_signed.extend(["--foo", "--bar"])
    command.signed_stdin = b"stdin"
    command.env_signed["FOO"] = "bar"
    signed_command.command = command.SerializeToString()
    signed_command.source_path = "/home/quux/mycommands.textproto"

    args = api_signed_commands_pb2.ApiCreateSignedCommandsArgs()
    args.signed_commands.append(signed_command)
    self.handler.Handle(args)

    wrote = data_store.REL_DB.ReadSignedCommand(
        "foo", api_signed_commands_pb2.ApiSignedCommand.OS.WINDOWS
    )
    self.assertEqual(wrote.ed25519_signature, signed_command.ed25519_signature)
    self.assertEqual(wrote.id, signed_command.id)
    self.assertEqual(wrote.operating_system, signed_command.operating_system)
    self.assertEqual(wrote.command, command.SerializeToString())
    self.assertEqual(wrote.source_path, "/home/quux/mycommands.textproto")

  def testCreateSignedCommands_MissingIdRaises(self):
    missing_id = create_signed_command("missing_id")
    missing_id.ClearField("id")

    args = api_signed_commands_pb2.ApiCreateSignedCommandsArgs()
    args.signed_commands.append(missing_id)

    with self.assertRaises(ValueError, msg="id is required."):
      self.handler.Handle(args)

  def testCreateSignedCommands_MissingOperatingSystemRaises(self):
    missing_operating_system = create_signed_command("missing_operating_system")
    missing_operating_system.ClearField("operating_system")

    args = api_signed_commands_pb2.ApiCreateSignedCommandsArgs()
    args.signed_commands.append(missing_operating_system)

    with self.assertRaises(ValueError, msg="operating system is required."):
      self.handler.Handle(args)

  def testCreateSignedCommands_MissingPathRaises(self):
    missing_path = create_signed_command("missing_path")
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.ParseFromString(missing_path.command)
    rrg_command.ClearField("path")
    missing_path.command = rrg_command.SerializeToString()
    args = api_signed_commands_pb2.ApiCreateSignedCommandsArgs()
    args.signed_commands.append(missing_path)
    with self.assertRaises(ValueError, msg="path is required."):
      self.handler.Handle(args)

  def testCreateSignedCommands_MissingSignatureRaises(self):
    signed_command = create_signed_command("missing_signature")
    signed_command.ClearField("ed25519_signature")

    args = api_signed_commands_pb2.ApiCreateSignedCommandsArgs()
    args.signed_commands.append(signed_command)

    with self.assertRaises(ValueError):
      self.handler.Handle(args)

  def testCreateSignedCommands_DuplicateCommandRaises(self):
    signed_command = create_signed_command("duplicate")

    args = api_signed_commands_pb2.ApiCreateSignedCommandsArgs()
    args.signed_commands.extend([signed_command, signed_command])

    with self.assertRaises(db.AtLeastOneDuplicatedSignedCommandError):
      self.handler.Handle(args)


class ApiListSignedCommandsTest(api_test_lib.ApiCallHandlerTest):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  def setUp(self):
    super().setUp()
    self.handler = api_signed_commands.ApiListSignedCommandsHandler()

  def testApiListSignedCommands(self):
    rrg_command = rrg_execute_signed_command_pb2.Command()

    signed_command_1 = create_signed_command("test_name_1")
    rrg_command.ParseFromString(signed_command_1.command)
    rrg_command.path.raw_bytes = "/foo/bar".encode("utf-8")
    signed_command_1.command = rrg_command.SerializeToString()
    signed_command_2 = create_signed_command("test_name_2")
    rrg_command.ParseFromString(signed_command_2.command)
    rrg_command.path.raw_bytes = "/foo/bar/baz".encode("utf-8")
    signed_command_2.command = rrg_command.SerializeToString()
    args = api_signed_commands_pb2.ApiCreateSignedCommandsArgs()
    args.signed_commands.extend([signed_command_1, signed_command_2])
    api_signed_commands.ApiCreateSignedCommandsHandler().Handle(args)

    listed_commands = self.handler.Handle()

    self.assertLen(listed_commands.signed_commands, 2)

    commands_by_id = {c.id: c for c in listed_commands.signed_commands}
    command_1 = rrg_execute_signed_command_pb2.Command()
    command_1.ParseFromString(commands_by_id["test_name_1"].command)
    self.assertEqual(command_1.path.raw_bytes.decode("utf-8"), "/foo/bar")
    command_2 = rrg_execute_signed_command_pb2.Command()
    command_2.ParseFromString(commands_by_id["test_name_2"].command)
    self.assertEqual(command_2.path.raw_bytes.decode("utf-8"), "/foo/bar/baz")

  def testApiGetSignedCommands_NoCommandsDoesNotRaise(self):
    self.assertEmpty(self.handler.Handle().signed_commands)


class ApiDeleteAllSignedCommandsTest(api_test_lib.ApiCallHandlerTest):

  def setUp(self):
    super().setUp()
    self.handler = api_signed_commands.ApiDeleteAllSignedCommandsHandler()

  def testDeleteAllSignedCommands(self):
    signed_command_1 = create_signed_command("for_deletion_1")
    signed_command_2 = create_signed_command("for_deletion_2")

    args = api_signed_commands_pb2.ApiCreateSignedCommandsArgs()
    args.signed_commands.extend([signed_command_1, signed_command_2])
    api_signed_commands.ApiCreateSignedCommandsHandler().Handle(args)

    self.assertLen(data_store.REL_DB.ReadSignedCommands(), 2)

    self.handler.Handle()
    self.assertEmpty(data_store.REL_DB.ReadSignedCommands())


if __name__ == "__main__":
  absltest.main()
