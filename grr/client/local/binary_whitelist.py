#!/usr/bin/env python
"""Deployment-specific whitelisted binaries."""

import platform


def IsExecutionWhitelisted(cmd, args):
  """Check if a binary and args is whitelisted.

  Args:
    cmd: Canonical path to the binary.
    args: List of arguments to be passed to the binary.

  Returns:
    Bool, True if it is whitelisted.

  This function is not called directly but used by client_utils_common.py to
  detect site-specific binaries that are allowed to run.
  """


  return False
