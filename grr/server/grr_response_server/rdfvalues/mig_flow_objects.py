#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import flows_pb2
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects


def ToProtoFlowRequest(
    rdf: rdf_flow_objects.FlowRequest,
) -> flows_pb2.FlowRequest:
  return rdf.AsPrimitiveProto()


def ToRDFFlowRequest(
    proto: flows_pb2.FlowRequest,
) -> rdf_flow_objects.FlowRequest:
  return rdf_flow_objects.FlowRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowResponse(
    rdf: rdf_flow_objects.FlowResponse,
) -> flows_pb2.FlowResponse:
  return rdf.AsPrimitiveProto()


def ToRDFFlowResponse(
    proto: flows_pb2.FlowResponse,
) -> rdf_flow_objects.FlowResponse:
  return rdf_flow_objects.FlowResponse.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowIterator(
    rdf: rdf_flow_objects.FlowIterator,
) -> flows_pb2.FlowIterator:
  return rdf.AsPrimitiveProto()


def ToRDFFlowIterator(
    proto: flows_pb2.FlowIterator,
) -> rdf_flow_objects.FlowIterator:
  return rdf_flow_objects.FlowIterator.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowStatus(rdf: rdf_flow_objects.FlowStatus) -> flows_pb2.FlowStatus:
  return rdf.AsPrimitiveProto()


def ToRDFFlowStatus(proto: flows_pb2.FlowStatus) -> rdf_flow_objects.FlowStatus:
  return rdf_flow_objects.FlowStatus.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowResult(rdf: rdf_flow_objects.FlowResult) -> flows_pb2.FlowResult:
  return rdf.AsPrimitiveProto()


def ToRDFFlowResult(proto: flows_pb2.FlowResult) -> rdf_flow_objects.FlowResult:
  return rdf_flow_objects.FlowResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowError(rdf: rdf_flow_objects.FlowError) -> flows_pb2.FlowError:
  return rdf.AsPrimitiveProto()


def ToRDFFlowError(proto: flows_pb2.FlowError) -> rdf_flow_objects.FlowError:
  return rdf_flow_objects.FlowError.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowLogEntry(
    rdf: rdf_flow_objects.FlowLogEntry,
) -> flows_pb2.FlowLogEntry:
  return rdf.AsPrimitiveProto()


def ToRDFFlowLogEntry(
    proto: flows_pb2.FlowLogEntry,
) -> rdf_flow_objects.FlowLogEntry:
  return rdf_flow_objects.FlowLogEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowOutputPluginLogEntry(
    rdf: rdf_flow_objects.FlowOutputPluginLogEntry,
) -> flows_pb2.FlowOutputPluginLogEntry:
  return rdf.AsPrimitiveProto()


def ToRDFFlowOutputPluginLogEntry(
    proto: flows_pb2.FlowOutputPluginLogEntry,
) -> rdf_flow_objects.FlowOutputPluginLogEntry:
  return rdf_flow_objects.FlowOutputPluginLogEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlow(rdf: rdf_flow_objects.Flow) -> flows_pb2.Flow:
  return rdf.AsPrimitiveProto()


def ToRDFFlow(proto: flows_pb2.Flow) -> rdf_flow_objects.Flow:
  return rdf_flow_objects.Flow.FromSerializedBytes(proto.SerializeToString())


def ToProtoScheduledFlow(
    rdf: rdf_flow_objects.ScheduledFlow,
) -> flows_pb2.ScheduledFlow:
  return rdf.AsPrimitiveProto()


def ToRDFScheduledFlow(
    proto: flows_pb2.ScheduledFlow,
) -> rdf_flow_objects.ScheduledFlow:
  return rdf_flow_objects.ScheduledFlow.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowResultCount(
    rdf: rdf_flow_objects.FlowResultCount,
) -> flows_pb2.FlowResultCount:
  return rdf.AsPrimitiveProto()


def ToRDFFlowResultCount(
    proto: flows_pb2.FlowResultCount,
) -> rdf_flow_objects.FlowResultCount:
  return rdf_flow_objects.FlowResultCount.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowResultMetadata(
    rdf: rdf_flow_objects.FlowResultMetadata,
) -> flows_pb2.FlowResultMetadata:
  return rdf.AsPrimitiveProto()


def ToRDFFlowResultMetadata(
    proto: flows_pb2.FlowResultMetadata,
) -> rdf_flow_objects.FlowResultMetadata:
  return rdf_flow_objects.FlowResultMetadata.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoDefaultFlowProgress(
    rdf: rdf_flow_objects.DefaultFlowProgress,
) -> flows_pb2.DefaultFlowProgress:
  return rdf.AsPrimitiveProto()


def ToRDFDefaultFlowProgress(
    proto: flows_pb2.DefaultFlowProgress,
) -> rdf_flow_objects.DefaultFlowProgress:
  return rdf_flow_objects.DefaultFlowProgress.FromSerializedBytes(
      proto.SerializeToString()
  )
