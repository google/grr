#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""This is a development server for running the UI."""


import logging
import socket
import SocketServer
from wsgiref import simple_server

from django.core.handlers import wsgi

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup


config_lib.DEFINE_integer("AdminUI.port", 8000, "port to listen on")

config_lib.DEFINE_string("AdminUI.bind", "::", "interface to bind to.")

config_lib.DEFINE_bool("AdminUI.django_debug", False,
                       "Turn on to add django debugging")

config_lib.DEFINE_string(
    "AdminUI.django_secret_key", "CHANGE_ME",
    "This is a secret key that should be set in the server "
    "config. It is used in XSRF and session protection.")


class ThreadingDjango(SocketServer.ThreadingMixIn, simple_server.WSGIServer):
  address_family = socket.AF_INET6


def main(_):
  """Run the main test harness."""
  config_lib.CONFIG.AddContext(
      "AdminUI Context",
      "Context applied when running the admin user interface GUI.")
  startup.Init()

  # Start up a server in another thread
  base_url = "http://%s:%d" % (config_lib.CONFIG["AdminUI.bind"],
                               config_lib.CONFIG["AdminUI.port"])
  logging.info("Base URL is %s", base_url)

  # Make a simple reference implementation WSGI server
  server = simple_server.make_server(config_lib.CONFIG["AdminUI.bind"],
                                     config_lib.CONFIG["AdminUI.port"],
                                     wsgi.WSGIHandler(),
                                     server_class=ThreadingDjango)

  server.serve_forever()

if __name__ == "__main__":
  flags.StartMain(main)
