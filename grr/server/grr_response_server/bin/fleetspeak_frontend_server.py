#!/usr/bin/env python
"""This is the GRR frontend FS Server."""
import logging

from typing import Iterable, Dict

import grpc

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import communicator
from grr_response_server import data_store
from grr_response_server import fleetspeak_utils
from grr_response_server import frontend_lib
from fleetspeak.src.common.proto.fleetspeak import common_pb2


class GRRFSServer:
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
  def Process(self, fs_msg: common_pb2.Message, context: grpc.ServicerContext):
    """Processes a single fleetspeak message."""
    try:
      validation_info = dict(fs_msg.validation_info.tags)
      if fs_msg.message_type == "GrrMessage":
        grr_message = rdf_flows.GrrMessage.FromSerializedBytes(
            fs_msg.data.value)
        self._ProcessGRRMessages(fs_msg.source.client_id, [grr_message],
                                 validation_info)
      elif fs_msg.message_type == "MessageList":
        packed_messages = rdf_flows.PackedMessageList.FromSerializedBytes(
            fs_msg.data.value)
        message_list = communicator.Communicator.DecompressMessageList(
            packed_messages)
        self._ProcessGRRMessages(fs_msg.source.client_id, message_list.job,
                                 validation_info)
      else:
        logging.error("Received message with unrecognized message_type: %s",
                      fs_msg.message_type)
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
    except Exception:
      logging.exception("Exception processing message: %s", fs_msg)
      raise

  def _ProcessGRRMessages(self, fs_client_id: bytes,
                          grr_messages: Iterable[rdf_flows.GrrMessage],
                          validation_info: Dict[str, str]):
    """Handles messages from GRR clients received via Fleetspeak.

    This method updates the last-ping timestamp of the client before beginning
    processing.

    Args:
      fs_client_id: The Fleetspeak client-id for the client.
      grr_messages: An Iterable of GrrMessages.
      validation_info:
    """
    grr_client_id = fleetspeak_utils.FleetspeakIDToGRRID(fs_client_id)
    try:
      for grr_message in grr_messages:
        grr_message.source = grr_client_id
        grr_message.auth_state = (
            rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)
      client_is_new = self.frontend.EnrolFleetspeakClient(
          client_id=grr_client_id)
      if not client_is_new:
        data_store.REL_DB.WriteClientMetadata(
            grr_client_id,
            last_ping=rdfvalue.RDFDatetime.Now(),
            fleetspeak_validation_info=validation_info)
      self.frontend.ReceiveMessages(
          client_id=grr_client_id, messages=grr_messages)
    except Exception:
      logging.exception("Exception receiving messages from: %s", grr_client_id)
      raise
