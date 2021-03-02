#!/usr/bin/env python
"""Functionality to create a filesystem server."""

import sys
from typing import List, Optional

from grr_response_client.unprivileged import communication


def _MakeServerArgs(channel: communication.Channel) -> List[str]:
  """Returns the args to run the filesystem server command."""

  named_flags = [
      "--filesystem_server_pipe_input",
      str(channel.pipe_input),
      "--filesystem_server_pipe_output",
      str(channel.pipe_output),
  ]

  # PyInstaller executable
  if getattr(sys, "frozen", False):
    return [sys.executable] + sys.argv[1:] + named_flags

  # Running from a unit test

  return [
    sys.executable, "-m",
    "grr_response_client.unprivileged.filesystem.server_main",
    str(channel.pipe_input),
    str(channel.pipe_output),
  ]


def CreateFilesystemServer(
    device_file_descriptor: Optional[int] = None) -> communication.Server:
  extra_file_descriptors = []
  if device_file_descriptor is not None:
    extra_file_descriptors.append(device_file_descriptor)
  server = communication.SubprocessServer(_MakeServerArgs,
                                          extra_file_descriptors)
  return server
