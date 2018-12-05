#!/usr/bin/env python
"""This is a backend analysis worker which will be deployed on the server.

We basically pull a new task from the task master, and run the plugin
it specifies.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


# pylint: disable=unused-import,g-bad-import-order
from grr_response_server import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.config import server as config_server
from grr_response_core.lib import flags
from grr_response_server import access_control
from grr_response_server import fleetspeak_connector
from grr_response_server import server_startup
from grr_response_server import worker_lib


def main(argv):
  """Main."""
  del argv  # Unused.

  if flags.FLAGS.version:
    print("GRR worker {}".format(config_server.VERSION["packageversion"]))
    return

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
