#!/usr/bin/env python
"""The GRR frontend server."""

import logging
import time
from typing import Mapping, Optional, Sequence, Union

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import collection
from grr_response_core.lib.util import random
from grr_response_core.stats import metrics
from grr_response_proto import flows_pb2
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import message_handlers
from grr_response_server import sinks
from grr_response_server import worker_lib
from grr_response_server.databases import db
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_proto import rrg_pb2


RRG_PARCEL_COUNT = metrics.Counter(
    name="rrg_parcel_count",
    fields=[("sink", str)],
)
RRG_PARCEL_ACCEPT_ERRORS = metrics.Counter(
    name="rrg_parcel_accept_errors",
    fields=[("sink", str)],
)

FRONTEND_USERNAME = "GRRFrontEnd"


class FrontEndServer(object):
  """This is the front end server.

  This class interfaces clients into the GRR backend system. We process message
  bundles to and from the client, without caring how message bundles are
  transmitted to the client.

  - receives an encrypted message parcel from clients.
  - Decrypts messages from this.
  - schedules the messages to their relevant queues.
  - Collects the messages from the client queue
  - Bundles and encrypts the messages for the client.
  """

  def __init__(
      self,
      max_queue_size=50,
      message_expiry_time=120,
      max_retransmission_time=10,
  ):
    self.message_expiry_time = message_expiry_time
    self.max_retransmission_time = max_retransmission_time
    self.max_queue_size = max_queue_size

  # TODO: Inline this function and simplify code.
  def EnrollFleetspeakClientIfNeeded(
      self,
      client_id: str,
      fleetspeak_validation_tags: Mapping[str, str],
  ) -> Optional[objects_pb2.ClientMetadata]:
    """Enrols a Fleetspeak-enabled client for use with GRR.

    Args:
      client_id: GRR client-id for the client.
      fleetspeak_validation_tags: Validation tags supplied by Fleetspeak.

    Returns:
      None if the client is new, and actually got enrolled. This method
      is a no-op if the client already exists (in which case the existing
      client metadata is returned).
    """
    # If already enrolled, return.
    try:
      return data_store.REL_DB.ReadClientMetadata(client_id)
    except db.UnknownClientError:
      pass

    logging.info("Enrolling a new Fleetspeak client: %r", client_id)

    now = rdfvalue.RDFDatetime.Now()
    data_store.REL_DB.WriteClientMetadata(
        client_id,
        first_seen=now,
        last_ping=now,
        fleetspeak_validation_info=fleetspeak_validation_tags,
    )

    return None

  legacy_well_known_session_ids = set([
      str(rdfvalue.SessionID(flow_name="Foreman", queue=rdfvalue.RDFURN("W"))),
      str(rdfvalue.SessionID(flow_name="Stats", queue=rdfvalue.RDFURN("W"))),
  ])

  # Message handler requests addressed to these handlers will be processed
  # directly on the frontend and not written to the worker queue.
  # Currently we only do this for BlobHandler, since it's important
  # to write blobs to the datastore as fast as possible. GetFile/MultiGetFile
  # logic depends on blobs being in the blob store to do file hashing.
  _SHORTCUT_HANDLERS = frozenset([transfer.BlobHandler.handler_name])

  def ReceiveMessages(
      self,
      client_id: str,
      messages: Sequence[rdf_flows.GrrMessage],
  ) -> None:
    """Receives and processes the messages.

    For each message we update the request object, and place the
    response in that request's queue. If the request is complete, we
    send a message to the worker.

    Args:
      client_id: The client which sent the messages.
      messages: A list of GrrMessage RDFValues.
    """
    now = time.time()
    unprocessed_msgs = []
    worker_message_handler_requests = []
    frontend_message_handler_requests = []
    dropped_count = 0

    # TODO: Remove `fixed_messages` once old clients
    # have been migrated.
    fixed_messages = []
    for message in messages:
      if message.type != rdf_flows.GrrMessage.Type.STATUS:
        fixed_messages.append(message)
        continue

      stat = rdf_flows.GrrStatus(message.payload)
      if not stat.HasField("cpu_time_used"):
        fixed_messages.append(message)
        continue

      if stat.cpu_time_used.HasField("deprecated_user_cpu_time"):
        stat.cpu_time_used.user_cpu_time = (
            stat.cpu_time_used.deprecated_user_cpu_time
        )
        stat.cpu_time_used.deprecated_user_cpu_time = None
      if stat.cpu_time_used.HasField("deprecated_system_cpu_time"):
        stat.cpu_time_used.system_cpu_time = (
            stat.cpu_time_used.deprecated_system_cpu_time
        )
        stat.cpu_time_used.deprecated_system_cpu_time = None
      message.payload = stat
      fixed_messages.append(message)

    messages = fixed_messages

    msgs_by_session_id = collection.Group(messages, lambda m: m.session_id)
    for session_id, msgs in msgs_by_session_id.items():
      try:
        for msg in msgs:
          if (
              msg.auth_state != msg.AuthorizationState.AUTHENTICATED
          ):
            dropped_count += 1
            continue

          session_id_str = str(session_id)
          if session_id_str in message_handlers.session_id_map:
            request = rdf_objects.MessageHandlerRequest(
                client_id=msg.source.Basename(),
                handler_name=message_handlers.session_id_map[session_id],
                request_id=msg.response_id or random.UInt32(),
                request=msg.payload,
            )
            if request.handler_name in self._SHORTCUT_HANDLERS:
              frontend_message_handler_requests.append(request)
            else:
              worker_message_handler_requests.append(request)
          elif session_id_str in self.legacy_well_known_session_ids:
            logging.debug(
                "Dropping message for legacy well known session id %s",
                session_id,
            )
          else:
            unprocessed_msgs.append(msg)
      except ValueError:
        logging.exception(
            "Unpacking error in at least one of %d messages for session id %s",
            len(msgs),
            session_id,
        )
        raise

    if dropped_count:
      logging.info(
          "Dropped %d unauthenticated messages for %s", dropped_count, client_id
      )

    if unprocessed_msgs:
      flow_responses = []
      for message in unprocessed_msgs:
        try:
          response = rdf_flow_objects.FlowResponseForLegacyResponse(message)
        except ValueError as e:
          logging.warning(
              "Failed to parse legacy FlowResponse:\n%s\n%s", e, message
          )
        else:
          if isinstance(response, rdf_flow_objects.FlowStatus):
            response = mig_flow_objects.ToProtoFlowStatus(response)
          if isinstance(response, rdf_flow_objects.FlowIterator):
            response = mig_flow_objects.ToProtoFlowIterator(response)
          if isinstance(response, rdf_flow_objects.FlowResponse):
            response = mig_flow_objects.ToProtoFlowResponse(response)
          flow_responses.append(response)

      data_store.REL_DB.WriteFlowResponses(flow_responses)

      for msg in unprocessed_msgs:
        if msg.type == rdf_flows.GrrMessage.Type.STATUS:
          stat = rdf_flows.GrrStatus(msg.payload)
          if stat.status == rdf_flows.GrrStatus.ReturnedStatus.CLIENT_KILLED:
            # A client crashed while performing an action, fire an event.
            crash_details = rdf_client.ClientCrash(
                client_id=client_id,
                session_id=msg.session_id,
                backtrace=stat.backtrace,
                crash_message=stat.error_message,
                timestamp=rdfvalue.RDFDatetime.Now(),
            )
            events.Events.PublishEvent(
                "ClientCrash", crash_details, username=FRONTEND_USERNAME
            )

    if worker_message_handler_requests:
      worker_message_handler_requests = [
          mig_objects.ToProtoMessageHandlerRequest(r)
          for r in worker_message_handler_requests
      ]
      data_store.REL_DB.WriteMessageHandlerRequests(
          worker_message_handler_requests
      )

    if frontend_message_handler_requests:
      frontend_message_handler_requests = [
          mig_objects.ToProtoMessageHandlerRequest(r)
          for r in frontend_message_handler_requests
      ]
      worker_lib.ProcessMessageHandlerRequests(
          frontend_message_handler_requests
      )

    logging.debug(
        "Received %s messages from %s in %s sec",
        len(messages),
        client_id,
        time.time() - now,
    )

  # TODO: Remove once no longer needed.
  def ReceiveRRGResponse(
      self,
      client_id: str,
      response: rrg_pb2.Response,
  ) -> None:
    """Receives and processes a single response from the RRG agent.

    Args:
      client_id: An identifier of the client for which we process the response.
      response: A response to process.
    """
    self.ReceiveRRGResponses(client_id, [response])

  def ReceiveRRGResponses(
      self,
      client_id: str,
      responses: Sequence[rrg_pb2.Response],
  ) -> None:
    """Receives and processes multiple responses from the RRG agent.

    Args:
      client_id: An identifier of the client for which we process the response.
      responses: Responses to process.
    """
    flow_responses = []
    flow_rrg_logs: dict[tuple[int, int], dict[int, rrg_pb2.Log]] = {}

    for response in responses:
      flow_response: Union[
          flows_pb2.FlowResponse,
          flows_pb2.FlowStatus,
          flows_pb2.FlowIterator,
      ]

      if response.HasField("status"):
        flow_response = flows_pb2.FlowStatus()
        flow_response.network_bytes_sent = response.status.network_bytes_sent
        # TODO: Populate `cpu_time_used` and `runtime_us`

        if response.status.HasField("error"):
          # TODO: Convert RRG error types to GRR error types.
          flow_response.status = flows_pb2.FlowStatus.Status.ERROR
          flow_response.error_message = response.status.error.message
        else:
          flow_response.status = flows_pb2.FlowStatus.Status.OK

      elif response.HasField("result"):
        flow_response = flows_pb2.FlowResponse()
        flow_response.any_payload.CopyFrom(response.result)
      elif response.HasField("log"):
        request_rrg_logs = flow_rrg_logs.setdefault(
            (response.flow_id, response.request_id), {}
        )
        request_rrg_logs[response.response_id] = response.log
        continue
      else:
        raise ValueError(f"Unexpected response: {response}")

      flow_response.client_id = client_id
      flow_response.flow_id = f"{response.flow_id:016X}"
      flow_response.request_id = response.request_id
      flow_response.response_id = response.response_id

      flow_responses.append(flow_response)

    data_store.REL_DB.WriteFlowResponses(flow_responses)

    for (flow_id, request_id), logs in flow_rrg_logs.items():
      data_store.REL_DB.WriteFlowRRGLogs(
          client_id=client_id,
          flow_id=f"{flow_id:016X}",
          request_id=request_id,
          logs=logs,
      )

  # TODO: Remove once no longer needed.
  def ReceiveRRGParcel(
      self,
      client_id: str,
      parcel: rrg_pb2.Parcel,
  ) -> None:
    """Receives and processes a single parcel from the RRG agent.

    Args:
      client_id: An identifier of the client for which we process the response.
      parcel: A parcel to process.
    """
    self.ReceiveRRGParcels(client_id, [parcel])

  def ReceiveRRGParcels(
      self,
      client_id: str,
      parcels: Sequence[rrg_pb2.Parcel],
  ) -> None:
    """Receives and processes multiple parcels from the RRG agent.

    Args:
      client_id: An identifier of the client for which we process the response.
      parcels: Parcels to process.
    """
    parcels_by_sink_name = {}
    for parcel in parcels:
      sink_name = rrg_pb2.Sink.Name(parcel.sink)
      parcels_by_sink_name.setdefault(sink_name, []).append(parcel)

    for sink_name, sink_parcels in parcels_by_sink_name.items():
      RRG_PARCEL_COUNT.Increment(fields=[sink_name], delta=len(sink_parcels))

    try:
      sinks.AcceptMany(client_id, parcels)
    except Exception:  # pylint: disable=broad-exception-caught
      # TODO: `AcceptMany` should raise an error that specifies
      # which sink caused the exception. Then we don't have to increment the
      # count for all sinks.
      for sink_name in parcels_by_sink_name:
        RRG_PARCEL_ACCEPT_ERRORS.Increment(fields=[sink_name])
      logging.exception("Failed to process parcels for '%s'", client_id)
