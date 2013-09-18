#!/usr/bin/env python
"""Select operating system specific implementations of builder."""
import platform

# pylint: disable=unused-import,g-import-not-at-top,g-bad-name

if platform.system() == "Linux":
  from grr.lib.builders import linux
  LinuxClientBuilder = linux.LinuxClientBuilder
  CentosClientBuilder = linux.CentosClientBuilder

elif platform.system() == "Windows":
  from grr.lib.builders import windows
  WindowsClientBuilder = windows.WindowsClientBuilder

elif platform.system() == "Darwin":
  from grr.lib.builders import osx
  DarwinClientBuilder = osx.DarwinClientBuilder
