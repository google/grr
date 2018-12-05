#!/usr/bin/env python
"""This is the GRR frontend FS Server."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import time
import grpc


# pylint: disable=unused-import,g-bad-import-order
from grr_response_server import server_plugins
# pylint: enable=unused-import, g-bad-import-order

from grr_response_core import config
from grr_response_core.lib import communicator
from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.stats import stats_utils
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server import frontend_lib
from grr_response_server import server_startup


class GRRFSServer(object):
  """The GRR FS frontend server.

  This class is only responsible for the read end of Fleetspeak comms. The write
  end is used in Fleetspeak frontend, worker and admin_ui processes.
  """

  def __init__(self):
    self.frontend = frontend_lib.FrontEndServer(
        certificate=config.CONFIG["Frontend.certificate"],
        private_key=config.CONFIG["PrivateKeys.server_key"],
        max_queue_size=config.CONFIG["Frontend.max_queue_size"],
        message_expiry_time=config.CONFIG["Frontend.message_expiry_time"],
        max_retransmission_time=config.CONFIG[
            "Frontend.max_retransmission_time"])

  @stats_utils.Counted("frontend_request_count", fields=["fleetspeak"])
  @stats_utils.Timed("frontend_request_latency", fields=["fleetspeak"])
  def Process(self, fs_msg, context):
    """Processes a single fleetspeak message."""
    try:
      if fs_msg.message_type == "GrrMessage":
        self._ProcessGrrMessage(fs_msg)
        return

      if fs_msg.message_type == "MessageList":
        self._ProcessMessageList(fs_msg)
        return

      logging.error("Received message with unrecognized message_type: %s",
                    fs_msg.message_type)
      context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
    except Exception as e:
      logging.error("Exception processing message: %s", str(e))
      raise

  def _ProcessGrrMessage(self, fs_msg):
    """Process a FS message when message_type is GrrMessage."""
    grr_id = fleetspeak_utils.FleetspeakIDToGRRID(fs_msg.source.client_id)

    msg = rdf_flows.GrrMessage.FromSerializedString(fs_msg.data.value)
    msg.source = grr_id

    # Fleetspeak ensures authentication.
    msg.auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    self.frontend.EnrolFleetspeakClient(client_id=grr_id)
    self.frontend.ReceiveMessages(client_id=grr_id, messages=[msg])

  def _ProcessMessageList(self, fs_msg):
    """Process a FS message when message_type is MessageList."""
    grr_id = fleetspeak_utils.FleetspeakIDToGRRID(fs_msg.source.client_id)

    msg_list = rdf_flows.PackedMessageList.FromSerializedString(
        fs_msg.data.value)
    msg_list = communicator.Communicator.DecompressMessageList(msg_list)

    for msg in msg_list.job:
      msg.source = grr_id
      msg.auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    self.frontend.EnrolFleetspeakClient(client_id=grr_id)
    self.frontend.ReceiveMessages(client_id=grr_id, messages=msg_list.job)


def main(argv):
  del argv  # Unused.

  config.CONFIG.AddContext("FleetspeakFrontend Context")

  server_startup.Init()
  server_startup.DropPrivileges()

  fleetspeak_connector.Init()

  fsd = GRRFSServer()
  fleetspeak_connector.CONN.Listen(fsd.Process)

  logging.info("Serving through Fleetspeak ...")

  try:
    while True:
      time.sleep(600)
  except KeyboardInterrupt:
    print("Caught keyboard interrupt, stopping")


if __name__ == "__main__":
  flags.StartMain(main)
