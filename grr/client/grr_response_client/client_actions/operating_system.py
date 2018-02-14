#!/usr/bin/env python
"""A facade to operating system dependent client actions."""

import platform

# pylint: disable=g-import-not-at-top
# pylint: disable=g-wrong-blank-lines

# These imports populate the Action registry
if platform.system() == "Linux":
  from grr_response_client.client_actions.linux import linux
  submodule = linux
elif platform.system() == "Windows":
  from grr_response_client.client_actions.windows import windows
  submodule = windows
elif platform.system() == "Darwin":
  from grr_response_client.client_actions.osx import osx
  import grr_response_client.client_actions.osx.local  # pylint: disable=unused-import

  submodule = osx

# pylint: enable=g-import-not-at-top
# pylint: enable=g-wrong-blank-lines

# pylint: disable=invalid-name

EnumerateInterfaces = submodule.EnumerateInterfaces
EnumerateFilesystems = submodule.EnumerateFilesystems
GetInstallDate = submodule.GetInstallDate
Uninstall = submodule.Uninstall
UpdateAgent = submodule.UpdateAgent
