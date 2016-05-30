#!/usr/bin/env python
"""This is a single binary demo program."""


import threading


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
from grr.gui import admin_ui
# pylint: enable=unused-import,g-bad-import-order

from grr.client import client
from grr.gui import runtests
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup
from grr.tools import http_server
from grr.worker import worker


def main(argv):
  """Sets up all the component in their own threads."""
  config_lib.CONFIG.AddContext(
      "Demo Context",
      "The demo runs all functions in a single process using the "
      "in memory data store.")

  config_lib.CONFIG.AddContext("Test Context",
                               "Context applied when we run tests.")

  flags.FLAGS.config = config_lib.Resource().Filter(
      "install_data/etc/grr-server.yaml")

  flags.FLAGS.secondary_configs = [
      config_lib.Resource().Filter("test_data/grr_test.yaml@grr-response-test")
  ]

  startup.Init()

  # pylint: disable=unused-import,unused-variable,g-import-not-at-top
  from grr.gui import gui_plugins
  # pylint: enable=unused-import,unused-variable,g-import-not-at-top

  # This is the worker thread.
  worker_thread = threading.Thread(target=worker.main,
                                   args=[argv],
                                   name="Worker")
  worker_thread.daemon = True
  worker_thread.start()

  # This is the http server Frontend that clients communicate with.
  http_thread = threading.Thread(target=http_server.main,
                                 args=[argv],
                                 name="HTTP Server")
  http_thread.daemon = True
  http_thread.start()

  client_thread = threading.Thread(target=client.main,
                                   args=[argv],
                                   name="Client")
  client_thread.daemon = True
  client_thread.start()

  # The UI is running in the main thread.
  runtests.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
