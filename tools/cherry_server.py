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

"""This is the CherryPy based version of the GRR HTTP Server."""


import sys
import time


import cherrypy

from grr.client import conf
from grr.client import conf as flags

# pylint: disable=W0611
# pylint: enable=W0611

from grr.lib import communicator
from grr.lib import mongo_data_store
from grr.lib import flow
from grr.lib import log
from grr.lib import registry
# pylint: disable=W0611
from grr.lib import server_flags
# pylint: enable=W0611
from grr.proto import jobs_pb2

FLAGS = flags.FLAGS

# pylint: disable=C6409


class GrrCherryServer(object):
  """The CherryPy version of the GRR http server."""

  def __init__(self):
    self.serverpem = open(FLAGS.server_cert, "rb").read()
    registry.Init()
    self.logger = log.GrrLogger(component="Cherryserver")
    self.front_end = flow.FrontEndServer(
        FLAGS.server_private_key, self.logger,
        max_queue_size=FLAGS.max_queue_size,
        message_expiry_time=FLAGS.message_expiry_time,
        max_retransmission_time=FLAGS.max_retransmission_time)

  @cherrypy.expose
  def server_pem(self):
    return self.serverpem

  @cherrypy.expose
  def control_py(self):
    """GRR HTTP handler for receiving client posts."""

    try:
      data = cherrypy.request.body.read()
      request_comms = jobs_pb2.ClientCommunication()
      request_comms.ParseFromString(data)

      responses_comms = jobs_pb2.ClientCommunication()

      self.front_end.HandleMessageBundles(
          request_comms, responses_comms)

      return responses_comms.SerializeToString()
    except communicator.UnknownClientCert:
      cherrypy.response.status = 406
      return "Enrollment required"


def main(unused_argv):
  """Main."""
  # TODO(user): this always serves on port 8080 by default.
  cherrypy.quickstart(GrrCherryServer())

if __name__ == "__main__":
  if sys.stderr.isatty(): FLAGS.logtostderr = True
  conf.StartMain(main)
