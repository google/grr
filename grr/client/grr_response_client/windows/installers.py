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
import errno
import logging
import os
import shutil
import subprocess
import sys
import time
import _winreg
import pywintypes
import win32process
import win32service
import win32serviceutil

from grr import config
from grr_response_client import installer


def StartService(service_name):
  """Start a Windows service with the given name.

  Args:
    service_name: string The name of the service to be stopped.
  """
  logging.info("Starting Windows service %s", service_name)

  try:
    win32serviceutil.StartService(service_name)
  except pywintypes.error as e:
    logging.info("Unable to stop service: %s with error: %s", service_name, e)


def StopService(service_name, service_binary_name=None):
  """Stop a Windows service with the given name.

  Args:
    service_name: string The name of the service to be stopped.
    service_binary_name: string If given, also kill this binary as a best effort
        fallback solution.
  """
  logging.info("Stopping Windows service %s; Binary name: %s", service_name,
               service_binary_name)

  # QueryServiceStatus returns: scvType, svcState, svcControls, err,
  # svcErr, svcCP, svcWH
  try:
    status = win32serviceutil.QueryServiceStatus(service_name)[1]
  except pywintypes.error as e:
    logging.info("Unable to query status of service: %s with error: %s",
                 service_name, e)
    return

  for _ in range(20):
    if status == win32service.SERVICE_STOPPED:
      break
    elif status != win32service.SERVICE_STOP_PENDING:
      logging.info("Attempting to stop service %s", service_name)
      try:
        win32serviceutil.StopService(service_name)
      except pywintypes.error as e:
        logging.info("Unable to stop service: %s with error: %s", service_name,
                     e)
    time.sleep(1)
    status = win32serviceutil.QueryServiceStatus(service_name)[1]

  if status != win32service.SERVICE_STOPPED and service_binary_name is not None:
    # Taskkill will fail on systems predating Windows XP, this is a best
    # effort fallback solution.
    output = subprocess.check_output(
        ["taskkill", "/im",
         "%s*" % service_binary_name, "/f"],
        shell=True,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE)

    logging.debug("%s", output)

    # Sleep a bit to ensure that process really quits.
    time.sleep(2)


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
    """Wait until the service can be stopped."""
    StopService(
        service_name=config.CONFIG["Nanny.service_name"],
        service_binary_name=config.CONFIG["Nanny.service_binary_name"])
    if config.CONFIG["Client.fleetspeak_enabled"]:
      StopService(service_name=config.CONFIG["Client.fleetspeak_service_name"])

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

    fleetspeak_unsigned_config_path = os.path.join(
        executable_directory,
        config.CONFIG["Client.fleetspeak_unsigned_config_fname"])
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
        # The Fleetspeak config will be written to the registry, so
        # no need to copy it to the installation directory.
        if src_path == fleetspeak_unsigned_config_path:
          continue
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

  @classmethod
  def WriteFleetspeakServiceConfigToRegistry(cls):
    """Register the GRR client to be run by Fleetspeak."""
    logging.info("Writing Fleetspeak service config to registry.")

    fleetspeak_unsigned_config_path = os.path.join(
        os.path.dirname(sys.executable),
        config.CONFIG["Client.fleetspeak_unsigned_config_fname"])

    full_key_path = config.CONFIG["Client.fleetspeak_unsigned_services_regkey"]
    hive_name, key_path = full_key_path.split("\\", 1)
    hive = getattr(_winreg, hive_name)
    regkey = _winreg.CreateKey(hive, key_path)

    with open(fleetspeak_unsigned_config_path) as f:
      _winreg.SetValueEx(regkey, config.CONFIG["Client.name"], 0,
                         _winreg.REG_SZ, f.read())

  def RestartFleetspeakService(self):
    """Restart the Fleetspeak service so that config changes are applied."""
    StopService(service_name=config.CONFIG["Client.fleetspeak_service_name"])
    StartService(service_name=config.CONFIG["Client.fleetspeak_service_name"])

  def Run(self):
    if config.CONFIG["Client.fleetspeak_enabled"]:
      self.WriteFleetspeakServiceConfigToRegistry()

      logging.info(
          "Restarting Fleetspeak service. Note it is OK that this step fails "
          "if Fleetspeak has not been installed yet.")
      self.RestartFleetspeakService()
    else:
      self.InstallNanny()
