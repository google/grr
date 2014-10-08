#!/usr/bin/env python
"""This is a development server for running the UI."""


import logging
import socket
import SocketServer
import ssl
from wsgiref import simple_server

# pylint: disable=unused-import,g-bad-import-order
from grr.gui import django_lib
from grr.lib import server_plugins
from grr.gui import plot_lib
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup


class ThreadingDjango(SocketServer.ThreadingMixIn, simple_server.WSGIServer):
  address_family = socket.AF_INET6


def main(_):
  """Run the main test harness."""
  config_lib.CONFIG.AddContext(
      "AdminUI Context",
      "Context applied when running the admin user interface GUI.")
  startup.Init()

  # Start up a server in another thread

  # Make a simple reference implementation WSGI server
  server = simple_server.make_server(config_lib.CONFIG["AdminUI.bind"],
                                     config_lib.CONFIG["AdminUI.port"],
                                     django_lib.GetWSGIHandler(),
                                     server_class=ThreadingDjango)

  proto = "HTTP"

  if config_lib.CONFIG["AdminUI.enable_ssl"]:
    cert_file = config_lib.CONFIG["AdminUI.ssl_cert_file"]
    if not cert_file:
      raise ValueError("Need a valid cert file to enable SSL.")

    key_file = config_lib.CONFIG["AdminUI.ssl_key_file"]
    server.socket = ssl.wrap_socket(server.socket, certfile=cert_file,
                                    keyfile=key_file, server_side=True)
    proto = "HTTPS"

    # SSL errors are swallowed by the WSGIServer so if your configuration does
    # not work, uncomment the line below, point your browser at the gui and look
    # at the log file to see why SSL complains:
    # server.socket.accept()

  sa = server.socket.getsockname()
  logging.info("Serving %s on %s port %d ...", proto, sa[0], sa[1])

  server.serve_forever()

if __name__ == "__main__":
  flags.StartMain(main)
