#!/usr/bin/env python
"""This is a backend analysis worker which will be deployed on the server.

We basically pull a new task from the task master, and run the plugin
it specifies.
"""


# pylint: disable=unused-import,g-bad-import-order
from grr.server.grr_response_server import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr import config
from grr.config import contexts
from grr.config import server as config_server
from grr.lib import flags
from grr.server.grr_response_server import access_control
from grr.server.grr_response_server import fleetspeak_connector
from grr.server.grr_response_server import server_startup
from grr.server.grr_response_server import worker_lib

flags.DEFINE_version(config_server.VERSION["packageversion"])


def main(argv):
  """Main."""
  del argv  # Unused.
  config.CONFIG.AddContext(contexts.WORKER_CONTEXT,
                           "Context applied when running a worker.")

  # Initialise flows and config_lib
  server_startup.Init()

  fleetspeak_connector.Init()

  token = access_control.ACLToken(username="GRRWorker").SetUID()
  worker_obj = worker_lib.GRRWorker(token=token)
  worker_obj.Run()


if __name__ == "__main__":
  flags.StartMain(main)
