#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import flows_pb2
from grr_response_server.rdfvalues import hunts as rdf_hunts


def ToProtoFlowLikeObjectReference(
    rdf: rdf_hunts.FlowLikeObjectReference,
) -> flows_pb2.FlowLikeObjectReference:
  return rdf.AsPrimitiveProto()


def ToRDFFlowLikeObjectReference(
    proto: flows_pb2.FlowLikeObjectReference,
) -> rdf_hunts.FlowLikeObjectReference:
  return rdf_hunts.FlowLikeObjectReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoHuntRunnerArgs(
    rdf: rdf_hunts.HuntRunnerArgs,
) -> flows_pb2.HuntRunnerArgs:
  return rdf.AsPrimitiveProto()


def ToRDFHuntRunnerArgs(
    proto: flows_pb2.HuntRunnerArgs,
) -> rdf_hunts.HuntRunnerArgs:
  return rdf_hunts.HuntRunnerArgs.FromSerializedBytes(proto.SerializeToString())
