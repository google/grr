#!/usr/bin/env python
# Lint as: python3
"""This is the GRR frontend FS Server."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import time

from absl import app


# pylint: disable=unused-import,g-bad-import-order
from grr_response_server import server_plugins
# pylint: enable=unused-import, g-bad-import-order

from grr_response_core import config
from grr_response_server import fleetspeak_connector
from grr_response_server import server_startup
from grr_response_server.bin import fleetspeak_frontend_server



def main(argv):
  del argv  # Unused.

  config.CONFIG.AddContext("FleetspeakFrontend Context")

  server_startup.Init()
  server_startup.DropPrivileges()

  fleetspeak_connector.Init()

  fsd = fleetspeak_frontend_server.GRRFSServer()
  fleetspeak_connector.CONN.Listen(fsd.Process)

  logging.info("Serving through Fleetspeak ...")

  try:
    while True:
      time.sleep(600)
  except KeyboardInterrupt:
    print("Caught keyboard interrupt, stopping")


if __name__ == "__main__":
  app.run(main)
