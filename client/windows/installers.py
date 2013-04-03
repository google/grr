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
import ctypes
import os
import re
import shutil
import subprocess
import sys
import time
import _winreg

import logging

from grr.client import installer
from grr.lib import config_lib
from grr.lib import utils


config_lib.DEFINE_string(
    name="Client.install_path",
    default=r"%(SystemRoot|env)\\System32\\%(name)\\%(version_string)",
    help="Where the client binaries are installed.")

config_lib.DEFINE_list(
    "ClientBuildWindows.old_key_map", [
        "HKEY_LOCAL_MACHINE\\Software\\GRR\\certificate->Client.private_key",
        "HKEY_LOCAL_MACHINE\\Software\\GRR\\server_serial_number"
        "->Client.server_serial_number",
        ],
    """
A mapping of old registry values which will be copied to new values. The old
value location must start with a valid hive name, followed by a key name, and
end with the value name. The source location must be separated from the new
parameter name by a -> symbol.

For example:

  HKEY_LOCAL_MACHINE\\Software\\GRR\\certificate -> Client.certificate
""")


class CheckForWow64(installer.Installer):
  """Check to ensure we are not running on a Wow64 system."""

  def RunOnce(self):
    i = ctypes.c_int()
    kernel32 = ctypes.windll.kernel32
    process = kernel32.GetCurrentProcess()

    if kernel32.IsWow64Process(process, ctypes.byref(i)):
      raise RuntimeError("Will not install a 32 bit client on a 64 bit system. "
                         "Please use the correct client.")


class CopyToSystemDir(installer.Installer):
  """Copy the distribution from the temp directory to the target."""

  pre = ["CheckForWow64"]

  def StopPreviousService(self):
    """Wait until the service can be stopped."""
    service = config_lib.CONFIG["NannyWindows.service_name"]
    try:
      logging.info("Attempting to stop service %s", service)
      output = subprocess.check_output(["sc", "stop", service],
                                       shell=True,
                                       stdin=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

      logging.debug("%s", output)

      for _ in range(20):
        try:
          output = subprocess.check_output(["sc", "query", service],
                                           shell=True,
                                           stdin=subprocess.PIPE,
                                           stderr=subprocess.PIPE)

          logging.debug(output)
          if "STOPPED" in output:
            break
        except subprocess.CalledProcessError as e:
          pass

        time.sleep(1)

    except subprocess.CalledProcessError as e:
      # Hopefully we can keep going here.
      logging.info("Failed to call sc: %s. Maybe the service does not "
                   "exist yet.", e)

      # Try to kill  the processes forcefully.
      subprocess.call(["taskkill", "/im", "%s*" %
                       config_lib.CONFIG["NannyWindows.service_binary_name"],
                       "/f"],
                      shell=True,
                      stdout=subprocess.PIPE,
                      stdin=subprocess.PIPE,
                      stderr=subprocess.PIPE)

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

  # These sections will be copied.
  sections_to_copy = ["CA", "Client", "NannyWindows", "Logging"]

  def CopyConfigToRegistry(self):
    """Copy the configuration into the registry key.

    Copy the config specified in the --config flag over to the
    system registry.
    """
    config_url = config_lib.CONFIG["Client.config"]
    new_config = config_lib.GrrConfigManager()
    new_config.Initialize(filename=config_url)

    logging.info("Copying new configuration to %s", config_url)

    for section, data in config_lib.CONFIG.raw_data.items():
      # Skip those sections which are not relevant to the client.
      if section not in self.sections_to_copy:
        continue

      for key, value in data.items():
        if "." in key: continue

        # This writes the fully interpolated values to the new
        # configuration file.
        parameter = "%s.%s" % (section, key)

        # Get the value and encode it appropriately.
        value = config_lib.CONFIG.Get(parameter, verify=False, environ=False)
        new_config.Set(parameter, value, verify=False)

    new_config.Write()

  def InstallNanny(self):
    """Install the nanny program."""
    args = [config_lib.CONFIG["NannyWindows.nanny_binary"],
            "--service_key",
            config_lib.CONFIG["NannyWindows.service_key"],
            "install"]

    logging.debug("Calling %s", (args,))
    subprocess.call(args,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.PIPE)

  def Run(self):
    self.CopyConfigToRegistry()
    self.InstallNanny()


class UpdateClients(installer.Installer):
  """Copy configuration from old clients."""

  def Run(self):
    for mapping in config_lib.CONFIG["ClientBuildWindows.old_key_map"]:
      try:
        src, parameter_name = mapping.split("->")
        src_components = re.split(r"[/\\]", src.strip())
        parameter_name = parameter_name.strip()

        key_name = "\\".join(src_components[1:-1])
        value_name = src_components[-1]

        key = _winreg.CreateKeyEx(getattr(_winreg, src_components[0]),
                                  key_name, 0,
                                  _winreg.KEY_ALL_ACCESS)

        value, _ = _winreg.QueryValueEx(key, value_name)

        config_lib.CONFIG.SetRaw(
            parameter_name, utils.SmartStr(value))

        _winreg.DeleteValue(key, value_name)

        logging.info("Migrated old parameter %s", src)
      except (OSError, AttributeError, IndexError, ValueError) as e:
        logging.debug("mapping %s ignored: %s", mapping, e)
