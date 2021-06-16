#!/usr/bin/env python
"""A module with an action for collecting named pipes."""
import contextlib
import logging
import os
import platform
from typing import Iterator

from grr_response_client import actions
from grr_response_core.lib.rdfvalues import client as rdf_client


def ListNamedPipes() -> Iterator[rdf_client.NamedPipe]:
  """Yields all named pipes available in the system."""
  if platform.system() != "Windows":
    raise RuntimeError(f"Unsupported platform: {platform.system()}")

  # pylint: disable=g-import-not-at-top
  # pytype: disable=import-error
  import ctypes
  import ctypes.wintypes
  import win32api
  import win32file
  import win32pipe
  import winerror
  # pytype: enable=import-error
  # pylint: enable=g-import-not-at-top

  # The `GetNamedPipeHandleState` function provided by the `win32pipe` module is
  # broken (calling it results in invalid function exception). Hence, we need to
  # go to a lower level and use raw Windows API calls to get this information.
  #
  # https://docs.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-getnamedpipehandlestatew
  # pytype: disable=module-attr
  GetNamedPipeHandleStateW = ctypes.windll.kernel32.GetNamedPipeHandleStateW  # pylint: disable=invalid-name
  # pytype: enable=module-attr
  GetNamedPipeHandleStateW.argtypes = [
      ctypes.wintypes.HANDLE,
      ctypes.wintypes.LPDWORD,
      ctypes.wintypes.LPDWORD,
      ctypes.wintypes.LPDWORD,
      ctypes.wintypes.LPDWORD,
      ctypes.wintypes.LPWSTR,
      ctypes.wintypes.DWORD,
  ]
  GetNamedPipeHandleStateW.restype = ctypes.wintypes.BOOL

  # For some reason the `GetNamedPipeClientComputerName` function does not exist
  # in `win32pipe`. Hence, we implement a low-level wrapper for Windows API for
  # it ourselves.
  #
  # https://docs.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-getnamedpipeclientcomputernamew
  # pytype: disable=module-attr
  GetNamedPipeClientComputerNameW = ctypes.windll.kernel32.GetNamedPipeClientComputerNameW  # pylint: disable=invalid-name
  # pytype: enable=module-attr
  GetNamedPipeClientComputerNameW.argtypes = [
      ctypes.wintypes.HANDLE,
      ctypes.wintypes.LPWSTR,
      ctypes.wintypes.ULONG,
  ]
  GetNamedPipeClientComputerNameW.restype = ctypes.wintypes.BOOL

  # https://docs.microsoft.com/en-us/windows/win32/ipc/pipe-names
  for name in os.listdir(r"\\.\pipe"):
    pipe = rdf_client.NamedPipe()
    pipe.name = name

    try:
      handle = win32file.CreateFile(f"\\\\.\\pipe\\{name}", 0, 0, None,
                                    win32file.OPEN_EXISTING, 0, None)
    except win32file.error as error:
      # There might be some permission issues. We log the error and skip getting
      # pipe details, but still yield a result with at least the name filled-in.
      logging.error("Cannot open pipe '%s': %s", name, error)
      yield pipe
      continue

    with contextlib.closing(handle):
      try:
        pipe_info = win32pipe.GetNamedPipeInfo(handle)
        flags, in_buffer_size, out_buffer_size, max_instance_count = pipe_info

        pipe.flags = flags
        pipe.in_buffer_size = in_buffer_size
        pipe.out_buffer_size = out_buffer_size
        pipe.max_instance_count = max_instance_count
      except win32pipe.error as error:
        # Getting the information might fail (for whatever reason), but we don't
        # want to fail action execution as other probing calls might succeed.
        logging.error("Failed to get info about pipe '%s': '%s'", name, error)

      try:
        pipe.server_pid = win32pipe.GetNamedPipeServerProcessId(handle)
      except win32pipe.error as error:
        # See similar comment for `GetNamedPipeInfo` for more information.
        message = "Failed to get server pid of pipe '%s': '%s'"
        logging.error(message, name, error)

      try:
        pipe.client_pid = win32pipe.GetNamedPipeClientProcessId(handle)
      except win32pipe.error as error:
        # See similar comment for `GetNamedPipeInfo` for more information.
        message = "Failed to get client pid of pipe '%s': '%s'"
        logging.error(message, name, error)

      cur_instance_count = ctypes.wintypes.DWORD()
      status = GetNamedPipeHandleStateW(
          ctypes.wintypes.HANDLE(int(handle)),
          None,
          ctypes.byref(cur_instance_count),
          None,
          None,
          None,
          0,
      )

      if status == 0:
        # See similar comment for `GetNamedPipeInfo` for more information.
        error = win32api.GetLastError()
        logging.error("Failed to get state of pipe '%s': %s", name, error)
      else:
        pipe.cur_instance_count = cur_instance_count.value

      client_computer_name = (ctypes.wintypes.WCHAR * _COMPUTER_NAME_MAX_SIZE)()  # pytype: disable=not-callable
      status = GetNamedPipeClientComputerNameW(
          ctypes.wintypes.HANDLE(int(handle)),
          client_computer_name,
          _COMPUTER_NAME_MAX_SIZE,
      )

      if status == 0:
        # See similar comment for `GetNamedPipeInfo` for more information.
        error = win32api.GetLastError()
        # Not being able to get computer name of a local pipe is expected, there
        # is no need to log errors in such cases.
        if error != winerror.ERROR_PIPE_LOCAL:
          logging.error("Failed to get hostname of pipe '%s': %s", name, error)
      else:
        pipe.client_computer_name = client_computer_name.value

      yield pipe


class ListNamedPipesAction(actions.ActionPlugin):
  """An action for collecting named pipes."""

  in_rdfvalue = None
  out_rdfvalues = [rdf_client.NamedPipe]

  def Run(self, args: None) -> None:
    """Executes the action."""
    for result in ListNamedPipes():
      self.SendReply(result)


# The length is 15 characters but we also might need one extra byte for the null
# character.
#
# https://docs.microsoft.com/en-us/troubleshoot/windows-server/identity/naming-conventions-for-computer-domain-site-ou
_COMPUTER_NAME_MAX_SIZE = 16
