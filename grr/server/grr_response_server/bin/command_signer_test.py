#!/usr/bin/env python
import hashlib

from absl.testing import absltest
from absl.testing import flagsaver

from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_server import command_signer as command_signer_lib
from grr_response_server.bin import command_signer
from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2


class SignTest(absltest.TestCase):

  def setUp(self):
    super().setUp()

    self.signer = command_signer_lib.EphemeralKeyCommandSigner()

  def assertSignatureValid(
      self,
      command: api_signed_commands_pb2.ApiSignedCommand,
  ):
    try:
      self.signer.Verify(command.ed25519_signature, command.command)
    except command_signer_lib.CommandSignatureValidationError as error:
      raise AssertionError("Invalid command signature") from error

  def testGeneral(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path = "foo"
    command.args.add().signed = "bar"
    command.args.add().signed = "baz"
    command.env_vars.add(name="FOO", value="bar")
    command.env_vars.add(name="BAZ", value="qux")
    command.signed_stdin = b"quux"

    signed_command = command_signer.Sign(command, self.signer)
    self.assertSignatureValid(signed_command)

    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.ParseFromString(signed_command.command)

    expected = rrg_execute_signed_command_pb2.Command()
    expected.path.raw_bytes = b"foo"
    expected.args_signed.extend(["bar", "baz"])
    expected.env_signed["FOO"] = "bar"
    expected.env_signed["BAZ"] = "qux"
    expected.signed_stdin = b"quux"

    self.assertEqual(expected, rrg_command)

  def testArgsSignedOnly(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path = "/usr/bin/rm"
    command.args.add().signed = "--recursive"
    command.args.add().signed = "/tmp"

    signed_command = command_signer.Sign(command, self.signer)
    self.assertSignatureValid(signed_command)

    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.ParseFromString(signed_command.command)

    self.assertEqual(rrg_command.path.raw_bytes, "/usr/bin/rm".encode())
    self.assertEqual(rrg_command.args_signed, ["--recursive", "/tmp"])

  def testArgsUnsigned(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path = "/usr/bin/echo"
    command.args.add().signed = "-n"
    command.args.add().unsigned_allowed = True

    signed_command = command_signer.Sign(command, self.signer)
    self.assertSignatureValid(signed_command)

    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.ParseFromString(signed_command.command)

    self.assertEqual(rrg_command.path.raw_bytes, "/usr/bin/echo".encode())
    self.assertLen(rrg_command.args, 2)
    self.assertEqual(rrg_command.args[0].signed, "-n")
    self.assertTrue(rrg_command.args[1].unsigned_allowed)

  def testArgsFilestoreFileSha256(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path = "/usr/bin/cat"
    command.args.add().unsigned_filestore_file_sha256_allowed = True

    signed_command = command_signer.Sign(command, self.signer)
    self.assertSignatureValid(signed_command)

    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.ParseFromString(signed_command.command)

    self.assertEqual(rrg_command.path.raw_bytes, "/usr/bin/cat".encode())
    self.assertLen(rrg_command.args, 1)
    self.assertTrue(rrg_command.args[0].unsigned_filestore_file_sha256_allowed)

  def testEnvUnsigned(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path = "/foo/bar"
    command.env_vars_unsigned_allowed.append("FOO")

    signed_command = command_signer.Sign(command, self.signer)
    self.assertSignatureValid(signed_command)

    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.ParseFromString(signed_command.command)

    self.assertEqual(rrg_command.path.raw_bytes, "/foo/bar".encode("utf-8"))
    self.assertIn("FOO", rrg_command.env_unsigned_allowed)

  def testEnvInherited(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path = "/foo/bar"
    command.env_vars_inherited.append("FOO")

    signed_command = command_signer.Sign(command, self.signer)
    self.assertSignatureValid(signed_command)

    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.ParseFromString(signed_command.command)

    self.assertEqual(rrg_command.path.raw_bytes, "/foo/bar".encode("utf-8"))
    self.assertIn("FOO", rrg_command.env_inherited)

  def testPathTemplate(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path_template = "${FOO}/baz"

    with flagsaver.flagsaver(
        (command_signer.FLAG_TEMPLATE_PARAMS, ["FOO=/bar"]),
    ):
      signed_command = command_signer.Sign(command, self.signer)
      self.assertSignatureValid(signed_command)

      rrg_command = rrg_execute_signed_command_pb2.Command()
      rrg_command.ParseFromString(signed_command.command)

    self.assertEqual(rrg_command.path.raw_bytes, "/bar/baz".encode("utf-8"))

  def testPathTemplate_Excessive(self):
    command = api_signed_commands_pb2.ApiCommand()
    command.path_template = "/foo/bar"

    # We want to verify that providing unused parameters is fine (some commands
    # might be interested only in a portion of parameters, some other commands
    # might be interested in completely different parameters).
    with flagsaver.flagsaver(
        (command_signer.FLAG_TEMPLATE_PARAMS, ["FOO=/baz"]),
    ):
      signed_command = command_signer.Sign(command, self.signer)
      self.assertSignatureValid(signed_command)

      rrg_command = rrg_execute_signed_command_pb2.Command()
      rrg_command.ParseFromString(signed_command.command)

    self.assertEqual(rrg_command.path.raw_bytes, "/foo/bar".encode("utf-8"))

  def testPathOnServerTemplate(self):
    content = b"""\
#!/usr/bin/env bash
echo 'Hello, world!'
"""

    file = self.create_tempfile(content=content)

    command = api_signed_commands_pb2.ApiCommand()
    command.path_on_server_template = file.full_path

    signed_command = command_signer.Sign(command, self.signer)
    self.assertSignatureValid(signed_command)

    rrg_command = rrg_execute_signed_command_pb2.Command()
    rrg_command.ParseFromString(signed_command.command)

    self.assertEqual(
        rrg_command.filestore_file_sha256,
        hashlib.sha256(content).digest(),
    )


if __name__ == "__main__":
  absltest.main()
