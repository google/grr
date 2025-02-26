#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import hunts_pb2
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects


def ToProtoHuntArgumentsStandard(
    rdf: rdf_hunt_objects.HuntArgumentsStandard,
) -> hunts_pb2.HuntArgumentsStandard:
  return rdf.AsPrimitiveProto()


def ToRDFHuntArgumentsStandard(
    proto: hunts_pb2.HuntArgumentsStandard,
) -> rdf_hunt_objects.HuntArgumentsStandard:
  return rdf_hunt_objects.HuntArgumentsStandard.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoVariableHuntFlowGroup(
    rdf: rdf_hunt_objects.VariableHuntFlowGroup,
) -> hunts_pb2.VariableHuntFlowGroup:
  return rdf.AsPrimitiveProto()


def ToRDFVariableHuntFlowGroup(
    proto: hunts_pb2.VariableHuntFlowGroup,
) -> rdf_hunt_objects.VariableHuntFlowGroup:
  return rdf_hunt_objects.VariableHuntFlowGroup.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoHuntArgumentsVariable(
    rdf: rdf_hunt_objects.HuntArgumentsVariable,
) -> hunts_pb2.HuntArgumentsVariable:
  return rdf.AsPrimitiveProto()


def ToRDFHuntArgumentsVariable(
    proto: hunts_pb2.HuntArgumentsVariable,
) -> rdf_hunt_objects.HuntArgumentsVariable:
  return rdf_hunt_objects.HuntArgumentsVariable.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoHuntArguments(
    rdf: rdf_hunt_objects.HuntArguments,
) -> hunts_pb2.HuntArguments:
  return rdf.AsPrimitiveProto()


def ToRDFHuntArguments(
    proto: hunts_pb2.HuntArguments,
) -> rdf_hunt_objects.HuntArguments:
  return rdf_hunt_objects.HuntArguments.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoHunt(rdf: rdf_hunt_objects.Hunt) -> hunts_pb2.Hunt:
  return rdf.AsPrimitiveProto()


def ToRDFHunt(proto: hunts_pb2.Hunt) -> rdf_hunt_objects.Hunt:
  return rdf_hunt_objects.Hunt.FromSerializedBytes(proto.SerializeToString())


def ToProtoHuntMetadata(
    rdf: rdf_hunt_objects.HuntMetadata,
) -> hunts_pb2.HuntMetadata:
  return rdf.AsPrimitiveProto()


def ToRDFHuntMetadata(
    proto: hunts_pb2.HuntMetadata,
) -> rdf_hunt_objects.HuntMetadata:
  return rdf_hunt_objects.HuntMetadata.FromSerializedBytes(
      proto.SerializeToString()
  )
