#!/usr/bin/env python
"""Rdfvalues for flows."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import random
from grr_response_proto import hunts_pb2


def RandomHuntId() -> str:
  """Returns a random hunt id encoded as a hex string."""
  return "{:016X}".format(random.Id64())


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


class HuntMetadata(rdf_structs.RDFProtoStruct):
  protobuf = hunts_pb2.HuntMetadata
  rdf_deps = [
      rdfvalue.RDFDatetime,
      rdfvalue.DurationSeconds,
  ]
