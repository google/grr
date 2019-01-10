#!/usr/bin/env python
"""Rdfvalues for flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import random
from grr_response_proto import hunts_pb2
from grr_response_server import foreman_rules
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin


# TODO(user): look into using 48-bit or 64-bit ids to avoid clashes.
def RandomHuntId():
  """Returns a random hunt id encoded as a hex string."""
  return "%08X" % random.PositiveUInt32()


class HuntArgumentsStandard(rdf_structs.RDFProtoStruct):
  """Hunt arguments for standard (non-variable) hunts."""
  protobuf = hunts_pb2.HuntArgumentsStandard
  rdf_deps = []


class VariableHuntFlowGroup(rdf_structs.RDFProtoStruct):
  """Flow group for variable hunt arguments."""
  protobuf = hunts_pb2.VariableHuntFlowGroup
  rdf_deps = []


class HuntArgumentsVariable(rdf_structs.RDFProtoStruct):
  """Hunt arguments for variable hunts."""
  protobuf = hunts_pb2.HuntArgumentsVariable
  rdf_deps = [
      VariableHuntFlowGroup,
  ]


class HuntArguments(rdf_structs.RDFProtoStruct):
  """Hunt arguments."""
  protobuf = hunts_pb2.HuntArguments
  rdf_deps = [
      HuntArgumentsStandard,
      HuntArgumentsVariable,
  ]

  @classmethod
  def Standard(cls, *args, **kwargs):
    return cls(
        hunt_type=cls.HuntType.STANDARD,
        standard=HuntArgumentsStandard(*args, **kwargs))

  @classmethod
  def Variable(cls, *args, **kwargs):
    return cls(
        hunt_type=cls.HuntType.VARIABLE,
        variable=HuntArgumentsVariable(*args, **kwargs))


class Hunt(rdf_structs.RDFProtoStruct):
  """Hunt object."""
  protobuf = hunts_pb2.Hunt
  rdf_deps = [
      HuntArguments,
      foreman_rules.ForemanClientRuleSet,
      rdfvalue.RDFDatetime,
      rdf_flow_runner.OutputPluginState,
      rdf_hunts.FlowLikeObjectReference,
      rdf_output_plugin.OutputPluginDescriptor,
      rdf_stats.ClientResourcesStats,
  ]

  def __init__(self, *args, **kwargs):
    super(Hunt, self).__init__(*args, **kwargs)

    if not self.HasField("hunt_id"):
      self.hunt_id = RandomHuntId()

    if not self.HasField("hunt_state"):
      self.hunt_state = self.HuntState.PAUSED

    if not self.HasField("create_time"):
      self.create_time = rdfvalue.RDFDatetime.Now()

    if not self.HasField("expiry_time"):
      self.expiry_time = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("2w")

    if not self.HasField("client_rate"):
      self.client_rate = 20.0
