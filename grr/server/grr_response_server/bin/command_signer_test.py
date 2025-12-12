#!/usr/bin/env python
from absl.testing import absltest

from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_server.bin import command_signer
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


class CommandSignerTest(absltest.TestCase):

  def testConvertToRrgCommand(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path = "foo"
    command.args.add().signed = "bar"
    command.args.add().signed = "baz"
    command.env_vars.add(name="FOO", value="bar")
    command.env_vars.add(name="BAZ", value="qux")
    command.signed_stdin = b"quux"

    rrg_command = command_signer._ConvertToRrgCommand(command)

    expected = rrg_execute_signed_command_pb2.Command()
    expected.path.raw_bytes = b"foo"
    expected.args_signed.extend(["bar", "baz"])
    expected.env_signed["FOO"] = "bar"
    expected.env_signed["BAZ"] = "qux"
    expected.signed_stdin = b"quux"

    self.assertEqual(expected, rrg_command)

  def testConvertToRRGCommand_ArgsSignedOnly(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path = "/usr/bin/rm"
    command.args.add().signed = "--recursive"
    command.args.add().signed = "/tmp"

    rrg_command = command_signer._ConvertToRrgCommand(command)

    self.assertEqual(rrg_command.path.raw_bytes, "/usr/bin/rm".encode())
    self.assertEqual(rrg_command.args_signed, ["--recursive", "/tmp"])

  def testConvertToRRGCommand_ArgsUnsigned(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path = "/usr/bin/echo"
    command.args.add().signed = "-n"
    command.args.add().unsigned_allowed = True

    rrg_command = command_signer._ConvertToRrgCommand(command)

    self.assertEqual(rrg_command.path.raw_bytes, "/usr/bin/echo".encode())
    self.assertLen(rrg_command.args, 2)
    self.assertEqual(rrg_command.args[0].signed, "-n")
    self.assertTrue(rrg_command.args[1].unsigned_allowed)

  def testConvertToRrgCommand_EnvUnsigned(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path = "/foo/bar"
    command.env_vars_unsigned_allowed.append("FOO")

    rrg_command = command_signer._ConvertToRrgCommand(command)
    self.assertEqual(rrg_command.path.raw_bytes, "/foo/bar".encode("utf-8"))
    self.assertIn("FOO", rrg_command.env_unsigned_allowed)


if __name__ == "__main__":
  absltest.main()
