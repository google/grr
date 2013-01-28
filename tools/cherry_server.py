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


import cherrypy

from grr.client import conf
from grr.client import conf as flags

from grr.lib import communicator
from grr.lib import flow
from grr.lib import key_utils
from grr.lib import log
from grr.lib import rdfvalue
from grr.lib import registry
# pylint: disable=W0611
from grr.lib import server_plugins
# pylint: enable=W0611

FLAGS = flags.FLAGS

# pylint: disable=C6409


class GrrCherryServer(object):
  """The CherryPy version of the GRR http server."""

  def __init__(self):
    self.serverpem = key_utils.GetCert("Server_Public_Cert")
    registry.Init()
    self.logger = log.GrrLogger(component="Cherryserver")
    self.front_end = flow.FrontEndServer(
        "Server_Private_Key", self.logger,
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
      request_comms = rdfvalue.ClientCommunication(data)

      responses_comms = rdfvalue.ClientCommunication()

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
