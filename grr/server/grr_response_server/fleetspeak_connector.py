#!/usr/bin/env python
"""A facade for the GRR-FS server-side connection."""
import logging
from typing import Optional

from grr_response_core import config
from fleetspeak.server_connector import connector as fs_client

# The singleton instance of the Fleetspeak connector.
CONN: Optional[fs_client.ServiceClient] = None

# Singleton information mapping Fleetspeak labels to GRR labels.
label_map = {}

unknown_label = None


def Init(service_client=None):
  """Initializes the Fleetspeak connector."""
  global CONN
  global label_map

  if service_client is None:
    service_client_cls = fs_client.InsecureGRPCServiceClient

    fleetspeak_message_listen_address = (
        config.CONFIG["Server.fleetspeak_message_listen_address"] or None)
    fleetspeak_server = config.CONFIG["Server.fleetspeak_server"] or None

    if fleetspeak_message_listen_address is None and fleetspeak_server is None:
      logging.warning(
          "Missing config options `Server.fleetspeak_message_listen_address', "
          "`Server.fleetspeak_server', at least one of which is required to "
          "initialize a connection to Fleetspeak; Not using Fleetspeak.")
      return

    service_client = service_client_cls(
        "GRR",
        fleetspeak_message_listen_address=fleetspeak_message_listen_address,
        fleetspeak_server=fleetspeak_server,
        threadpool_size=50)

  label_map = {}
  for entry in config.CONFIG["Server.fleetspeak_label_map"]:
    key, value = entry.split(":")
    label_map[key.strip()] = value.strip()

  CONN = service_client
  logging.info("Fleetspeak connector initialized.")
