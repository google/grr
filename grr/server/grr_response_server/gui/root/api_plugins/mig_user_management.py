#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto.api.root import user_management_pb2
from grr_response_server.gui.root.api_plugins import user_management


def ToProtoApiCreateGrrUserArgs(
    rdf: user_management.ApiCreateGrrUserArgs,
) -> user_management_pb2.ApiCreateGrrUserArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiCreateGrrUserArgs(
    proto: user_management_pb2.ApiCreateGrrUserArgs,
) -> user_management.ApiCreateGrrUserArgs:
  return user_management.ApiCreateGrrUserArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiDeleteGrrUserArgs(
    rdf: user_management.ApiDeleteGrrUserArgs,
) -> user_management_pb2.ApiDeleteGrrUserArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiDeleteGrrUserArgs(
    proto: user_management_pb2.ApiDeleteGrrUserArgs,
) -> user_management.ApiDeleteGrrUserArgs:
  return user_management.ApiDeleteGrrUserArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiModifyGrrUserArgs(
    rdf: user_management.ApiModifyGrrUserArgs,
) -> user_management_pb2.ApiModifyGrrUserArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiModifyGrrUserArgs(
    proto: user_management_pb2.ApiModifyGrrUserArgs,
) -> user_management.ApiModifyGrrUserArgs:
  return user_management.ApiModifyGrrUserArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListGrrUsersArgs(
    rdf: user_management.ApiListGrrUsersArgs,
) -> user_management_pb2.ApiListGrrUsersArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiListGrrUsersArgs(
    proto: user_management_pb2.ApiListGrrUsersArgs,
) -> user_management.ApiListGrrUsersArgs:
  return user_management.ApiListGrrUsersArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListGrrUsersResult(
    rdf: user_management.ApiListGrrUsersResult,
) -> user_management_pb2.ApiListGrrUsersResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListGrrUsersResult(
    proto: user_management_pb2.ApiListGrrUsersResult,
) -> user_management.ApiListGrrUsersResult:
  return user_management.ApiListGrrUsersResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetGrrUserArgs(
    rdf: user_management.ApiGetGrrUserArgs,
) -> user_management_pb2.ApiGetGrrUserArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetGrrUserArgs(
    proto: user_management_pb2.ApiGetGrrUserArgs,
) -> user_management.ApiGetGrrUserArgs:
  return user_management.ApiGetGrrUserArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
