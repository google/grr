#!/usr/bin/env python
"""Rdfvalues for flows."""

import re

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import action_registry
from grr_response_server import output_plugin
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects


class FlowRequest(rdf_structs.RDFProtoStruct):
  """Flow request object."""

  protobuf = flows_pb2.FlowRequest
  rdf_deps = [
      rdf_protodict.Dict,
      rdfvalue.RDFDatetime,
  ]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    if not self.HasField("next_response_id"):
      self.next_response_id = 1


class FlowMessage(object):
  """Base class for all messages flows can receive."""

  @property
  def client_id(self) -> str:
    return self.Get("client_id")

  @client_id.setter
  def client_id(self, value: str) -> None:
    self.Set("client_id", value)

  @property
  def flow_id(self) -> str:
    return self.Get("flow_id")

  @flow_id.setter
  def flow_id(self, value: str) -> None:
    self.Set("flow_id", value)

  @property
  def request_id(self) -> int:
    return self.Get("request_id")

  @request_id.setter
  def request_id(self, value: int) -> None:
    self.Set("request_id", value)

  @property
  def response_id(self) -> int:
    return self.Get("response_id")

  @response_id.setter
  def response_id(self, value: int) -> None:
    self.Set("response_id", value)


class FlowResponse(FlowMessage, rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowResponse
  rdf_deps = []

  def AsLegacyGrrMessage(self):
    return rdf_flows.GrrMessage(
        session_id="%s/flows/%s" % (self.client_id, self.flow_id),
        request_id=self.request_id,
        response_id=self.response_id,
        type=rdf_flows.GrrMessage.Type.MESSAGE,
        timestamp=self.timestamp,
        payload=self.payload)


class FlowIterator(FlowMessage, rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowIterator
  rdf_deps = []

  def AsLegacyGrrMessage(self):
    return rdf_flows.GrrMessage(
        session_id="%s/flows/%s" % (self.client_id, self.flow_id),
        request_id=self.request_id,
        response_id=self.response_id,
        type=rdf_flows.GrrMessage.Type.ITERATOR,
        timestamp=self.timestamp)


class FlowStatus(FlowMessage, rdf_structs.RDFProtoStruct):
  """The flow status object."""

  protobuf = flows_pb2.FlowStatus
  rdf_deps = [
      rdf_client_stats.CpuSeconds,
      rdfvalue.Duration,
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
    if self.runtime_us:
      payload.runtime_us = self.runtime_us

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

  def AsLegacyGrrMessage(self):
    return rdf_flows.GrrMessage(
        session_id="%s/flows/%s" % (self.client_id, self.flow_id),
        source=self.client_id,
        type="MESSAGE",
        timestamp=self.timestamp,
        payload=self.payload)


class FlowError(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowError
  rdf_deps = [rdfvalue.RDFDatetime]


class FlowLogEntry(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowLogEntry
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]


class FlowOutputPluginLogEntry(rdf_structs.RDFProtoStruct):
  """Log entry of a flow output plugin."""

  protobuf = flows_pb2.FlowOutputPluginLogEntry
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  def ToOutputPluginBatchProcessingStatus(self):
    if self.log_entry_type == self.LogEntryType.LOG:
      status = output_plugin.OutputPluginBatchProcessingStatus.Status.SUCCESS
    elif self.log_entry_type == self.LogEntryType.ERROR:
      status = output_plugin.OutputPluginBatchProcessingStatus.Status.ERROR
    else:
      raise ValueError("Unexpected log_entry_type: %r" % self.log_entry_type)

    return output_plugin.OutputPluginBatchProcessingStatus(
        summary=self.message, batch_index=0, batch_size=0, status=status)


class Flow(rdf_structs.RDFProtoStruct):
  """Flow DB object."""

  protobuf = flows_pb2.Flow
  rdf_deps = [
      "OutputPluginDescriptor",  # TODO(user): dependency loop.
      rdf_flow_runner.OutputPluginState,
      rdf_client.ClientCrash,
      rdf_client_stats.CpuSeconds,
      rdf_objects.FlowReference,
      rdf_protodict.AttributedDict,
      rdfvalue.RDFDatetime,
      rdfvalue.Duration,
  ]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    if not self.HasField("cpu_time_used"):
      self.cpu_time_used.user_cpu_time = 0
      self.cpu_time_used.system_cpu_time = 0

    if not self.HasField("network_bytes_sent"):
      self.network_bytes_sent = 0

    if not self.HasField("runtime_us"):
      self.runtime_us = rdfvalue.Duration(0)


def _ClientIDFromSessionID(session_id):
  """Extracts the client id from a session id."""

  parts = session_id.Split(4)
  client_id = parts[0]
  if re.match(r"C\.[0-9a-f]{16}", client_id):
    return client_id

  raise ValueError("Unable to parse client id from session_id: %s" % session_id)


status_map = {
    rdf_flows.GrrStatus.ReturnedStatus.OK:
        FlowStatus.Status.OK,
    rdf_flows.GrrStatus.ReturnedStatus.IOERROR:
        FlowStatus.Status.IOERROR,
    rdf_flows.GrrStatus.ReturnedStatus.CLIENT_KILLED:
        FlowStatus.Status.CLIENT_KILLED,
    rdf_flows.GrrStatus.ReturnedStatus.NETWORK_LIMIT_EXCEEDED:
        FlowStatus.Status.NETWORK_LIMIT_EXCEEDED,
    rdf_flows.GrrStatus.ReturnedStatus.RUNTIME_LIMIT_EXCEEDED:
        FlowStatus.Status.RUNTIME_LIMIT_EXCEEDED,
    rdf_flows.GrrStatus.ReturnedStatus.CPU_LIMIT_EXCEEDED:
        FlowStatus.Status.CPU_LIMIT_EXCEEDED,
    rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR:
        FlowStatus.Status.ERROR,
}

inv_status_map = {v: k for k, v in status_map.items()}


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
      raise ValueError("Unable to convert returned status: %s" %
                       legacy_status.status)
    response = FlowStatus(
        client_id=_ClientIDFromSessionID(legacy_msg.session_id),
        flow_id=legacy_msg.session_id.Basename(),
        request_id=legacy_msg.request_id,
        response_id=legacy_msg.response_id,
        status=status_map[legacy_status.status],
        error_message=legacy_status.error_message,
        backtrace=legacy_status.backtrace,
        cpu_time_used=legacy_status.cpu_time_used,
        network_bytes_sent=legacy_status.network_bytes_sent,
        runtime_us=legacy_status.runtime_us)
  elif legacy_msg.type == legacy_msg.Type.ITERATOR:
    response = FlowIterator(
        client_id=_ClientIDFromSessionID(legacy_msg.session_id),
        flow_id=legacy_msg.session_id.Basename(),
        request_id=legacy_msg.request_id,
        response_id=legacy_msg.response_id)
  else:
    raise ValueError("Unknown message type: %d" % legacy_msg.type)

  return response


def GRRMessageFromClientActionRequest(request):
  stub = action_registry.ACTION_STUB_BY_ID[request.action_identifier]
  name = stub.__name__

  return rdf_flows.GrrMessage(
      session_id="%s/%s" % (request.client_id, request.flow_id),
      name=name,
      request_id=request.request_id,
      queue=rdf_client.ClientURN(request.client_id),
      payload=request.action_args,
      cpu_limit=request.cpu_limit_ms / 1000.0,
      network_bytes_limit=request.network_bytes_limit,
      runtime_limit_us=request.runtime_limit_us,
      # Legacy clients will fail if the task id is not set.
      # TODO(amoser): Remove task ids after April 2021.
      generate_task_id=True)


class ScheduledFlow(rdf_structs.RDFProtoStruct):
  """A scheduled flow, to be executed after approval has been granted."""
  protobuf = flows_pb2.ScheduledFlow

  rdf_deps = [rdf_flow_runner.FlowRunnerArgs, rdfvalue.RDFDatetime]


class FlowResultCount(rdf_structs.RDFProtoStruct):
  """Result count per type and tag."""
  protobuf = flows_pb2.FlowResultCount


class FlowResultMetadata(rdf_structs.RDFProtoStruct):
  """Metadata about results returned for the flow."""
  protobuf = flows_pb2.FlowResultMetadata
  rdf_deps = [
      FlowResultCount,
  ]


class DefaultFlowProgress(rdf_structs.RDFProtoStruct):
  """Default flow progress for flows without a custom GetProgress handler."""
  protobuf = flows_pb2.DefaultFlowProgress
