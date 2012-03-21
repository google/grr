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
import win32service
import win32serviceutil
import winerror

from grr.client import client_config
from grr.lib import utils
from grr.proto import jobs_pb2


def CanonicalPathToLocalPath(path):
  """Converts the canonical paths as used by GRR to OS specific paths.

  Due to the inconsistencies between handling paths in windows we need to
  convert a path to an OS specific version prior to using it. This function
  should be called just before any OS specific functions.

  Canonical paths on windows have:
    - / instead of \\.
    - Begin with /X:// where X is the drive letter.

  Args:
    path: A canonical path specification.

  Returns:
    A windows specific path.
  """
  # Account for raw devices
  path = path.replace("/\\", "\\")
  path = path.replace("/", "\\")
  m = re.match(r"\\([a-zA-Z]):(.*)$", path)
  if m:
    path = "%s:\\%s" % (m.group(1), m.group(2))

  return path


def LocalPathToCanonicalPath(path):
  """Converts path from the local system's convention to the canonical."""
  path_components = path.split("/")
  result = []
  for component in path_components:
    # Devices must maintain their \\ so they do not get broken up.
    m = re.match(r"\\\\.\\", component)

    # The component is not special and can be converted as normal
    if not m:
      component = component.replace("\\", "/")

    result.append(component)

  return utils.JoinPath(*result)


def WinFindProxies():
  """Tries to find proxies by interrogating all the user's settings.

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

  proxies.extend(client_config.PROXY_SERVERS)
  return proxies


def WinGetRawDevice(path):
  """Resolves the raw device that contains the path.

  Args:
    path: A path to examine.

  Returns:
    A pathspec to read the raw device as well as the modified path to read
    within the raw device. This is usually the path without the mount point.

  Raises:
    IOError: if the path does not exist or some unexpected behaviour occurs.
  """
  path = CanonicalPathToLocalPath(path)
  # Try to expand the shortened paths
  try:
    path = win32file.GetLongPathName(path)
  except pywintypes.error:
    pass

  try:
    mount_point = win32file.GetVolumePathName(path)
  except pywintypes.error, details:
    logging.info("path not found. %s", details)
    raise IOError("No mountpoint for path: %s", path)

  if not path.startswith(mount_point):
    raise IOError("path %s is not mounted under %s?" % (path, mount_point))

  corrected_path = LocalPathToCanonicalPath(path[len(mount_point):])
  corrected_path = utils.NormalizePath(corrected_path)

  volume = win32file.GetVolumeNameForVolumeMountPoint(mount_point).rstrip("\\")
  volume = LocalPathToCanonicalPath(volume)

  # The pathspec for the raw volume
  result = jobs_pb2.Path(path=volume, pathtype=jobs_pb2.Path.OS,
                         mount_point=mount_point.rstrip("\\"))

  return result, corrected_path


def InstallDriver(driver_path, service_name, driver_display_name):
  """Loads a driver and start it."""
  hscm = win32service.OpenSCManager(None, None,
                                    win32service.SC_MANAGER_ALL_ACCESS)
  try:
    win32service.CreateService(hscm,
                               service_name,
                               driver_display_name,
                               win32service.SERVICE_ALL_ACCESS,
                               win32service.SERVICE_KERNEL_DRIVER,
                               win32service.SERVICE_DEMAND_START,
                               win32service.SERVICE_ERROR_IGNORE,
                               driver_path,
                               None,  # No load ordering
                               0,     # No Tag identifier
                               None,  # Service deps
                               None,  # User name
                               None)  # Password
    win32serviceutil.StartService(service_name)
  except pywintypes.error, e:
    if e[0] == 1073:
      raise OSError("Service already exists.")
    else:
      raise RuntimeError("StartService failure: {0}".format(e))


def UninstallDriver(driver_path, service_name, delete_file=False):
  """Unloads the driver and delete the driver file.

  Args:
    driver_path: Full path name to the driver file.
    service_name: Name of the service the driver is loaded as.
    delete_file: Should we delete the driver file after removing the service.

  Raises:
    OSError: On failure to uninstall or delete.
  """

  try:
    win32serviceutil.StopService(service_name)
  except pywintypes.error, e:
    if e[0] not in [winerror.ERROR_SERVICE_NOT_ACTIVE,
                    winerror.ERROR_SERVICE_DOES_NOT_EXIST]:
      raise OSError("Could not stop service: {0}".format(e))

  try:
    win32serviceutil.RemoveService(service_name)
  except pywintypes.error, e:
    if e[0] != winerror.ERROR_SERVICE_DOES_NOT_EXIST:
      raise OSError("Could not remove service: {0}".format(e))

  if delete_file:
    try:
      if os.path.exists(driver_path):
        os.remove(driver_path)
    except (OSError, IOError), e:
      raise OSError("Driver deletion failed: " + str(e))
