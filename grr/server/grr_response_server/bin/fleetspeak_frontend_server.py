#!/usr/bin/env python
"""This is the GRR frontend FS Server."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import grpc

from grr_response_core import config
from grr_response_core.lib import communicator
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import data_store
from grr_response_server import fleetspeak_utils
from grr_response_server import frontend_lib


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
        max_retransmission_time=config
        .CONFIG["Frontend.max_retransmission_time"])

  @frontend_lib.FRONTEND_REQUEST_COUNT.Counted(fields=["fleetspeak"])
  @frontend_lib.FRONTEND_REQUEST_LATENCY.Timed(fields=["fleetspeak"])
  def Process(self, fs_msg, context):
    """Processes a single fleetspeak message."""
    try:
      if fs_msg.message_type == "GrrMessage":
        grr_message = rdf_flows.GrrMessage.FromSerializedBytes(
            fs_msg.data.value)
        self._ProcessGRRMessages(fs_msg.source.client_id, [grr_message])
      elif fs_msg.message_type == "MessageList":
        packed_messages = rdf_flows.PackedMessageList.FromSerializedBytes(
            fs_msg.data.value)
        message_list = communicator.Communicator.DecompressMessageList(
            packed_messages)
        self._ProcessGRRMessages(fs_msg.source.client_id, message_list.job)
      else:
        logging.error("Received message with unrecognized message_type: %s",
                      fs_msg.message_type)
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
    except Exception as e:
      logging.error("Exception processing message: %s", str(e))
      raise

  def _ProcessGRRMessages(self, fs_client_id, grr_messages):
    """Handles messages from GRR clients received via Fleetspeak.

    This method updates the last-ping timestamp of the client before beginning
    processing.

    Args:
      fs_client_id: The Fleetspeak client-id for the client.
      grr_messages: An Iterable of GrrMessages.
    """
    grr_client_id = fleetspeak_utils.FleetspeakIDToGRRID(fs_client_id)
    for grr_message in grr_messages:
      grr_message.source = grr_client_id
      grr_message.auth_state = (
          rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)
    client_is_new = self.frontend.EnrolFleetspeakClient(client_id=grr_client_id)
    if not client_is_new:
      data_store.REL_DB.WriteClientMetadata(
          grr_client_id, last_ping=rdfvalue.RDFDatetime.Now())
    self.frontend.ReceiveMessages(
        client_id=grr_client_id, messages=grr_messages)
