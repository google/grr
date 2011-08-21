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
import pdb
import SocketServer
import sys
import time


from grr.client import conf
from grr.client import conf as flags


from grr.lib import communicator
from grr.lib import mongo_data_store
from grr.lib import flow
from grr.lib import log
from grr.proto import jobs_pb2


flags.DEFINE_integer("max_queue_size", 50,
                     "Maximum number of messages to queue for the client.")

flags.DEFINE_integer("max_receiver_threads", 10,
                     "Maximum number of threads to use for receivers.")

flags.DEFINE_integer("max_retransmission_time", 10,
                     "Maximum number of times we are allowed to "
                     "retransmit a request until it fails.")

flags.DEFINE_integer("message_expiry_time", 40,
                     "Maximum time messages remain valid within the system.")

flags.DEFINE_string("bind_address", "127.0.0.1", "The ip address to bind.")

flags.DEFINE_integer("bind_port", 8080, "The port to bind.")

flags.DEFINE_string("keystore_path", "grr/keys/test/server.pem",
                    "The path to the server cert and key pair")

FLAGS = flags.FLAGS



class GRRHTTPServerHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  """GRR HTTP handler for receiving client posts."""

  def do_GET(self):
    """Server the server pem with GET requests."""
    if self.path == "/server.pem":
      self.Send(self.server.server_pem)

  def Send(self, data, status=200, ctype="application/octet-stream",
           last_modified=0):
    self.send_response(status)
    self.send_header("Content-type", ctype)
    self.send_header("Content-Length", len(data))
    self.send_header("Last-Modified", self.date_time_string(last_modified))
    self.end_headers()
    self.wfile.write(data)

  def do_POST(self):
    """Process encrypted message bundles."""
    try:
      length = int(self.headers.getheader("content-length"))
      input_data = self.rfile.read(length)

      parameters = dict(cgi.parse_qsl(input_data))

      request_comms = jobs_pb2.ClientCommunication()
      request_comms.ParseFromString(parameters["data"].decode("base64"))

      responses_comms = jobs_pb2.ClientCommunication()

      event_id = self.server.logger.GetNewEventId(time.time())
      self.server.front_end.HandleMessageBundles(
          request_comms, responses_comms, event_id)

      self.Send(responses_comms.SerializeToString())
    except communicator.UnknownClientCert:
      # "406 Not Acceptable: The server can only generate a response that is not
      # accepted by the client". This is because we can not encrypt for the
      # client appropriately.
      return self.Send("Enrollment required", status=406)

    except Exception:
      if FLAGS.debug:
        pdb.post_mortem()

      return self.Send("Error", status=500)


class GRRHTTPServer(BaseHTTPServer.HTTPServer, SocketServer.ThreadingMixIn):
  """The GRR HTTP frontend server."""

  allow_reuse_address = True
  request_queue_size = 500

  def __init__(self, *args, **kwargs):
    self.logger = log.GrrLogger(component=self.__class__.__name__)

    self.front_end = flow.FrontEndServer(
        FLAGS.keystore_path, self.logger, max_queue_size=FLAGS.max_queue_size,
        message_expiry_time=FLAGS.message_expiry_time,
        max_retransmission_time=FLAGS.max_retransmission_time)

    self.server_pem = open(FLAGS.keystore_path, "rb").read()

    BaseHTTPServer.HTTPServer.__init__(self, *args, **kwargs)


def main(unused_argv):
  """Main."""
  flow.Init()

  server_address = (FLAGS.bind_address, FLAGS.bind_port)
  httpd = GRRHTTPServer(server_address, GRRHTTPServerHandler)

  sa = httpd.socket.getsockname()
  print "Serving HTTP on", sa[0], "port", sa[1], "..."
  httpd.serve_forever()

if __name__ == "__main__":
  if sys.stderr.isatty(): FLAGS.logtostderr = True
  conf.StartMain(main)
