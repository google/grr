#!/usr/bin/env python
"""Helper script for running end-to-end tests."""

import pathlib
import subprocess
import sys
import tempfile

from absl import app
from absl import flags
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
import psutil

from grr_response_test.lib import api_helpers
from grr_response_test.lib import self_contained_components


ROOT_DIR = (pathlib.Path(__file__).parent / ".." / "..").resolve()

_TESTS = flags.DEFINE_list(
    "tests", [],
    "(Optional) comma-separated list of tests to run (skipping all others). "
    "If this flag is not specified, all tests available for the platform "
    "will run.")

_MANUAL_TESTS = flags.DEFINE_list(
    "manual_tests", [],
    "A comma-separated list of extra tests to run (such tests are not run by "
    "default and have to be manually enabled with this flag).")

_MYSQL_DATABASE = flags.DEFINE_string("mysql_database", "grr_test_db",
                                      "MySQL database name to use for GRR.")

_FLEETSPEAK_MYSQL_DATABASE = flags.DEFINE_string(
    "fleetspeak_mysql_database", "fleetspeak_test_db",
    "MySQL database name to use for Fleetspeak.")

_MYSQL_USERNAME = flags.DEFINE_string("mysql_username", None,
                                      "MySQL username to use.")

_MYSQL_PASSWORD = flags.DEFINE_string("mysql_password", None,
                                      "MySQL password to use.")

_LOGGING_PATH = flags.DEFINE_string(
    "logging_path", None, "Base logging path for server components to use.")

_OSQUERY_PATH = flags.DEFINE_string(
    name="osquery_path",
    default="",
    help="A path to the osquery executable.",
)

_RRG_PATH = flags.DEFINE_string(
    "rrg_path",
    default=None,
    help="A path to the RRG executable.",
)


def main(argv):
  del argv  # Unused.

  if _MYSQL_USERNAME.value is None:
    raise ValueError("--mysql_username has to be specified.")

  command_signing_key = ed25519.Ed25519PrivateKey.generate()
  command_verifying_key = command_signing_key.public_key()

  command_signing_key_file = tempfile.NamedTemporaryFile(delete=False)
  command_signing_key_file.write(
      command_signing_key.private_bytes(
          encoding=serialization.Encoding.Raw,
          format=serialization.PrivateFormat.Raw,
          encryption_algorithm=serialization.NoEncryption(),
      ),
  )
  command_signing_key_file.close()

  command_verifying_key_bytes = command_verifying_key.public_bytes(
      encoding=serialization.Encoding.Raw,
      format=serialization.PublicFormat.Raw,
  )

  # Generate server and client configs.
  grr_configs = self_contained_components.InitGRRConfigs(
      _MYSQL_DATABASE.value,
      mysql_username=_MYSQL_USERNAME.value,
      mysql_password=_MYSQL_PASSWORD.value,
      logging_path=_LOGGING_PATH.value,
      osquery_path=_OSQUERY_PATH.value,
      command_signing_key_path=command_signing_key_file.name,
  )

  fleetspeak_configs = self_contained_components.InitFleetspeakConfigs(
      grr_configs,
      _FLEETSPEAK_MYSQL_DATABASE.value,
      mysql_username=_MYSQL_USERNAME.value,
      mysql_password=_MYSQL_PASSWORD.value,
      logging_path=_LOGGING_PATH.value,
      rrg_path=_RRG_PATH.value,
      rrg_command_verifying_key_bytes=command_verifying_key_bytes,
  )

  # Start all remaining server components.
  # Start a background thread that kills the main process if one of the
  # server subprocesses dies.
  server_processes = self_contained_components.StartServerProcesses(
      grr_configs, fleetspeak_configs
  )
  self_contained_components.DieIfSubProcessDies(server_processes)

  api_port = api_helpers.GetAdminUIPortFromConfig(grr_configs.server_config)
  grrapi = api_helpers.WaitForAPIEndpoint(api_port)

  command_signer_args = [
      "--config",
      grr_configs.server_config,
      "--api_endpoint",
      f"http://localhost:{api_port}",
      # pylint: disable=line-too-long
      # pyformat: disable
      str(ROOT_DIR / "config" / "command_execution" / "flow_and_artifact_commands.textproto"),
      # pylint: enable=line-too-long
      # pyformat: enable
  ]

  if _OSQUERY_PATH.value:
    command_signer_args.extend([
        # TODO - Adjust command signer to skip commands with non-
        # existing template parameters.
        #
        # Right now we have to specify a template parameter for every platform
        # with a dummy value for platforms that we are not interested in just
        # because there is a command for it in the file.
        "--template-param",
        f"OSQUERY_LINUX={_OSQUERY_PATH.value}",
        "--template-param",
        f"OSQUERY_MACOS={_OSQUERY_PATH.value}",
        "--template-param",
        f"OSQUERY_WINDOWS={_OSQUERY_PATH.value}",
        # pylint: disable=line-too-long
        # pyformat: disable
        str(ROOT_DIR / "config" / "command_execution" / "osquery_commands.textproto"),
        # pylint: enable=line-too-long
        # pyformat: enable
    ])

  subprocess.run(
      [
          sys.executable,
          "-u",
          "-m",
          "grr_response_server.bin.command_signer",
      ]
      + command_signer_args,
      check=True,
  )

  # Start the client.
  preliminary_client_p = self_contained_components.StartClientProcess(
      fleetspeak_configs
  )

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
  client_p = self_contained_components.StartClientProcess(fleetspeak_configs)
  # Start a background thread that kills the main process if
  # client subprocess dies.
  self_contained_components.DieIfSubProcessDies([client_p])

  # Run the test suite against the enrolled client.
  self_contained_components.RunEndToEndTests(
      client_id,
      grr_configs.server_config,
      tests=_TESTS.value,
      manual_tests=_MANUAL_TESTS.value)

  print("RunEndToEndTests execution succeeded.")
  sys.exit(0)


if __name__ == "__main__":
  app.run(main)
