#!/usr/bin/env python
"""A facade for the GRR-FS server-side connection."""

import logging
from fleetspeak.src.server.grpcservice.client import client as fs_client
from grr import config

# The singleton instance of the Fleetspeak connector.
CONN = None


def Init(service_client=None):
  """Initializes the Fleetspeak connector."""
  global CONN

  if service_client is None:
    service_client_cls = fs_client.InsecureGRPCServiceClient

    fleetspeak_message_listen_address = (
        config.CONFIG["Server.fleetspeak_message_listen_address"] or None)
    fleetspeak_server = config.CONFIG["Server.fleetspeak_server"] or None

    if fleetspeak_message_listen_address is None and fleetspeak_server is None:
      logging.warn(
          "Missing config options `Server.fleetspeak_message_listen_address', "
          "`Server.fleetspeak_server', at least one of which is required to "
          "initialize a connection to Fleetspeak; Not using Fleetspeak.")
      return

    service_client = service_client_cls(
        "GRR",
        fleetspeak_message_listen_address=fleetspeak_message_listen_address,
        fleetspeak_server=fleetspeak_server,
        threadpool_size=50)

  CONN = service_client
  logging.info("Fleetspeak connector initialized.")


def Reset():
  """Resets the Fleetspeak connector, so that it can be reinitialized.

  This should not normally be needed, but is useful in unittests.

  Note: We're not sure a complete reset is always possible.
  """
  global CONN
  CONN = None
