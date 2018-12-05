#!/usr/bin/env python
"""This is a development server for running the UI."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import socket
import SocketServer
import ssl
from wsgiref import simple_server

from builtins import range  # pylint: disable=redefined-builtin
import ipaddr

from grr_response_core import config
from grr_response_core.config import contexts
from grr_response_core.config import server as config_server

# pylint: disable=unused-import,g-bad-import-order
from grr_response_server.gui import local
from grr_response_server import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr_response_core.lib import flags
from grr_response_server import server_startup
from grr_response_server.gui import wsgiapp


class ThreadedServer(SocketServer.ThreadingMixIn, simple_server.WSGIServer):
  address_family = socket.AF_INET6


def main(_):
  """Run the main test harness."""

  if flags.FLAGS.version:
    print("GRR Admin UI {}".format(config_server.VERSION["packageversion"]))
    return

  config.CONFIG.AddContext(
      contexts.ADMIN_UI_CONTEXT,
      "Context applied when running the admin user interface GUI.")
  server_startup.Init()

  if not config.CONFIG["AdminUI.headless"] and (not os.path.exists(
      os.path.join(config.CONFIG["AdminUI.document_root"],
                   "dist/grr-ui.bundle.js")) or not os.path.exists(
                       os.path.join(config.CONFIG["AdminUI.document_root"],
                                    "dist/grr-ui.bundle.css"))):
    raise RuntimeError("Can't find compiled JS/CSS bundles. "
                       "Please reinstall the PIP package using "
                       "\"pip install -e .\" to rebuild the bundles.")

  # Start up a server in another thread
  bind_address = config.CONFIG["AdminUI.bind"]
  ip = ipaddr.IPAddress(bind_address)
  if ip.version == 4:
    # Address looks like an IPv4 address.
    ThreadedServer.address_family = socket.AF_INET

  max_port = config.CONFIG.Get("AdminUI.port_max",
                               config.CONFIG["AdminUI.port"])

  for port in range(config.CONFIG["AdminUI.port"], max_port + 1):
    # Make a simple reference implementation WSGI server
    try:
      server = simple_server.make_server(
          bind_address,
          port,
          wsgiapp.AdminUIApp().WSGIHandler(),
          server_class=ThreadedServer)
      break
    except socket.error as e:
      if e.errno == socket.errno.EADDRINUSE and port < max_port:
        logging.info("Port %s in use, trying %s", port, port + 1)
      else:
        raise

  proto = "HTTP"

  if config.CONFIG["AdminUI.enable_ssl"]:
    cert_file = config.CONFIG["AdminUI.ssl_cert_file"]
    if not cert_file:
      raise ValueError("Need a valid cert file to enable SSL.")

    key_file = config.CONFIG["AdminUI.ssl_key_file"]
    server.socket = ssl.wrap_socket(
        server.socket, certfile=cert_file, keyfile=key_file, server_side=True)
    proto = "HTTPS"

    # SSL errors are swallowed by the WSGIServer so if your configuration does
    # not work, uncomment the line below, point your browser at the gui and look
    # at the log file to see why SSL complains:
    # server.socket.accept()

  sa = server.socket.getsockname()
  logging.info("Serving %s on %s port %d ...", proto, sa[0], sa[1])
  server_startup.DropPrivileges()

  server.serve_forever()


if __name__ == "__main__":
  flags.StartMain(main)
