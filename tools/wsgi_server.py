#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""This is the WSGI based version of the GRR HTTP Server.

If you want to set up apache as an http server for GRR, here is a site config
file you can use. Be aware though that this might not be 100% reliable since
mod_wsgi uses subinterpreters which might lead to strange errors in the GRR
code.

<VirtualHost *:80>

    ServerName www.example.com
    ServerAlias example.com
    ServerAdmin webmaster@example.com

    DocumentRoot /tmp/wsgitest

    SetEnv configuration /tmp/wsgitest/grr/tools/wsgi.conf
    WSGIApplicationGroup %{GLOBAL}
    WSGIScriptAlias / /tmp/wsgitest/grr/tools/wsgi_server.py

    <Directory /tmp/wsgitest/grr/tools>
    Order allow,deny
    Allow from all
    </Directory>

</VirtualHost>

"""


import os
import sys

grrpath = os.path.dirname(os.path.realpath(__file__))
grrpath = grrpath.replace("/grr/tools", "")

if grrpath not in sys.path:
  sys.path.append(grrpath)


import logging

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
from grr.tools import http_server
from grr.gui import webauth
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import communicator
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import master
from grr.lib import rdfvalue
from grr.lib import startup
from grr.lib import stats


flags.DEFINE_integer("max_queue_size", 500,
                     "Maximum number of messages to queue for the client.")

flags.DEFINE_integer("max_retransmission_time", 10,
                     "Maximum number of times we are allowed to "
                     "retransmit a request until it fails.")

flags.DEFINE_integer("message_expiry_time", 600,
                     "Maximum time messages remain valid within the system.")




class GrrWSGIServer(object):
  """A WSGI based GRR HTTP server."""

  server_pem = ""

  def __init__(self):
    startup.Init()
    self.server_pem = config_lib.CONFIG["Frontend.certificate"]
    self.front_end = flow.FrontEndServer(
        certificate=config_lib.CONFIG["Frontend.certificate"],
        private_key=config_lib.CONFIG["PrivateKeys.server_key"],
        max_queue_size=config_lib.CONFIG["Frontend.max_queue_size"],
        message_expiry_time=config_lib.CONFIG["Frontend.message_expiry_time"],
        max_retransmission_time=config_lib.CONFIG[
            "Frontend.max_retransmission_time"])

  def handle(self, environ, start_response):
    """The request handler."""
    if not master.MASTER_WATCHER.IsMaster():
      # We shouldn't be getting requests from the client unless we
      # are the active instance.
      stats.STATS.IncrementCounter("frontend_inactive_request_count",
                                   fields=["http"])
      logging.info("Request sent to inactive frontend")

    if environ["REQUEST_METHOD"] == "GET":
      if environ["PATH_INFO"] == "/server.pem":
        return self.Send(self.server_pem, start_response)
      else:
        return self.Send("", start_response)

    if environ["REQUEST_METHOD"] == "POST":
      try:
        length = int(environ["CONTENT_LENGTH"])
        input_data = environ["wsgi.input"].read(length)

        request_comms = rdfvalue.ClientCommunication(input_data)

        responses_comms = rdfvalue.ClientCommunication()

        self.front_end.HandleMessageBundles(
            request_comms, responses_comms)

        return self.Send(responses_comms.SerializeToString(), start_response)
      except communicator.UnknownClientCert:
        return self.Send("Enrollment required",
                         start_response, "406 Not acceptable")

  def Send(self, output, start_response, status="200 OK"):
    response_headers = [("Content-type", "text/plain"),
                        ("Content-Length", str(len(output)))]
    start_response(status, response_headers)

    return [output]


WSGISERVER = []


def application(environ, start_response):

  # We cannot continue without a config file so we don't try/catch.
  parser = flags.PARSER
  parser.parse_args(["--config", environ["configuration"]])
  if not WSGISERVER:
    WSGISERVER.append(GrrWSGIServer())

  return WSGISERVER[0].handle(environ, start_response)
