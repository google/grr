#!/usr/bin/env python
"""These are windows specific installers.

NOTE: Subprocess module is broken on windows in that pipes are not handled
correctly. See for example:

http://bugs.python.org/issue3905

This problem seems to go away when we use pipes for all standard handles:
https://launchpadlibrarian.net/134750748/pyqtgraph_subprocess.patch

We also set shell=True because that seems to avoid having an extra cmd.exe
window pop up.
"""
import os
import re
import shutil
import subprocess
import sys
import time
import _winreg
import pywintypes
import win32process
import win32service
import win32serviceutil

import logging

from grr.client import installer
from grr.lib import config_lib
from grr.lib import utils


class CheckForWow64(installer.Installer):
  """Check to ensure we are not running on a Wow64 system."""

  def RunOnce(self):
    if win32process.IsWow64Process():
      raise RuntimeError("Will not install a 32 bit client on a 64 bit system. "
                         "Please use the correct client.")


class CopyToSystemDir(installer.Installer):
  """Copy the distribution from the temp directory to the target."""

  pre = ["CheckForWow64"]

  def StopPreviousService(self):
    """Wait until the service can be stopped."""
    service = config_lib.CONFIG["Nanny.service_name"]

    # QueryServiceStatus returns: scvType, svcState, svcControls, err,
    # svcErr, svcCP, svcWH
    try:
      status = win32serviceutil.QueryServiceStatus(service)[1]
    except pywintypes.error, e:
      logging.info("Unable to query status of service: %s with error: %s",
                   service, e)
      return

    for _ in range(20):
      if status == win32service.SERVICE_STOPPED:
        break
      elif status != win32service.SERVICE_STOP_PENDING:
        logging.info("Attempting to stop service %s", service)
        try:
          win32serviceutil.StopService(service)
        except pywintypes.error, e:
          logging.info("Unable to stop service: %s with error: %s", service, e)
      time.sleep(1)
      status = win32serviceutil.QueryServiceStatus(service)[1]

    if status != win32service.SERVICE_STOPPED:
      service_binary = config_lib.CONFIG["Nanny.service_binary_name"]

      # Taskkill will fail on systems predating Windows XP, this is a best
      # effort fallback solution.
      output = subprocess.check_output(
          ["taskkill", "/im", "%s*" % service_binary, "/f"],
          shell=True,
          stdin=subprocess.PIPE,
          stderr=subprocess.PIPE)

      logging.debug("%s", output)

      # Sleep a bit to ensure that process really quits.
      time.sleep(2)

  def RunOnce(self):
    """Copy the binaries from the temporary unpack location.

    We need to first stop the running service or we might not be able to write
    on the binary. We then copy the entire directory where we are running from
    into the location indicated by "Client.install_path".
    """
    self.StopPreviousService()

    executable_directory = os.path.dirname(sys.executable)
    install_path = config_lib.CONFIG["Client.install_path"]
    logging.info("Installing binaries %s -> %s", executable_directory,
                 config_lib.CONFIG["Client.install_path"])

    try:
      shutil.rmtree(install_path)
    except OSError:
      pass

    # Create the installation directory.
    try:
      os.makedirs(install_path)
    except OSError:
      pass

    # Recursively copy the temp directory to the installation directory.
    for root, dirs, files in os.walk(executable_directory):
      for name in dirs:
        src_path = os.path.join(root, name)
        relative_path = os.path.relpath(src_path, executable_directory)
        dest_path = os.path.join(install_path, relative_path)

        try:
          os.mkdir(dest_path)
        except OSError:
          pass

      for name in files:
        src_path = os.path.join(root, name)
        relative_path = os.path.relpath(src_path, executable_directory)
        dest_path = os.path.join(install_path, relative_path)

        shutil.copy(src_path, dest_path)


class WindowsInstaller(installer.Installer):
  """Install the windows client binary."""

  pre = ["CopyToSystemDir", "UpdateClients"]

  # These options will be copied to the registry to configure the nanny service.
  nanny_options = ("Nanny.child_binary",
                   "Nanny.child_command_line",
                   "Nanny.service_name",
                   "Nanny.service_description",)

  def InstallNanny(self):
    """Install the nanny program."""
    # We need to copy the nanny sections to the registry to ensure the
    # service is correctly configured.
    new_config = config_lib.CONFIG.MakeNewConfig()
    new_config.SetWriteBack(config_lib.CONFIG["Config.writeback"])

    for option in self.nanny_options:
      new_config.Set(option, config_lib.CONFIG.Get(option))

    new_config.Write()

    args = [config_lib.CONFIG["Nanny.binary"], "--service_key",
            config_lib.CONFIG["Nanny.service_key"], "install"]

    logging.debug("Calling %s", (args,))
    output = subprocess.check_output(args,
                                     shell=True,
                                     stdin=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
    logging.debug("%s", output)

  def Run(self):
    self.InstallNanny()


class UpdateClients(installer.Installer):
  """Copy configuration from old clients."""

  def Run(self):
    try:
      new_config = config_lib.CONFIG.MakeNewConfig()
      new_config.SetWriteBack(config_lib.CONFIG["Config.writeback"])

      for mapping in config_lib.CONFIG["Installer.old_key_map"]:
        try:
          src, parameter_name = mapping.split("->")
          src_components = re.split(r"[/\\]", src.strip())
          parameter_name = parameter_name.strip()

          key_name = "\\".join(src_components[1:-1])
          value_name = src_components[-1]
          key = _winreg.CreateKeyEx(
              getattr(_winreg, src_components[0]), key_name, 0,
              _winreg.KEY_ALL_ACCESS)

          value, _ = _winreg.QueryValueEx(key, value_name)

          new_config.SetRaw(parameter_name, utils.SmartStr(value))

          _winreg.DeleteValue(key, value_name)

          logging.info("Migrated old parameter %s", src)
        except (OSError, AttributeError, IndexError, ValueError) as e:
          logging.debug("mapping %s ignored: %s", mapping, e)
    finally:
      new_config.Write()
