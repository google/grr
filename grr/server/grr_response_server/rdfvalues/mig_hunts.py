#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.rdfvalues import hunts as rdf_hunts


def ToProtoHuntNotification(
    rdf: rdf_hunts.HuntNotification,
) -> jobs_pb2.HuntNotification:
  return rdf.AsPrimitiveProto()


def ToRDFHuntNotification(
    proto: jobs_pb2.HuntNotification,
) -> rdf_hunts.HuntNotification:
  return rdf_hunts.HuntNotification.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoHuntContext(rdf: rdf_hunts.HuntContext) -> flows_pb2.HuntContext:
  return rdf.AsPrimitiveProto()


def ToRDFHuntContext(proto: flows_pb2.HuntContext) -> rdf_hunts.HuntContext:
  return rdf_hunts.HuntContext.FromSerializedBytes(proto.SerializeToString())


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


def ToProtoHuntError(rdf: rdf_hunts.HuntError) -> jobs_pb2.HuntError:
  return rdf.AsPrimitiveProto()


def ToRDFHuntError(proto: jobs_pb2.HuntError) -> rdf_hunts.HuntError:
  return rdf_hunts.HuntError.FromSerializedBytes(proto.SerializeToString())


def ToProtoGenericHuntArgs(
    rdf: rdf_hunts.GenericHuntArgs,
) -> flows_pb2.GenericHuntArgs:
  return rdf.AsPrimitiveProto()


def ToRDFGenericHuntArgs(
    proto: flows_pb2.GenericHuntArgs,
) -> rdf_hunts.GenericHuntArgs:
  return rdf_hunts.GenericHuntArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCreateGenericHuntFlowArgs(
    rdf: rdf_hunts.CreateGenericHuntFlowArgs,
) -> flows_pb2.CreateGenericHuntFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFCreateGenericHuntFlowArgs(
    proto: flows_pb2.CreateGenericHuntFlowArgs,
) -> rdf_hunts.CreateGenericHuntFlowArgs:
  return rdf_hunts.CreateGenericHuntFlowArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
