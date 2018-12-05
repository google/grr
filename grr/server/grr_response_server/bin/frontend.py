#!/usr/bin/env python
"""This is the GRR frontend HTTP Server."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import cgi
import io
import logging
import pdb
import socket
import threading


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems
from http import server as http_server
import ipaddr
import socketserver

from google.protobuf import json_format

# pylint: disable=unused-import,g-bad-import-order
from grr_response_server import server_plugins
# pylint: enable=unused-import, g-bad-import-order

from grr_response_core import config
from grr_response_core.config import server as config_server
from grr_response_core.lib import communicator
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_utils
from grr_response_server import aff4
from grr_response_server import frontend_lib
from grr_response_server import master
from grr_response_server import server_logging
from grr_response_server import server_startup


class GRRHTTPServerHandler(http_server.BaseHTTPRequestHandler):
  """GRR HTTP handler for receiving client posts."""

  statustext = {
      200: "200 OK",
      404: "404 Not Found",
      406: "406 Not Acceptable",
      500: "500 Internal Server Error"
  }

  active_counter_lock = threading.Lock()
  active_counter = 0

  def _IncrementActiveCount(self):
    with GRRHTTPServerHandler.active_counter_lock:
      GRRHTTPServerHandler.active_counter += 1
      stats_collector_instance.Get().SetGaugeValue(
          "frontend_active_count", self.active_counter, fields=["http"])

  def _DecrementActiveCount(self):
    with GRRHTTPServerHandler.active_counter_lock:
      GRRHTTPServerHandler.active_counter -= 1
      stats_collector_instance.Get().SetGaugeValue(
          "frontend_active_count", self.active_counter, fields=["http"])

  def Send(self,
           data,
           status=200,
           ctype="application/octet-stream",
           additional_headers=None,
           last_modified=0):
    """Sends a response to the client."""
    if additional_headers:
      additional_header_strings = [
          "%s: %s\r\n" % (name, val)
          for name, val in iteritems(additional_headers)
      ]
    else:
      additional_header_strings = []

    header = ""
    header += "HTTP/1.0 %s\r\n" % self.statustext[status]
    header += "Server: GRR Server\r\n"
    header += "Content-type: %s\r\n" % ctype
    header += "Content-Length: %d\r\n" % len(data)
    header += "Last-Modified: %s\r\n" % self.date_time_string(last_modified)
    header += "".join(additional_header_strings)
    header += "\r\n"

    self.wfile.write(header.encode("utf-8"))
    self.wfile.write(data)

  rekall_profile_path = "/rekall_profiles"

  static_content_path = "/static/"

  def do_GET(self):  # pylint: disable=g-bad-name
    """Serve the server pem with GET requests."""
    self._IncrementActiveCount()
    try:
      if self.path.startswith("/server.pem"):
        stats_collector_instance.Get().IncrementCounter(
            "frontend_http_requests", fields=["cert", "http"])
        self.ServerPem()
      elif self.path.startswith(self.rekall_profile_path):
        stats_collector_instance.Get().IncrementCounter(
            "frontend_http_requests", fields=["rekall", "http"])
        self.ServeRekallProfile(self.path)
      elif self.path.startswith(self.static_content_path):
        stats_collector_instance.Get().IncrementCounter(
            "frontend_http_requests", fields=["static", "http"])
        self.ServeStatic(self.path[len(self.static_content_path):])
    finally:
      self._DecrementActiveCount()

  def ServeRekallProfile(self, path):
    """This servers rekall profiles from the frontend server.

    Format is /rekall_profiles/<version>/<profile_name>

    Args:
      path: The path the client requested.
    """
    logging.debug("Rekall profile request from IP %s for %s",
                  self.client_address[0], path)
    remaining_path = path[len(self.rekall_profile_path):]
    if not remaining_path.startswith("/"):
      self.Send("Error serving profile.", status=500, ctype="text/plain")
      return

    components = remaining_path[1:].split("/", 1)

    if len(components) != 2:
      self.Send("Error serving profile.", status=500, ctype="text/plain")
      return
    version, name = components
    profile = self.server.frontend.GetRekallProfile(name, version=version)
    if not profile:
      self.Send("Profile not found.", status=404, ctype="text/plain")
      return

    json_data = json_format.MessageToJson(profile.AsPrimitiveProto())

    sanitized_data = ")]}'\n" + json_data.replace("<", r"\u003c").replace(
        ">", r"\u003e")

    additional_headers = {
        "Content-Disposition": "attachment; filename=response.json",
        "X-Content-Type-Options": "nosniff"
    }
    self.Send(
        sanitized_data,
        status=200,
        ctype="application/json",
        additional_headers=additional_headers)

  AFF4_READ_BLOCK_SIZE = 10 * 1024 * 1024

  def ServeStatic(self, path):
    aff4_path = aff4.FACTORY.GetStaticContentPath().Add(path)
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
    self.Send(self.server.server_cert.AsPEM())

  RECV_BLOCK_SIZE = 8192

  def _GetPOSTData(self, length):
    # During our tests we have encountered some issue with the socket library
    # that would stall for a long time when calling socket.recv(n) with a large
    # n. rfile.read() passes the length down to socket.recv() so it's much
    # faster to read the data in small 8k chunks.
    input_data = io.BytesIO()
    while length >= 0:
      read_size = min(self.RECV_BLOCK_SIZE, length)
      data = self.rfile.read(read_size)
      if not data:
        break
      input_data.write(data)
      length -= len(data)
    return input_data.getvalue()

  def _GenerateChunk(self, length):
    """Generates data for a single chunk."""

    while 1:
      to_read = min(length, self.RECV_BLOCK_SIZE)
      if to_read == 0:
        return

      data = self.rfile.read(to_read)
      if not data:
        return

      yield data
      length -= len(data)

  def GenerateFileData(self):
    """Generates the file data for a chunk encoded file."""
    # Handle chunked encoding:
    # https://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.6.1
    while 1:
      line = self.rfile.readline()
      # We do not support chunked extensions, just ignore them.
      chunk_size = int(line.split(";")[0], 16)
      if chunk_size == 0:
        break

      for chunk in self._GenerateChunk(chunk_size):
        yield chunk

      # Chunk is followed by \r\n.
      lf = self.rfile.read(2)
      if lf != "\r\n":
        raise IOError("Unable to parse chunk.")

    # Skip entity headers.
    for header in self.rfile.readline():
      if not header:
        break

  def do_POST(self):  # pylint: disable=g-bad-name
    """Process encrypted message bundles."""
    self._IncrementActiveCount()
    try:
      if self.path.startswith("/upload"):
        stats_collector_instance.Get().IncrementCounter(
            "frontend_http_requests", fields=["upload", "http"])

        logging.error("Requested no longer supported file upload through HTTP.")
        self.Send("File upload though HTTP is no longer supported", status=404)
      else:
        stats_collector_instance.Get().IncrementCounter(
            "frontend_http_requests", fields=["control", "http"])
        self.Control()

    except Exception as e:  # pylint: disable=broad-except
      if flags.FLAGS.debug:
        pdb.post_mortem()

      logging.exception("Had to respond with status 500.")
      self.Send("Error: %s" % e, status=500)
    finally:
      self._DecrementActiveCount()

  @stats_utils.Counted("frontend_request_count", fields=["http"])
  @stats_utils.Timed("frontend_request_latency", fields=["http"])
  def Control(self):
    """Handle POSTS."""
    if not master.MASTER_WATCHER.IsMaster():
      # We shouldn't be getting requests from the client unless we
      # are the active instance.
      stats_collector_instance.Get().IncrementCounter(
          "frontend_inactive_request_count", fields=["http"])
      logging.info("Request sent to inactive frontend from %s",
                   self.client_address[0])

    # Get the api version
    try:
      api_version = int(cgi.parse_qs(self.path.split("?")[1])["api"][0])
    except (ValueError, KeyError, IndexError):
      # The oldest api version we support if not specified.
      api_version = 3

    try:
      content_length = self.headers.getheader("content-length")
      if not content_length:
        raise IOError("No content-length header provided.")

      length = int(content_length)

      request_comms = rdf_flows.ClientCommunication.FromSerializedString(
          self._GetPOSTData(length))

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
          timestamp=rdfvalue.RDFDatetime.Now().AsMicrosecondsSinceEpoch(),
          raw_headers=utils.SmartStr(self.headers),
          source_ip=utils.SmartStr(source_ip))

      source, nr_messages = self.server.frontend.HandleMessageBundles(
          request_comms, responses_comms)

      server_logging.LOGGER.LogHttpFrontendAccess(
          request_comms.orig_request, source=source, message_count=nr_messages)

      self.Send(responses_comms.SerializeToString())

    except communicator.UnknownClientCert:
      # "406 Not Acceptable: The server can only generate a response that is not
      # accepted by the client". This is because we can not encrypt for the
      # client appropriately.
      self.Send("Enrollment required", status=406)


class GRRHTTPServer(socketserver.ThreadingMixIn, http_server.HTTPServer):
  """The GRR HTTP frontend server."""

  allow_reuse_address = True
  request_queue_size = 500

  address_family = socket.AF_INET6

  def __init__(self, server_address, handler, frontend=None, **kwargs):
    stats_collector_instance.Get().SetGaugeValue("frontend_max_active_count",
                                                 self.request_queue_size)

    if frontend:
      self.frontend = frontend
    else:
      self.frontend = frontend_lib.FrontEndServer(
          certificate=config.CONFIG["Frontend.certificate"],
          private_key=config.CONFIG["PrivateKeys.server_key"],
          max_queue_size=config.CONFIG["Frontend.max_queue_size"],
          message_expiry_time=config.CONFIG["Frontend.message_expiry_time"],
          max_retransmission_time=config
          .CONFIG["Frontend.max_retransmission_time"])
    self.server_cert = config.CONFIG["Frontend.certificate"]

    (address, _) = server_address
    version = ipaddr.IPAddress(address).version
    if version == 4:
      self.address_family = socket.AF_INET
    elif version == 6:
      self.address_family = socket.AF_INET6

    logging.info("Will attempt to listen on %s", server_address)
    http_server.HTTPServer.__init__(self, server_address, handler, **kwargs)

  def Shutdown(self):
    self.shutdown()


def CreateServer(frontend=None):
  """Start frontend http server."""
  max_port = config.CONFIG.Get("Frontend.port_max",
                               config.CONFIG["Frontend.bind_port"])

  for port in range(config.CONFIG["Frontend.bind_port"], max_port + 1):

    server_address = (config.CONFIG["Frontend.bind_address"], port)
    try:
      httpd = GRRHTTPServer(
          server_address, GRRHTTPServerHandler, frontend=frontend)
      break
    except socket.error as e:
      if e.errno == socket.errno.EADDRINUSE and port < max_port:
        logging.info("Port %s in use, trying %s", port, port + 1)
      else:
        raise

  sa = httpd.socket.getsockname()
  logging.info("Serving HTTP on %s port %d ...", sa[0], sa[1])
  return httpd


def main(argv):
  """Main."""
  del argv  # Unused.

  if flags.FLAGS.version:
    print("GRR frontend {}".format(config_server.VERSION["packageversion"]))
    return

  config.CONFIG.AddContext("HTTPServer Context")

  server_startup.Init()

  httpd = CreateServer()

  server_startup.DropPrivileges()

  try:
    httpd.serve_forever()
  except KeyboardInterrupt:
    print("Caught keyboard interrupt, stopping")


if __name__ == "__main__":
  flags.StartMain(main)
