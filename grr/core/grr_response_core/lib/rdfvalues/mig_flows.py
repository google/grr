#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2


def ToProtoGrrMessage(rdf: rdf_flows.GrrMessage) -> jobs_pb2.GrrMessage:
  return rdf.AsPrimitiveProto()


def ToRDFGrrMessage(proto: jobs_pb2.GrrMessage) -> rdf_flows.GrrMessage:
  return rdf_flows.GrrMessage.FromSerializedBytes(proto.SerializeToString())


def ToProtoGrrStatus(rdf: rdf_flows.GrrStatus) -> jobs_pb2.GrrStatus:
  return rdf.AsPrimitiveProto()


def ToRDFGrrStatus(proto: jobs_pb2.GrrStatus) -> rdf_flows.GrrStatus:
  return rdf_flows.GrrStatus.FromSerializedBytes(proto.SerializeToString())


def ToProtoFlowProcessingRequest(
    rdf: rdf_flows.FlowProcessingRequest,
) -> flows_pb2.FlowProcessingRequest:
  return rdf.AsPrimitiveProto()


def ToRDFFlowProcessingRequest(
    proto: flows_pb2.FlowProcessingRequest,
) -> rdf_flows.FlowProcessingRequest:
  return rdf_flows.FlowProcessingRequest.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoNotification(rdf: rdf_flows.Notification) -> jobs_pb2.Notification:
  return rdf.AsPrimitiveProto()


def ToRDFNotification(proto: jobs_pb2.Notification) -> rdf_flows.Notification:
  return rdf_flows.Notification.FromSerializedBytes(proto.SerializeToString())


def ToProtoFlowNotification(
    rdf: rdf_flows.FlowNotification,
) -> jobs_pb2.FlowNotification:
  return rdf.AsPrimitiveProto()


def ToRDFFlowNotification(
    proto: jobs_pb2.FlowNotification,
) -> rdf_flows.FlowNotification:
  return rdf_flows.FlowNotification.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoPackedMessageList(
    rdf: rdf_flows.PackedMessageList,
) -> jobs_pb2.PackedMessageList:
  return rdf.AsPrimitiveProto()


def ToRDFPackedMessageList(
    proto: jobs_pb2.PackedMessageList,
) -> rdf_flows.PackedMessageList:
  return rdf_flows.PackedMessageList.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoMessageList(rdf: rdf_flows.MessageList) -> jobs_pb2.MessageList:
  return rdf.AsPrimitiveProto()


def ToRDFMessageList(proto: jobs_pb2.MessageList) -> rdf_flows.MessageList:
  return rdf_flows.MessageList.FromSerializedBytes(proto.SerializeToString())


def ToProtoCipherProperties(
    rdf: rdf_flows.CipherProperties,
) -> jobs_pb2.CipherProperties:
  return rdf.AsPrimitiveProto()


def ToRDFCipherProperties(
    proto: jobs_pb2.CipherProperties,
) -> rdf_flows.CipherProperties:
  return rdf_flows.CipherProperties.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoCipherMetadata(
    rdf: rdf_flows.CipherMetadata,
) -> jobs_pb2.CipherMetadata:
  return rdf.AsPrimitiveProto()


def ToRDFCipherMetadata(
    proto: jobs_pb2.CipherMetadata,
) -> rdf_flows.CipherMetadata:
  return rdf_flows.CipherMetadata.FromSerializedBytes(proto.SerializeToString())


def ToProtoFlowLog(rdf: rdf_flows.FlowLog) -> jobs_pb2.FlowLog:
  return rdf.AsPrimitiveProto()


def ToRDFFlowLog(proto: jobs_pb2.FlowLog) -> rdf_flows.FlowLog:
  return rdf_flows.FlowLog.FromSerializedBytes(proto.SerializeToString())


def ToProtoHttpRequest(rdf: rdf_flows.HttpRequest) -> jobs_pb2.HttpRequest:
  return rdf.AsPrimitiveProto()


def ToRDFHttpRequest(proto: jobs_pb2.HttpRequest) -> rdf_flows.HttpRequest:
  return rdf_flows.HttpRequest.FromSerializedBytes(proto.SerializeToString())


def ToProtoClientCommunication(
    rdf: rdf_flows.ClientCommunication,
) -> jobs_pb2.ClientCommunication:
  return rdf.AsPrimitiveProto()


def ToRDFClientCommunication(
    proto: jobs_pb2.ClientCommunication,
) -> rdf_flows.ClientCommunication:
  return rdf_flows.ClientCommunication.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoEmptyFlowArgs(
    rdf: rdf_flows.EmptyFlowArgs,
) -> flows_pb2.EmptyFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFEmptyFlowArgs(
    proto: flows_pb2.EmptyFlowArgs,
) -> rdf_flows.EmptyFlowArgs:
  return rdf_flows.EmptyFlowArgs.FromSerializedBytes(proto.SerializeToString())
