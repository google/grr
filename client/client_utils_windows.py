#!/usr/bin/env python

# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Windows specific utils."""


import exceptions
import logging
import os
import re
import _winreg
import pywintypes
import win32file

from grr.lib import utils
from grr.proto import jobs_pb2


def InterpolatePath(path):
  """Interpolates the path based on client information.

  Args:
    path: The format string on the path.

  Returns:
    Interpolated path.
  """
  args = dict(SYSTEM_DIR=os.environ.get("SYSTEM_DIR"),
              PROGRAM_FILES=os.environ.get("PROGRAM_FILES"))
  return path % args


def WinFindProxies():
  """Try to find proxies by interrogating all the user's settings.

  This function is a modified urillib.getproxies_registry() from the
  standard library. We just store the proxy value in the environment
  for urllib to find it.

  TODO(user): Iterate through all the possible values if one proxy
  fails, in case more than one proxy is specified in different users
  profiles.

  Returns:
    A list of proxies.
  """

  proxies = []
  for i in range(0, 100):
    try:
      sid = _winreg.EnumKey(_winreg.HKEY_USERS, i)
    except exceptions.WindowsError:
      break

    try:
      subkey = (sid + "\\Software\\Microsoft\\Windows"
                "\\CurrentVersion\\Internet Settings")

      internet_settings = _winreg.OpenKey(_winreg.HKEY_USERS,
                                          subkey)

      proxy_enable = _winreg.QueryValueEx(internet_settings,
                                          "ProxyEnable")[0]

      if proxy_enable:
        # Returned as Unicode but problems if not converted to ASCII
        proxy_server = str(_winreg.QueryValueEx(internet_settings,
                                                "ProxyServer")[0])
        if "=" in proxy_server:
          # Per-protocol settings
          for p in proxy_server.split(";"):
            protocol, address = p.split("=", 1)
                  # See if address has a type:// prefix

            if not re.match("^([^/:]+)://", address):
              address = "%s://%s" % (protocol, address)

            proxies.append(address)
        else:
          # Use one setting for all protocols
          if proxy_server[:5] == "http:":
            proxies.append(proxy_server)
          else:
            proxies.append("http://%s" % proxy_server)

      internet_settings.Close()

    except (exceptions.WindowsError, ValueError, TypeError):
      continue

  logging.debug("Found proxy servers: %s", proxies)

  return proxies


def WinSplitPathspec(pathspec):
  """Splits a given path into device, mountpoint, and remaining path.

  Examples:

  Let's say "\\.\Volume{11111}\" is mounted on "C:\", then

  "C:\\Windows\\" is split into
  (device="\\.\Volume{11111}\", mountpoint="C:\", path="Windows")

  and

  "\\.\Volume{11111}\Windows\" is split into
  ("\\.\Volume{11111}\", "C:\", "Windows")

  After the split, mountpoint and path can always be concatenated
  to obtain a valid os file path.

  Args:
    pathspec: Path specification to be split.

  Returns:
    Pathspec split into device, mountpoint, and remaining path.

  Raises:
    IOError: Path was not found on any mounted device.

  """
  # Do not split Registry requests.
  if pathspec.pathtype == jobs_pb2.Path.REGISTRY:
    return pathspec

  path = pathspec.mountpoint + pathspec.path
  path = utils.SmartUnicode(path)
  path = InterpolatePath(path)

  # We need \ only for windows.
  path = path.replace("/", "\\").strip("\\")

  path = utils.NormalizePath(path, "\\").lstrip("\\")

  try:
    mp = win32file.GetVolumePathName(path)
  except pywintypes.error, details:
    logging.error("path not found. %s", details)
    raise IOError("No mountpoint for path: %s", path)

  # GetVolumeNameForVolumeMountPoint is picky when it comes to trailing \'s
  mp = mp.rstrip("\\")
  mp += "\\"
  volume = win32file.GetVolumeNameForVolumeMountPoint(mp)

  volume = volume.replace("\\\\?\\", "\\\\.\\")

  res = jobs_pb2.Path()
  res.pathtype = pathspec.pathtype
  res.device, res.mountpoint = volume, mp
  if path.lower().startswith(mp.lower()):
    res.path = path[len(res.mountpoint):]
  else:
    # Path contains a volume string.
    volume = volume.lstrip("\\.?")
    pos = path.lower().find(volume.lower())
    res.path = path[pos+len(volume):]

  return res
