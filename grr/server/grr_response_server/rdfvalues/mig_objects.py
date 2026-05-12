#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import objects_pb2
from grr_response_server.rdfvalues import objects as rdf_objects


def ToProtoPathInfo(rdf: rdf_objects.PathInfo) -> objects_pb2.PathInfo:
  return rdf.AsPrimitiveProto()


def ToRDFPathInfo(proto: objects_pb2.PathInfo) -> rdf_objects.PathInfo:
  return rdf_objects.PathInfo.FromSerializedBytes(proto.SerializeToString())


def ToProtoHuntReference(
    rdf: rdf_objects.HuntReference,
) -> objects_pb2.HuntReference:
  return rdf.AsPrimitiveProto()


def ToRDFHuntReference(
    proto: objects_pb2.HuntReference,
) -> rdf_objects.HuntReference:
  return rdf_objects.HuntReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoFlowReference(
    rdf: rdf_objects.FlowReference,
) -> objects_pb2.FlowReference:
  return rdf.AsPrimitiveProto()


def ToRDFFlowReference(
    proto: objects_pb2.FlowReference,
) -> rdf_objects.FlowReference:
  return rdf_objects.FlowReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoMessageHandlerRequest(
    rdf: rdf_objects.MessageHandlerRequest,
) -> objects_pb2.MessageHandlerRequest:
  return rdf.AsPrimitiveProto()


def ToRDFMessageHandlerRequest(
    proto: objects_pb2.MessageHandlerRequest,
) -> rdf_objects.MessageHandlerRequest:
  return rdf_objects.MessageHandlerRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoClientPathID(
    rdf: rdf_objects.ClientPathID,
) -> objects_pb2.ClientPathID:
  return rdf.AsPrimitiveProto()


def ToRDFClientPathID(
    proto: objects_pb2.ClientPathID,
) -> rdf_objects.ClientPathID:
  return rdf_objects.ClientPathID.FromSerializedBytes(proto.SerializeToString())


def ToProtoSerializedValueOfUnrecognizedType(
    rdf: rdf_objects.SerializedValueOfUnrecognizedType,
) -> objects_pb2.SerializedValueOfUnrecognizedType:
  return rdf.AsPrimitiveProto()


def ToRDFSerializedValueOfUnrecognizedType(
    proto: objects_pb2.SerializedValueOfUnrecognizedType,
) -> rdf_objects.SerializedValueOfUnrecognizedType:
  return rdf_objects.SerializedValueOfUnrecognizedType.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoSignedBinaryID(
    rdf: rdf_objects.SignedBinaryID,
) -> objects_pb2.SignedBinaryID:
  return rdf.AsPrimitiveProto()


def ToRDFSignedBinaryID(
    proto: objects_pb2.SignedBinaryID,
) -> rdf_objects.SignedBinaryID:
  return rdf_objects.SignedBinaryID.FromSerializedBytes(
      proto.SerializeToString()
  )
