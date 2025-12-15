#!/usr/bin/env python
"""This is the GRR frontend FS Server."""

from collections.abc import Sequence
import logging
import sys
from typing import Optional

import grpc

from google.protobuf import message as proto2_message
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import mig_flows
from grr_response_core.lib.util import cache
from grr_response_core.stats import metrics
from grr_response_proto import jobs_pb2
from grr_response_server import communicator
from grr_response_server import data_store
from grr_response_server import fleetspeak
from grr_response_server import fleetspeak_utils
from grr_response_server import frontend_lib
from fleetspeak.src.common.proto.fleetspeak import common_pb2
from grr_response_proto import rrg_pb2


INCOMING_FLEETSPEAK_MESSAGES = metrics.Counter(
    "incoming_fleetspeak_messages", fields=[("status", str)]
)

FRONTEND_REQUEST_COUNT = metrics.Counter(
    "frontend_request_count", fields=[("source", str)]
)

FRONTEND_REQUEST_LATENCY = metrics.Event(
    "frontend_request_latency", fields=[("source", str)]
)

FLEETSPEAK_MESSAGE_BATCH_ERRORS = metrics.Counter(
    "fleetspeak_message_batch_errors",
    fields=[("type", str)],
)

FLEETSPEAK_MESSAGE_BATCH_DECODE_ERRORS = metrics.Counter(
    "fleetspeak_message_batch_decode_errors",
    fields=[("expected_type", str)],
)

MIN_DELAY_BETWEEN_METADATA_UPDATES = rdfvalue.Duration.From(
    30, rdfvalue.SECONDS
)

WARN_IF_PROCESSING_LONGER_THAN = rdfvalue.Duration.From(30, rdfvalue.SECONDS)


@cache.WithLimitedCallFrequencyWithoutReturnValue(
    MIN_DELAY_BETWEEN_METADATA_UPDATES
)
def RateLimitedWriteClientMetadata(
    client_id: str,
    # fleetspeak_validation_info has to be hashable in order for the decorator
    # function to work. Hence using frozenset instead of a dict.
    fleetspeak_validation_info: frozenset[tuple[str, str]],
) -> None:
  """Rate-limiter to prevent overload of a single DB row on heavy QPS load."""
  data_store.REL_DB.WriteClientMetadata(
      client_id,
      last_ping=rdfvalue.RDFDatetime.Now(),
      fleetspeak_validation_info=dict(fleetspeak_validation_info),
  )


class GRRFSServer:
  """The GRR FS frontend server.

  This class is only responsible for the read end of Fleetspeak comms. The write
  end is used in Fleetspeak frontend, worker and admin_ui processes.
  """

  def __init__(self):
    self.frontend = frontend_lib.FrontEndServer(
        max_queue_size=config.CONFIG["Frontend.max_queue_size"],
        message_expiry_time=config.CONFIG["Frontend.message_expiry_time"],
        max_retransmission_time=config.CONFIG[
            "Frontend.max_retransmission_time"
        ],
    )

  def ProcessFromGRPC(
      self, fs_msg: common_pb2.Message, context: grpc.ServicerContext
  ) -> None:
    """Fleetspeak message processing entrypoint for GRPC delivery."""
    self.Process(fs_msg, context)

  def ProcessFromCPS(self, fs_msg: common_pb2.Message) -> None:
    """Fleetspeak message processing entrypoint for Cloud Pub/Sub delivery."""
    self.Process(fs_msg, None)

  @FRONTEND_REQUEST_COUNT.Counted(fields=["fleetspeak-batch"])
  @FRONTEND_REQUEST_LATENCY.Timed(fields=["fleetspeak-batch"])
  def ProcessBatch(
      self,
      batch: fleetspeak.MessageBatch,
  ) -> None:
    """Processes a message batch from Fleetspeak."""
    client_id = batch.client_id

    try:
      metadata = self.frontend.EnrollFleetspeakClientIfNeeded(
          client_id=client_id,
          fleetspeak_validation_tags=batch.validation_info_tags,
      )
      if metadata is not None:
        if metadata.ping:
          elapsed_since_ping = (
              rdfvalue.RDFDatetime.Now() - rdfvalue.RDFDatetime(metadata.ping)
          )
        else:
          elapsed_since_ping = rdfvalue.Duration(sys.maxsize)

        if elapsed_since_ping >= MIN_DELAY_BETWEEN_METADATA_UPDATES:
          logging.info("updating metadata for existing client: %r", client_id)
          RateLimitedWriteClientMetadata(
              client_id,
              frozenset(batch.validation_info_tags.items()),
          )

      if batch.message_type == "GrrMessage":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(
            fields=["PROCESS_GRR"],
            delta=len(batch.messages),
        )

        grr_message_protos: list[jobs_pb2.GrrMessage] = []
        for message in batch.messages:
          grr_message_proto = jobs_pb2.GrrMessage()
          try:
            grr_message_proto.ParseFromString(message.value)
          except proto2_message.DecodeError:
            logging.exception("invalid GRR message object: %r", message)
            FLEETSPEAK_MESSAGE_BATCH_DECODE_ERRORS.Increment(
                fields=[jobs_pb2.GrrMessage.DESCRIPTOR.full_name]
            )
            continue

          grr_message_protos.append(grr_message_proto)

        grr_messages = list(map(mig_flows.ToRDFGrrMessage, grr_message_protos))
        self._ProcessGRRMessages(client_id, grr_messages)

      elif batch.message_type == "MessageList":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(
            fields=["PROCESS_GRR_MESSAGE_LIST"],
            delta=len(batch.messages),
        )

        grr_message_protos: list[jobs_pb2.GrrMessage] = []
        for message in batch.messages:
          packed_message_list_proto = jobs_pb2.PackedMessageList()
          try:
            packed_message_list_proto.ParseFromString(message.value)
          except proto2_message.DecodeError:
            logging.exception("invalid GRR message list object: %r", message)
            FLEETSPEAK_MESSAGE_BATCH_DECODE_ERRORS.Increment(
                fields=[jobs_pb2.PackedMessageList.DESCRIPTOR.full_name]
            )
            continue

          message_list_proto = mig_flows.ToProtoMessageList(
              communicator.Communicator.DecompressMessageList(
                  mig_flows.ToRDFPackedMessageList(packed_message_list_proto),
              )
          )

          grr_message_protos.extend(message_list_proto.job)

        grr_messages = list(map(mig_flows.ToRDFGrrMessage, grr_message_protos))
        self._ProcessGRRMessages(client_id, grr_messages)

      elif batch.message_type == "rrg.Response":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(
            fields=["PROCESS_RRG_RESPONSE"],
            delta=len(batch.messages),
        )

        rrg_responses: list[rrg_pb2.Response] = []
        for message in batch.messages:
          rrg_response = rrg_pb2.Response()
          try:
            rrg_response.ParseFromString(message.value)
          except proto2_message.DecodeError:
            logging.exception("Invalid RRG response: %s", message)
            FLEETSPEAK_MESSAGE_BATCH_DECODE_ERRORS.Increment(
                fields=[rrg_pb2.Response.DESCRIPTOR.full_name]
            )
            continue

          rrg_responses.append(rrg_response)

        self.frontend.ReceiveRRGResponses(client_id, rrg_responses)

      elif batch.message_type == "rrg.Parcel":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(
            fields=["PROCESS_RRG_PARCEL"],
            delta=len(batch.messages),
        )

        rrg_parcels: list[rrg_pb2.Parcel] = []
        for message in batch.messages:
          rrg_parcel = rrg_pb2.Parcel()
          try:
            rrg_parcel.ParseFromString(message.value)
          except proto2_message.DecodeError:
            logging.exception("Invalid RRG parcel: %s", message)
            FLEETSPEAK_MESSAGE_BATCH_DECODE_ERRORS.Increment(
                fields=[rrg_pb2.Parcel.DESCRIPTOR.full_name]
            )
            continue

          rrg_parcels.append(rrg_parcel)

        self.frontend.ReceiveRRGParcels(client_id, rrg_parcels)
      else:
        INCOMING_FLEETSPEAK_MESSAGES.Increment(
            fields=["INVALID"],
            delta=len(batch.messages),
        )
        logging.error("Message batch of unknown type: %r", batch.message_type)
    except Exception:
      logging.exception("Failed to process message batch: %s", batch)
      FLEETSPEAK_MESSAGE_BATCH_ERRORS.Increment(fields=[batch.message_type])
      raise

  @FRONTEND_REQUEST_COUNT.Counted(fields=["fleetspeak"])
  @FRONTEND_REQUEST_LATENCY.Timed(fields=["fleetspeak"])
  def Process(
      self, fs_msg: common_pb2.Message, context: Optional[grpc.ServicerContext]
  ) -> None:
    """Processes a single fleetspeak message."""
    request_start_time = rdfvalue.RDFDatetime.Now()
    logged_actions = []

    def _LogDelayed(msg: str) -> None:
      elapsed = rdfvalue.RDFDatetime.Now() - request_start_time
      logged_actions.append((elapsed, msg))

    fs_client_id = fs_msg.source.client_id
    grr_client_id = fleetspeak_utils.FleetspeakIDToGRRID(fs_client_id)

    if fs_msg.is_blocklisted_source:
      INCOMING_FLEETSPEAK_MESSAGES.Increment(fields=["SKIPPED_BLOCKLISTED"])
      return

    validation_info = dict(fs_msg.validation_info.tags)

    try:
      _LogDelayed("Enrolling Fleetspeak client")
      existing_client_mdata = self.frontend.EnrollFleetspeakClientIfNeeded(
          grr_client_id,
          validation_info,
      )
      _LogDelayed(f"Enrolled fleetspeak client: {existing_client_mdata}")
      # Only update the client metadata if the client exists and the last
      # update happened more than MIN_DELAY_BETWEEN_METADATA_UPDATES ago.
      now = rdfvalue.RDFDatetime.Now()
      if existing_client_mdata is not None and existing_client_mdata.ping:
        last_ping = rdfvalue.RDFDatetime(existing_client_mdata.ping)
        time_since_last_ping = now - last_ping
        if time_since_last_ping > MIN_DELAY_BETWEEN_METADATA_UPDATES:
          _LogDelayed(
              "Writing client metadata for existing client "
              f"(time_since_last_ping={time_since_last_ping}"
          )
          # Even though we explicitly check for the last_ping timestamp to
          # be older than (now - MIN_DELAY_BETWEEN_METADATA_UPDATES), we
          # still can experience WriteClientMetadata spikes when a client
          # sends a lot of messages together after more than
          # MIN_DELAY_BETWEEN_METADATA_UPDATES seconds of silence. These
          # messages are likely to be handled by various threads of the
          # same GRR Fleetspeak Frontend process. This creates a race
          # condition: multiple threads of the process will read the same
          # row, check the last ping and decided to update it. Rate-limiting
          # the calls protects against this scenario. Note: it doesn't
          # protect against the scenario of multiple GRR Fletspeak Frontend
          # processes receiving the messages at the same time, but such
          # protection currently is likely excessive.
          RateLimitedWriteClientMetadata(
              grr_client_id,
              frozenset(validation_info.items()),
          )
          _LogDelayed("Written client metadata for existing client")

      if fs_msg.message_type == "GrrMessage":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(fields=["PROCESS_GRR"])

        grr_message = rdf_flows.GrrMessage.FromSerializedBytes(
            fs_msg.data.value
        )
        _LogDelayed("Starting processing GRR message")
        self._ProcessGRRMessages(grr_client_id, [grr_message])
        _LogDelayed("Finished processing GRR message")
      elif fs_msg.message_type == "MessageList":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(
            fields=["PROCESS_GRR_MESSAGE_LIST"]
        )

        packed_messages = rdf_flows.PackedMessageList.FromSerializedBytes(
            fs_msg.data.value
        )
        message_list = communicator.Communicator.DecompressMessageList(
            packed_messages
        )
        _LogDelayed("Starting processing GRR message list")
        self._ProcessGRRMessages(grr_client_id, message_list.job)
        _LogDelayed("Finished processing GRR message list")
      elif fs_msg.message_type == "rrg.Response":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(fields=["PROCESS_RRG_RESPONSE"])

        rrg_response = rrg_pb2.Response()
        rrg_response.ParseFromString(fs_msg.data.value)

        _LogDelayed("Starting processing RRG response")
        self.frontend.ReceiveRRGResponse(grr_client_id, rrg_response)
        _LogDelayed("Finished processing RRG response")
      elif fs_msg.message_type == "rrg.Parcel":
        INCOMING_FLEETSPEAK_MESSAGES.Increment(fields=["PROCESS_RRG_PARCEL"])

        rrg_parcel = rrg_pb2.Parcel()
        rrg_parcel.ParseFromString(fs_msg.data.value)

        _LogDelayed("Starting processing RRG parcel")
        self.frontend.ReceiveRRGParcel(grr_client_id, rrg_parcel)
        _LogDelayed("Finished processing RRG parcel")
      else:
        INCOMING_FLEETSPEAK_MESSAGES.Increment(fields=["INVALID"])

        logging.error(
            "Received message with unrecognized message_type: %s",
            fs_msg.message_type,
        )
        if context:
          context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
    except Exception:
      logging.exception("Exception processing message: %s", fs_msg)
      raise
    finally:
      total_elapsed = rdfvalue.RDFDatetime.Now() - request_start_time
      if total_elapsed > WARN_IF_PROCESSING_LONGER_THAN:
        logged_str = "\n".join(
            "\t[{elapsed}]: {msg}".format(elapsed=elapsed, msg=msg)
            for elapsed, msg in logged_actions
        )
        logging.warning(
            "Handling Fleetspeak frontend RPC took %s:\n%s",
            total_elapsed,
            logged_str,
        )

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
            rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED
        )
      self.frontend.ReceiveMessages(
          client_id=grr_client_id, messages=grr_messages
      )
    except Exception:
      logging.exception("Exception receiving messages from: %s", grr_client_id)
      raise
