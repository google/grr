#!/usr/bin/env python
"""Wrapper for running a fleetspeak client in a virtualenv setup.

This script is meant to be used for development.

Requirements for running this script:

 * Running from a virtualenv.
 * PIP package `fleetspeak-client-bin` is installed.
 * `grr_config_updater initialize` has been run.
 * Fleetspeak has been enabled.
"""

import os
import platform
import subprocess

from absl import app

from google.protobuf import text_format
from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib import package
from grr_response_core.lib import utils
from grr_response_core.lib.util import temp
from fleetspeak.src.client.daemonservice.proto.fleetspeak_daemonservice import config_pb2 as fs_daemon_config_pb2
from fleetspeak.src.client.generic.proto.fleetspeak_client_generic import config_pb2 as fs_cli_config_pb2
from fleetspeak.src.common.proto.fleetspeak import system_pb2 as fs_system_pb2


class Error(Exception):
  pass


def _CreateClientConfig(tmp_dir: str) -> str:
  """Creates and returns the path to a fleetspeak client config."""

  def TmpPath(*args):
    return os.path.join(tmp_dir, *args)

  server_config_dir = package.ResourcePath(
      "fleetspeak-server-bin", "fleetspeak-server-bin/etc/fleetspeak-server")
  if not os.path.exists(server_config_dir):
    raise Error(
        f"Fleetspeak server config dir not found: {server_config_dir}. "
        "Please make sure `grr_config_updater initialize` has been run.")
  client_config_name = {
      "Linux": "linux_client.config",
      "Windows": "windows_client.config",
      "Darwin": "darwin_client.config",
  }
  client_config_path = os.path.join(server_config_dir,
                                    client_config_name[platform.system()])
  with open(client_config_path, "r") as f:
    client_config = text_format.Parse(f.read(), fs_cli_config_pb2.Config())
  if client_config.HasField("filesystem_handler"):
    client_config.filesystem_handler.configuration_directory = TmpPath()
    # We store the client state file in `Logging.path`.
    # 1) We need a writable path, where writing a file doesn't surprise the
    #    user (as opposed to other paths in the source tree).
    # 2) We need the state file to be somewhat persistent, i.e. kept after
    #    re-runs of this command. Otherwise the client ID of the client would
    #    change at each re-run.
    client_config.filesystem_handler.state_file = os.path.join(
        config.CONFIG["Logging.path"], "fleetspeak-client.state")
  with open(TmpPath("config"), "w") as f:
    f.write(text_format.MessageToString(client_config))
  return TmpPath("config")


def _CreateServiceConfig(config_dir: str) -> None:
  """Creates a fleetspeak service config in the config directory."""
  service_config_path = config.CONFIG["ClientBuilder.fleetspeak_config_path"]
  with open(service_config_path, "r") as f:
    data = config.CONFIG.InterpolateValue(f.read())
    service_config = text_format.Parse(data,
                                       fs_system_pb2.ClientServiceConfig())
  daemon_config = fs_daemon_config_pb2.Config()
  service_config.config.Unpack(daemon_config)
  del daemon_config.argv[:]
  daemon_config.argv.extend([
      "grr_client",
  ])
  service_config.config.Pack(daemon_config)
  utils.EnsureDirExists(os.path.join(config_dir, "textservices"))
  with open(os.path.join(config_dir, "textservices", "GRR.textproto"),
            "w") as f:
    f.write(text_format.MessageToString(service_config))


def _RunClient(tmp_dir: str) -> None:
  """Runs the fleetspeak client."""
  config_path = _CreateClientConfig(tmp_dir)
  _CreateServiceConfig(tmp_dir)
  fleetspeak_client = package.ResourcePath(
      "fleetspeak-client-bin",
      "fleetspeak-client-bin/usr/bin/fleetspeak-client")
  if not fleetspeak_client or not os.path.exists(fleetspeak_client):
    raise Error(
        f"Fleetspeak client binary not found: {fleetspeak_client}."
        "Please make sure that the package `fleetspeak-client-bin` has been "
        "installed.")
  command = [
      fleetspeak_client,
      "--logtostderr",
      "-config",
      config_path,
  ]
  subprocess.check_call(command)


def main(argv):
  del argv  # unused
  config_lib.ParseConfigCommandLine()
  with temp.AutoTempDirPath(remove_non_empty=True) as tmp_dir:
    _RunClient(tmp_dir)


if __name__ == "__main__":
  app.run(main)
