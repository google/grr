#!/usr/bin/env python
"""CLI to generate and save signatures for commands."""

from collections.abc import Sequence

from absl import app
from absl import flags
from absl import logging

from google.protobuf import text_format
from grr_response_core.lib import config_lib
from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_server import command_signer
from grr_response_server import ephemeral_key_command_signer
from grr_response_server import maintenance_utils
from grr_response_server import private_key_file_command_signer # pylint: disable=line-too-long

from grr_response_proto.rrg.action import execute_signed_command_pb2 as rrg_execute_signed_command_pb2

FLAG_REGENERATE = flags.DEFINE_bool(
    name="regenerate",
    default=False,
    help="If true prunes the database of existing signatures before writing.",
)

EPHEMERAL_SIGNING_KEY = flags.DEFINE_bool(
    name="ephemeral_signing_key",
    default=False,
    help="If set, uses a fake signing key instead of the one from the config.",
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

  rrg_command.path.raw_bytes = command.path.encode("utf-8")

  # For compatibility with agents that do not support generalized arguments, we
  # use the `args_signed` field as long as there are no unsigned arguments.
  if any(arg.unsigned_allowed for arg in command.args):
    for arg in command.args:
      if arg.unsigned_allowed:
        rrg_command.args.add().unsigned_allowed = True
      else:
        rrg_command.args.add().signed = arg.signed
  else:
    for arg in command.args:
      rrg_command.args_signed.append(arg.signed)

  for env_var in command.env_vars:
    rrg_command.env_signed[env_var.name] = env_var.value
  rrg_command.env_unsigned_allowed.extend(command.env_vars_unsigned_allowed)

  if command.HasField("signed_stdin"):
    rrg_command.signed_stdin = command.signed_stdin
  elif command.HasField("unsigned_stdin_allowed"):
    rrg_command.unsigned_stdin_allowed = command.unsigned_stdin_allowed
  return rrg_command


def main(args: Sequence[str]) -> None:
  config_lib.ParseConfigCommandLine()

  root_api = maintenance_utils.InitGRRRootAPI()

  if not args[1:]:
    logging.warning("No input files provided")

  if FLAG_REGENERATE.value:
    logging.info("Pruning existing signed commands from the database")
    root_api.DeleteAllSignedCommands()

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
  root_api.CreateSignedCommands(signed_commands)


if __name__ == "__main__":
  app.run(main)
