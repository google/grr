#!/usr/bin/env python
"""FS GRR server side integration utility functions."""

import binascii
import datetime
from typing import Collection, List

from google.protobuf import timestamp_pb2
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import text
from grr_response_core.stats import metrics
from grr_response_proto import jobs_pb2
from grr_response_server import fleetspeak_connector
from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2
from fleetspeak.src.common.proto.fleetspeak import system_pb2 as fs_system_pb2
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2
from fleetspeak.src.server.proto.fleetspeak_server import resource_pb2
from grr_response_proto import rrg_pb2


FLEETSPEAK_CALL_LATENCY = metrics.Event(
    "fleetspeak_call_latency", fields=[("call", str)]
)

WRITE_SINGLE_TRY_TIMEOUT = datetime.timedelta(seconds=30)
WRITE_TOTAL_TIMEOUT = datetime.timedelta(seconds=300)

READ_SINGLE_TRY_TIMEOUT = datetime.timedelta(seconds=60)
READ_TOTAL_TIMEOUT = datetime.timedelta(seconds=120)

GRR_REQUEST_COUNT = metrics.Counter(
    name="grr_request_count",
    fields=[("action", str), ("labels", str)],
)

RRG_REQUEST_COUNT = metrics.Counter(
    name="rrg_request_count",
    fields=[("action", str), ("labels", str)],
)


@FLEETSPEAK_CALL_LATENCY.Timed(fields=["InsertMessage"])
def SendGrrMessageThroughFleetspeak(
    grr_id: str,
    grr_msg: rdf_flows.GrrMessage,
    labels: Collection[str],  # TODO: Remove once RRG rollout done.
) -> None:
  """Sends the given GrrMessage through FS with retrying.

  The send operation is retried if a `grpc.RpcError` occurs.

  The maximum number of retries corresponds to the config value
  `Server.fleetspeak_send_retry_attempts`.

  A retry is delayed by the number of seconds specified in the config value
  `Server.fleetspeak_send_retry_sleep_time_secs`.

  Args:
    grr_id: ID of grr client to send message to.
    grr_msg: GRR message to send.
    labels: Labels of the endpoint to send the message to.
  """
  fs_msg = fs_common_pb2.Message(
      message_type="GrrMessage",
      destination=fs_common_pb2.Address(
          client_id=GRRIDToFleetspeakID(grr_id), service_name="GRR"
      ),
  )
  fs_msg.data.Pack(grr_msg.AsPrimitiveProto())
  if grr_msg.session_id is not None:
    annotation = fs_msg.annotations.entries.add()
    annotation.key, annotation.value = "flow_id", grr_msg.session_id.Basename()
  if grr_msg.request_id is not None:
    annotation = fs_msg.annotations.entries.add()
    annotation.key, annotation.value = "request_id", str(grr_msg.request_id)
  fleetspeak_connector.CONN.outgoing.InsertMessage(
      fs_msg,
      single_try_timeout=WRITE_SINGLE_TRY_TIMEOUT,
      timeout=WRITE_TOTAL_TIMEOUT,
  )

  GRR_REQUEST_COUNT.Increment(
      fields=[
          grr_msg.name,
          ",".join(sorted(labels)),
      ]
  )


@FLEETSPEAK_CALL_LATENCY.Timed(fields=["InsertMessage"])
def SendGrrMessageProtoThroughFleetspeak(
    grr_id: str,
    grr_msg: jobs_pb2.GrrMessage,
    labels: Collection[str],  # TODO: Remove once RRG rollout done.
) -> None:
  """Sends the given GrrMessage through FS with retrying.

  The send operation is retried if a `grpc.RpcError` occurs.

  The maximum number of retries corresponds to the config value
  `Server.fleetspeak_send_retry_attempts`.

  A retry is delayed by the number of seconds specified in the config value
  `Server.fleetspeak_send_retry_sleep_time_secs`.

  Args:
    grr_id: ID of grr client to send message to.
    grr_msg: GRR message to send.
    labels: Labels of the endpoint to send the message to.
  """
  fs_msg = fs_common_pb2.Message(
      message_type="GrrMessage",
      destination=fs_common_pb2.Address(
          client_id=GRRIDToFleetspeakID(grr_id), service_name="GRR"
      ),
  )
  fs_msg.data.Pack(grr_msg)
  if grr_msg.session_id is not None:
    annotation = fs_msg.annotations.entries.add()
    annotation.key = "flow_id"
    annotation.value = rdfvalue.FlowSessionID(grr_msg.session_id).Basename()
  if grr_msg.request_id is not None:
    annotation = fs_msg.annotations.entries.add()
    annotation.key = "request_id"
    annotation.value = str(grr_msg.request_id)
  fleetspeak_connector.CONN.outgoing.InsertMessage(
      fs_msg,
      single_try_timeout=WRITE_SINGLE_TRY_TIMEOUT,
      timeout=WRITE_TOTAL_TIMEOUT,
  )

  GRR_REQUEST_COUNT.Increment(
      fields=[
          grr_msg.name,
          ",".join(sorted(labels)),
      ]
  )


@FLEETSPEAK_CALL_LATENCY.Timed(fields=["InsertMessage"])
def SendRrgRequest(
    client_id: str,
    request: rrg_pb2.Request,
    labels: Collection[str],  # TODO: Remove once RRG rollout done.
) -> None:
  """Sends a RRG action request to the specified endpoint.

  Args:
    client_id: A unique endpoint identifier as recognized by GRR.
    request: A request to send to the endpoint.
    labels: Labels of the endpoint to send the message to.
  """
  message = fs_common_pb2.Message()
  message.message_type = "rrg.Request"
  message.destination.service_name = "RRG"
  message.destination.client_id = GRRIDToFleetspeakID(client_id)
  message.data.Pack(request)

  # It is not entirely clear to me why we set these annotations below, but
  # messages sent to Python agents do it, so we should do it as well.
  message.annotations.entries.add(
      key="flow_id",
      value=str(request.flow_id),
  )
  message.annotations.entries.add(
      key="request_id",
      value=str(request.request_id),
  )

  fleetspeak_connector.CONN.outgoing.InsertMessage(
      message,
      single_try_timeout=WRITE_SINGLE_TRY_TIMEOUT,
      timeout=WRITE_TOTAL_TIMEOUT,
  )

  RRG_REQUEST_COUNT.Increment(
      fields=[
          rrg_pb2.Action.Name(request.action),
          ",".join(sorted(labels)),
      ]
  )


@FLEETSPEAK_CALL_LATENCY.Timed(fields=["InsertMessage"])
def KillFleetspeak(grr_id: str, force: bool) -> None:
  """Kills Fleespeak on the given client."""
  die_req = fs_system_pb2.DieRequest(force=force)
  fs_msg = fs_common_pb2.Message()
  fs_msg.message_type = "Die"
  fs_msg.destination.client_id = GRRIDToFleetspeakID(grr_id)
  fs_msg.destination.service_name = "system"
  fs_msg.data.Pack(die_req)

  fleetspeak_connector.CONN.outgoing.InsertMessage(
      fs_msg,
      single_try_timeout=WRITE_SINGLE_TRY_TIMEOUT,
      timeout=WRITE_TOTAL_TIMEOUT,
  )


@FLEETSPEAK_CALL_LATENCY.Timed(fields=["InsertMessage"])
def RestartFleetspeakGrrService(grr_id: str) -> None:
  """Restarts the GRR service on the given client."""
  restart_req = fs_system_pb2.RestartServiceRequest(name="GRR")
  fs_msg = fs_common_pb2.Message()
  fs_msg.message_type = "RestartService"
  fs_msg.destination.client_id = GRRIDToFleetspeakID(grr_id)
  fs_msg.destination.service_name = "system"
  fs_msg.data.Pack(restart_req)

  fleetspeak_connector.CONN.outgoing.InsertMessage(
      fs_msg,
      single_try_timeout=WRITE_SINGLE_TRY_TIMEOUT,
      timeout=WRITE_TOTAL_TIMEOUT,
  )


@FLEETSPEAK_CALL_LATENCY.Timed(fields=["DeletePendingMessages"])
def DeleteFleetspeakPendingMessages(grr_id: str) -> None:
  """Deletes fleetspeak messages pending for the given client."""
  delete_req = admin_pb2.DeletePendingMessagesRequest()
  delete_req.client_ids.append(GRRIDToFleetspeakID(grr_id))
  fleetspeak_connector.CONN.outgoing.DeletePendingMessages(
      delete_req,
      single_try_timeout=WRITE_SINGLE_TRY_TIMEOUT,
      timeout=WRITE_TOTAL_TIMEOUT,
  )


@FLEETSPEAK_CALL_LATENCY.Timed(fields=["GetPendingMessageCount"])
def GetFleetspeakPendingMessageCount(grr_id: str) -> int:
  get_req = admin_pb2.GetPendingMessageCountRequest()
  get_req.client_ids.append(GRRIDToFleetspeakID(grr_id))
  get_resp = fleetspeak_connector.CONN.outgoing.GetPendingMessageCount(
      get_req,
      single_try_timeout=READ_SINGLE_TRY_TIMEOUT,
      timeout=READ_TOTAL_TIMEOUT,
  )
  return get_resp.count


@FLEETSPEAK_CALL_LATENCY.Timed(fields=["GetPendingMessages"])
def GetFleetspeakPendingMessages(
    grr_id: str, offset: int, limit: int, want_data: bool
) -> admin_pb2.GetPendingMessagesResponse:
  get_req = admin_pb2.GetPendingMessagesRequest()
  get_req.client_ids.append(GRRIDToFleetspeakID(grr_id))
  get_req.offset = offset
  get_req.limit = limit
  get_req.want_data = want_data
  return fleetspeak_connector.CONN.outgoing.GetPendingMessages(
      get_req,
      single_try_timeout=READ_SINGLE_TRY_TIMEOUT,
      timeout=READ_TOTAL_TIMEOUT,
  )


def FleetspeakIDToGRRID(fs_id: bytes) -> str:
  return "C." + text.Hexify(fs_id)


def GRRIDToFleetspeakID(grr_id):
  # Strip the 'C.' prefix and convert to binary.
  return binascii.unhexlify(grr_id[2:])


def TSToRDFDatetime(ts):
  """Convert a protobuf.Timestamp to an RDFDatetime."""
  return rdfvalue.RDFDatetime(ts.seconds * 1000000 + ts.nanos // 1000)


@FLEETSPEAK_CALL_LATENCY.Timed(fields=["ListClients"])
def GetLabelsFromFleetspeak(client_id):
  """Returns labels for a Fleetspeak-enabled client.

  Fleetspeak-enabled clients delegate labeling to Fleetspeak, as opposed to
  using labels in the GRR config.

  Args:
    client_id: Id of the client to fetch Fleetspeak labels for.

  Returns:
    A list of client labels.
  """
  res = fleetspeak_connector.CONN.outgoing.ListClients(
      admin_pb2.ListClientsRequest(client_ids=[GRRIDToFleetspeakID(client_id)]),
      single_try_timeout=READ_SINGLE_TRY_TIMEOUT,
      timeout=READ_TOTAL_TIMEOUT,
  )
  if not res.clients or not res.clients[0].labels:
    return []

  grr_labels = []
  label_prefix = config.CONFIG["Server.fleetspeak_label_prefix"]
  for fs_label in res.clients[0].labels:
    if fs_label.service_name != "client" or (
        label_prefix and not fs_label.label.startswith(label_prefix)
    ):
      continue
    try:
      grr_labels.append(fleetspeak_connector.label_map[fs_label.label])
    except KeyError:
      grr_labels.append(fs_label.label)

  return grr_labels


@FLEETSPEAK_CALL_LATENCY.Timed(fields=["FetchClientResourceUsageRecords"])
def FetchClientResourceUsageRecords(
    client_id: str,
    start_range: timestamp_pb2.Timestamp,
    end_range: timestamp_pb2.Timestamp,
) -> List[resource_pb2.ClientResourceUsageRecord]:
  """Returns aggregated resource usage metrics of a client from Fleetspeak.

  Args:
    client_id: Id of the client to fetch Fleetspeak resource usage records for.
    start_range: Start timestamp of range.
    end_range: end timestamp of range.

  Returns:
    A list of client resource usage records retrieved from Fleetspeak.
  """
  res = fleetspeak_connector.CONN.outgoing.FetchClientResourceUsageRecords(
      admin_pb2.FetchClientResourceUsageRecordsRequest(
          client_id=GRRIDToFleetspeakID(client_id),
          start_timestamp=start_range,
          end_timestamp=end_range,
      ),
      single_try_timeout=READ_SINGLE_TRY_TIMEOUT,
      timeout=READ_TOTAL_TIMEOUT,
  )
  if not res.records:
    return []
  return list(res.records)
