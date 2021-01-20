#!/usr/bin/env python
"""Functionality to create a filesystem server."""

from typing import List
import sys

from grr_response_client.unprivileged import communication


def _MakeServerArgs(socket_fd: int) -> List[str]:
  return [
      sys.executable, "-m",
      "grr_response_client.unprivileged.filesystem.server_main",
      str(socket_fd)
  ]


def CreateFilesystemServer() -> communication.Server:
  server = communication.SubprocessServer(_MakeServerArgs)
  return server
