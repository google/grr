#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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


from grr.client import conf as flags

# pylint: disable=W0611
# pylint: enable=W0611

from grr.lib import communicator
from grr.lib import mongo_data_store
from grr.lib import flow
from grr.lib import log
from grr.lib import registry
from grr.proto import jobs_pb2

flags.DEFINE_integer("max_queue_size", 500,
                     "Maximum number of messages to queue for the client.")

flags.DEFINE_integer("max_receiver_threads", 10,
                     "Maximum number of threads to use for receivers.")

flags.DEFINE_integer("max_retransmission_time", 10,
                     "Maximum number of times we are allowed to "
                     "retransmit a request until it fails.")

flags.DEFINE_integer("message_expiry_time", 600,
                     "Maximum time messages remain valid within the system.")

flags.DEFINE_string("server_cert", "grr/keys/test/server.pem",
                    "The path to the server public key and certificate.")

flags.DEFINE_string("server_private_key", "grr/keys/test/server-priv.pem",
                    "The path to the server private key.")



class GrrWSGIServer(object):
  """A WSGI based GRR HTTP server."""

  server_pem = ""

  def __init__(self):
    registry.Init()
    self.server_pem = open(FLAGS.server_cert, "rb").read()
    self.logger = log.GrrLogger(component="WSGI server")
    self.front_end = flow.FrontEndServer(
        FLAGS.server_private_key, self.logger,
        max_queue_size=FLAGS.max_queue_size,
        message_expiry_time=FLAGS.message_expiry_time,
        max_retransmission_time=FLAGS.max_retransmission_time)

  def handle(self, environ, start_response):
    """The request handler."""

    if environ["REQUEST_METHOD"] == "GET":
      if environ["PATH_INFO"] == "/server.pem":
        return self.Send(self.server_pem, start_response)
      else:
        return self.Send("", start_response)

    if environ["REQUEST_METHOD"] == "POST":
      try:
        length = int(environ["CONTENT_LENGTH"])
        input_data = environ["wsgi.input"].read(length)

        request_comms = jobs_pb2.ClientCommunication()
        request_comms.ParseFromString(input_data)

        responses_comms = jobs_pb2.ClientCommunication()

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
  global FLAGS
  FLAGS = parser.values

  if not WSGISERVER:
    WSGISERVER.append(GrrWSGIServer())
  return WSGISERVER[0].handle(environ, start_response)
