#!/usr/bin/env python
"""RDFValue implementations for hunts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import foreman_rules
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin


class HuntNotification(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.HuntNotification
  rdf_deps = [
      rdf_client.ClientURN,
      rdfvalue.SessionID,
  ]


class HuntContext(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.HuntContext
  rdf_deps = [
      rdf_client_stats.ClientResources,
      rdf_stats.ClientResourcesStats,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]


class FlowLikeObjectReference(rdf_structs.RDFProtoStruct):
  """A reference to a flow or a hunt."""
  protobuf = flows_pb2.FlowLikeObjectReference
  rdf_deps = [
      rdf_objects.FlowReference,
      rdf_objects.HuntReference,
  ]

  @classmethod
  def FromHuntId(cls, hunt_id):
    res = FlowLikeObjectReference()
    res.object_type = "HUNT_REFERENCE"
    res.hunt_reference = rdf_objects.HuntReference(hunt_id=hunt_id)
    return res

  @classmethod
  def FromFlowIdAndClientId(cls, flow_id, client_id):
    res = FlowLikeObjectReference()
    res.object_type = "FLOW_REFERENCE"
    res.flow_reference = rdf_objects.FlowReference(
        flow_id=flow_id, client_id=client_id)
    return res


class HuntRunnerArgs(rdf_structs.RDFProtoStruct):
  """Hunt runner arguments definition."""

  protobuf = flows_pb2.HuntRunnerArgs
  rdf_deps = [
      rdfvalue.Duration,
      foreman_rules.ForemanClientRuleSet,
      rdf_output_plugin.OutputPluginDescriptor,
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
      rdf_client.ClientURN,
  ]


class GenericHuntArgs(rdf_structs.RDFProtoStruct):
  """Arguments to the generic hunt."""
  protobuf = flows_pb2.GenericHuntArgs
  rdf_deps = [
      rdf_flow_runner.FlowRunnerArgs,
      rdf_output_plugin.OutputPluginDescriptor,
  ]

  def Validate(self):
    self.flow_runner_args.Validate()
    self.flow_args.Validate()

  def GetFlowArgsClass(self):
    if self.flow_runner_args.flow_name:
      flow_cls = registry.AFF4FlowRegistry.FlowClassByName(
          self.flow_runner_args.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class CreateGenericHuntFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CreateGenericHuntFlowArgs
  rdf_deps = [
      GenericHuntArgs,
      HuntRunnerArgs,
  ]
