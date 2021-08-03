#!/usr/bin/env python
"""Sandboxing functionality on Linux."""

import ctypes
import ctypes.util
import errno
import grp
import os
import pwd


# See unshare(2)
CLONE_NEWIPC = 0x08000000
CLONE_NEWNET = 0x40000000


class Error(Exception):
  pass


def EnterSandbox(user: str, group: str) -> None:
  """Enters the sandbox.

  Drops root privileges, by changing the user and group.

  Args:
    user: New UNIX user name to run as. If empty then the user is not changed.
    group: New UNIX group name to run as. If empty then the group is not
      changed.
  """
  if not (user or group):
    return

  # Disable networking and IPC by creating new (empty) namespaces for the
  # current process.
  libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("c"))
  unshare = getattr(libc, "unshare", None)
  if unshare:
    unshare.argtypes = [ctypes.c_int]
    unshare.restype = ctypes.c_int

    def Unshare(flags: int) -> None:
      res = unshare(flags)
      if res == 0:
        return
      error = ctypes.get_errno()
      if error != errno.EINVAL:
        raise Error(f"unshare({flags}) failed with error {error}.")

    Unshare(CLONE_NEWNET)
    Unshare(CLONE_NEWIPC)

  if group:
    gid = grp.getgrnam(group).gr_gid
    os.setgroups([gid])
    os.setresgid(gid, gid, gid)

  if user:
    uid = pwd.getpwnam(user).pw_uid
    os.setresuid(uid, uid, uid)
