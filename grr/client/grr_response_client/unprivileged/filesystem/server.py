#!/usr/bin/env python
"""Functionality to create an unprivileged filesystem server."""

from typing import Optional

from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged import interface_registry
from grr_response_client.unprivileged import server


def CreateFilesystemServer(
    device_file_descriptor: Optional[int] = None) -> communication.Server:
  extra_file_descriptors = []
  if device_file_descriptor is not None:
    extra_file_descriptors.append(
        communication.FileDescriptor.FromFileDescriptor(device_file_descriptor))
  return server.CreateServer(extra_file_descriptors,
                             interface_registry.Interface.FILESYSTEM)
