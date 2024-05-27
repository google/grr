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


def ToProtoApiHunt(rdf: hunt.ApiHunt) -> hunt_pb2.ApiHunt:
  return rdf.AsPrimitiveProto()


def ToRDFApiHunt(proto: hunt_pb2.ApiHunt) -> hunt.ApiHunt:
  return hunt.ApiHunt.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiHuntResult(rdf: hunt.ApiHuntResult) -> hunt_pb2.ApiHuntResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiHuntResult(proto: hunt_pb2.ApiHuntResult) -> hunt.ApiHuntResult:
  return hunt.ApiHuntResult.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiHuntClient(rdf: hunt.ApiHuntClient) -> hunt_pb2.ApiHuntClient:
  return rdf.AsPrimitiveProto()


def ToRDFApiHuntClient(proto: hunt_pb2.ApiHuntClient) -> hunt.ApiHuntClient:
  return hunt.ApiHuntClient.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiHuntLog(rdf: hunt.ApiHuntLog) -> hunt_pb2.ApiHuntLog:
  return rdf.AsPrimitiveProto()


def ToRDFApiHuntLog(proto: hunt_pb2.ApiHuntLog) -> hunt.ApiHuntLog:
  return hunt.ApiHuntLog.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiHuntError(rdf: hunt.ApiHuntError) -> hunt_pb2.ApiHuntError:
  return rdf.AsPrimitiveProto()


def ToRDFApiHuntError(proto: hunt_pb2.ApiHuntError) -> hunt.ApiHuntError:
  return hunt.ApiHuntError.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListHuntsArgs(
    rdf: hunt.ApiListHuntsArgs,
) -> hunt_pb2.ApiListHuntsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntsArgs(
    proto: hunt_pb2.ApiListHuntsArgs,
) -> hunt.ApiListHuntsArgs:
  return hunt.ApiListHuntsArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListHuntsResult(
    rdf: hunt.ApiListHuntsResult,
) -> hunt_pb2.ApiListHuntsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntsResult(
    proto: hunt_pb2.ApiListHuntsResult,
) -> hunt.ApiListHuntsResult:
  return hunt.ApiListHuntsResult.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiVerifyHuntAccessArgs(
    rdf: hunt.ApiVerifyHuntAccessArgs,
) -> hunt_pb2.ApiVerifyHuntAccessArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiVerifyHuntAccessArgs(
    proto: hunt_pb2.ApiVerifyHuntAccessArgs,
) -> hunt.ApiVerifyHuntAccessArgs:
  return hunt.ApiVerifyHuntAccessArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiVerifyHuntAccessResult(
    rdf: hunt.ApiVerifyHuntAccessResult,
) -> hunt_pb2.ApiVerifyHuntAccessResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiVerifyHuntAccessResult(
    proto: hunt_pb2.ApiVerifyHuntAccessResult,
) -> hunt.ApiVerifyHuntAccessResult:
  return hunt.ApiVerifyHuntAccessResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetHuntArgs(rdf: hunt.ApiGetHuntArgs) -> hunt_pb2.ApiGetHuntArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntArgs(proto: hunt_pb2.ApiGetHuntArgs) -> hunt.ApiGetHuntArgs:
  return hunt.ApiGetHuntArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiCountHuntResultsByTypeArgs(
    rdf: hunt.ApiCountHuntResultsByTypeArgs,
) -> hunt_pb2.ApiCountHuntResultsByTypeArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiCountHuntResultsByTypeArgs(
    proto: hunt_pb2.ApiCountHuntResultsByTypeArgs,
) -> hunt.ApiCountHuntResultsByTypeArgs:
  return hunt.ApiCountHuntResultsByTypeArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiTypeCount(rdf: hunt.ApiTypeCount) -> hunt_pb2.ApiTypeCount:
  return rdf.AsPrimitiveProto()


def ToRDFApiTypeCount(proto: hunt_pb2.ApiTypeCount) -> hunt.ApiTypeCount:
  return hunt.ApiTypeCount.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiCountHuntResultsByTypeResult(
    rdf: hunt.ApiCountHuntResultsByTypeResult,
) -> hunt_pb2.ApiCountHuntResultsByTypeResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiCountHuntResultsByTypeResult(
    proto: hunt_pb2.ApiCountHuntResultsByTypeResult,
) -> hunt.ApiCountHuntResultsByTypeResult:
  return hunt.ApiCountHuntResultsByTypeResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntResultsArgs(
    rdf: hunt.ApiListHuntResultsArgs,
) -> hunt_pb2.ApiListHuntResultsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntResultsArgs(
    proto: hunt_pb2.ApiListHuntResultsArgs,
) -> hunt.ApiListHuntResultsArgs:
  return hunt.ApiListHuntResultsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntResultsResult(
    rdf: hunt.ApiListHuntResultsResult,
) -> hunt_pb2.ApiListHuntResultsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntResultsResult(
    proto: hunt_pb2.ApiListHuntResultsResult,
) -> hunt.ApiListHuntResultsResult:
  return hunt.ApiListHuntResultsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntCrashesArgs(
    rdf: hunt.ApiListHuntCrashesArgs,
) -> hunt_pb2.ApiListHuntCrashesArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntCrashesArgs(
    proto: hunt_pb2.ApiListHuntCrashesArgs,
) -> hunt.ApiListHuntCrashesArgs:
  return hunt.ApiListHuntCrashesArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntCrashesResult(
    rdf: hunt.ApiListHuntCrashesResult,
) -> hunt_pb2.ApiListHuntCrashesResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntCrashesResult(
    proto: hunt_pb2.ApiListHuntCrashesResult,
) -> hunt.ApiListHuntCrashesResult:
  return hunt.ApiListHuntCrashesResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetHuntResultsExportCommandArgs(
    rdf: hunt.ApiGetHuntResultsExportCommandArgs,
) -> hunt_pb2.ApiGetHuntResultsExportCommandArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntResultsExportCommandArgs(
    proto: hunt_pb2.ApiGetHuntResultsExportCommandArgs,
) -> hunt.ApiGetHuntResultsExportCommandArgs:
  return hunt.ApiGetHuntResultsExportCommandArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetHuntResultsExportCommandResult(
    rdf: hunt.ApiGetHuntResultsExportCommandResult,
) -> hunt_pb2.ApiGetHuntResultsExportCommandResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntResultsExportCommandResult(
    proto: hunt_pb2.ApiGetHuntResultsExportCommandResult,
) -> hunt.ApiGetHuntResultsExportCommandResult:
  return hunt.ApiGetHuntResultsExportCommandResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntOutputPluginsArgs(
    rdf: hunt.ApiListHuntOutputPluginsArgs,
) -> hunt_pb2.ApiListHuntOutputPluginsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntOutputPluginsArgs(
    proto: hunt_pb2.ApiListHuntOutputPluginsArgs,
) -> hunt.ApiListHuntOutputPluginsArgs:
  return hunt.ApiListHuntOutputPluginsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntOutputPluginsResult(
    rdf: hunt.ApiListHuntOutputPluginsResult,
) -> hunt_pb2.ApiListHuntOutputPluginsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntOutputPluginsResult(
    proto: hunt_pb2.ApiListHuntOutputPluginsResult,
) -> hunt.ApiListHuntOutputPluginsResult:
  return hunt.ApiListHuntOutputPluginsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntOutputPluginLogsArgs(
    rdf: hunt.ApiListHuntOutputPluginLogsArgs,
) -> hunt_pb2.ApiListHuntOutputPluginLogsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntOutputPluginLogsArgs(
    proto: hunt_pb2.ApiListHuntOutputPluginLogsArgs,
) -> hunt.ApiListHuntOutputPluginLogsArgs:
  return hunt.ApiListHuntOutputPluginLogsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntOutputPluginLogsResult(
    rdf: hunt.ApiListHuntOutputPluginLogsResult,
) -> hunt_pb2.ApiListHuntOutputPluginLogsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntOutputPluginLogsResult(
    proto: hunt_pb2.ApiListHuntOutputPluginLogsResult,
) -> hunt.ApiListHuntOutputPluginLogsResult:
  return hunt.ApiListHuntOutputPluginLogsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntOutputPluginErrorsArgs(
    rdf: hunt.ApiListHuntOutputPluginErrorsArgs,
) -> hunt_pb2.ApiListHuntOutputPluginErrorsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntOutputPluginErrorsArgs(
    proto: hunt_pb2.ApiListHuntOutputPluginErrorsArgs,
) -> hunt.ApiListHuntOutputPluginErrorsArgs:
  return hunt.ApiListHuntOutputPluginErrorsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntOutputPluginErrorsResult(
    rdf: hunt.ApiListHuntOutputPluginErrorsResult,
) -> hunt_pb2.ApiListHuntOutputPluginErrorsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntOutputPluginErrorsResult(
    proto: hunt_pb2.ApiListHuntOutputPluginErrorsResult,
) -> hunt.ApiListHuntOutputPluginErrorsResult:
  return hunt.ApiListHuntOutputPluginErrorsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntLogsArgs(
    rdf: hunt.ApiListHuntLogsArgs,
) -> hunt_pb2.ApiListHuntLogsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntLogsArgs(
    proto: hunt_pb2.ApiListHuntLogsArgs,
) -> hunt.ApiListHuntLogsArgs:
  return hunt.ApiListHuntLogsArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListHuntLogsResult(
    rdf: hunt.ApiListHuntLogsResult,
) -> hunt_pb2.ApiListHuntLogsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntLogsResult(
    proto: hunt_pb2.ApiListHuntLogsResult,
) -> hunt.ApiListHuntLogsResult:
  return hunt.ApiListHuntLogsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntErrorsArgs(
    rdf: hunt.ApiListHuntErrorsArgs,
) -> hunt_pb2.ApiListHuntErrorsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntErrorsArgs(
    proto: hunt_pb2.ApiListHuntErrorsArgs,
) -> hunt.ApiListHuntErrorsArgs:
  return hunt.ApiListHuntErrorsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntErrorsResult(
    rdf: hunt.ApiListHuntErrorsResult,
) -> hunt_pb2.ApiListHuntErrorsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntErrorsResult(
    proto: hunt_pb2.ApiListHuntErrorsResult,
) -> hunt.ApiListHuntErrorsResult:
  return hunt.ApiListHuntErrorsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetHuntClientCompletionStatsArgs(
    rdf: hunt.ApiGetHuntClientCompletionStatsArgs,
) -> hunt_pb2.ApiGetHuntClientCompletionStatsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntClientCompletionStatsArgs(
    proto: hunt_pb2.ApiGetHuntClientCompletionStatsArgs,
) -> hunt.ApiGetHuntClientCompletionStatsArgs:
  return hunt.ApiGetHuntClientCompletionStatsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetHuntClientCompletionStatsResult(
    rdf: hunt.ApiGetHuntClientCompletionStatsResult,
) -> hunt_pb2.ApiGetHuntClientCompletionStatsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntClientCompletionStatsResult(
    proto: hunt_pb2.ApiGetHuntClientCompletionStatsResult,
) -> hunt.ApiGetHuntClientCompletionStatsResult:
  return hunt.ApiGetHuntClientCompletionStatsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetHuntFilesArchiveArgs(
    rdf: hunt.ApiGetHuntFilesArchiveArgs,
) -> hunt_pb2.ApiGetHuntFilesArchiveArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntFilesArchiveArgs(
    proto: hunt_pb2.ApiGetHuntFilesArchiveArgs,
) -> hunt.ApiGetHuntFilesArchiveArgs:
  return hunt.ApiGetHuntFilesArchiveArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetHuntFileArgs(
    rdf: hunt.ApiGetHuntFileArgs,
) -> hunt_pb2.ApiGetHuntFileArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntFileArgs(
    proto: hunt_pb2.ApiGetHuntFileArgs,
) -> hunt.ApiGetHuntFileArgs:
  return hunt.ApiGetHuntFileArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGetHuntStatsArgs(
    rdf: hunt.ApiGetHuntStatsArgs,
) -> hunt_pb2.ApiGetHuntStatsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntStatsArgs(
    proto: hunt_pb2.ApiGetHuntStatsArgs,
) -> hunt.ApiGetHuntStatsArgs:
  return hunt.ApiGetHuntStatsArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGetHuntStatsResult(
    rdf: hunt.ApiGetHuntStatsResult,
) -> hunt_pb2.ApiGetHuntStatsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntStatsResult(
    proto: hunt_pb2.ApiGetHuntStatsResult,
) -> hunt.ApiGetHuntStatsResult:
  return hunt.ApiGetHuntStatsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntClientsArgs(
    rdf: hunt.ApiListHuntClientsArgs,
) -> hunt_pb2.ApiListHuntClientsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntClientsArgs(
    proto: hunt_pb2.ApiListHuntClientsArgs,
) -> hunt.ApiListHuntClientsArgs:
  return hunt.ApiListHuntClientsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntClientsResult(
    rdf: hunt.ApiListHuntClientsResult,
) -> hunt_pb2.ApiListHuntClientsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntClientsResult(
    proto: hunt_pb2.ApiListHuntClientsResult,
) -> hunt.ApiListHuntClientsResult:
  return hunt.ApiListHuntClientsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetHuntContextArgs(
    rdf: hunt.ApiGetHuntContextArgs,
) -> hunt_pb2.ApiGetHuntContextArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntContextArgs(
    proto: hunt_pb2.ApiGetHuntContextArgs,
) -> hunt.ApiGetHuntContextArgs:
  return hunt.ApiGetHuntContextArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetHuntContextResult(
    rdf: hunt.ApiGetHuntContextResult,
) -> hunt_pb2.ApiGetHuntContextResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntContextResult(
    proto: hunt_pb2.ApiGetHuntContextResult,
) -> hunt.ApiGetHuntContextResult:
  return hunt.ApiGetHuntContextResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiCreateHuntArgs(
    rdf: hunt.ApiCreateHuntArgs,
) -> hunt_pb2.ApiCreateHuntArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiCreateHuntArgs(
    proto: hunt_pb2.ApiCreateHuntArgs,
) -> hunt.ApiCreateHuntArgs:
  return hunt.ApiCreateHuntArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiModifyHuntArgs(
    rdf: hunt.ApiModifyHuntArgs,
) -> hunt_pb2.ApiModifyHuntArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiModifyHuntArgs(
    proto: hunt_pb2.ApiModifyHuntArgs,
) -> hunt.ApiModifyHuntArgs:
  return hunt.ApiModifyHuntArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiDeleteHuntArgs(
    rdf: hunt.ApiDeleteHuntArgs,
) -> hunt_pb2.ApiDeleteHuntArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiDeleteHuntArgs(
    proto: hunt_pb2.ApiDeleteHuntArgs,
) -> hunt.ApiDeleteHuntArgs:
  return hunt.ApiDeleteHuntArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGetExportedHuntResultsArgs(
    rdf: hunt.ApiGetExportedHuntResultsArgs,
) -> hunt_pb2.ApiGetExportedHuntResultsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetExportedHuntResultsArgs(
    proto: hunt_pb2.ApiGetExportedHuntResultsArgs,
) -> hunt.ApiGetExportedHuntResultsArgs:
  return hunt.ApiGetExportedHuntResultsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoPerClientFileCollectionArgs(
    rdf: hunt.PerClientFileCollectionArgs,
) -> hunt_pb2.PerClientFileCollectionArgs:
  return rdf.AsPrimitiveProto()


def ToRDFPerClientFileCollectionArgs(
    proto: hunt_pb2.PerClientFileCollectionArgs,
) -> hunt.PerClientFileCollectionArgs:
  return hunt.PerClientFileCollectionArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiCreatePerClientFileCollectionHuntArgs(
    rdf: hunt.ApiCreatePerClientFileCollectionHuntArgs,
) -> hunt_pb2.ApiCreatePerClientFileCollectionHuntArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiCreatePerClientFileCollectionHuntArgs(
    proto: hunt_pb2.ApiCreatePerClientFileCollectionHuntArgs,
) -> hunt.ApiCreatePerClientFileCollectionHuntArgs:
  return hunt.ApiCreatePerClientFileCollectionHuntArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
