#!/usr/bin/env python
"""Rdfvalues for flows."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

from typing import Optional

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import random
from grr_response_proto import hunts_pb2
from grr_response_server import foreman_rules
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
      rdfvalue.Duration,
      rdf_hunts.FlowLikeObjectReference,
      rdf_output_plugin.OutputPluginDescriptor,
  ]

  def __init__(self, *args, **kwargs):
    super(Hunt, self).__init__(*args, **kwargs)

    if not self.HasField("hunt_id"):
      self.hunt_id = RandomHuntId()

    if not self.HasField("hunt_state"):
      self.hunt_state = self.HuntState.PAUSED

    if not self.HasField("duration"):
      self.duration = rdfvalue.Duration("2w")

    if not self.HasField("client_rate"):
      self.client_rate = 20.5

    if not self.HasField("client_limit"):
      self.client_limit = 100

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

    if not self.HasField("num_clients_at_start_time"):
      self.num_clients_at_start_time = 0

  @property
  def expiry_time(self):
    """Returns the expiry time of the hunt."""
    if self.init_start_time is not None:
      return self.init_start_time + self.duration
    else:
      return None

  @property
  def expired(self):
    """Checks if the hunt has expired."""
    expiry_time = self.expiry_time
    if expiry_time is not None:
      return expiry_time < rdfvalue.RDFDatetime.Now()
    else:
      return False


def IsHuntSuitableForFlowProcessing(hunt_state):
  return hunt_state in [Hunt.HuntState.PAUSED, Hunt.HuntState.STARTED]


class HuntMetadata(rdf_structs.RDFProtoStruct):
  protobuf = hunts_pb2.HuntMetadata
  rdf_deps = [
      rdfvalue.RDFDatetime,
      rdfvalue.Duration,
  ]

  @classmethod
  def FromHunt(cls, h):
    return cls(
        hunt_id=h.hunt_id,
        description=h.description or None,
        create_time=h.create_time,
        creator=h.creator,
        duration=h.duration,
        client_rate=h.client_rate,
        client_limit=h.client_limit,
        hunt_state=h.hunt_state,
        hunt_state_comment=h.hunt_state_comment or None,
        last_update_time=h.last_update_time,
        init_start_time=h.init_start_time,
        last_start_time=h.last_start_time)
