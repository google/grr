#!/usr/bin/env python
"""CLI to generate and save signatures for commands."""

import argparse
from absl import app
from absl.flags import argparse_flags
from google.protobuf import text_format
from grr_response_core.lib import config_lib
from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_server import command_signer
from grr_response_server import private_key_file_command_signer  # pylint: disable=line-too-long
from grr_response_proto.rrg.action import execute_signed_command_pb2


parser = argparse_flags.ArgumentParser(
    description="Generate command signatures for command execution in RRG."
)
generate_command_signatures_parser = parser.add_subparsers(
    dest="generate_command_signatures_parser",
)
generate = generate_command_signatures_parser.add_parser(
    "generate_command_signatures_from_file",
    help="Generate signatures for all given commands.",
)
generate.add_argument(
    "--input_file",
    help="Input textproto file with commands to generate signatures for.",
)
generate.add_argument(
    "--regenerate",
    default=False,
    help="If true prunes the database of existing signatures before writing.",
)


def _GetCommandSigner() -> command_signer.AbstractCommandSigner:
  """Signs commands and returns the complete signed commands."""

  return private_key_file_command_signer.PrivateKeyFileCommandSigner()  # pylint: disable=line-too-long


def _ConvertToRrgCommand(
    command: api_signed_commands_pb2.ApiCommand,
) -> execute_signed_command_pb2.Command:
  """Converts a GRR command to a RRG command."""
  rrg_command = execute_signed_command_pb2.Command()

  rrg_command.path.raw_bytes = command.path.encode("utf-8")
  rrg_command.args.extend(command.args)
  for env_var in command.env_vars:
    rrg_command.env[env_var.name] = env_var.value
  if command.HasField("signed_stdin"):
    rrg_command.signed_stdin = command.signed_stdin
  else:
    rrg_command.unsigned_stdin_allowed = command.unsigned_stdin_allowed
  return rrg_command


def main(args: argparse.Namespace) -> None:
  config_lib.ParseConfigCommandLine()
  if (
      args.generate_command_signatures_parser
      == "generate_command_signatures_from_file"
  ):
    root_api = maintenance_utils.InitGRRRootAPI()
    if args.regenerate:
      root_api.DeleteAllSignedCommands()

    with open(args.input_file, "r") as f:
      commands = text_format.Parse(
          f.read(),
          api_signed_commands_pb2.ApiCommands(),
      )

    signer = _GetCommandSigner()

    signed_commands = api_signed_commands_pb2.ApiSignedCommands()
    for command in commands.commands:
      rrg_command = _ConvertToRrgCommand(command)

      signed_command = signed_commands.signed_commands.add()
      signed_command.id = command.id
      signed_command.operating_system = command.operating_system
      signed_command.command = rrg_command.SerializeToString()
      command.ed25519_signature = signer.Sign(rrg_command)

    root_api.CreateSignedCommands(signed_commands)


def Run() -> None:  # pylint: disable=invalid-name
  app.run(main, flags_parser=lambda argv: parser.parse_args())


if __name__ == "__main__":
  Run()
