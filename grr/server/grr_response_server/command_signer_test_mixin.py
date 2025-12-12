#!/usr/bin/env python
"""Mixin class to be used in tests for CommandSigner implementations."""

from grr_response_server import command_signer
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


class CommandSignerTestMixin:
  """Mixin class to be used in tests for CommandSigner implementations."""

  signer: command_signer.AbstractCommandSigner

  def testVerifySignatureCanSignAndVerify(self):  # pylint: disable=invalid-name
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = b"/bin/ls"
    command.args_signed.append("-l")
    command.env_signed["PATH"] = "/usr/bin"
    command.unsigned_stdin_allowed = True

    signature = self.signer.Sign(command)
    self.assertLen(signature, 64)

    self.signer.Verify(signature, command)

  def testVerifySignatureRaisesWhenSignatureIsInvalid(self):  # pylint: disable=invalid-name
    command = rrg_execute_signed_command_pb2.Command()
    command.path.raw_bytes = b"/bin/ls"

    signature = b"invalid signature"
    with self.assertRaises(command_signer.CommandSignatureValidationError):
      self.signer.Verify(signature, command)
