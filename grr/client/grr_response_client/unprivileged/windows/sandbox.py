#!/usr/bin/env python
"""Interface to Windows Sandboxing for the `process` module.

Adds support for global sandbox initialization and handles checks for whether
sandboxing is supported by the current platform.
"""

import logging
import platform
from typing import Iterable, Optional

_sandbox_name: Optional[str] = None


class Error(Exception):
  pass


def InitSandbox(name: str, paths_read_only: Iterable[str]) -> None:
  """Initializes a global sandbox.

  Args:
    name: The unique name of the Sandbox. Windows will create unique state
      (directory tree, regisry tree and a SID) based on the name.
    paths_read_only: Lists of paths which will be shared in read-only and
      execute mode with the Sandbox SID.

  Raises:
    Error: if the global sandbox has been already initialized.
  """
  if int(platform.release()) < 8:
    logging.info(
        "Skipping sandbox initialization. Unsupported platform release: %s.",
        platform.release())
    return
  global _sandbox_name
  if _sandbox_name is not None:
    raise Error(
        f"Sandbox has been already initialized with name {_sandbox_name}.")
  logging.info("Initializing sandbox. Name: %s. Read-only paths: %s.", name,
               paths_read_only)
  # pylint:disable=g-import-not-at-top
  from grr_response_client.unprivileged.windows import sandbox_lib
  # pylint:enable=g-import-not-at-top
  sandbox_lib.InitSandbox(name, paths_read_only)
  _sandbox_name = name


class Sandbox:
  """Represents an optional, app container based sandbox.

  Provides necessary data to be used for the win32 API `CreateProcesss` for
  running a process in the context of a sandbox.
  """

  @property
  def sid_string(self) -> Optional[str]:
    """App container SID represented as string.

    `None` if an App container is not available.
    """
    return None

  @property
  def desktop_name(self) -> Optional[str]:
    """Full alternate desktop name of the App container.

    `None` if an App container is not available.
    """
    return None

  def __enter__(self) -> "Sandbox":
    return self

  def __exit__(self, exc_type, exc_value, traceback) -> None:
    pass


class NullSandbox(Sandbox):
  """A Sandbox implementation performing no sandboxing."""


class AppContainerSandbox(Sandbox):
  """A `Sandbox` implementation performing AppContainer based sandboxing.

  See
  https://docs.microsoft.com/en-us/windows/win32/secauthz/appcontainer-for-legacy-applications-
  for details on AppContainers.
  """

  def __init__(self, name: str) -> None:
    """Constructor.

    Args:
      name: Name of the app container.
    """
    # pylint:disable=g-import-not-at-top
    from grr_response_client.unprivileged.windows import sandbox_lib
    # pylint:enable=g-import-not-at-top
    self._sandbox = sandbox_lib.Sandbox(name)

  @property
  def sid_string(self) -> Optional[str]:
    return self._sandbox.sid_string

  @property
  def desktop_name(self) -> Optional[str]:
    return self._sandbox.desktop_name

  def __enter__(self) -> "AppContainerSandbox":
    self._sandbox.Open()
    logging.info("Entering sandbox. SID: %s. Desktop: %s.", self.sid_string,
                 self.desktop_name)
    return self

  def __exit__(self, exc_type, exc_value, traceback) -> None:
    self._sandbox.Close()


def CreateSandbox() -> Sandbox:
  """Creates an app container based sandbox.

  Returns:
     A null `Sandbox` implementation in case of sandboxing is not available
     or if `InitSandbox` has not been called.
  """
  global _sandbox_name
  if _sandbox_name is None:
    return NullSandbox()
  else:
    return AppContainerSandbox(_sandbox_name)


def IsSandboxInitialized() -> bool:
  """Returns `True` if a global sandbox has been successfully initialized."""
  return _sandbox_name is not None
