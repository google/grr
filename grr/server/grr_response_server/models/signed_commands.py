#!/usr/bin/env python
"""Module with data models and helpers related to signed commands."""

from grr_response_proto import signed_commands_pb2
from grr_response_proto.api import signed_commands_pb2 as api_signed_commands_pb2
from grr_response_server.models import protobuf_utils as models_utils


def OperatingSystemToApiOperatingSystem(
    operating_system: signed_commands_pb2.SignedCommand.OS,
) -> api_signed_commands_pb2.ApiSignedCommand.OS:
  """Converts a operating system to an API operating system."""
  os_map = {
      signed_commands_pb2.SignedCommand.OS.WINDOWS: (
          api_signed_commands_pb2.ApiSignedCommand.OS.WINDOWS
      ),
      signed_commands_pb2.SignedCommand.OS.LINUX: (
          api_signed_commands_pb2.ApiSignedCommand.OS.LINUX
      ),
      signed_commands_pb2.SignedCommand.OS.MACOS: (
          api_signed_commands_pb2.ApiSignedCommand.OS.MACOS
      ),
  }
  return os_map.get(
      operating_system,
      api_signed_commands_pb2.ApiSignedCommand.OS.UNSET,
  )


def InitApiSignedCommandFromSignedCommand(
    signed_command: signed_commands_pb2.SignedCommand,
) -> api_signed_commands_pb2.ApiSignedCommand:
  """Initializes an API signed command from a signed command."""

  api_signed_command = api_signed_commands_pb2.ApiSignedCommand()

  models_utils.CopyAttr(signed_command, api_signed_command, "id")
  models_utils.CopyAttr(signed_command, api_signed_command, "ed25519_signature")

  api_signed_command.operating_system = OperatingSystemToApiOperatingSystem(
      signed_command.operating_system
  )

  api_signed_command.command = signed_command.command
  return api_signed_command
