#!/usr/bin/env python
"""Data structures used by GRR server's flow runner."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server.rdfvalues import objects as rdf_objects


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
      rdfvalue.RDFURN,
      RequestState,
  ]


class OutputPluginState(rdf_structs.RDFProtoStruct):
  """The output plugin state."""
  protobuf = output_plugin_pb2.OutputPluginState
  rdf_deps = [
      rdf_protodict.AttributedDict,
      "OutputPluginDescriptor",  # TODO(user): dependency loop.
  ]

  def GetPlugin(self):
    return self.plugin_descriptor.GetPluginForState(self.plugin_state)

  def Log(self, msg):
    # Cannot append to lists in AttributedDicts.
    self.plugin_state["logs"] += [msg]

  def Error(self, msg):
    # Cannot append to lists in AttributedDicts.
    self.plugin_state["errors"] += [msg]


class FlowContext(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.FlowContext
  rdf_deps = [
      rdf_client_stats.ClientResources,
      OutputPluginState,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]
