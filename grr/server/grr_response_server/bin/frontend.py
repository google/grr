#!/usr/bin/env python
"""This is the GRR frontend HTTP Server."""

from http import server as http_server
import io
import ipaddress
import logging
import pdb
import socket
import socketserver
import threading
from urllib import parse as urlparse

from absl import app
from absl import flags

from grr_response_core import config
from grr_response_core.config import server as config_server
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import compatibility
from grr_response_server import communicator
from grr_response_server import frontend_lib
from grr_response_server import server_logging
from grr_response_server import server_startup

_VERSION = flags.DEFINE_bool(
    "version",
    default=False,
    allow_override=True,
    help="Print the GRR frontend version number and exit immediately.")


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
      frontend_lib.FRONTEND_ACTIVE_COUNT.SetValue(
          self.active_counter, fields=["http"])

  def _DecrementActiveCount(self):
    with GRRHTTPServerHandler.active_counter_lock:
      GRRHTTPServerHandler.active_counter -= 1
      frontend_lib.FRONTEND_ACTIVE_COUNT.SetValue(
          self.active_counter, fields=["http"])

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
          for name, val in additional_headers.items()
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

  static_content_path = "/static/"

  def do_GET(self):  # pylint: disable=g-bad-name
    """Serve the server pem with GET requests."""
    self._IncrementActiveCount()
    try:
      if self.path.startswith("/server.pem"):
        frontend_lib.FRONTEND_HTTP_REQUESTS.Increment(fields=["cert", "http"])
        self.ServerPem()
      elif self.path.startswith(self.static_content_path):
        frontend_lib.FRONTEND_HTTP_REQUESTS.Increment(fields=["static", "http"])
        self.ServeStatic(self.path[len(self.static_content_path):])
    finally:
      self._DecrementActiveCount()

  def ServerPem(self):
    self.Send(self.server.server_cert.AsPEM())

  RECV_BLOCK_SIZE = 8192

  def _GetPOSTData(self, length):
    """Returns a specified number of bytes of the POST data."""
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
        frontend_lib.FRONTEND_HTTP_REQUESTS.Increment(fields=["upload", "http"])

        logging.error("Requested no longer supported file upload through HTTP.")
        self.Send(b"File upload though HTTP is no longer supported", status=404)
      else:
        frontend_lib.FRONTEND_HTTP_REQUESTS.Increment(
            fields=["control", "http"])
        self.Control()

    except Exception as e:  # pylint: disable=broad-except
      if flags.FLAGS.pdb_post_mortem:
        pdb.post_mortem()

      logging.exception("Had to respond with status 500.")
      self.Send(("Error: %s" % e).encode("utf-8"), status=500)
    finally:
      self._DecrementActiveCount()

  @frontend_lib.FRONTEND_REQUEST_COUNT.Counted(fields=["http"])
  @frontend_lib.FRONTEND_REQUEST_LATENCY.Timed(fields=["http"])
  def Control(self):
    """Handle POSTS."""
    # Get the api version
    try:
      api_version = int(urlparse.parse_qs(self.path.split("?")[1])["api"][0])
    except (ValueError, KeyError, IndexError):
      # The oldest api version we support if not specified.
      api_version = 3

    try:
      if compatibility.PY2:
        content_length = self.headers.getheader("content-length")
      else:
        content_length = self.headers.get("content-length")
      if not content_length:
        raise IOError("No content-length header provided.")

      length = int(content_length)

      request_comms = rdf_flows.ClientCommunication.FromSerializedBytes(
          self._GetPOSTData(length))

      # If the client did not supply the version in the protobuf we use the get
      # parameter.
      if not request_comms.api_version:
        request_comms.api_version = api_version

      # Reply using the same version we were requested with.
      responses_comms = rdf_flows.ClientCommunication(
          api_version=request_comms.api_version)

      # TODO: Python's documentation is just plain terrible and
      # does not explain what `client_address` exactly is or what type does it
      # have (because its Python, why would they bother) so just to be on the
      # safe side, we anticipate byte-string addresses in Python 2 and convert
      # that if needed. On Python 3 these should be always unicode strings, so
      # once support for Python 2 is dropped this branch can be removed.
      address = self.client_address[0]
      if compatibility.PY2 and isinstance(self.client_address[0], bytes):
        address = address.decode("ascii")
      source_ip = ipaddress.ip_address(address)

      if source_ip.version == 6:
        source_ip = source_ip.ipv4_mapped or source_ip

      request_comms.orig_request = rdf_flows.HttpRequest(
          timestamp=rdfvalue.RDFDatetime.Now(),
          raw_headers=str(self.headers),
          source_ip=str(source_ip))

      source, nr_messages = self.server.frontend.HandleMessageBundles(
          request_comms, responses_comms)

      server_logging.LOGGER.LogHttpFrontendAccess(
          request_comms.orig_request, source=source, message_count=nr_messages)

      self.Send(responses_comms.SerializeToBytes())

    except communicator.UnknownClientCertError:
      # "406 Not Acceptable: The server can only generate a response that is not
      # accepted by the client". This is because we can not encrypt for the
      # client appropriately.
      self.Send(b"Enrollment required", status=406)


class GRRHTTPServer(socketserver.ThreadingMixIn, http_server.HTTPServer):
  """The GRR HTTP frontend server."""

  allow_reuse_address = True
  request_queue_size = 500

  address_family = socket.AF_INET6

  def __init__(self, server_address, handler, frontend=None, **kwargs):
    frontend_lib.FRONTEND_MAX_ACTIVE_COUNT.SetValue(self.request_queue_size)

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
    version = ipaddress.ip_address(address).version
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

  if _VERSION.value:
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
  app.run(main)
