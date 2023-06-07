#!/usr/bin/env python
"""This is the GRR frontend FS Server."""
import logging

from typing import Sequence

import grpc

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.stats import metrics
from grr_response_server import communicator
from grr_response_server import data_store
from grr_response_server import fleetspeak_utils
from grr_response_server import frontend_lib
from fleetspeak.src.common.proto.fleetspeak import common_pb2
from grr_response_proto import rrg_pb2


INCOMING_FLEETSPEAK_MESSAGES = metrics.Counter(
    "incoming_fleetspeak_messages", fields=[("status", str)]
)


# TODO: remove after the issue is fixed.
CLIENT_ID_SKIP_LIST = frozenset(
    [
    ]
)


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
    fs_client_id = fs_msg.source.client_id
    grr_client_id = fleetspeak_utils.FleetspeakIDToGRRID(fs_client_id)

    if fs_msg.is_blocklisted_source:
      INCOMING_FLEETSPEAK_MESSAGES.Increment(fields=["SKIPPED_BLOCKLISTED"])
      return

    # TODO: remove after the issue is fixed.
    if grr_client_id in CLIENT_ID_SKIP_LIST:
      INCOMING_FLEETSPEAK_MESSAGES.Increment(fields=["SKIPPED_SKIP_LIST"])
      return

    validation_info = dict(fs_msg.validation_info.tags)

    try:
      if fs_msg.source.service_name == "RRG":
        rrg_support = True
      else:
        # `None` leaves the bit as it is stored in the database and `False` sets
        # it to false. Since the server can receive messages from both agents,
        # we don't want to set the `rrg_support` bit to `False` each time the
        # Python agent sends something.
        rrg_support = None

      client_is_new = self.frontend.EnrolFleetspeakClient(grr_client_id)
      # TODO: We want to update metadata even if client is not new
      # but is RRG-supported to set the `rrg_support` bit for older clients. In
      # the future we should devise a smarter way of doing this but for now the
      # amount of RRG-supported clients should be neglegible.
      if not client_is_new or rrg_support:
        data_store.REL_DB.WriteClientMetadata(
            grr_client_id,
            last_ping=rdfvalue.RDFDatetime.Now(),
            fleetspeak_validation_info=validation_info,
            rrg_support=rrg_support,
        )

      if fs_msg.message_type == "GrrMessage":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(fields=["PROCESS_GRR"])

        grr_message = rdf_flows.GrrMessage.FromSerializedBytes(
            fs_msg.data.value)
        self._ProcessGRRMessages(grr_client_id, [grr_message])
      elif fs_msg.message_type == "MessageList":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(
            fields=["PROCESS_GRR_MESSAGE_LIST"]
        )

        packed_messages = rdf_flows.PackedMessageList.FromSerializedBytes(
            fs_msg.data.value)
        message_list = communicator.Communicator.DecompressMessageList(
            packed_messages)
        self._ProcessGRRMessages(grr_client_id, message_list.job)
      elif fs_msg.message_type == "rrg.Response":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(fields=["PROCESS_RRG_RESPONSE"])

        rrg_response = rrg_pb2.Response()
        rrg_response.ParseFromString(fs_msg.data.value)

        self.frontend.ReceiveRRGResponse(grr_client_id, rrg_response)
      elif fs_msg.message_type == "rrg.Parcel":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(fields=["PROCESS_RRG_PARCEL"])

        rrg_parcel = rrg_pb2.Parcel()
        rrg_parcel.ParseFromString(fs_msg.data.value)

        self.frontend.ReceiveRRGParcel(grr_client_id, rrg_parcel)
      else:
        INCOMING_FLEETSPEAK_MESSAGES.Increment(fields=["INVALID"])

        logging.error("Received message with unrecognized message_type: %s",
                      fs_msg.message_type)
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
    except Exception:
      logging.exception("Exception processing message: %s", fs_msg)
      raise

  def _ProcessGRRMessages(
      self,
      grr_client_id: str,
      grr_messages: Sequence[rdf_flows.GrrMessage],
  ) -> None:
    """Handles messages from GRR clients received via Fleetspeak.

    This method updates the last-ping timestamp of the client before beginning
    processing.

    Args:
      grr_client_id: The unique identifier of the GRR client.
      grr_messages: A sequence of `GrrMessage`.
    """
    try:
      for grr_message in grr_messages:
        grr_message.source = grr_client_id
        grr_message.auth_state = (
            rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)
      self.frontend.ReceiveMessages(
          client_id=grr_client_id, messages=grr_messages)
    except Exception:
      logging.exception("Exception receiving messages from: %s", grr_client_id)
      raise
