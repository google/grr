#!/usr/bin/env python
# Lint as: python3
"""Helper API-client-based functions for self-contained tests."""
import time

from typing import Tuple

import requests

from grr_api_client import api
from grr_response_core import config
from grr_response_core.lib import config_lib


class Error(Exception):
  """Module-specific base error class."""


class APIEndpointTimeoutError(Error):
  """Raised when API endpoint doesn't come online in time."""


class ClientEnrollmentTimeoutError(Error):
  """Raised when a client does not enroll in time."""


class ClientVersionTimeoutError(Error):
  """Raised then a client doesn't report a specific version in time."""


def GetFleetspeakPortsFromConfig(config_path: str) -> Tuple[int, int]:
  """Gets Fleetspeak frontend and admin ports from GRR config."""
  conf = config_lib.LoadConfig(config.CONFIG.MakeNewConfig(), config_path)
  frontend_port = int(
      conf["Server.fleetspeak_message_listen_address"].rsplit(":")[-1])
  admin_port = int(conf["Server.fleetspeak_server"].rsplit(":")[-1])
  return frontend_port, admin_port


def GetAdminUIPortFromConfig(config_path: str) -> int:
  """Gets the AdminUI.port setting from a given config file."""
  conf = config_lib.LoadConfig(config.CONFIG.MakeNewConfig(), config_path)
  return conf["AdminUI.port"]


_WAIT_TIMEOUT_SECS = 150
_CHECK_INTERVAL = 1


def WaitForAPIEndpoint(port: int) -> api.GrrApi:
  """Waits for API endpoint to come online."""
  api_endpoint = "http://localhost:%d" % port

  start_time = time.time()
  while time.time() - start_time < _WAIT_TIMEOUT_SECS:
    try:
      grrapi = api.InitHttp(api_endpoint=api_endpoint)
      grrapi.ListGrrBinaries()
      return grrapi
    except (requests.exceptions.ConnectionError, ConnectionRefusedError):
      print("Connection error (%s), waiting..." % api_endpoint)
      time.sleep(_CHECK_INTERVAL)
      continue

  raise APIEndpointTimeoutError("API endpoint %s didn't come up." %
                                api_endpoint)


def WaitForClientToEnroll(grrapi: api.GrrApi) -> str:
  """Waits for an already started client to enroll.

  If the client doesn't enroll within ~100 seconds, main process gets killed.

  Args:
    grrapi: GRR API object.

  Returns:
    A string with an enrolled client's id.

  Raises:
    ClientEnrollmentTimeoutError: if the client fails to enroll in time.
  """
  start_time = time.time()
  while time.time() - start_time < _WAIT_TIMEOUT_SECS:
    clients = list(grrapi.SearchClients(query="."))

    if clients:
      return clients[0].client_id

    print("No clients enrolled, waiting...")
    time.sleep(_CHECK_INTERVAL)

  raise ClientEnrollmentTimeoutError("Client didn't enroll.")


def KillClient(grrapi: api.GrrApi, client_id: str):
  """Kills a given client."""

  f = grrapi.Client(client_id).CreateFlow("Kill")
  f.WaitUntilDone(timeout=60)


def WaitForClientVersionGreaterThan(api_client_obj, min_version):
  """Waits until the client version becomes greater than a given value."""

  start_time = time.time()
  while time.time() - start_time < _WAIT_TIMEOUT_SECS:
    version = api_client_obj.Get().data.agent_info.client_version
    if version > min_version:
      print("Got expected client version %d." % version)
      return version

    print("Got client version: %d, must be > %d" % (version, min_version))
    time.sleep(_CHECK_INTERVAL)

  raise ClientVersionTimeoutError(
      "Timed out while waiting for the client version > %d." % min_version)
