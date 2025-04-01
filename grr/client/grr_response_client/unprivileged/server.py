#!/usr/bin/env python
"""Functionality to create an unprivileged server."""

import sys

from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged import interface_registry
from grr_response_core import config


def _MakeServerArgs(
    channel: communication.Channel, interface: interface_registry.Interface
) -> list[str]:
  """Returns the args to run the unprivileged server command."""
  assert channel.pipe_input is not None and channel.pipe_output is not None
  named_flags = [
      "--unprivileged_server_pipe_input",
      str(channel.pipe_input.Serialize()),
      "--unprivileged_server_pipe_output",
      str(channel.pipe_output.Serialize()),
      "--unprivileged_server_interface",
      interface.value,
      "--unprivileged_user",
      config.CONFIG["Client.unprivileged_user"],
      "--unprivileged_group",
      config.CONFIG["Client.unprivileged_group"],
  ]

  # PyInstaller executable
  if getattr(sys, "frozen", False):
    return [sys.executable] + named_flags

  # Running from a unit test

  return [
    sys.executable, "-m",
    "grr_response_client.unprivileged.server_main",
  ] + named_flags


def CreateServer(
    extra_file_descriptors: list[communication.FileDescriptor],
    interface: interface_registry.Interface,
) -> communication.Server:
  server = communication.SubprocessServer(
      lambda channel: _MakeServerArgs(channel, interface),
      extra_file_descriptors,
  )
  return server
