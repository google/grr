#!/usr/bin/env python
"""Wrapper for running a fleetspeak server in a virtualenv setup.

This script is meant to be used for development.

Requirements for running this script:

 * Running from a virtualenv.
 * PIP package `fletspeak-server-bin` is installed.
 * `grr_config_updater initialize` has been run.
 * Fleetspeak has been enabled.
"""
import os
import subprocess

from absl import app

from grr_response_core.lib import package


class Error(Exception):
  pass


def main(argv):
  config_dir = package.ResourcePath(
      "fleetspeak-server-bin", "fleetspeak-server-bin/etc/fleetspeak-server")
  if not os.path.exists(config_dir):
    raise Error(
        f"Configuration directory not found: {config_dir}. "
        "Please make sure `grr_config_updater initialize` has been run.")
  fleetspeak_server = package.ResourcePath(
      "fleetspeak-server-bin",
      "fleetspeak-server-bin/usr/bin/fleetspeak-server")
  if not os.path.exists(fleetspeak_server):
    raise Error(
        f"Fleetspeak server binary not found: {fleetspeak_server}. "
        "Please make sure that the package `fleetspeak-server-bin` has been "
        "installed.")
  command = [
      fleetspeak_server,
      "--logtostderr",
      "--services_config",
      os.path.join(config_dir, "server.services.config"),
      "--components_config",
      os.path.join(config_dir, "server.components.config"),
  ]
  subprocess.check_call(command)


if __name__ == "__main__":
  app.run(main)
