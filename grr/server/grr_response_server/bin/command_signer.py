#!/usr/bin/env python
"""CLI to generate and save signatures for commands."""

from collections.abc import Sequence
import string

from absl import app
from absl import flags
from absl import logging

from google.protobuf import text_format
from grr_api_client import api as api_http
from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_server import command_signer
from grr_response_server import ephemeral_key_command_signer
from grr_response_server import private_key_file_command_signer # pylint: disable=line-too-long
# Required to register config options before reading stubby endpoint flags.
from grr_response_server.local import server_config  # pylint: disable=unused-import

from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2

FLAG_REGENERATE = flags.DEFINE_bool(
    name="regenerate",
    default=False,
    help="If true prunes the database of existing signatures before writing.",
)

FLAG_API_ENDPOINT = flags.DEFINE_string(
    name="api_endpoint",
    default="",
    help="GRR API endpoint to use for sending signed commands.",
)

FLAG_API_USER = flags.DEFINE_string(
    name="api_user",
    default="",
    help="GRR API user to use for sending signed commands.",
)

FLAG_API_PASSWORD = flags.DEFINE_string(
    name="api_password",
    default="",
    help="GRR API password to use for sending signed commands.",
)

EPHEMERAL_SIGNING_KEY = flags.DEFINE_bool(
    name="ephemeral_signing_key",
    default=False,
    help="If set, uses a fake signing key instead of the one from the config.",
)

FLAG_TEMPLATE_PARAMS = flags.DEFINE_multi_string(
    name="template-param",
    default=[],
    help="`KEY=VALUE` pair to use for templated command fields.",
)


def _GetCommandSigner() -> command_signer.AbstractCommandSigner:
  """Signs commands and returns the complete signed commands."""

  if EPHEMERAL_SIGNING_KEY.value:
    return ephemeral_key_command_signer.EphemeralKeyCommandSigner()

  return private_key_file_command_signer.PrivateKeyFileCommandSigner()  # pylint: disable=line-too-long


def _ConvertToRrgCommand(
    command: api_signed_commands_pb2.ApiCommand,
) -> rrg_execute_signed_command_pb2.Command:
  """Converts a GRR command to a RRG command."""
  rrg_command = rrg_execute_signed_command_pb2.Command()

  path: str
  if command.path_template:
    path_template = string.Template(command.path_template)
    path_template_params = dict([
        template_param.split("=", 1)
        for template_param in FLAG_TEMPLATE_PARAMS.value
    ])
    path = path_template.substitute(path_template_params)
  else:
    path = command.path

  rrg_command.path.raw_bytes = path.encode("utf-8")

  # For compatibility with agents that do not support generalized arguments, we
  # use the `args_signed` field as long as there are no unsigned arguments nor
  # filestore file arguments.
  if any(
      arg.unsigned_allowed or arg.filestore_file_sha256_allowed
      for arg in command.args
  ):
    for arg in command.args:
      if arg.unsigned_allowed:
        rrg_command.args.add().unsigned_allowed = True
      elif arg.filestore_file_sha256_allowed:
        rrg_command.args.add().filestore_file_sha256_allowed = True
      else:
        rrg_command.args.add().signed = arg.signed
  else:
    for arg in command.args:
      rrg_command.args_signed.append(arg.signed)

  for env_var in command.env_vars:
    rrg_command.env_signed[env_var.name] = env_var.value
  rrg_command.env_unsigned_allowed.extend(command.env_vars_unsigned_allowed)
  rrg_command.env_inherited.extend(command.env_vars_inherited)

  if command.HasField("signed_stdin"):
    rrg_command.signed_stdin = command.signed_stdin
  elif command.HasField("unsigned_stdin_allowed"):
    rrg_command.unsigned_stdin_allowed = command.unsigned_stdin_allowed
  return rrg_command


def main(args: Sequence[str]) -> None:
  config_lib.ParseConfigCommandLine()

  api = api_http.InitHttp(
      api_endpoint=FLAG_API_ENDPOINT.value,
      auth=(FLAG_API_USER.value, FLAG_API_PASSWORD.value),
  )  # pylint: disable=unused-variable

  if not args[1:]:
    logging.warning("No input files provided")

  if FLAG_REGENERATE.value:
    logging.info("Pruning existing signed commands from the database")
    api.root.DeleteAllSignedCommands()

  signer = _GetCommandSigner()
  signed_commands = api_signed_commands_pb2.ApiSignedCommands()

  for input_path in args[1:]:
    logging.info("Reading input file: %r", input_path)

    with open(input_path, "r") as f:
      commands = text_format.Parse(
          f.read(),
          api_signed_commands_pb2.ApiCommands(),
      )

    for command in commands.commands:
      rrg_command = _ConvertToRrgCommand(command)

      signed_command = signed_commands.signed_commands.add()
      signed_command.id = command.id
      signed_command.operating_system = command.operating_system
      signed_command.command = rrg_command.SerializeToString()
      signed_command.ed25519_signature = signer.Sign(rrg_command)
      signed_command.source_path = input_path

      logging.info("Signed command: %r", signed_command.id)

  logging.info(
      "Writing %d signed commands to the database",
      len(signed_commands.signed_commands),
  )
  api.root.CreateSignedCommands(signed_commands)


if __name__ == "__main__":
  app.run(main)
