#!/usr/bin/env python
# Lint as: python3
"""Helper script for running end-to-end tests."""

import sys

from absl import app
from absl import flags
import psutil

from grr_response_test.lib import api_helpers
from grr_response_test.lib import self_contained_components


flags.DEFINE_list(
    "tests", [],
    "(Optional) comma-separated list of tests to run (skipping all others). "
    "If this flag is not specified, all tests available for the platform "
    "will run.")

flags.DEFINE_list(
    "manual_tests", [],
    "A comma-separated list of extra tests to run (such tests are not run by "
    "default and have to be manually enabled with this flag).")

flags.DEFINE_boolean(
    "with_fleetspeak",
    default=False,
    help="Assume Fleetspeak is present on the system and use it.")

flags.DEFINE_string("mysql_database", "grr_test_db",
                    "MySQL database name to use for GRR.")

flags.DEFINE_string("fleetspeak_mysql_database", "fleetspeak_test_db",
                    "MySQL database name to use for Fleetspeak.")

flags.DEFINE_string("mysql_username", None, "MySQL username to use.")

flags.DEFINE_string("mysql_password", None, "MySQL password to use.")

flags.DEFINE_string("logging_path", None,
                    "Base logging path for server components to use.")

flags.DEFINE_string(
    name="osquery_path",
    default="",
    help="A path to the osquery executable.",
)


def main(argv):
  del argv  # Unused.

  if flags.FLAGS.mysql_username is None:
    raise ValueError("--mysql_username has to be specified.")

  # Generate server and client configs.
  grr_configs = self_contained_components.InitGRRConfigs(
      flags.FLAGS.mysql_database,
      mysql_username=flags.FLAGS.mysql_username,
      mysql_password=flags.FLAGS.mysql_password,
      logging_path=flags.FLAGS.logging_path,
      osquery_path=flags.FLAGS.osquery_path,
      with_fleetspeak=flags.FLAGS.with_fleetspeak)

  fleetspeak_configs = None
  if flags.FLAGS.with_fleetspeak:
    fleetspeak_configs = self_contained_components.InitFleetspeakConfigs(
        grr_configs,
        flags.FLAGS.fleetspeak_mysql_database,
        mysql_username=flags.FLAGS.mysql_username,
        mysql_password=flags.FLAGS.mysql_password)

  # Start all remaining server components.
  # Start a background thread that kills the main process if one of the
  # server subprocesses dies.
  server_processes = self_contained_components.StartServerProcesses(
      grr_configs=grr_configs, fleetspeak_configs=fleetspeak_configs)
  self_contained_components.DieIfSubProcessDies(server_processes)

  api_port = api_helpers.GetAdminUIPortFromConfig(grr_configs.server_config)
  grrapi = api_helpers.WaitForAPIEndpoint(api_port)

  # Start the client.
  preliminary_client_p = self_contained_components.StartClientProcess(
      grr_configs=grr_configs, fleetspeak_configs=fleetspeak_configs)

  # Wait for the client to enroll and get its id.
  client_id = api_helpers.WaitForClientToEnroll(grrapi)
  print("Found client id: %s" % client_id)

  # Python doesn't guarantee the process name of processes started by the Python
  # interpreter. They may vary from platform to platform. In order to ensure
  # that Client.binary_name config setting matches the actual process name,
  # let's get the name via psutil, kill the client and set the
  # Config.binary_name explicitly.
  client_binary_name = str(psutil.Process(preliminary_client_p.pid).name())
  preliminary_client_p.kill()
  preliminary_client_p.wait()

  # Simply add the Client.binary_name to the client's configuration YAML.
  with open(grr_configs.client_config, mode="a", encoding="utf-8") as fd:
    fd.write("\nClient.binary_name: %s\n" % client_binary_name)

  print("Starting the client with Client.binary_name=%s" % client_binary_name)
  client_p = self_contained_components.StartClientProcess(
      grr_configs=grr_configs, fleetspeak_configs=fleetspeak_configs)
  # Start a background thread that kills the main process if
  # client subprocess dies.
  self_contained_components.DieIfSubProcessDies([client_p])

  # Run the test suite against the enrolled client.
  self_contained_components.RunEndToEndTests(
      client_id,
      grr_configs.server_config,
      tests=flags.FLAGS.tests,
      manual_tests=flags.FLAGS.manual_tests)

  print("RunEndToEndTests execution succeeded.")
  sys.exit(0)


if __name__ == "__main__":
  app.run(main)
