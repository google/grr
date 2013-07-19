#!/usr/bin/env python
"""Client utilities."""



import sys

# Select the version of what we want based on the OS:

# pylint: disable=g-bad-name
# pylint: disable=g-import-not-at-top
if sys.platform == "win32":
  from grr.client import client_utils_windows
  FindProxies = client_utils_windows.WinFindProxies
  GetRawDevice = client_utils_windows.WinGetRawDevice
  CanonicalPathToLocalPath = client_utils_windows.CanonicalPathToLocalPath
  LocalPathToCanonicalPath = client_utils_windows.LocalPathToCanonicalPath
  NannyController = client_utils_windows.NannyController

  KeepAlive = client_utils_windows.KeepAlive
  WinChmod = client_utils_windows.WinChmod

elif sys.platform == "darwin":
  from grr.client import client_utils_osx
  from grr.client import client_utils_linux

  FindProxies = client_utils_osx.OSXFindProxies
  GetRawDevice = client_utils_osx.OSXGetRawDevice

  # Should be the same as linux.
  CanonicalPathToLocalPath = client_utils_linux.CanonicalPathToLocalPath
  LocalPathToCanonicalPath = client_utils_linux.LocalPathToCanonicalPath

  # Should be the same as linux.
  NannyController = client_utils_linux.NannyController

  KeepAlive = client_utils_osx.KeepAlive

else:
  from grr.client import client_utils_linux
  # Linux platform
  FindProxies = client_utils_linux.LinFindProxies
  GetRawDevice = client_utils_linux.LinGetRawDevice
  CanonicalPathToLocalPath = client_utils_linux.CanonicalPathToLocalPath
  LocalPathToCanonicalPath = client_utils_linux.LocalPathToCanonicalPath
  NannyController = client_utils_linux.NannyController

  KeepAlive = client_utils_linux.KeepAlive
