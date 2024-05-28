#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import flow_pb2
from grr_response_server.gui.api_plugins import flow


def ToProtoApiFlowDescriptor(
    rdf: flow.ApiFlowDescriptor,
) -> flow_pb2.ApiFlowDescriptor:
  return rdf.AsPrimitiveProto()


def ToRDFApiFlowDescriptor(
    proto: flow_pb2.ApiFlowDescriptor,
) -> flow.ApiFlowDescriptor:
  return flow.ApiFlowDescriptor.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiFlowReference(
    rdf: flow.ApiFlowReference,
) -> flow_pb2.ApiFlowReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiFlowReference(
    proto: flow_pb2.ApiFlowReference,
) -> flow.ApiFlowReference:
  return flow.ApiFlowReference.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiFlow(rdf: flow.ApiFlow) -> flow_pb2.ApiFlow:
  return rdf.AsPrimitiveProto()


def ToRDFApiFlow(proto: flow_pb2.ApiFlow) -> flow.ApiFlow:
  return flow.ApiFlow.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiFlowRequest(rdf: flow.ApiFlowRequest) -> flow_pb2.ApiFlowRequest:
  return rdf.AsPrimitiveProto()


def ToRDFApiFlowRequest(proto: flow_pb2.ApiFlowRequest) -> flow.ApiFlowRequest:
  return flow.ApiFlowRequest.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiFlowResult(rdf: flow.ApiFlowResult) -> flow_pb2.ApiFlowResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiFlowResult(proto: flow_pb2.ApiFlowResult) -> flow.ApiFlowResult:
  return flow.ApiFlowResult.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiFlowLog(rdf: flow.ApiFlowLog) -> flow_pb2.ApiFlowLog:
  return rdf.AsPrimitiveProto()


def ToRDFApiFlowLog(proto: flow_pb2.ApiFlowLog) -> flow.ApiFlowLog:
  return flow.ApiFlowLog.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGetFlowArgs(rdf: flow.ApiGetFlowArgs) -> flow_pb2.ApiGetFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFlowArgs(proto: flow_pb2.ApiGetFlowArgs) -> flow.ApiGetFlowArgs:
  return flow.ApiGetFlowArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListFlowRequestsArgs(
    rdf: flow.ApiListFlowRequestsArgs,
) -> flow_pb2.ApiListFlowRequestsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowRequestsArgs(
    proto: flow_pb2.ApiListFlowRequestsArgs,
) -> flow.ApiListFlowRequestsArgs:
  return flow.ApiListFlowRequestsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFlowRequestsResult(
    rdf: flow.ApiListFlowRequestsResult,
) -> flow_pb2.ApiListFlowRequestsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowRequestsResult(
    proto: flow_pb2.ApiListFlowRequestsResult,
) -> flow.ApiListFlowRequestsResult:
  return flow.ApiListFlowRequestsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFlowResultsArgs(
    rdf: flow.ApiListFlowResultsArgs,
) -> flow_pb2.ApiListFlowResultsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowResultsArgs(
    proto: flow_pb2.ApiListFlowResultsArgs,
) -> flow.ApiListFlowResultsArgs:
  return flow.ApiListFlowResultsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFlowResultsResult(
    rdf: flow.ApiListFlowResultsResult,
) -> flow_pb2.ApiListFlowResultsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowResultsResult(
    proto: flow_pb2.ApiListFlowResultsResult,
) -> flow.ApiListFlowResultsResult:
  return flow.ApiListFlowResultsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFlowLogsArgs(
    rdf: flow.ApiListFlowLogsArgs,
) -> flow_pb2.ApiListFlowLogsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowLogsArgs(
    proto: flow_pb2.ApiListFlowLogsArgs,
) -> flow.ApiListFlowLogsArgs:
  return flow.ApiListFlowLogsArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListFlowLogsResult(
    rdf: flow.ApiListFlowLogsResult,
) -> flow_pb2.ApiListFlowLogsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowLogsResult(
    proto: flow_pb2.ApiListFlowLogsResult,
) -> flow.ApiListFlowLogsResult:
  return flow.ApiListFlowLogsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFlowResultsExportCommandArgs(
    rdf: flow.ApiGetFlowResultsExportCommandArgs,
) -> flow_pb2.ApiGetFlowResultsExportCommandArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFlowResultsExportCommandArgs(
    proto: flow_pb2.ApiGetFlowResultsExportCommandArgs,
) -> flow.ApiGetFlowResultsExportCommandArgs:
  return flow.ApiGetFlowResultsExportCommandArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFlowResultsExportCommandResult(
    rdf: flow.ApiGetFlowResultsExportCommandResult,
) -> flow_pb2.ApiGetFlowResultsExportCommandResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFlowResultsExportCommandResult(
    proto: flow_pb2.ApiGetFlowResultsExportCommandResult,
) -> flow.ApiGetFlowResultsExportCommandResult:
  return flow.ApiGetFlowResultsExportCommandResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFlowFilesArchiveArgs(
    rdf: flow.ApiGetFlowFilesArchiveArgs,
) -> flow_pb2.ApiGetFlowFilesArchiveArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFlowFilesArchiveArgs(
    proto: flow_pb2.ApiGetFlowFilesArchiveArgs,
) -> flow.ApiGetFlowFilesArchiveArgs:
  return flow.ApiGetFlowFilesArchiveArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFlowOutputPluginsArgs(
    rdf: flow.ApiListFlowOutputPluginsArgs,
) -> flow_pb2.ApiListFlowOutputPluginsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowOutputPluginsArgs(
    proto: flow_pb2.ApiListFlowOutputPluginsArgs,
) -> flow.ApiListFlowOutputPluginsArgs:
  return flow.ApiListFlowOutputPluginsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFlowOutputPluginsResult(
    rdf: flow.ApiListFlowOutputPluginsResult,
) -> flow_pb2.ApiListFlowOutputPluginsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowOutputPluginsResult(
    proto: flow_pb2.ApiListFlowOutputPluginsResult,
) -> flow.ApiListFlowOutputPluginsResult:
  return flow.ApiListFlowOutputPluginsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFlowOutputPluginLogsArgs(
    rdf: flow.ApiListFlowOutputPluginLogsArgs,
) -> flow_pb2.ApiListFlowOutputPluginLogsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowOutputPluginLogsArgs(
    proto: flow_pb2.ApiListFlowOutputPluginLogsArgs,
) -> flow.ApiListFlowOutputPluginLogsArgs:
  return flow.ApiListFlowOutputPluginLogsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFlowOutputPluginLogsResult(
    rdf: flow.ApiListFlowOutputPluginLogsResult,
) -> flow_pb2.ApiListFlowOutputPluginLogsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowOutputPluginLogsResult(
    proto: flow_pb2.ApiListFlowOutputPluginLogsResult,
) -> flow.ApiListFlowOutputPluginLogsResult:
  return flow.ApiListFlowOutputPluginLogsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFlowOutputPluginErrorsArgs(
    rdf: flow.ApiListFlowOutputPluginErrorsArgs,
) -> flow_pb2.ApiListFlowOutputPluginErrorsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowOutputPluginErrorsArgs(
    proto: flow_pb2.ApiListFlowOutputPluginErrorsArgs,
) -> flow.ApiListFlowOutputPluginErrorsArgs:
  return flow.ApiListFlowOutputPluginErrorsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFlowOutputPluginErrorsResult(
    rdf: flow.ApiListFlowOutputPluginErrorsResult,
) -> flow_pb2.ApiListFlowOutputPluginErrorsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowOutputPluginErrorsResult(
    proto: flow_pb2.ApiListFlowOutputPluginErrorsResult,
) -> flow.ApiListFlowOutputPluginErrorsResult:
  return flow.ApiListFlowOutputPluginErrorsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListFlowsArgs(
    rdf: flow.ApiListFlowsArgs,
) -> flow_pb2.ApiListFlowsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowsArgs(
    proto: flow_pb2.ApiListFlowsArgs,
) -> flow.ApiListFlowsArgs:
  return flow.ApiListFlowsArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListFlowsResult(
    rdf: flow.ApiListFlowsResult,
) -> flow_pb2.ApiListFlowsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowsResult(
    proto: flow_pb2.ApiListFlowsResult,
) -> flow.ApiListFlowsResult:
  return flow.ApiListFlowsResult.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiCreateFlowArgs(
    rdf: flow.ApiCreateFlowArgs,
) -> flow_pb2.ApiCreateFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiCreateFlowArgs(
    proto: flow_pb2.ApiCreateFlowArgs,
) -> flow.ApiCreateFlowArgs:
  return flow.ApiCreateFlowArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiCancelFlowArgs(
    rdf: flow.ApiCancelFlowArgs,
) -> flow_pb2.ApiCancelFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiCancelFlowArgs(
    proto: flow_pb2.ApiCancelFlowArgs,
) -> flow.ApiCancelFlowArgs:
  return flow.ApiCancelFlowArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListFlowDescriptorsResult(
    rdf: flow.ApiListFlowDescriptorsResult,
) -> flow_pb2.ApiListFlowDescriptorsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListFlowDescriptorsResult(
    proto: flow_pb2.ApiListFlowDescriptorsResult,
) -> flow.ApiListFlowDescriptorsResult:
  return flow.ApiListFlowDescriptorsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetExportedFlowResultsArgs(
    rdf: flow.ApiGetExportedFlowResultsArgs,
) -> flow_pb2.ApiGetExportedFlowResultsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetExportedFlowResultsArgs(
    proto: flow_pb2.ApiGetExportedFlowResultsArgs,
) -> flow.ApiGetExportedFlowResultsArgs:
  return flow.ApiGetExportedFlowResultsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiExplainGlobExpressionArgs(
    rdf: flow.ApiExplainGlobExpressionArgs,
) -> flow_pb2.ApiExplainGlobExpressionArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiExplainGlobExpressionArgs(
    proto: flow_pb2.ApiExplainGlobExpressionArgs,
) -> flow.ApiExplainGlobExpressionArgs:
  return flow.ApiExplainGlobExpressionArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiExplainGlobExpressionResult(
    rdf: flow.ApiExplainGlobExpressionResult,
) -> flow_pb2.ApiExplainGlobExpressionResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiExplainGlobExpressionResult(
    proto: flow_pb2.ApiExplainGlobExpressionResult,
) -> flow.ApiExplainGlobExpressionResult:
  return flow.ApiExplainGlobExpressionResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiScheduledFlow(
    rdf: flow.ApiScheduledFlow,
) -> flow_pb2.ApiScheduledFlow:
  return rdf.AsPrimitiveProto()


def ToRDFApiScheduledFlow(
    proto: flow_pb2.ApiScheduledFlow,
) -> flow.ApiScheduledFlow:
  return flow.ApiScheduledFlow.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListScheduledFlowsArgs(
    rdf: flow.ApiListScheduledFlowsArgs,
) -> flow_pb2.ApiListScheduledFlowsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListScheduledFlowsArgs(
    proto: flow_pb2.ApiListScheduledFlowsArgs,
) -> flow.ApiListScheduledFlowsArgs:
  return flow.ApiListScheduledFlowsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListScheduledFlowsResult(
    rdf: flow.ApiListScheduledFlowsResult,
) -> flow_pb2.ApiListScheduledFlowsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListScheduledFlowsResult(
    proto: flow_pb2.ApiListScheduledFlowsResult,
) -> flow.ApiListScheduledFlowsResult:
  return flow.ApiListScheduledFlowsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiUnscheduleFlowArgs(
    rdf: flow.ApiUnscheduleFlowArgs,
) -> flow_pb2.ApiUnscheduleFlowArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiUnscheduleFlowArgs(
    proto: flow_pb2.ApiUnscheduleFlowArgs,
) -> flow.ApiUnscheduleFlowArgs:
  return flow.ApiUnscheduleFlowArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiUnscheduleFlowResult(
    rdf: flow.ApiUnscheduleFlowResult,
) -> flow_pb2.ApiUnscheduleFlowResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiUnscheduleFlowResult(
    proto: flow_pb2.ApiUnscheduleFlowResult,
) -> flow.ApiUnscheduleFlowResult:
  return flow.ApiUnscheduleFlowResult.FromSerializedBytes(
      proto.SerializeToString()
  )
