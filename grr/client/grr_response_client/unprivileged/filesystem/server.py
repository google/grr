#!/usr/bin/env python
"""Functionality to create a filesystem server."""

import sys
from typing import List

from grr_response_client.unprivileged import communication


def _MakeServerArgs(socket_fd: int) -> List[str]:
  """Returns the args to run the filesystem server command."""

  named_socket_flag = ["--filesystem_server_socket", str(socket_fd)]

  # PyInstaller executable
  if getattr(sys, "frozen", False):
    return [sys.executable] + sys.argv[1:] + named_socket_flag


  # Running from a unit test

  return [
    sys.executable, "-m",
    "grr_response_client.unprivileged.filesystem.server_main",
    str(socket_fd),
  ]


def CreateFilesystemServer() -> communication.Server:
  server = communication.SubprocessServer(_MakeServerArgs)
  return server
