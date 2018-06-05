#!/usr/bin/env python
"""RDFValue implementations for hunts."""

from grr import config
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client
from grr.lib.rdfvalues import objects
from grr.lib.rdfvalues import stats
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr.server.grr_response_server import foreman_rules
from grr.server.grr_response_server import output_plugin


class HuntNotification(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.HuntNotification
  rdf_deps = [
      client.ClientURN,
      rdfvalue.SessionID,
  ]


class HuntContext(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.HuntContext
  rdf_deps = [
      client.ClientResources,
      stats.ClientResourcesStats,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]


class FlowLikeObjectReference(rdf_structs.RDFProtoStruct):
  """A reference to a flow or a hunt."""
  protobuf = flows_pb2.FlowLikeObjectReference
  rdf_deps = [
      objects.FlowReference,
      objects.HuntReference,
  ]

  @classmethod
  def FromHuntId(cls, hunt_id):
    res = FlowLikeObjectReference()
    res.object_type = "HUNT_REFERENCE"
    res.hunt_reference = objects.HuntReference(hunt_id=hunt_id)
    return res

  @classmethod
  def FromFlowIdAndClientId(cls, flow_id, client_id):
    res = FlowLikeObjectReference()
    res.object_type = "FLOW_REFERENCE"
    res.flow_reference = objects.FlowReference(
        flow_id=flow_id, client_id=client_id)
    return res


class HuntRunnerArgs(rdf_structs.RDFProtoStruct):
  """Hunt runner arguments definition."""

  protobuf = flows_pb2.HuntRunnerArgs
  rdf_deps = [
      rdfvalue.Duration,
      foreman_rules.ForemanClientRuleSet,
      output_plugin.OutputPluginDescriptor,
      rdfvalue.RDFURN,
      FlowLikeObjectReference,
  ]

  def __init__(self, initializer=None, **kwargs):
    super(HuntRunnerArgs, self).__init__(initializer=initializer, **kwargs)

    if initializer is None:
      if not self.HasField("crash_limit"):
        self.crash_limit = config.CONFIG["Hunt.default_crash_limit"]

      if not self.HasField("avg_results_per_client_limit"):
        self.avg_results_per_client_limit = config.CONFIG[
            "Hunt.default_avg_results_per_client_limit"]

      if not self.HasField("avg_cpu_seconds_per_client_limit"):
        self.avg_cpu_seconds_per_client_limit = config.CONFIG[
            "Hunt.default_avg_cpu_seconds_per_client_limit"]

      if not self.HasField("avg_network_bytes_per_client_limit"):
        self.avg_network_bytes_per_client_limit = config.CONFIG[
            "Hunt.default_avg_network_bytes_per_client_limit"]

  def Validate(self):
    if self.HasField("client_rule_set"):
      self.client_rule_set.Validate()


class HuntError(rdf_structs.RDFProtoStruct):
  """An RDFValue class representing a hunt error."""
  protobuf = jobs_pb2.HuntError
  rdf_deps = [
      client.ClientURN,
  ]
