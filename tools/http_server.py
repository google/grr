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

"""This is the GRR frontend HTTP Server."""


import BaseHTTPServer
import cgi

from multiprocessing import freeze_support
from multiprocessing import Process
import pdb
import socket
import SocketServer
import sys


import ipaddr

from grr.client import conf
from grr.client import conf as flags
import logging

from grr.lib import communicator
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import key_utils
from grr.lib import log
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import server_plugins  # pylint: disable=W0611
from grr.lib import utils


flags.DEFINE_string("http_bind_address", "::", "The ip address to bind.")

flags.DEFINE_integer("http_bind_port", 8080, "The port to bind.")

flags.DEFINE_integer("processes", 1,
                     "Number of processes to use for the HTTP server")

FLAGS = flags.FLAGS
CONFIG = config_lib.CONFIG
CONFIG.flag_sections.append("ServerFlags")

# pylint: disable=C6409


class GRRHTTPServerHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """GRR HTTP handler for receiving client posts."""

  def do_GET(self):
    """Server the server pem with GET requests."""
    if self.path.startswith("/server.pem"):
      self.wfile.write(("HTTP/1.0 200\r\n"
                        "Server: BaseHTTP/0.3 Python/2.6.5\r\n"
                        "Content-type: application/octet-stream\r\n"
                        "Content-Length: %d\r\n"
                        "Cache-Control: no-cache\r\n"
                        "\r\n"
                        "%s" % (len(self.server.server_cert),
                                self.server.server_cert)))

  statustext = {200: "200 OK",
                406: "406 Not Acceptable",
                500: "500 Internal Server Error"}

  def Send(self, data, status=200, ctype="application/octet-stream",
           last_modified=0):

    self.wfile.write(("HTTP/1.0 %s\r\n"
                      "Server: BaseHTTP/0.3 Python/2.6.5\r\n"
                      "Content-type: %s\r\n"
                      "Content-Length: %d\r\n"
                      "Last-Modified: %s\r\n"
                      "\r\n"
                      "%s") %
                     (self.statustext[status], ctype, len(data),
                      self.date_time_string(last_modified), data))

  def do_POST(self):
    """Process encrypted message bundles."""
    # Get the api version
    try:
      api_version = int(cgi.parse_qs(self.path.split("?")[1])["api"][0])
    except (ValueError, KeyError, IndexError):
      # The oldest api version we support if not specified.
      api_version = 2

    try:
      length = int(self.headers.getheader("content-length"))
      input_data = self.rfile.read(length)

      request_comms = rdfvalue.ClientCommunication(input_data)

      # If the client did not supply the version in the protobuf we use the get
      # parameter.
      if not request_comms.api_version:
        request_comms.api_version = api_version

      # Reply using the same version we were requested with.
      responses_comms = rdfvalue.ClientCommunication(
          api_version=request_comms.api_version)

      source_ip = ipaddr.IPAddress(self.client_address[0])

      if source_ip.version == 6:
        source_ip = source_ip.ipv4_mapped or source_ip

      request_comms.orig_request = rdfvalue.HttpRequest(
          raw_headers=utils.SmartStr(self.headers),
          source_ip=utils.SmartStr(source_ip))

      source, nr_messages = self.server.frontend.HandleMessageBundles(
          request_comms, responses_comms)

      logging.info("HTTP request from %s (%s), %d bytes - %d messages.",
                   source, utils.SmartStr(source_ip), length, nr_messages)

      self.Send(responses_comms.SerializeToString())

    except communicator.UnknownClientCert:
      # "406 Not Acceptable: The server can only generate a response that is not
      # accepted by the client". This is because we can not encrypt for the
      # client appropriately.
      return self.Send("Enrollment required", status=406)

    except Exception as e:
      if FLAGS.debug:
        pdb.post_mortem()

      logging.error("Had to respond with status 500: %s.", e)
      return self.Send("Error", status=500)


class GRRHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
  """The GRR HTTP frontend server."""

  allow_reuse_address = True
  request_queue_size = 500

  address_family = socket.AF_INET6

  def __init__(self, server_address, handler, frontend=None, logger=None,
               *args, **kwargs):
    if frontend:
      if logger is None:
        raise RuntimeError("No logger provided.")
      self._logger = logger
      self.frontend = frontend
    else:
      self._logger = log.GrrLogger(component=self.__class__.__name__)
      self.frontend = flow.FrontEndServer(
          "Server_Private_Key", self._logger,
          max_queue_size=FLAGS.max_queue_size,
          message_expiry_time=FLAGS.message_expiry_time,
          max_retransmission_time=FLAGS.max_retransmission_time)

    self.server_cert = key_utils.GetCert("Server_Public_Cert")

    (address, _) = server_address
    version = ipaddr.IPAddress(address).version
    if version == 4:
      self.address_family = socket.AF_INET
    elif version == 6:
      self.address_family = socket.AF_INET6

    BaseHTTPServer.HTTPServer.__init__(self, server_address, handler, *args,
                                       **kwargs)


def serve_forever(server):
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass


def main(unused_argv):
  """Main."""
  registry.Init()

  server_address = (FLAGS.http_bind_address, FLAGS.http_bind_port)
  httpd = GRRHTTPServer(server_address, GRRHTTPServerHandler)

  sa = httpd.socket.getsockname()
  logging.info("Serving HTTP on %s port %d ...", sa[0], sa[1])

  if FLAGS.processes > 1:
    # Multiprocessing
    for _ in range(FLAGS.processes - 1):
      Process(target=serve_forever, args=(httpd,)).start()

  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    print "Caught keyboard interrupt, stopping"

if __name__ == "__main__":
  freeze_support()
  if sys.stderr.isatty(): FLAGS.logtostderr = True
  conf.StartMain(main)
