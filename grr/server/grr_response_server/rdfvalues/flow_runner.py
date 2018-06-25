#!/usr/bin/env python
"""Data structures used by GRR server's flow runner."""

from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr.server.grr_response_server.rdfvalues import objects as rdf_objects


class RequestState(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.RequestState
  rdf_deps = [
      rdf_client.ClientURN,
      rdf_protodict.Dict,
      rdf_flows.GrrMessage,
      rdf_flows.GrrStatus,
      rdfvalue.SessionID,
  ]


class FlowRunnerArgs(rdf_structs.RDFProtoStruct):
  """The argument to the flow runner.

  Note that all flows receive these arguments. This object is stored in the
  flows state.context.arg attribute.
  """
  protobuf = flows_pb2.FlowRunnerArgs
  rdf_deps = [
      rdf_client.ClientURN,
      rdf_objects.FlowReference,
      "OutputPluginDescriptor",  # TODO(user): dependency loop.
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
      RequestState,
  ]


class OutputPluginState(rdf_structs.RDFProtoStruct):
  protobuf = output_plugin_pb2.OutputPluginState
  rdf_deps = [
      rdf_protodict.AttributedDict,
      "OutputPluginDescriptor",  # TODO(user): dependency loop.
  ]


class FlowContext(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowContext
  rdf_deps = [
      rdf_client.ClientResources,
      OutputPluginState,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]
