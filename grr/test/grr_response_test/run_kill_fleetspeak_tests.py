#!/usr/bin/env python
# Lint as: python3
"""Runs an end-to-end test of the kill fleetspeak feature."""

import sys
import time
from typing import Text

from absl import app
from absl import flags
import psutil

from grr_api_client import api
from grr_api_client import flow as api_flow
from grr_response_test.lib import api_helpers
from grr_response_test.lib import self_contained_components

flags.DEFINE_string("mysql_database", "grr_test_db",
                    "MySQL database name to use.")

flags.DEFINE_string("fleetspeak_mysql_database", "fleetspeak_test_db",
                    "MySQL database name to use for Fleetspeak.")

flags.DEFINE_string("mysql_username", None, "MySQL username to use.")

flags.DEFINE_string("mysql_password", None, "MySQL password to use.")

flags.DEFINE_string("logging_path", None,
                    "Base logging path for server components to use.")


def FindGrrClientProcess(config_path: Text) -> psutil.Process:
  """Finds the running GRR process."""
  for proc in psutil.process_iter(["pid", "cmdline", "create_time"]):
    name_found = False
    config_found = False
    for arg in proc.cmdline():
      if "grr_fs_client" in arg:
        name_found = True
      if config_path in arg:
        config_found = True
    if name_found and config_found:
      return proc
  raise RuntimeError("Couldn't find GRR client process.")


def RunInterrogate(grr_api: api.GrrApi, client_id: Text) -> api_flow.Flow:
  """Runs the Interrogate flow."""
  args = grr_api.types.CreateFlowArgs("Interrogate")
  args.lightweight = True

  runner_args = grr_api.types.CreateFlowRunnerArgs()
  runner_args.notify_to_user = False

  flow = grr_api.Client(client_id).CreateFlow(
      name="Interrogate", args=args, runner_args=runner_args)
  flow.WaitUntilDone(600)

  return flow


def main(argv):
  grr_configs = self_contained_components.InitGRRConfigs(
      flags.FLAGS.mysql_database,
      mysql_username=flags.FLAGS.mysql_username,
      mysql_password=flags.FLAGS.mysql_password,
      logging_path=flags.FLAGS.logging_path,
      with_fleetspeak=True)

  fleetspeak_configs = self_contained_components.InitFleetspeakConfigs(
      grr_configs,
      flags.FLAGS.fleetspeak_mysql_database,
      mysql_username=flags.FLAGS.mysql_username,
      mysql_password=flags.FLAGS.mysql_password)

  server_processes = self_contained_components.StartServerProcesses(
      grr_configs=grr_configs, fleetspeak_configs=fleetspeak_configs)

  api_port = api_helpers.GetAdminUIPortFromConfig(grr_configs.server_config)

  grr_api = api_helpers.WaitForAPIEndpoint(api_port)

  if list(grr_api.SearchClients()):
    raise Exception("This tests expects to be run on an empty database.")

  client_p = self_contained_components.StartClientProcess(
      grr_configs=grr_configs, fleetspeak_configs=fleetspeak_configs)

  client_id = api_helpers.WaitForClientToEnroll(grr_api)

  print("client_id is", client_id)

  client_proc_before = FindGrrClientProcess(grr_configs.client_config)

  print("GRR process has process ID {}.".format(client_proc_before.pid))

  print("Running Interrogate flow 1.")
  result = RunInterrogate(grr_api, client_id)
  print("Interrogate flow 1 finished with result {}.".format(result))

  print("Running RestartFleetspeakGrrService().")
  self_contained_components.RunApiShellRawAccess(
      grr_configs.server_config,
      "grrapi.root.Client(\"{}\").RestartFleetspeakGrrService()".format(
          client_id))
  print("Finished RestartFleetspeakGrrService().")

  # We have to wait for the restart to finish.
  # Killing the GRR service while a flow is running might make the flow hang.
  # The GRR client sends the reply of an action to fleetspeak, then deletes
  # the action from the transaction log. However, fleetspeak buffers the reply
  # in memory for up to one second. If the GRR client gets killed in this
  # time window, the reply is lost.
  time.sleep(10)

  client_proc_after = FindGrrClientProcess(grr_configs.client_config)
  print("GRR process has process ID {} after restart.".format(
      client_proc_before.pid))

  if client_proc_before.pid == client_proc_after.pid:
    raise Exception("Process ID of GRR process didn't change as expected. "
                    "Before: {}. After: {}.".format(client_proc_before.pid,
                                                    client_proc_after.pid))

  print("Running Interrogate flow 2.")
  result = RunInterrogate(grr_api, client_id)
  print("Interrogate flow 2 finished with result {}.".format(result))

  if client_p.poll() is not None:
    raise Exception(
        "Fleetspeak client process is expected to run, but it terminated.")

  # With force=False the fleetspeak client performs a graceful shutdown.
  print("Running KillFleetspeak(force=False).")
  self_contained_components.RunApiShellRawAccess(
      grr_configs.server_config,
      "grrapi.root.Client(\"{}\").KillFleetspeak(force=False)".format(
          client_id))
  print("Finished KillFleetspeak(force=False).")

  print("Waiting for fleetspeak client to terminate.")
  client_p.wait(5)
  print("Fleetspeak client terminated.")

  print("Restarting fleetspeak client.")
  client_p = self_contained_components.StartClientProcess(
      grr_configs=grr_configs, fleetspeak_configs=fleetspeak_configs)

  print("Running Interrogate flow 3.")
  result = RunInterrogate(grr_api, client_id)
  print("Interrogate flow 3 finished with result {}.".format(result))

  if client_p.poll() is not None:
    raise Exception(
        "Fleetspeak client process is expected to run, but it terminated.")

  # With force=True the fleetspeak clients just exits.
  print("Running KillFleetspeak(force=True).")
  self_contained_components.RunApiShellRawAccess(
      grr_configs.server_config,
      "grrapi.root.Client(\"{}\").KillFleetspeak(force=True)".format(client_id))
  print("Finished KillFleetspeak(force=True).")

  print("Waiting for fleetspeak client to terminate.")
  client_p.wait(5)
  print("Fleetspeak client terminated.")

  print("Restarting fleetspeak client.")
  client_p = self_contained_components.StartClientProcess(
      grr_configs=grr_configs, fleetspeak_configs=fleetspeak_configs)

  print("Running Interrogate flow 4.")
  result = RunInterrogate(grr_api, client_id)
  print("Interrogate flow 4 finished with result {}.".format(result))

  print("Finished.")

  sys.exit(0)


if __name__ == "__main__":
  app.run(main)
