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

from google.protobuf import text_format

from fleetspeak.src.client.daemonservice.proto.fleetspeak_daemonservice import config_pb2 as fs_config_pb2
from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2
from fleetspeak.src.common.proto.fleetspeak import system_pb2 as fs_system_pb2

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

  def GenerateFleetspeakServiceConfig(self):
    """Generate a service config, used to register the GRR client with FS."""
    logging.info("Generating Fleetspeak service config.")

    fs_service_config = fs_system_pb2.ClientServiceConfig(
        name="GRR",
        factory="Daemon",
        required_labels=[
            fs_common_pb2.Label(
                service_name="client",
                label="windows",
            ),
        ],
    )
    daemonservice_config = fs_config_pb2.Config(
        argv=[
            # Note this is an argv list, so we can't use
            # config.CONFIG["Nanny.child_command_line"] directly.
            config.CONFIG["Nanny.child_binary"],
            "--config=%s.yaml" % config.CONFIG["Nanny.child_binary"],
        ],
        memory_limit=2147483648,  # 2GB
        monitor_heartbeats=True,
        heartbeat_unresponsive_grace_period_seconds=600,
        heartbeat_unresponsive_kill_period_seconds=300,
    )
    fs_service_config.config.Pack(daemonservice_config)

    str_fs_service_config = text_format.MessageToString(
        fs_service_config, as_one_line=True)

    return str_fs_service_config

  def WriteFleetspeakServiceConfigToRegistry(self, str_fs_service_config):
    """Register the GRR client to be run by Fleetspeak."""
    logging.info("Writing Fleetspeak service config to registry.")

    regkey = _winreg.CreateKey(
        _winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Fleetspeak\textservices",
    )

    _winreg.SetValueEx(
        regkey,
        config.CONFIG["Client.name"],
        0,
        _winreg.REG_SZ,
        str_fs_service_config,
    )

  def RestartFleetspeakService(self):
    """Restart the Fleetspeak service so that config changes are applied."""
    StopService(service_name=config.CONFIG["Client.fleetspeak_service_name"])
    StartService(service_name=config.CONFIG["Client.fleetspeak_service_name"])

  def Run(self):
    if config.CONFIG["Client.fleetspeak_enabled"]:
      str_fs_service_config = self.GenerateFleetspeakServiceConfig()
      self.WriteFleetspeakServiceConfigToRegistry(str_fs_service_config)

      logging.info(
          "Restarting Fleetspeak service. Note it is OK that this step fails "
          "if Fleetspeak has not been installed yet.")
      self.RestartFleetspeakService()
    else:
      self.InstallNanny()
