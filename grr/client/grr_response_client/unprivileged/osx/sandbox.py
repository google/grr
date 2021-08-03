#!/usr/bin/env python
"""Sandboxing functionality on OSX."""

import ctypes
# pylint: disable=g-importing-member
from ctypes import c_char_p
from ctypes import c_int
from ctypes import c_int64
# pylint: enable=g-importing-member
import ctypes.util
import grp
import os
import pwd


SANDBOX_NAMED = 0x0001


class Error(Exception):
  pass


def EnterSandbox(user: str, group: str) -> None:
  """Enters the sandbox.

  Drops root privileges, by changing the user and group.

  Args:
    user: New UNIX user name to run as. If empty then the user is not changed.
    group: New UNIX group name to run as. If empty then the group is not
      changed.

  Raises:
    Error: on system error.
  """
  if not (user or group):
    return

  libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("c"))
  sandbox_init = getattr(libc, "sandbox_init", None)
  if sandbox_init:
    sandbox_init.argtypes = [
        c_char_p,
        c_int64,
        ctypes.POINTER(c_char_p),
    ]
    sandbox_init.restype = c_int
    res = sandbox_init(b"no-network", SANDBOX_NAMED, None)
    if res != 0:
      error = ctypes.get_errno()
      raise Error(f"sandbox_init failed with error {error}.")

  if group:
    gid = grp.getgrnam(group).gr_gid
    os.setgroups([gid])
    os.setgid(gid)

  if user:
    uid = pwd.getpwnam(user).pw_uid
    os.setuid(uid)
