#!/usr/bin/env python
"""Registry of unprivileged RPC interfaces."""

import enum
from typing import Dict

from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged.filesystem import server_lib as filesystem_server_lib
from grr_response_client.unprivileged.memory import server_lib as memory_server_lib


class Interface(enum.Enum):
  """Enum of supported RPC interfaces.

  The value of the enum is a string suitable to be used as flag value.
  """

  FILESYSTEM = "filesystem"
  MEMORY = "memory"


_REGISTRY: Dict[Interface, communication.ConnectionHandler] = {
    Interface.FILESYSTEM: filesystem_server_lib.Dispatch,
    Interface.MEMORY: memory_server_lib.Dispatch,
}


class Error(Exception):
  pass


def GetConnectionHandlerForInterfaceString(
    interface_str: str) -> communication.ConnectionHandler:
  """Returns the connection handler for the respective interface."""
  try:
    interface = Interface(interface_str)
  except ValueError as e:
    raise Error(f"Bad interface string {interface_str}.") from e
  try:
    dispatch = _REGISTRY[interface]
  except KeyError as e:
    raise Error(f"Unknown interface {interface}.") from e
  return dispatch
