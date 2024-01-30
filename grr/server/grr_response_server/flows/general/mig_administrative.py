#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import flows_pb2
from grr_response_server.flows.general import administrative


def ToProtoDeleteGRRTempFilesArgs(
    rdf: administrative.DeleteGRRTempFilesArgs,
) -> flows_pb2.DeleteGRRTempFilesArgs:
  return rdf.AsPrimitiveProto()


def ToRDFDeleteGRRTempFilesArgs(
    proto: flows_pb2.DeleteGRRTempFilesArgs,
) -> administrative.DeleteGRRTempFilesArgs:
  return administrative.DeleteGRRTempFilesArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoUpdateConfigurationArgs(
    rdf: administrative.UpdateConfigurationArgs,
) -> flows_pb2.UpdateConfigurationArgs:
  return rdf.AsPrimitiveProto()


def ToRDFUpdateConfigurationArgs(
    proto: flows_pb2.UpdateConfigurationArgs,
) -> administrative.UpdateConfigurationArgs:
  return administrative.UpdateConfigurationArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExecutePythonHackArgs(
    rdf: administrative.ExecutePythonHackArgs,
) -> flows_pb2.ExecutePythonHackArgs:
  return rdf.AsPrimitiveProto()


def ToRDFExecutePythonHackArgs(
    proto: flows_pb2.ExecutePythonHackArgs,
) -> administrative.ExecutePythonHackArgs:
  return administrative.ExecutePythonHackArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExecutePythonHackResult(
    rdf: administrative.ExecutePythonHackResult,
) -> flows_pb2.ExecutePythonHackResult:
  return rdf.AsPrimitiveProto()


def ToRDFExecutePythonHackResult(
    proto: flows_pb2.ExecutePythonHackResult,
) -> administrative.ExecutePythonHackResult:
  return administrative.ExecutePythonHackResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExecuteCommandArgs(
    rdf: administrative.ExecuteCommandArgs,
) -> flows_pb2.ExecuteCommandArgs:
  return rdf.AsPrimitiveProto()


def ToRDFExecuteCommandArgs(
    proto: flows_pb2.ExecuteCommandArgs,
) -> administrative.ExecuteCommandArgs:
  return administrative.ExecuteCommandArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoOnlineNotificationArgs(
    rdf: administrative.OnlineNotificationArgs,
) -> flows_pb2.OnlineNotificationArgs:
  return rdf.AsPrimitiveProto()


def ToRDFOnlineNotificationArgs(
    proto: flows_pb2.OnlineNotificationArgs,
) -> administrative.OnlineNotificationArgs:
  return administrative.OnlineNotificationArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoLaunchBinaryArgs(
    rdf: administrative.LaunchBinaryArgs,
) -> flows_pb2.LaunchBinaryArgs:
  return rdf.AsPrimitiveProto()


def ToRDFLaunchBinaryArgs(
    proto: flows_pb2.LaunchBinaryArgs,
) -> administrative.LaunchBinaryArgs:
  return administrative.LaunchBinaryArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
