#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import user_pb2
from grr_response_proto.api import user_pb2 as user_pb20
from grr_response_server.gui.api_plugins import user


def ToProtoGUISettings(rdf: user.GUISettings) -> user_pb2.GUISettings:
  return rdf.AsPrimitiveProto()


def ToRDFGUISettings(proto: user_pb2.GUISettings) -> user.GUISettings:
  return user.GUISettings.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiNotificationClientReference(
    rdf: user.ApiNotificationClientReference,
) -> user_pb20.ApiNotificationClientReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiNotificationClientReference(
    proto: user_pb20.ApiNotificationClientReference,
) -> user.ApiNotificationClientReference:
  return user.ApiNotificationClientReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiNotificationHuntReference(
    rdf: user.ApiNotificationHuntReference,
) -> user_pb20.ApiNotificationHuntReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiNotificationHuntReference(
    proto: user_pb20.ApiNotificationHuntReference,
) -> user.ApiNotificationHuntReference:
  return user.ApiNotificationHuntReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiNotificationCronReference(
    rdf: user.ApiNotificationCronReference,
) -> user_pb20.ApiNotificationCronReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiNotificationCronReference(
    proto: user_pb20.ApiNotificationCronReference,
) -> user.ApiNotificationCronReference:
  return user.ApiNotificationCronReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiNotificationFlowReference(
    rdf: user.ApiNotificationFlowReference,
) -> user_pb20.ApiNotificationFlowReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiNotificationFlowReference(
    proto: user_pb20.ApiNotificationFlowReference,
) -> user.ApiNotificationFlowReference:
  return user.ApiNotificationFlowReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiNotificationVfsReference(
    rdf: user.ApiNotificationVfsReference,
) -> user_pb20.ApiNotificationVfsReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiNotificationVfsReference(
    proto: user_pb20.ApiNotificationVfsReference,
) -> user.ApiNotificationVfsReference:
  return user.ApiNotificationVfsReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiNotificationClientApprovalReference(
    rdf: user.ApiNotificationClientApprovalReference,
) -> user_pb20.ApiNotificationClientApprovalReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiNotificationClientApprovalReference(
    proto: user_pb20.ApiNotificationClientApprovalReference,
) -> user.ApiNotificationClientApprovalReference:
  return user.ApiNotificationClientApprovalReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiNotificationHuntApprovalReference(
    rdf: user.ApiNotificationHuntApprovalReference,
) -> user_pb20.ApiNotificationHuntApprovalReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiNotificationHuntApprovalReference(
    proto: user_pb20.ApiNotificationHuntApprovalReference,
) -> user.ApiNotificationHuntApprovalReference:
  return user.ApiNotificationHuntApprovalReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiNotificationCronJobApprovalReference(
    rdf: user.ApiNotificationCronJobApprovalReference,
) -> user_pb20.ApiNotificationCronJobApprovalReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiNotificationCronJobApprovalReference(
    proto: user_pb20.ApiNotificationCronJobApprovalReference,
) -> user.ApiNotificationCronJobApprovalReference:
  return user.ApiNotificationCronJobApprovalReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiNotificationUnknownReference(
    rdf: user.ApiNotificationUnknownReference,
) -> user_pb20.ApiNotificationUnknownReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiNotificationUnknownReference(
    proto: user_pb20.ApiNotificationUnknownReference,
) -> user.ApiNotificationUnknownReference:
  return user.ApiNotificationUnknownReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiNotificationReference(
    rdf: user.ApiNotificationReference,
) -> user_pb20.ApiNotificationReference:
  return rdf.AsPrimitiveProto()


def ToRDFApiNotificationReference(
    proto: user_pb20.ApiNotificationReference,
) -> user.ApiNotificationReference:
  return user.ApiNotificationReference.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiNotification(
    rdf: user.ApiNotification,
) -> user_pb20.ApiNotification:
  return rdf.AsPrimitiveProto()


def ToRDFApiNotification(
    proto: user_pb20.ApiNotification,
) -> user.ApiNotification:
  return user.ApiNotification.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGrrUserInterfaceTraits(
    rdf: user.ApiGrrUserInterfaceTraits,
) -> user_pb20.ApiGrrUserInterfaceTraits:
  return rdf.AsPrimitiveProto()


def ToRDFApiGrrUserInterfaceTraits(
    proto: user_pb20.ApiGrrUserInterfaceTraits,
) -> user.ApiGrrUserInterfaceTraits:
  return user.ApiGrrUserInterfaceTraits.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGrrUser(rdf: user.ApiGrrUser) -> user_pb20.ApiGrrUser:
  return rdf.AsPrimitiveProto()


def ToRDFApiGrrUser(proto: user_pb20.ApiGrrUser) -> user.ApiGrrUser:
  return user.ApiGrrUser.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiClientApproval(
    rdf: user.ApiClientApproval,
) -> user_pb20.ApiClientApproval:
  return rdf.AsPrimitiveProto()


def ToRDFApiClientApproval(
    proto: user_pb20.ApiClientApproval,
) -> user.ApiClientApproval:
  return user.ApiClientApproval.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiHuntApproval(
    rdf: user.ApiHuntApproval,
) -> user_pb20.ApiHuntApproval:
  return rdf.AsPrimitiveProto()


def ToRDFApiHuntApproval(
    proto: user_pb20.ApiHuntApproval,
) -> user.ApiHuntApproval:
  return user.ApiHuntApproval.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiCronJobApproval(
    rdf: user.ApiCronJobApproval,
) -> user_pb20.ApiCronJobApproval:
  return rdf.AsPrimitiveProto()


def ToRDFApiCronJobApproval(
    proto: user_pb20.ApiCronJobApproval,
) -> user.ApiCronJobApproval:
  return user.ApiCronJobApproval.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiCreateClientApprovalArgs(
    rdf: user.ApiCreateClientApprovalArgs,
) -> user_pb20.ApiCreateClientApprovalArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiCreateClientApprovalArgs(
    proto: user_pb20.ApiCreateClientApprovalArgs,
) -> user.ApiCreateClientApprovalArgs:
  return user.ApiCreateClientApprovalArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetClientApprovalArgs(
    rdf: user.ApiGetClientApprovalArgs,
) -> user_pb20.ApiGetClientApprovalArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetClientApprovalArgs(
    proto: user_pb20.ApiGetClientApprovalArgs,
) -> user.ApiGetClientApprovalArgs:
  return user.ApiGetClientApprovalArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGrantClientApprovalArgs(
    rdf: user.ApiGrantClientApprovalArgs,
) -> user_pb20.ApiGrantClientApprovalArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGrantClientApprovalArgs(
    proto: user_pb20.ApiGrantClientApprovalArgs,
) -> user.ApiGrantClientApprovalArgs:
  return user.ApiGrantClientApprovalArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListClientApprovalsArgs(
    rdf: user.ApiListClientApprovalsArgs,
) -> user_pb20.ApiListClientApprovalsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListClientApprovalsArgs(
    proto: user_pb20.ApiListClientApprovalsArgs,
) -> user.ApiListClientApprovalsArgs:
  return user.ApiListClientApprovalsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListClientApprovalsResult(
    rdf: user.ApiListClientApprovalsResult,
) -> user_pb20.ApiListClientApprovalsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListClientApprovalsResult(
    proto: user_pb20.ApiListClientApprovalsResult,
) -> user.ApiListClientApprovalsResult:
  return user.ApiListClientApprovalsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiCreateHuntApprovalArgs(
    rdf: user.ApiCreateHuntApprovalArgs,
) -> user_pb20.ApiCreateHuntApprovalArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiCreateHuntApprovalArgs(
    proto: user_pb20.ApiCreateHuntApprovalArgs,
) -> user.ApiCreateHuntApprovalArgs:
  return user.ApiCreateHuntApprovalArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetHuntApprovalArgs(
    rdf: user.ApiGetHuntApprovalArgs,
) -> user_pb20.ApiGetHuntApprovalArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetHuntApprovalArgs(
    proto: user_pb20.ApiGetHuntApprovalArgs,
) -> user.ApiGetHuntApprovalArgs:
  return user.ApiGetHuntApprovalArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGrantHuntApprovalArgs(
    rdf: user.ApiGrantHuntApprovalArgs,
) -> user_pb20.ApiGrantHuntApprovalArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGrantHuntApprovalArgs(
    proto: user_pb20.ApiGrantHuntApprovalArgs,
) -> user.ApiGrantHuntApprovalArgs:
  return user.ApiGrantHuntApprovalArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntApprovalsArgs(
    rdf: user.ApiListHuntApprovalsArgs,
) -> user_pb20.ApiListHuntApprovalsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntApprovalsArgs(
    proto: user_pb20.ApiListHuntApprovalsArgs,
) -> user.ApiListHuntApprovalsArgs:
  return user.ApiListHuntApprovalsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListHuntApprovalsResult(
    rdf: user.ApiListHuntApprovalsResult,
) -> user_pb20.ApiListHuntApprovalsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListHuntApprovalsResult(
    proto: user_pb20.ApiListHuntApprovalsResult,
) -> user.ApiListHuntApprovalsResult:
  return user.ApiListHuntApprovalsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiCreateCronJobApprovalArgs(
    rdf: user.ApiCreateCronJobApprovalArgs,
) -> user_pb20.ApiCreateCronJobApprovalArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiCreateCronJobApprovalArgs(
    proto: user_pb20.ApiCreateCronJobApprovalArgs,
) -> user.ApiCreateCronJobApprovalArgs:
  return user.ApiCreateCronJobApprovalArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetCronJobApprovalArgs(
    rdf: user.ApiGetCronJobApprovalArgs,
) -> user_pb20.ApiGetCronJobApprovalArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetCronJobApprovalArgs(
    proto: user_pb20.ApiGetCronJobApprovalArgs,
) -> user.ApiGetCronJobApprovalArgs:
  return user.ApiGetCronJobApprovalArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGrantCronJobApprovalArgs(
    rdf: user.ApiGrantCronJobApprovalArgs,
) -> user_pb20.ApiGrantCronJobApprovalArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGrantCronJobApprovalArgs(
    proto: user_pb20.ApiGrantCronJobApprovalArgs,
) -> user.ApiGrantCronJobApprovalArgs:
  return user.ApiGrantCronJobApprovalArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListCronJobApprovalsArgs(
    rdf: user.ApiListCronJobApprovalsArgs,
) -> user_pb20.ApiListCronJobApprovalsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListCronJobApprovalsArgs(
    proto: user_pb20.ApiListCronJobApprovalsArgs,
) -> user.ApiListCronJobApprovalsArgs:
  return user.ApiListCronJobApprovalsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListCronJobApprovalsResult(
    rdf: user.ApiListCronJobApprovalsResult,
) -> user_pb20.ApiListCronJobApprovalsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListCronJobApprovalsResult(
    proto: user_pb20.ApiListCronJobApprovalsResult,
) -> user.ApiListCronJobApprovalsResult:
  return user.ApiListCronJobApprovalsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetPendingUserNotificationsCountResult(
    rdf: user.ApiGetPendingUserNotificationsCountResult,
) -> user_pb20.ApiGetPendingUserNotificationsCountResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetPendingUserNotificationsCountResult(
    proto: user_pb20.ApiGetPendingUserNotificationsCountResult,
) -> user.ApiGetPendingUserNotificationsCountResult:
  return user.ApiGetPendingUserNotificationsCountResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListPendingUserNotificationsArgs(
    rdf: user.ApiListPendingUserNotificationsArgs,
) -> user_pb20.ApiListPendingUserNotificationsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListPendingUserNotificationsArgs(
    proto: user_pb20.ApiListPendingUserNotificationsArgs,
) -> user.ApiListPendingUserNotificationsArgs:
  return user.ApiListPendingUserNotificationsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListPendingUserNotificationsResult(
    rdf: user.ApiListPendingUserNotificationsResult,
) -> user_pb20.ApiListPendingUserNotificationsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListPendingUserNotificationsResult(
    proto: user_pb20.ApiListPendingUserNotificationsResult,
) -> user.ApiListPendingUserNotificationsResult:
  return user.ApiListPendingUserNotificationsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiDeletePendingUserNotificationArgs(
    rdf: user.ApiDeletePendingUserNotificationArgs,
) -> user_pb20.ApiDeletePendingUserNotificationArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiDeletePendingUserNotificationArgs(
    proto: user_pb20.ApiDeletePendingUserNotificationArgs,
) -> user.ApiDeletePendingUserNotificationArgs:
  return user.ApiDeletePendingUserNotificationArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListAndResetUserNotificationsArgs(
    rdf: user.ApiListAndResetUserNotificationsArgs,
) -> user_pb20.ApiListAndResetUserNotificationsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListAndResetUserNotificationsArgs(
    proto: user_pb20.ApiListAndResetUserNotificationsArgs,
) -> user.ApiListAndResetUserNotificationsArgs:
  return user.ApiListAndResetUserNotificationsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListAndResetUserNotificationsResult(
    rdf: user.ApiListAndResetUserNotificationsResult,
) -> user_pb20.ApiListAndResetUserNotificationsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListAndResetUserNotificationsResult(
    proto: user_pb20.ApiListAndResetUserNotificationsResult,
) -> user.ApiListAndResetUserNotificationsResult:
  return user.ApiListAndResetUserNotificationsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListApproverSuggestionsArgs(
    rdf: user.ApiListApproverSuggestionsArgs,
) -> user_pb20.ApiListApproverSuggestionsArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListApproverSuggestionsArgs(
    proto: user_pb20.ApiListApproverSuggestionsArgs,
) -> user.ApiListApproverSuggestionsArgs:
  return user.ApiListApproverSuggestionsArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApproverSuggestion(
    rdf: user.ApproverSuggestion,
) -> user_pb20.ApiListApproverSuggestionsResult.ApproverSuggestion:
  return rdf.AsPrimitiveProto()


def ToRDFApproverSuggestion(
    proto: user_pb20.ApiListApproverSuggestionsResult.ApproverSuggestion,
) -> user.ApproverSuggestion:
  return user.ApproverSuggestion.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListApproverSuggestionsResult(
    rdf: user.ApiListApproverSuggestionsResult,
) -> user_pb20.ApiListApproverSuggestionsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListApproverSuggestionsResult(
    proto: user_pb20.ApiListApproverSuggestionsResult,
) -> user.ApiListApproverSuggestionsResult:
  return user.ApiListApproverSuggestionsResult.FromSerializedBytes(
      proto.SerializeToString()
  )
