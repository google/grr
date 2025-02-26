#!/usr/bin/env python
"""Functionality to create an unprivileged memory server."""

from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged import interface_registry
from grr_response_client.unprivileged import server


def CreateMemoryServer(
    process_file_descriptors: list[communication.FileDescriptor],
) -> communication.Server:
  return server.CreateServer(
      process_file_descriptors, interface_registry.Interface.MEMORY
  )
