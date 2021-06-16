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

import contextlib
import datetime
import errno
import itertools
import logging
import os
import shutil
import subprocess
import sys
import time
from typing import Callable, Iterable
from absl import flags
import pywintypes
import win32process
import win32service
import win32serviceutil
import winerror
import winreg

from grr_response_client.windows import regconfig
from grr_response_core import config


SERVICE_RESTART_DELAY_MSEC = 120 * 1000
SERVICE_RESET_FAIL_COUNT_DELAY_SEC = 86400


flags.DEFINE_string(
    "interpolate_fleetspeak_service_config", "",
    "If set, only interpolate a fleetspeak service config. "
    "The value is a path to a file to interpolate (rewrite).")


def _StartService(service_name):
  """Starts a Windows service with the given name.

  Args:
    service_name: string The name of the service to be started.
  """
  logging.info("Trying to start service %s.", service_name)
  try:
    win32serviceutil.StartService(service_name)
    logging.info("Service '%s' started.", service_name)
  except pywintypes.error as e:
    if getattr(e, "winerror", None) == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
      logging.debug("Tried to start '%s', but the service is not installed.",
                    service_name)
    else:
      logging.exception("Encountered error trying to start '%s':", service_name)


def _StartServices(service_names: Iterable[str]) -> None:
  for service_name in service_names:
    _StartService(service_name)


STOPPED_SERVICES = []


def _StopService(service_name, service_binary_name=None):
  """Stops a Windows service with the given name.

  Args:
    service_name: string The name of the service to be stopped.
    service_binary_name: string If given, also kill this binary as a best effort
      fallback solution.
  """
  logging.info("Trying to stop service %s.", service_name)
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
        STOPPED_SERVICES.append(service_name)
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


def _RemoveService(service_name):
  """Removes the service `service_name`."""
  logging.info("Trying to remove service %s.", service_name)
  try:
    win32serviceutil.RemoveService(service_name)
    logging.info("Service '%s' removed.", service_name)
  except pywintypes.error as e:
    if getattr(e, "winerror", None) == winerror.ERROR_SERVICE_DOES_NOT_EXIST:
      logging.debug("Tried to remove '%s', but the service is not installed.",
                    service_name)
    else:
      logging.exception("Unable to remove service '%s':", service_name)


def _CreateService(service_name: str, description: str,
                   command_line: str) -> None:
  """Creates a Windows service."""
  logging.info("Creating service '%s'.", service_name)

  with contextlib.ExitStack() as stack:
    hscm = win32service.OpenSCManager(None, None,
                                      win32service.SC_MANAGER_ALL_ACCESS)
    stack.callback(win32service.CloseServiceHandle, hscm)
    hs = win32service.CreateService(hscm, service_name, service_name,
                                    win32service.SERVICE_ALL_ACCESS,
                                    win32service.SERVICE_WIN32_OWN_PROCESS,
                                    win32service.SERVICE_AUTO_START,
                                    win32service.SERVICE_ERROR_NORMAL,
                                    command_line, None, 0, None, None, None)
    stack.callback(win32service.CloseServiceHandle, hs)
    service_failure_actions = {
        "ResetPeriod":
            SERVICE_RESET_FAIL_COUNT_DELAY_SEC,
        "RebootMsg":
            u"",
        "Command":
            u"",
        "Actions": [
            (win32service.SC_ACTION_RESTART, SERVICE_RESTART_DELAY_MSEC),
            (win32service.SC_ACTION_RESTART, SERVICE_RESTART_DELAY_MSEC),
            (win32service.SC_ACTION_RESTART, SERVICE_RESTART_DELAY_MSEC),
        ]
    }
    win32service.ChangeServiceConfig2(
        hs, win32service.SERVICE_CONFIG_FAILURE_ACTIONS,
        service_failure_actions)
    win32service.ChangeServiceConfig2(hs,
                                      win32service.SERVICE_CONFIG_DESCRIPTION,
                                      description)
  logging.info("Successfully created service '%s'.", service_name)


def _OpenRegkey(key_path):
  # Note that this function will create the specified registry key,
  # along with all its ancestors if they do not exist.
  hive_name, subpath = key_path.split("\\", 1)
  hive = getattr(winreg, hive_name)
  return winreg.CreateKey(hive, subpath)


def _CheckForWow64():
  """Checks to ensure we are not running on a Wow64 system."""
  if win32process.IsWow64Process():
    raise RuntimeError("Will not install a 32 bit client on a 64 bit system. "
                       "Please use the correct client.")


def _StopPreviousService():
  """Stops the Windows service hosting the GRR process."""
  _StopService(
      service_name=config.CONFIG["Nanny.service_name"],
      service_binary_name=config.CONFIG["Nanny.service_binary_name"])

  if not config.CONFIG["Client.fleetspeak_enabled"]:
    return

  _StopService(service_name=config.CONFIG["Client.fleetspeak_service_name"])


def _DeleteGrrFleetspeakService():
  """Deletes GRR's fleetspeak service entry from the registry."""
  # Delete GRR's Fleetspeak config from the registry so Fleetspeak
  # doesn't try to restart GRR unless/until installation completes
  # successfully.
  key_path = config.CONFIG["Client.fleetspeak_unsigned_services_regkey"]
  regkey = _OpenRegkey(key_path)
  try:
    winreg.DeleteValue(regkey, config.CONFIG["Client.name"])
    logging.info("Deleted value '%s' of key '%s'.",
                 config.CONFIG["Client.name"], key_path)
  except OSError as e:
    # Windows will raise a no-such-file-or-directory error if
    # GRR's config hasn't been written to the registry yet.
    if e.errno != errno.ENOENT:
      raise


def _FileRetryLoop(path: str, f: Callable[[], None]) -> None:
  """If `path` exists, calls `f` in a retry loop."""
  if not os.path.exists(path):
    return
  attempts = 0
  while True:
    try:
      f()
      return
    except OSError as e:
      attempts += 1
      if e.errno == errno.EACCES and attempts < 10:
        # The currently installed GRR process may stick around for a few
        # seconds after the service is terminated (keeping the contents of
        # the installation directory locked).
        logging.warning(
            "Encountered permission-denied error while trying to process "
            "'%s'. Retrying...",
            path,
            exc_info=True)
        time.sleep(3)
      else:
        raise


def _RmTree(path: str) -> None:
  _FileRetryLoop(path, lambda: shutil.rmtree(path))


def _Rename(src: str, dst: str) -> None:
  _FileRetryLoop(src, lambda: os.rename(src, dst))


def _RmTreePseudoTransactional(path: str) -> None:
  """Removes `path`.

  Makes sure that either `path` is gone or that it is still present as
  it was.

  Args:
    path: The path to remove.
  """
  suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
  temp_path = f"{path}_orphaned_{suffix}"
  logging.info("Trying to rename %s -> %s.", path, temp_path)

  # Assuming there was a `path`:
  # _Rename succeeds -> `path` is gone, we can proceed with the install.
  # _Rename fails -> we know that we still have `path` as it was.

  _Rename(path, temp_path)

  try:
    logging.info("Trying to remove %s.", temp_path)
    _RmTree(temp_path)
  except:  # pylint: disable=bare-except
    logging.warning("Failed to remove %s. Ignoring.", temp_path, exc_info=True)


def _IsReinstall() -> bool:
  result = os.path.exists(config.CONFIG["Client.install_path"])
  logging.info("Checking if this is a re-install: %s.", result)
  return result


def _ClearInstallPath() -> None:
  install_path = config.CONFIG["Client.install_path"]
  logging.info("Clearing install path %s.", install_path)
  _RmTreePseudoTransactional(install_path)
  os.makedirs(install_path)


def _CopyToSystemDir():
  """Copies the binaries from the temporary unpack location.

  This requires running services to be stopped or we might not be able to write
  on the binary. We then copy the entire directory where we are running from
  into the location indicated by "Client.install_path".
  """
  executable_directory = os.path.dirname(sys.executable)
  install_path = config.CONFIG["Client.install_path"]
  logging.info("Installing binaries %s -> %s", executable_directory,
               config.CONFIG["Client.install_path"])

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


# These options will be copied to the registry to configure the nanny service.
_NANNY_OPTIONS = frozenset([
    "Nanny.child_binary",
    "Nanny.child_command_line",
    "Nanny.service_name",
    "Nanny.service_description",
])

# Options for the legacy (non-Fleetspeak) GRR installation that should get
# deleted when installing Fleetspeak-enabled GRR clients.
_LEGACY_OPTIONS = frozenset(
    itertools.chain(_NANNY_OPTIONS,
                    ["Nanny.status", "Nanny.heartbeat", "Client.labels"]))


def _InstallNanny():
  """Installs the nanny program."""
  # We need to copy the nanny sections to the registry to ensure the
  # service is correctly configured.
  new_config = config.CONFIG.MakeNewConfig()
  new_config.SetWriteBack(config.CONFIG["Config.writeback"])

  for option in _NANNY_OPTIONS:
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


def _DeleteLegacyConfigOptions(registry_key_uri):
  """Deletes config values in the registry for legacy GRR installations."""
  key_spec = regconfig.ParseRegistryURI(registry_key_uri)
  try:
    regkey = winreg.OpenKeyEx(key_spec.winreg_hive, key_spec.path, 0,
                              winreg.KEY_ALL_ACCESS)
  except OSError as e:
    if e.errno == errno.ENOENT:
      logging.info("Skipping legacy config purge for non-existent key: %s.",
                   registry_key_uri)
      return
    else:
      raise
  for option in _LEGACY_OPTIONS:
    try:
      winreg.DeleteValue(regkey, option)
      logging.info("Deleted value '%s' of key %s.", option, key_spec)
    except OSError as e:
      # Windows will raise a no-such-file-or-directory error if the config
      # option does not exist in the registry. This is expected when upgrading
      # to a newer Fleetspeak-enabled version.
      if e.errno != errno.ENOENT:
        raise


def _IsFleetspeakBundled():
  return os.path.exists(
      os.path.join(config.CONFIG["Client.install_path"],
                   "fleetspeak-client.exe"))


def _InstallBundledFleetspeak():
  fleetspeak_client = os.path.join(config.CONFIG["Client.install_path"],
                                   "fleetspeak-client.exe")
  fleetspeak_config = os.path.join(config.CONFIG["Client.install_path"],
                                   "fleetspeak-client.config")
  _RemoveService(config.CONFIG["Client.fleetspeak_service_name"])
  _CreateService(
      service_name=config.CONFIG["Client.fleetspeak_service_name"],
      description="Fleetspeak communication agent.",
      command_line=f"\"{fleetspeak_client}\" -config \"{fleetspeak_config}\"")


def _MaybeInterpolateFleetspeakServiceConfig():
  """Interpolates the fleetspeak service config if present."""
  fleetspeak_unsigned_config_path = os.path.join(
      config.CONFIG["Client.install_path"],
      config.CONFIG["Client.fleetspeak_unsigned_config_fname"])
  template_path = f"{fleetspeak_unsigned_config_path}.in"
  if not os.path.exists(template_path):
    return
  _InterpolateFleetspeakServiceConfig(template_path,
                                      fleetspeak_unsigned_config_path)


def _InterpolateFleetspeakServiceConfig(src_path: str, dst_path: str) -> None:
  with open(src_path, "r") as src:
    src_data = src.read()
  with open(dst_path, "w") as dst:
    interpolated = config.CONFIG.InterpolateValue(src_data)
    interpolated = interpolated.replace("\\", "\\\\")
    interpolated = interpolated.rstrip("\n")
    dst.write(interpolated)


def _WriteGrrFleetspeakService():
  logging.info("Writing GRR fleetspeak service registry key.")
  # Write the Fleetspeak config to the registry.
  key_path = config.CONFIG["Client.fleetspeak_unsigned_services_regkey"]
  regkey = _OpenRegkey(key_path)
  fleetspeak_unsigned_config_path = os.path.join(
      config.CONFIG["Client.install_path"],
      config.CONFIG["Client.fleetspeak_unsigned_config_fname"])
  winreg.SetValueEx(regkey, config.CONFIG["Client.name"], 0, winreg.REG_SZ,
                    fleetspeak_unsigned_config_path)


def _Run():
  """Installs the windows client binary."""

  if flags.FLAGS.interpolate_fleetspeak_service_config:
    _InterpolateFleetspeakServiceConfig(
        flags.FLAGS.interpolate_fleetspeak_service_config,
        flags.FLAGS.interpolate_fleetspeak_service_config)
    fs_service = config.CONFIG["Client.fleetspeak_service_name"]
    _StopService(service_name=fs_service)
    _StartService(service_name=fs_service)
    return

  _CheckForWow64()
  is_reinstall = _IsReinstall()
  was_bundled_fleetspeak = _IsFleetspeakBundled() if is_reinstall else False
  _StopPreviousService()
  try:
    _ClearInstallPath()
  except:
    # We've failed to remove and old installation, but it's still there.
    # Bring back the services that we've stopped previously.
    _StartServices(STOPPED_SERVICES)
    raise
  if is_reinstall:
    # If the install path existed before, we have deleted the current, working
    # GRR installation.
    # We have to delete the fleetspeak service entry as well.
    _DeleteGrrFleetspeakService()
    if was_bundled_fleetspeak:
      _RemoveService(config.CONFIG["Client.fleetspeak_service_name"])
    _RemoveService(config.CONFIG["Nanny.service_name"])

  # At this point we have a "clean state".
  # The old installation is not present and not running any more.

  try:
    _CopyToSystemDir()
    _MaybeInterpolateFleetspeakServiceConfig()
  except:
    _StartServices(STOPPED_SERVICES)
    raise

  if not config.CONFIG["Client.fleetspeak_enabled"]:
    logging.info("Fleetspeak not enabled, installing nanny.")
    _InstallNanny()
    return

  # Remove the Nanny service for the legacy GRR since it will
  # not be needed any more.
  _RemoveService(config.CONFIG["Nanny.service_name"])
  _DeleteLegacyConfigOptions(config.CONFIG["Config.writeback"])

  _WriteGrrFleetspeakService()

  fs_service = config.CONFIG["Client.fleetspeak_service_name"]
  _StopService(service_name=fs_service)
  if _IsFleetspeakBundled():
    _InstallBundledFleetspeak()
  _StartService(service_name=fs_service)


def Run():
  try:
    _Run()
  except:
    logging.error("The installer failed with an exception.", exc_info=True)
    raise
