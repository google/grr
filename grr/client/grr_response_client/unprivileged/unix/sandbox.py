#!/usr/bin/env python
"""Sandboxing functionaliy."""

import grp
import os
import pwd


def EnterSandbox(user: str, group: str) -> None:
  """Enters the sandbox.

  Drops root privileges, by changing the user and group.

  Args:
    user: New UNIX user name to run as. If empty then the user is not changed.
    group: New UNIX group name to run as. If empty then the group is not
      changed.
  """
  if group:
    gid = grp.getgrnam(group).gr_gid
    os.setgroups([gid])
    if getattr(os, "setresgid", False):
      # We prefer setresgid if available, which is the case on Linux.
      # The reason is that it's the most explicit of the various set*id
      # variants.
      os.setresgid(gid, gid, gid)
    else:
      # This is the same as the above if called by the superuser.
      os.setgid(gid)

  if user:
    uid = pwd.getpwnam(user).pw_uid
    if getattr(os, "setresuid", False):
      # We prefer setresuid if available, which is the case on Linux.
      # The reason is that it's the most explicit of the various set*id
      # variants.
      os.setresuid(uid, uid, uid)
    else:
      # This is the same as the above if called by the superuser.
      os.setuid(uid)
