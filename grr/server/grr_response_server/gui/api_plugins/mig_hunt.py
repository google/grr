#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import hunt_pb2
from grr_response_server.gui.api_plugins import hunt


def ToProtoApiHuntReference(
    rdf: hunt.ApiHuntReference,
) -> hunt_pb2.ApiHuntReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiHuntReference(
    proto: hunt_pb2.ApiHuntReference,
) -> hunt.ApiHuntReference:
  return hunt.ApiHuntReference.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiFlowLikeObjectReference(
    rdf: hunt.ApiFlowLikeObjectReference,
) -> hunt_pb2.ApiFlowLikeObjectReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiFlowLikeObjectReference(
    proto: hunt_pb2.ApiFlowLikeObjectReference,
) -> hunt.ApiFlowLikeObjectReference:
  return hunt.ApiFlowLikeObjectReference.FromSerializedBytes(
      proto.SerializeToString()
  )
