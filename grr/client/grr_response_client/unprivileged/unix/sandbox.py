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
    os.setresgid(gid, gid, gid)

  if user:
    uid = pwd.getpwnam(user).pw_uid
    os.setresuid(uid, uid, uid)
