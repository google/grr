#!/usr/bin/env python
"""RDFValue implementations for hunts."""

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_server import foreman_rules
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin


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
        flow_id=flow_id, client_id=client_id
    )
    return res


class HuntRunnerArgs(rdf_structs.RDFProtoStruct):
  """Hunt runner arguments definition."""

  protobuf = flows_pb2.HuntRunnerArgs
  rdf_deps = [
      rdfvalue.DurationSeconds,
      foreman_rules.ForemanClientRuleSet,
      rdf_output_plugin.OutputPluginDescriptor,
      FlowLikeObjectReference,
  ]

  def __init__(self, **kwargs):
    super().__init__(**kwargs)

    if not self.HasField("client_rate"):
      self.client_rate = config.CONFIG["Hunt.default_client_rate"]

    if not self.HasField("crash_limit"):
      self.crash_limit = config.CONFIG["Hunt.default_crash_limit"]

    if not self.HasField("avg_results_per_client_limit"):
      self.avg_results_per_client_limit = config.CONFIG[
          "Hunt.default_avg_results_per_client_limit"
      ]

    if not self.HasField("avg_cpu_seconds_per_client_limit"):
      self.avg_cpu_seconds_per_client_limit = config.CONFIG[
          "Hunt.default_avg_cpu_seconds_per_client_limit"
      ]

    if not self.HasField("avg_network_bytes_per_client_limit"):
      self.avg_network_bytes_per_client_limit = config.CONFIG[
          "Hunt.default_avg_network_bytes_per_client_limit"
      ]

