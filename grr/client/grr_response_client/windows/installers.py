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
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import errno
import logging
import os
import shutil
import subprocess
import sys
import time

import _winreg
from builtins import range  # pylint: disable=redefined-builtin
import pywintypes
import win32process
import win32service
import win32serviceutil
import winerror

from grr_response_client import installer
from grr_response_core import config


def StartService(service_name):
  """Start a Windows service with the given name.

  Args:
    service_name: string The name of the service to be started.
  """
  try:
    win32serviceutil.StartService(service_name)
    logging.info("Service '%s' started.", service_name)
  except pywintypes.error as e:
    if getattr(e, "winerror", None) == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
      logging.debug("Tried to start '%s', but the service is not installed.",
                    service_name)
    else:
      logging.exception("Encountered error trying to start '%s':", service_name)


def StopService(service_name, service_binary_name=None):
  """Stop a Windows service with the given name.

  Args:
    service_name: string The name of the service to be stopped.
    service_binary_name: string If given, also kill this binary as a best effort
        fallback solution.
  """
  # QueryServiceStatus returns: scvType, svcState, svcControls, err,
  # svcErr, svcCP, svcWH
  try:
    status = win32serviceutil.QueryServiceStatus(service_name)[1]
  except pywintypes.error as e:
    if getattr(e, "winerror", None) == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
      logging.debug("Tried to stop '%s', but the service is not installed.",
                    service_name)
    else:
      logging.exception("Unable to query status of service '%s':", service_name)
    return

  for _ in range(20):
    if status == win32service.SERVICE_STOPPED:
      break
    elif status != win32service.SERVICE_STOP_PENDING:
      try:
        win32serviceutil.StopService(service_name)
      except pywintypes.error:
        logging.exception("Unable to stop service '%s':", service_name)
    time.sleep(1)
    status = win32serviceutil.QueryServiceStatus(service_name)[1]

  if status == win32service.SERVICE_STOPPED:
    logging.info("Service '%s' stopped.", service_name)
    return
  elif not service_binary_name:
    return

  # Taskkill will fail on systems predating Windows XP, this is a best
  # effort fallback solution.
  output = subprocess.check_output(
      ["taskkill", "/im", "%s*" % service_binary_name, "/f"],
      shell=True,
      stdin=subprocess.PIPE,
      stderr=subprocess.PIPE)

  logging.debug("%s", output)

  # Sleep a bit to ensure that process really quits.
  time.sleep(2)


def RemoveService(service_name):
  try:
    win32serviceutil.RemoveService(service_name)
    logging.info("Service '%s' removed.", service_name)
  except pywintypes.error as e:
    if getattr(e, "winerror", None) == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
      logging.debug("Tried to remove '%s', but the service is not installed.",
                    service_name)
    else:
      logging.exception("Unable to remove service '%s':", service_name)


def OpenRegkey(key_path):
  # Note that this function will create the specified registry key,
  # along with all its ancestors if they do not exist.
  hive_name, subpath = key_path.split("\\", 1)
  hive = getattr(_winreg, hive_name)
  return _winreg.CreateKey(hive, subpath)


class CheckForWow64(installer.Installer):
  """Check to ensure we are not running on a Wow64 system."""

  def RunOnce(self):
    if win32process.IsWow64Process():
      raise RuntimeError("Will not install a 32 bit client on a 64 bit system. "
                         "Please use the correct client.")


class CopyToSystemDir(installer.Installer):
  """Copy the distribution from the temp directory to the target."""

  pre = [CheckForWow64]

  def StopPreviousService(self):
    """Stops the Windows service hosting the GRR process."""
    StopService(
        service_name=config.CONFIG["Nanny.service_name"],
        service_binary_name=config.CONFIG["Nanny.service_binary_name"])

    if not config.CONFIG["Client.fleetspeak_enabled"]:
      return

    StopService(service_name=config.CONFIG["Client.fleetspeak_service_name"])

    # Delete GRR's Fleetspeak config from the registry so Fleetspeak
    # doesn't try to restart GRR unless/until installation completes
    # successfully.
    key_path = config.CONFIG["Client.fleetspeak_unsigned_services_regkey"]
    regkey = OpenRegkey(key_path)
    try:
      _winreg.DeleteValue(regkey, config.CONFIG["Client.name"])
      logging.info("Deleted value '%s' of key '%s'.",
                   config.CONFIG["Client.name"], key_path)
    except OSError as e:
      # Windows will raise a no-such-file-or-directory error if
      # GRR's config hasn't been written to the registry yet.
      if e.errno != errno.ENOENT:
        raise

  def RunOnce(self):
    """Copy the binaries from the temporary unpack location.

    We need to first stop the running service or we might not be able to write
    on the binary. We then copy the entire directory where we are running from
    into the location indicated by "Client.install_path".
    """
    self.StopPreviousService()

    executable_directory = os.path.dirname(sys.executable)
    install_path = config.CONFIG["Client.install_path"]
    logging.info("Installing binaries %s -> %s", executable_directory,
                 config.CONFIG["Client.install_path"])
    if os.path.exists(install_path):
      attempts = 0
      while True:
        try:
          shutil.rmtree(install_path)
          break
        except OSError as e:
          attempts += 1
          if e.errno == errno.EACCES and attempts < 10:
            # The currently installed GRR process may stick around for a few
            # seconds after the service is terminated (keeping the contents of
            # the installation directory locked).
            logging.warn(
                "Encountered permission-denied error while trying to empty out "
                "'%s'. Retrying...", install_path)
            time.sleep(3)
          else:
            raise e
    os.makedirs(install_path)

    # Recursively copy the temp directory to the installation directory.
    for root, dirs, files in os.walk(executable_directory):
      for name in dirs:
        src_path = os.path.join(root, name)
        relative_path = os.path.relpath(src_path, executable_directory)
        dest_path = os.path.join(install_path, relative_path)

        try:
          os.mkdir(dest_path)
        except OSError as e:
          # Ignore already-exists exceptions.
          if e.errno != errno.EEXIST:
            raise

      for name in files:
        src_path = os.path.join(root, name)
        relative_path = os.path.relpath(src_path, executable_directory)
        dest_path = os.path.join(install_path, relative_path)

        shutil.copy(src_path, dest_path)


class WindowsInstaller(installer.Installer):
  """Install the windows client binary."""

  pre = [CopyToSystemDir]

  # These options will be copied to the registry to configure the nanny service.
  nanny_options = (
      "Nanny.child_binary",
      "Nanny.child_command_line",
      "Nanny.service_name",
      "Nanny.service_description",
  )

  def InstallNanny(self):
    """Install the nanny program."""
    # We need to copy the nanny sections to the registry to ensure the
    # service is correctly configured.
    new_config = config.CONFIG.MakeNewConfig()
    new_config.SetWriteBack(config.CONFIG["Config.writeback"])

    for option in self.nanny_options:
      new_config.Set(option, config.CONFIG.Get(option))

    new_config.Write()

    args = [
        config.CONFIG["Nanny.binary"], "--service_key",
        config.CONFIG["Client.config_key"], "install"
    ]

    logging.debug("Calling %s", (args,))
    output = subprocess.check_output(
        args, shell=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    logging.debug("%s", output)

  def Run(self):
    if not config.CONFIG["Client.fleetspeak_enabled"]:
      self.InstallNanny()
      return

    # Remove the Nanny service for the legacy GRR since it will
    # not be needed any more.
    RemoveService(config.CONFIG["Nanny.service_name"])

    # Write the Fleetspeak config to the registry.
    key_path = config.CONFIG["Client.fleetspeak_unsigned_services_regkey"]
    regkey = OpenRegkey(key_path)
    fleetspeak_unsigned_config_path = os.path.join(
        config.CONFIG["Client.install_path"],
        config.CONFIG["Client.fleetspeak_unsigned_config_fname"])
    _winreg.SetValueEx(regkey, config.CONFIG["Client.name"], 0, _winreg.REG_SZ,
                       fleetspeak_unsigned_config_path)

    fs_service = config.CONFIG["Client.fleetspeak_service_name"]
    StopService(service_name=fs_service)
    StartService(service_name=fs_service)
