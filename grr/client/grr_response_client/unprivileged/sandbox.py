#!/usr/bin/env python
"""Multi-platform interface to Sandboxing."""

import logging
import platform
from typing import Iterable


def InitSandbox(name: str, paths_read_only: Iterable[str]) -> None:
  """Initializes a global sandbox.

  To be called in the privileged process.

  Args:
    name: The unique name of the Sandbox.
    paths_read_only: Lists of paths which will be shared in read-only and
      execute mode with the Sandbox.
  """
  if platform.system() != "Windows":
    return
  try:
    # pytype:disable=import-error
    # pylint:disable=g-import-not-at-top
    from grr_response_client.unprivileged.windows import sandbox
    # pylint:enable=g-import-not-at-top
    # pytype:enable=import-error
    sandbox.InitSandbox(name, paths_read_only)
  except:  # pylint:disable=bare-except
    # TODO: Windows sandboxing is still experimental.
    # Don't crash the client if anything goes wrong.
    logging.error("IsSandbox failed.", exc_info=True)


def IsSandboxInitialized() -> bool:
  """Returns `True` if a global sandbox has been successfully initialized.

  To be called in the privileged process.
  """
  if platform.system() == "Windows":
    try:
      # pytype:disable=import-error
      # pylint:disable=g-import-not-at-top
      from grr_response_client.unprivileged.windows import sandbox
      # pylint:enable=g-import-not-at-top
      # pytype:enable=import-error
      return sandbox.IsSandboxInitialized()
    except:  # pylint:disable=bare-except
      # TODO: Windows sandboxing is still experimental.
      # Don't crash the client if anything goes wrong.
      logging.error("IsSandboxInitialized failed.", exc_info=True)
      return False
  elif platform.system() in ("Linux", "Darwin"):
    # These platforms don't need initialization.
    return True
  else:
    return False


def EnterSandbox(user: str, group: str) -> None:
  """Enters a sandbox.

  Drops root privileges, by changing the user and group.

  To be called in the unprivileged process.

  Args:
    user: New user name to run as. If empty then the user is not changed.
    group: New group name to run as. If empty then the group is not changed.
  """
  if platform.system() == "Linux":
    # pylint: disable=g-import-not-at-top
    from grr_response_client.unprivileged.linux import sandbox
    # pylint: enable=g-import-not-at-top
    sandbox.EnterSandbox(user, group)
  elif platform.system() == "Darwin":
    # pytype: disable=import-error
    # pylint: disable=g-import-not-at-top
    from grr_response_client.unprivileged.osx import sandbox
    # pylint: enable=g-import-not-at-top
    # pytype: enable=import-error
    sandbox.EnterSandbox(user, group)
