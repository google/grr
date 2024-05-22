#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import client_pb2
from grr_response_server.gui.api_plugins import client


def ToProtoApiClient(rdf: client.ApiClient) -> client_pb2.ApiClient:
  return rdf.AsPrimitiveProto()


def ToRDFApiClient(proto: client_pb2.ApiClient) -> client.ApiClient:
  return client.ApiClient.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiSearchClientsArgs(
    rdf: client.ApiSearchClientsArgs,
) -> client_pb2.ApiSearchClientsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiSearchClientsArgs(
    proto: client_pb2.ApiSearchClientsArgs,
) -> client.ApiSearchClientsArgs:
  return client.ApiSearchClientsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiSearchClientsResult(
    rdf: client.ApiSearchClientsResult,
) -> client_pb2.ApiSearchClientsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiSearchClientsResult(
    proto: client_pb2.ApiSearchClientsResult,
) -> client.ApiSearchClientsResult:
  return client.ApiSearchClientsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiVerifyAccessArgs(
    rdf: client.ApiVerifyAccessArgs,
) -> client_pb2.ApiVerifyAccessArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiVerifyAccessArgs(
    proto: client_pb2.ApiVerifyAccessArgs,
) -> client.ApiVerifyAccessArgs:
  return client.ApiVerifyAccessArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiVerifyAccessResult(
    rdf: client.ApiVerifyAccessResult,
) -> client_pb2.ApiVerifyAccessResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiVerifyAccessResult(
    proto: client_pb2.ApiVerifyAccessResult,
) -> client.ApiVerifyAccessResult:
  return client.ApiVerifyAccessResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetClientArgs(
    rdf: client.ApiGetClientArgs,
) -> client_pb2.ApiGetClientArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetClientArgs(
    proto: client_pb2.ApiGetClientArgs,
) -> client.ApiGetClientArgs:
  return client.ApiGetClientArgs.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGetClientVersionsArgs(
    rdf: client.ApiGetClientVersionsArgs,
) -> client_pb2.ApiGetClientVersionsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetClientVersionsArgs(
    proto: client_pb2.ApiGetClientVersionsArgs,
) -> client.ApiGetClientVersionsArgs:
  return client.ApiGetClientVersionsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetClientVersionsResult(
    rdf: client.ApiGetClientVersionsResult,
) -> client_pb2.ApiGetClientVersionsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetClientVersionsResult(
    proto: client_pb2.ApiGetClientVersionsResult,
) -> client.ApiGetClientVersionsResult:
  return client.ApiGetClientVersionsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetClientVersionTimesArgs(
    rdf: client.ApiGetClientVersionTimesArgs,
) -> client_pb2.ApiGetClientVersionTimesArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetClientVersionTimesArgs(
    proto: client_pb2.ApiGetClientVersionTimesArgs,
) -> client.ApiGetClientVersionTimesArgs:
  return client.ApiGetClientVersionTimesArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetClientVersionTimesResult(
    rdf: client.ApiGetClientVersionTimesResult,
) -> client_pb2.ApiGetClientVersionTimesResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetClientVersionTimesResult(
    proto: client_pb2.ApiGetClientVersionTimesResult,
) -> client.ApiGetClientVersionTimesResult:
  return client.ApiGetClientVersionTimesResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiInterrogateClientArgs(
    rdf: client.ApiInterrogateClientArgs,
) -> client_pb2.ApiInterrogateClientArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiInterrogateClientArgs(
    proto: client_pb2.ApiInterrogateClientArgs,
) -> client.ApiInterrogateClientArgs:
  return client.ApiInterrogateClientArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiInterrogateClientResult(
    rdf: client.ApiInterrogateClientResult,
) -> client_pb2.ApiInterrogateClientResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiInterrogateClientResult(
    proto: client_pb2.ApiInterrogateClientResult,
) -> client.ApiInterrogateClientResult:
  return client.ApiInterrogateClientResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetInterrogateOperationStateArgs(
    rdf: client.ApiGetInterrogateOperationStateArgs,
) -> client_pb2.ApiGetInterrogateOperationStateArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetInterrogateOperationStateArgs(
    proto: client_pb2.ApiGetInterrogateOperationStateArgs,
) -> client.ApiGetInterrogateOperationStateArgs:
  return client.ApiGetInterrogateOperationStateArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetInterrogateOperationStateResult(
    rdf: client.ApiGetInterrogateOperationStateResult,
) -> client_pb2.ApiGetInterrogateOperationStateResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetInterrogateOperationStateResult(
    proto: client_pb2.ApiGetInterrogateOperationStateResult,
) -> client.ApiGetInterrogateOperationStateResult:
  return client.ApiGetInterrogateOperationStateResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetLastClientIPAddressArgs(
    rdf: client.ApiGetLastClientIPAddressArgs,
) -> client_pb2.ApiGetLastClientIPAddressArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetLastClientIPAddressArgs(
    proto: client_pb2.ApiGetLastClientIPAddressArgs,
) -> client.ApiGetLastClientIPAddressArgs:
  return client.ApiGetLastClientIPAddressArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetLastClientIPAddressResult(
    rdf: client.ApiGetLastClientIPAddressResult,
) -> client_pb2.ApiGetLastClientIPAddressResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetLastClientIPAddressResult(
    proto: client_pb2.ApiGetLastClientIPAddressResult,
) -> client.ApiGetLastClientIPAddressResult:
  return client.ApiGetLastClientIPAddressResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListClientCrashesArgs(
    rdf: client.ApiListClientCrashesArgs,
) -> client_pb2.ApiListClientCrashesArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListClientCrashesArgs(
    proto: client_pb2.ApiListClientCrashesArgs,
) -> client.ApiListClientCrashesArgs:
  return client.ApiListClientCrashesArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListClientCrashesResult(
    rdf: client.ApiListClientCrashesResult,
) -> client_pb2.ApiListClientCrashesResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListClientCrashesResult(
    proto: client_pb2.ApiListClientCrashesResult,
) -> client.ApiListClientCrashesResult:
  return client.ApiListClientCrashesResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiAddClientsLabelsArgs(
    rdf: client.ApiAddClientsLabelsArgs,
) -> client_pb2.ApiAddClientsLabelsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiAddClientsLabelsArgs(
    proto: client_pb2.ApiAddClientsLabelsArgs,
) -> client.ApiAddClientsLabelsArgs:
  return client.ApiAddClientsLabelsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiRemoveClientsLabelsArgs(
    rdf: client.ApiRemoveClientsLabelsArgs,
) -> client_pb2.ApiRemoveClientsLabelsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiRemoveClientsLabelsArgs(
    proto: client_pb2.ApiRemoveClientsLabelsArgs,
) -> client.ApiRemoveClientsLabelsArgs:
  return client.ApiRemoveClientsLabelsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListClientsLabelsResult(
    rdf: client.ApiListClientsLabelsResult,
) -> client_pb2.ApiListClientsLabelsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListClientsLabelsResult(
    proto: client_pb2.ApiListClientsLabelsResult,
) -> client.ApiListClientsLabelsResult:
  return client.ApiListClientsLabelsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListKbFieldsResult(
    rdf: client.ApiListKbFieldsResult,
) -> client_pb2.ApiListKbFieldsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListKbFieldsResult(
    proto: client_pb2.ApiListKbFieldsResult,
) -> client.ApiListKbFieldsResult:
  return client.ApiListKbFieldsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiKillFleetspeakArgs(
    rdf: client.ApiKillFleetspeakArgs,
) -> client_pb2.ApiKillFleetspeakArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiKillFleetspeakArgs(
    proto: client_pb2.ApiKillFleetspeakArgs,
) -> client.ApiKillFleetspeakArgs:
  return client.ApiKillFleetspeakArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiRestartFleetspeakGrrServiceArgs(
    rdf: client.ApiRestartFleetspeakGrrServiceArgs,
) -> client_pb2.ApiRestartFleetspeakGrrServiceArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiRestartFleetspeakGrrServiceArgs(
    proto: client_pb2.ApiRestartFleetspeakGrrServiceArgs,
) -> client.ApiRestartFleetspeakGrrServiceArgs:
  return client.ApiRestartFleetspeakGrrServiceArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiDeleteFleetspeakPendingMessagesArgs(
    rdf: client.ApiDeleteFleetspeakPendingMessagesArgs,
) -> client_pb2.ApiDeleteFleetspeakPendingMessagesArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiDeleteFleetspeakPendingMessagesArgs(
    proto: client_pb2.ApiDeleteFleetspeakPendingMessagesArgs,
) -> client.ApiDeleteFleetspeakPendingMessagesArgs:
  return client.ApiDeleteFleetspeakPendingMessagesArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFleetspeakPendingMessageCountArgs(
    rdf: client.ApiGetFleetspeakPendingMessageCountArgs,
) -> client_pb2.ApiGetFleetspeakPendingMessageCountArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFleetspeakPendingMessageCountArgs(
    proto: client_pb2.ApiGetFleetspeakPendingMessageCountArgs,
) -> client.ApiGetFleetspeakPendingMessageCountArgs:
  return client.ApiGetFleetspeakPendingMessageCountArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFleetspeakPendingMessageCountResult(
    rdf: client.ApiGetFleetspeakPendingMessageCountResult,
) -> client_pb2.ApiGetFleetspeakPendingMessageCountResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFleetspeakPendingMessageCountResult(
    proto: client_pb2.ApiGetFleetspeakPendingMessageCountResult,
) -> client.ApiGetFleetspeakPendingMessageCountResult:
  return client.ApiGetFleetspeakPendingMessageCountResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiFleetspeakAddress(
    rdf: client.ApiFleetspeakAddress,
) -> client_pb2.ApiFleetspeakAddress:
  return rdf.AsPrimitiveProto()


def ToRDFApiFleetspeakAddress(
    proto: client_pb2.ApiFleetspeakAddress,
) -> client.ApiFleetspeakAddress:
  return client.ApiFleetspeakAddress.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoEntry(
    rdf: client.ApiFleetspeakAnnotations.Entry,
) -> client_pb2.ApiFleetspeakAnnotations.Entry:
  return rdf.AsPrimitiveProto()


def ToRDFEntry(
    proto: client_pb2.ApiFleetspeakAnnotations.Entry,
) -> client.ApiFleetspeakAnnotations.Entry:
  return client.ApiFleetspeakAnnotations.Entry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiFleetspeakAnnotations(
    rdf: client.ApiFleetspeakAnnotations,
) -> client_pb2.ApiFleetspeakAnnotations:
  return rdf.AsPrimitiveProto()


def ToRDFApiFleetspeakAnnotations(
    proto: client_pb2.ApiFleetspeakAnnotations,
) -> client.ApiFleetspeakAnnotations:
  return client.ApiFleetspeakAnnotations.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoTag(
    rdf: client.ApiFleetspeakValidationInfo.Tag,
) -> client_pb2.ApiFleetspeakValidationInfo.Tag:
  return rdf.AsPrimitiveProto()


def ToRDFTag(
    proto: client_pb2.ApiFleetspeakValidationInfo.Tag,
) -> client.ApiFleetspeakValidationInfo.Tag:
  return client.ApiFleetspeakValidationInfo.Tag.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiFleetspeakValidationInfo(
    rdf: client.ApiFleetspeakValidationInfo,
) -> client_pb2.ApiFleetspeakValidationInfo:
  return rdf.AsPrimitiveProto()


def ToRDFApiFleetspeakValidationInfo(
    proto: client_pb2.ApiFleetspeakValidationInfo,
) -> client.ApiFleetspeakValidationInfo:
  return client.ApiFleetspeakValidationInfo.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiFleetspeakMessageResult(
    rdf: client.ApiFleetspeakMessageResult,
) -> client_pb2.ApiFleetspeakMessageResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiFleetspeakMessageResult(
    proto: client_pb2.ApiFleetspeakMessageResult,
) -> client.ApiFleetspeakMessageResult:
  return client.ApiFleetspeakMessageResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiFleetspeakMessage(
    rdf: client.ApiFleetspeakMessage,
) -> client_pb2.ApiFleetspeakMessage:
  return rdf.AsPrimitiveProto()


def ToRDFApiFleetspeakMessage(
    proto: client_pb2.ApiFleetspeakMessage,
) -> client.ApiFleetspeakMessage:
  return client.ApiFleetspeakMessage.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFleetspeakPendingMessagesArgs(
    rdf: client.ApiGetFleetspeakPendingMessagesArgs,
) -> client_pb2.ApiGetFleetspeakPendingMessagesArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFleetspeakPendingMessagesArgs(
    proto: client_pb2.ApiGetFleetspeakPendingMessagesArgs,
) -> client.ApiGetFleetspeakPendingMessagesArgs:
  return client.ApiGetFleetspeakPendingMessagesArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetFleetspeakPendingMessagesResult(
    rdf: client.ApiGetFleetspeakPendingMessagesResult,
) -> client_pb2.ApiGetFleetspeakPendingMessagesResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetFleetspeakPendingMessagesResult(
    proto: client_pb2.ApiGetFleetspeakPendingMessagesResult,
) -> client.ApiGetFleetspeakPendingMessagesResult:
  return client.ApiGetFleetspeakPendingMessagesResult.FromSerializedBytes(
      proto.SerializeToString()
  )
