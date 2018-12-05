#!/usr/bin/env python
"""Rdfvalues for flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re
from future.utils import iteritems

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects


class PendingFlowTermination(rdf_structs.RDFProtoStruct):
  """Descriptor of a pending flow termination."""
  protobuf = jobs_pb2.PendingFlowTermination


class FlowRequest(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowRequest
  rdf_deps = [
      rdf_protodict.Dict,
      rdfvalue.RDFDatetime,
  ]


class FlowMessage(object):
  """Base class for all messages flows can receive."""


class FlowResponse(FlowMessage, rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowResponse
  rdf_deps = []

  def AsLegacyGrrMessage(self):
    return rdf_flows.GrrMessage(
        session_id="%s/flows/%s" % (self.client_id, self.flow_id),
        request_id=self.request_id,
        response_id=self.response_id,
        type="MESSAGE",
        timestamp=self.timestamp,
        payload=self.payload)


class FlowIterator(FlowMessage, rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowIterator
  rdf_deps = []


class FlowStatus(FlowMessage, rdf_structs.RDFProtoStruct):
  """The flow status object."""

  protobuf = flows_pb2.FlowStatus
  rdf_deps = [
      rdf_client_stats.CpuSeconds,
  ]

  def AsLegacyGrrMessage(self):
    payload = rdf_flows.GrrStatus(status=inv_status_map[self.status])
    if self.error_message:
      payload.error_message = self.error_message
    if self.backtrace:
      payload.backtrace = self.backtrace
    if self.cpu_time_used:
      payload.cpu_time_used = self.cpu_time_used
    if self.network_bytes_sent:
      payload.network_bytes_sent = self.network_bytes_sent

    return rdf_flows.GrrMessage(
        session_id="%s/flows/%s" % (self.client_id, self.flow_id),
        request_id=self.request_id,
        response_id=self.response_id,
        type="STATUS",
        timestamp=self.timestamp,
        payload=payload)


class FlowResult(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowResult
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class FlowLogEntry(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowLogEntry
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class Flow(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.Flow
  rdf_deps = [
      "OutputPluginDescriptor",  # TODO(user): dependency loop.
      rdf_flow_runner.OutputPluginState,
      PendingFlowTermination,
      rdf_client.ClientCrash,
      rdf_client_stats.CpuSeconds,
      rdf_objects.FlowReference,
      rdf_protodict.AttributedDict,
      rdfvalue.RDFDatetime,
  ]


def _ClientIDFromSessionID(session_id):
  client_id = session_id.Split(3)[0]
  if not re.match(r"C\.[0-9a-f]{16}", client_id):
    raise ValueError(
        "Unable to parse client id from session_id: %s" % session_id)
  return client_id


status_map = {
    rdf_flows.GrrStatus.ReturnedStatus.OK:
        FlowStatus.Status.OK,
    rdf_flows.GrrStatus.ReturnedStatus.IOERROR:
        FlowStatus.Status.IOERROR,
    rdf_flows.GrrStatus.ReturnedStatus.CLIENT_KILLED:
        FlowStatus.Status.CLIENT_KILLED,
    rdf_flows.GrrStatus.ReturnedStatus.NETWORK_LIMIT_EXCEEDED:
        FlowStatus.Status.NETWORK_LIMIT_EXCEEDED,
    rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR:
        FlowStatus.Status.ERROR,
}

inv_status_map = {v: k for k, v in iteritems(status_map)}


def FlowResponseForLegacyResponse(legacy_msg):
  """Helper function to convert legacy client replies to flow responses."""
  if legacy_msg.type == legacy_msg.Type.MESSAGE:
    response = FlowResponse(
        client_id=_ClientIDFromSessionID(legacy_msg.session_id),
        flow_id=legacy_msg.session_id.Basename(),
        request_id=legacy_msg.request_id,
        response_id=legacy_msg.response_id,
        payload=legacy_msg.payload)
  elif legacy_msg.type == legacy_msg.Type.STATUS:
    legacy_status = legacy_msg.payload
    if legacy_status.status not in status_map:
      raise ValueError(
          "Unable to convert returned status: %s" % legacy_status.status)
    response = FlowStatus(
        client_id=_ClientIDFromSessionID(legacy_msg.session_id),
        flow_id=legacy_msg.session_id.Basename(),
        request_id=legacy_msg.request_id,
        response_id=legacy_msg.response_id,
        status=status_map[legacy_status.status],
        error_message=legacy_status.error_message,
        backtrace=legacy_status.backtrace,
        cpu_time_used=legacy_status.cpu_time_used,
        network_bytes_sent=legacy_status.network_bytes_sent)
  elif legacy_msg.type == legacy_msg.Type.ITERATOR:
    response = FlowIterator(
        client_id=_ClientIDFromSessionID(legacy_msg.session_id),
        flow_id=legacy_msg.session_id.Basename(),
        request_id=legacy_msg.request_id,
        response_id=legacy_msg.response_id)
  else:
    raise ValueError("Unknown message type: %d" % legacy_msg.type)

  # TODO(amoser): The current datastore api uses task ids as keys (instead of
  # the much more intuitive (client_id, flow_id, request_id) so we need to
  # propagate the task_id here. This can be removed once client messages are
  # stored properly.
  try:
    response.task_id = legacy_msg.task_id
  except ValueError:
    pass

  return response
