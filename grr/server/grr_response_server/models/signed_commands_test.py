#!/usr/bin/env python
from absl.testing import absltest

from grr_response_proto import signed_commands_pb2
from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_server.models import signed_commands as models_signed_commands
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


class InitApiSignedCommandFromSignedCommandTest(absltest.TestCase):

  def testBaseFields(self):
    signed_command = signed_commands_pb2.SignedCommand()
    signed_command.id = "foo-id"
    signed_command.operating_system = signed_commands_pb2.SignedCommand.OS.MACOS
    signed_command.ed25519_signature = b"foo-signature"
    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.path.raw_bytes = "foo-path".encode("utf-8")
    rrg_command.signed_stdin = b"foo-signed-stdin"
    rrg_command.args_signed.append("foo-arg-1")
    rrg_command.args_signed.append("foo-arg-2")
    rrg_command.env_signed["foo-env-var-1"] = "foo-env-var-1-value"
    rrg_command.env_signed["foo-env-var-2"] = "foo-env-var-2-value"
    signed_command.command = rrg_command.SerializeToString()

    expected = api_signed_commands_pb2.ApiSignedCommand(
        id="foo-id",
        ed25519_signature=b"foo-signature",
        operating_system=api_signed_commands_pb2.ApiSignedCommand.OS.MACOS,
        command=rrg_command.SerializeToString(),
    )
    result = models_signed_commands.InitApiSignedCommandFromSignedCommand(
        signed_command
    )
    self.assertEqual(expected, result)


if __name__ == "__main__":
  absltest.main()
