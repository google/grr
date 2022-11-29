#!/usr/bin/env python
"""Helper script for running end-to-end tests."""

import logging
import platform
import subprocess
import sys

from typing import Sequence

from absl import app
from absl import flags

import distro

from grr_api_client import errors
from grr_response_test.lib import api_helpers
from grr_response_test.lib import self_contained_components

_MYSQL_DATABASE = flags.DEFINE_string("mysql_database", "grr_test_db",
                                      "MySQL database name to use.")

_MYSQL_USERNAME = flags.DEFINE_string("mysql_username", None,
                                      "MySQL username to use.")

_MYSQL_PASSWORD = flags.DEFINE_string("mysql_password", None,
                                      "MySQL password to use.")

_LOGGING_PATH = flags.DEFINE_string(
    "logging_path", None, "Base logging path for server components to use.")

_HIGHEST_VERSION_INI = """
[Version]
major = 9
minor = 9
revision = 9
release = 9
packageversion = %(major)s.%(minor)s.%(revision)spost%(release)s
packagedepends = %(packageversion)s
"""


def _check_call_print_output(cmd: Sequence[str]):
  try:
    return subprocess.check_output(cmd)
  except subprocess.CalledProcessError as e:
    logging.info(e.stdout)
    logging.error(e.stderr)
    raise


def main(argv):
  del argv  # Unused.

  if _MYSQL_USERNAME.value is None:
    raise ValueError("--mysql_username has to be specified.")

  # Generate server and client configs.
  grr_configs = self_contained_components.InitGRRConfigs(
      _MYSQL_DATABASE.value,
      mysql_username=_MYSQL_USERNAME.value,
      mysql_password=_MYSQL_PASSWORD.value,
      logging_path=_LOGGING_PATH.value)

  print("Building the template.")
  template_path = self_contained_components.RunBuildTemplate(
      grr_configs.server_config, component_options={"Logging.verbose": True})

  print("Repack %s." % template_path)
  installer_path = self_contained_components.RunRepackTemplate(
      grr_configs.server_config, template_path)

  version_overrides = {
      "Source.version_major": 9,
      "Source.version_minor": 9,
      "Source.version_revision": 9,
      "Source.version_release": 9,
      "Source.version_string": "9.9.9.9",
      "Source.version_numeric": 9999,
      "Template.version_major": 9,
      "Template.version_minor": 9,
      "Template.version_revision": 9,
      "Template.version_release": 9,
      "Template.version_string": "9.9.9.9",
      "Template.version_numeric": 9999,
  }

  print("Building next ver. template.")
  next_ver_template_path = self_contained_components.RunBuildTemplate(
      grr_configs.server_config,
      component_options=version_overrides,
      version_ini=_HIGHEST_VERSION_INI)

  print("Repack next ver. %s." % template_path)
  next_ver_installer_path = self_contained_components.RunRepackTemplate(
      grr_configs.server_config,
      next_ver_template_path,
      component_options=version_overrides)

  print("First installer ready: %s. Next ver. installer ready: %s." %
        (installer_path, next_ver_installer_path))

  print("Starting the server.")
  # Start all remaining server components.
  # Start a background thread that kills the main process if one of the
  # server subprocesses dies.
  server_processes = self_contained_components.StartServerProcesses(grr_configs)
  self_contained_components.DieIfSubProcessDies(server_processes)

  api_port = api_helpers.GetAdminUIPortFromConfig(grr_configs.server_config)
  grrapi = api_helpers.WaitForAPIEndpoint(api_port)

  print("Installing the client.")
  system = platform.system().lower()
  if system == "linux":
    distro_id = distro.id()
    if distro_id in ["ubuntu", "debian"]:
      _check_call_print_output(
          ["apt", "install", "--reinstall", "-y", installer_path])
    elif distro_id in ["centos", "rhel", "fedora"]:
      _check_call_print_output(["rpm", "-Uvh", installer_path])
    else:
      raise RuntimeError("Unsupported linux distro: %s" % distro_id)
  elif system == "windows":
    _check_call_print_output([installer_path])
  elif system == "darwin":
    _check_call_print_output(
        ["installer", "-verbose", "-pkg", installer_path, "-target", "/"])
  else:
    raise RuntimeError("Unsupported platform for self-update tests: %s" %
                       system)

  # Wait for the client to enroll and get its id.
  client_id = api_helpers.WaitForClientToEnroll(grrapi)
  print("Found client id: %s" % client_id)

  print("Waiting for the client to report the initial version.")
  prev_version = api_helpers.WaitForClientVersionGreaterThan(
      grrapi.Client(client_id), 0)

  binary_id = self_contained_components.RunUploadExe(grr_configs.server_config,
                                                     next_ver_installer_path,
                                                     system)

  args = grrapi.types.CreateFlowArgs(flow_name="UpdateClient")
  args.binary_path = binary_id
  f = grrapi.Client(client_id).CreateFlow(name="UpdateClient", args=args)
  try:
    # Timeout has to be rather significant, since at the moment installers
    # are uploaded in chunks of 512Kb, each chunk requiring a round-trip
    # to/from the client.
    f.WaitUntilDone(timeout=180)
    print("Update flow finished successfully. This should never happen: "
          "the client should have been restarted.")
    sys.exit(-1)
  except errors.PollTimeoutError:
    print("Update flow timed out. This shouldn't happen: the flow should "
          "fail explicitly due to a client restart.")
    sys.exit(-1)
  except errors.FlowFailedError:
    print("Update flow failed (expected behavior, as the client got "
          "restarted).")

  print("Update flow details:")
  print(f.Get().data)

  print("Waiting for the client to report the updated version.")
  api_helpers.WaitForClientVersionGreaterThan(
      grrapi.Client(client_id), prev_version)

  print("Self-update test successful!")

  sys.exit(0)


if __name__ == "__main__":
  app.run(main)
