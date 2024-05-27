#!/usr/bin/env python
"""This is the GRR frontend FS Server."""

import logging
import time

from absl import app
from absl import flags

from grr_response_core import config
from grr_response_core.config import server as config_server
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_cps
from grr_response_server import server_startup
from grr_response_server.bin import fleetspeak_frontend_server


_VERSION = flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR Fleetspeak Frontend version and exit immediately.",
)


def main(argv):
  del argv  # Unused.

  if _VERSION.value:
    print(
        "GRR Fleetspeak Frontend {}".format(
            config_server.VERSION["packageversion"]
        )
    )
    return

  config.CONFIG.AddContext("FleetspeakFrontend Context")

  server_startup.Init()
  server_startup.DropPrivileges()

  fleetspeak_connector.Init()

  fsd = fleetspeak_frontend_server.GRRFSServer()

  cleanup_fn = lambda: None
  if config.CONFIG["Server.fleetspeak_cps_enabled"]:
    cps = fleetspeak_cps.Subscriber()
    cps.Start(fsd.ProcessFromCPS)
    cleanup_fn = cps.Stop
    logging.info("Waiting for messages via Fleetspeak Cloud Pub/Sub ...")
  else:
    fleetspeak_connector.CONN.Listen(fsd.ProcessFromGRPC)
    logging.info("Waiting for messages via Fleetspeak GRPC ...")

  try:
    while True:
      time.sleep(600)
  except KeyboardInterrupt:
    print("Caught keyboard interrupt, stopping")

  cleanup_fn()


if __name__ == "__main__":
  app.run(main)
