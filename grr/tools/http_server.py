#!/usr/bin/env python
"""This is the GRR frontend HTTP Server."""



import BaseHTTPServer
import cgi
import cStringIO
import pdb
import socket
import SocketServer
import threading
import time


import ipaddr

import logging

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=g-bad-import-order

from grr.lib import aff4
from grr.lib import communicator
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import master
from grr.lib import rdfvalue
from grr.lib import startup
from grr.lib import stats
from grr.lib import type_info
from grr.lib import utils
from grr.lib.flows.general import file_finder
from grr.lib.rdfvalues import flows as rdf_flows

# pylint: disable=g-bad-name


class GRRHTTPServerHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """GRR HTTP handler for receiving client posts."""

  statustext = {200: "200 OK",
                404: "404 Not Found",
                406: "406 Not Acceptable",
                500: "500 Internal Server Error"}

  active_counter_lock = threading.Lock()
  active_counter = 0

  def Send(self,
           data,
           status=200,
           ctype="application/octet-stream",
           last_modified=0):

    self.wfile.write(("HTTP/1.0 %s\r\n"
                      "Server: GRR Server\r\n"
                      "Content-type: %s\r\n"
                      "Content-Length: %d\r\n"
                      "Last-Modified: %s\r\n"
                      "\r\n"
                      "%s") % (self.statustext[status], ctype, len(data),
                               self.date_time_string(last_modified), data))

  def do_GET(self):
    """Serve the server pem with GET requests."""
    url_prefix = config_lib.CONFIG["Frontend.static_url_path_prefix"]
    if self.path.startswith("/server.pem"):
      self.ServerPem()
    elif self.path.startswith(url_prefix):
      path = self.path[len(url_prefix):]
      self.ServeStatic(path)

  AFF4_READ_BLOCK_SIZE = 10 * 1024 * 1024

  def ServeStatic(self, path):
    static_aff4_prefix = config_lib.CONFIG["Frontend.static_aff4_prefix"]
    aff4_path = rdfvalue.RDFURN(static_aff4_prefix).Add(path)
    try:
      logging.info("Serving %s", aff4_path)
      fd = aff4.FACTORY.Open(aff4_path, token=aff4.FACTORY.root_token)
      while True:
        data = fd.Read(self.AFF4_READ_BLOCK_SIZE)
        if not data:
          break

        self.Send(data)
    except (IOError, AttributeError):
      self.Send("", status=404)

  def ServerPem(self):
    self.Send(self.server.server_cert)

  RECV_BLOCK_SIZE = 8192

  def _GetPOSTData(self, length):
    # During our tests we have encountered some issue with the socket library
    # that would stall for a long time when calling socket.recv(n) with a large
    # n. rfile.read() passes the length down to socket.recv() so it's much
    # faster to read the data in small 8k chunks.
    input_data = cStringIO.StringIO()
    while length >= 0:
      read_size = min(self.RECV_BLOCK_SIZE, length)
      data = self.rfile.read(read_size)
      if not data:
        break
      input_data.write(data)
      length -= len(data)
    return input_data.getvalue()

  def do_POST(self):
    """Process encrypted message bundles."""
    self.Control()

  @stats.Counted("frontend_request_count", fields=["http"])
  @stats.Timed("frontend_request_latency", fields=["http"])
  def Control(self):
    """Handle POSTS."""
    if not master.MASTER_WATCHER.IsMaster():
      # We shouldn't be getting requests from the client unless we
      # are the active instance.
      stats.STATS.IncrementCounter("frontend_inactive_request_count",
                                   fields=["http"])
      logging.info("Request sent to inactive frontend from %s",
                   self.client_address[0])

    # Get the api version
    try:
      api_version = int(cgi.parse_qs(self.path.split("?")[1])["api"][0])
    except (ValueError, KeyError, IndexError):
      # The oldest api version we support if not specified.
      api_version = 3

    with GRRHTTPServerHandler.active_counter_lock:
      GRRHTTPServerHandler.active_counter += 1
      stats.STATS.SetGaugeValue("frontend_active_count",
                                self.active_counter,
                                fields=["http"])

    try:
      length = int(self.headers.getheader("content-length"))

      request_comms = rdf_flows.ClientCommunication(self._GetPOSTData(length))

      # If the client did not supply the version in the protobuf we use the get
      # parameter.
      if not request_comms.api_version:
        request_comms.api_version = api_version

      # Reply using the same version we were requested with.
      responses_comms = rdf_flows.ClientCommunication(
          api_version=request_comms.api_version)

      source_ip = ipaddr.IPAddress(self.client_address[0])

      if source_ip.version == 6:
        source_ip = source_ip.ipv4_mapped or source_ip

      request_comms.orig_request = rdf_flows.HttpRequest(
          raw_headers=utils.SmartStr(self.headers),
          source_ip=utils.SmartStr(source_ip))

      request_start_time = time.ctime()
      source, nr_messages = self.server.frontend.HandleMessageBundles(
          request_comms, responses_comms)

      logging.info(
          "HTTP request from %s (%s) @ %s, %d bytes - %d messages received,"
          " %d messages sent.", source, utils.SmartStr(source_ip),
          request_start_time, length, nr_messages, responses_comms.num_messages)

      self.Send(responses_comms.SerializeToString())

    except communicator.UnknownClientCert:
      # "406 Not Acceptable: The server can only generate a response that is not
      # accepted by the client". This is because we can not encrypt for the
      # client appropriately.
      self.Send("Enrollment required", status=406)

    except Exception as e:  # pylint: disable=broad-except
      if flags.FLAGS.debug:
        pdb.post_mortem()

      logging.error("Had to respond with status 500: %s.", e)
      self.Send("Error", status=500)

    finally:
      with GRRHTTPServerHandler.active_counter_lock:
        GRRHTTPServerHandler.active_counter -= 1
        stats.STATS.SetGaugeValue("frontend_active_count",
                                  self.active_counter,
                                  fields=["http"])


class GRRHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
  """The GRR HTTP frontend server."""

  allow_reuse_address = True
  request_queue_size = 500

  address_family = socket.AF_INET6

  def __init__(self, server_address, handler, frontend=None, *args, **kwargs):
    stats.STATS.SetGaugeValue("frontend_max_active_count",
                              self.request_queue_size)

    if frontend:
      self.frontend = frontend
    else:
      self.frontend = flow.FrontEndServer(
          certificate=config_lib.CONFIG["Frontend.certificate"],
          private_key=config_lib.CONFIG["PrivateKeys.server_key"],
          max_queue_size=config_lib.CONFIG["Frontend.max_queue_size"],
          message_expiry_time=config_lib.CONFIG["Frontend.message_expiry_time"],
          max_retransmission_time=config_lib.CONFIG[
              "Frontend.max_retransmission_time"])
    self.server_cert = config_lib.CONFIG["Frontend.certificate"]

    (address, _) = server_address
    version = ipaddr.IPAddress(address).version
    if version == 4:
      self.address_family = socket.AF_INET
    elif version == 6:
      self.address_family = socket.AF_INET6

    logging.info("Will attempt to listen on %s", server_address)
    BaseHTTPServer.HTTPServer.__init__(self, server_address, handler, *args,
                                       **kwargs)


def CreateServer(frontend=None):
  """Start frontend http server."""
  max_port = config_lib.CONFIG.Get("Frontend.port_max",
                                   config_lib.CONFIG["Frontend.bind_port"])

  for port in range(config_lib.CONFIG["Frontend.bind_port"], max_port + 1):

    server_address = (config_lib.CONFIG["Frontend.bind_address"], port)
    try:
      httpd = GRRHTTPServer(server_address,
                            GRRHTTPServerHandler,
                            frontend=frontend)
      break
    except socket.error as e:
      if e.errno == socket.errno.EADDRINUSE and port < max_port:
        logging.info("Port %s in use, trying %s", port, port + 1)
      else:
        raise

  sa = httpd.socket.getsockname()
  logging.info("Serving HTTP on %s port %d ...", sa[0], sa[1])
  return httpd


def Serve(server):
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass


def main(unused_argv):
  """Main."""
  config_lib.CONFIG.AddContext("HTTPServer Context")

  startup.Init()

  httpd = CreateServer()

  startup.DropPrivileges()

  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    print "Caught keyboard interrupt, stopping"


if __name__ == "__main__":
  flags.StartMain(main)
