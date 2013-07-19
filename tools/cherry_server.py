#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""This is the CherryPy based version of the GRR HTTP Server.

Note that this is unmaintained and untested, but left here as it may be useful
for others in the future.
"""



import cherrypy

from grr.lib import communicator
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import server_plugins  # pylint: disable=unused-import
from grr.lib import startup
from grr.tools import http_server  # pylint: disable=unused-import
# pylint: disable=g-bad-name


class GrrCherryServer(object):
  """The CherryPy version of the GRR http server."""

  def __init__(self):
    self.serverpem = config_lib.CONFIG["Frontend.certificate"]
    startup.Init()
    self.front_end = flow.FrontEndServer(
        certificate=config_lib.CONFIG["Frontend.certificate"],
        private_key=config_lib.CONFIG["PrivateKeys.server_key"],
        max_queue_size=config_lib.CONFIG["Frontend.max_queue_size"],
        message_expiry_time=config_lib.CONFIG["Frontend.message_expiry_time"],
        max_retransmission_time=config_lib.CONFIG[
            "Frontend.max_retransmission_time"])

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
  flags.StartMain(main)
