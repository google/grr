#!/usr/bin/env python
"""Select operating system specific implementations of builder."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform

# pylint: disable=unused-import,g-import-not-at-top,g-bad-name

if platform.system() == "Linux":
  from grr_response_core.lib.builders import linux
  LinuxClientBuilder = linux.LinuxClientBuilder
  CentosClientBuilder = linux.CentosClientBuilder

elif platform.system() == "Windows":
  from grr_response_core.lib.builders import windows
  WindowsClientBuilder = windows.WindowsClientBuilder

elif platform.system() == "Darwin":
  from grr_response_core.lib.builders import osx
  DarwinClientBuilder = osx.DarwinClientBuilder
