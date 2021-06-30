#!/usr/bin/env python
"""Functionality to create an unprivileged server."""

import sys
from typing import List

from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged import interface_registry
from grr_response_core import config


def _MakeServerArgs(channel: communication.Channel,
                    interface: interface_registry.Interface) -> List[str]:
  """Returns the args to run the unprivileged server command."""

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
    extra_file_descriptors: List[communication.FileDescriptor],
    interface: interface_registry.Interface) -> communication.Server:
  server = communication.SubprocessServer(
      lambda channel: _MakeServerArgs(channel, interface),
      extra_file_descriptors)
  return server
