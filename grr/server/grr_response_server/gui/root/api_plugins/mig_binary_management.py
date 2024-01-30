#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto.api.root import binary_management_pb2
from grr_response_server.gui.root.api_plugins import binary_management


def ToProtoApiUploadGrrBinaryArgs(
    rdf: binary_management.ApiUploadGrrBinaryArgs,
) -> binary_management_pb2.ApiUploadGrrBinaryArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiUploadGrrBinaryArgs(
    proto: binary_management_pb2.ApiUploadGrrBinaryArgs,
) -> binary_management.ApiUploadGrrBinaryArgs:
  return binary_management.ApiUploadGrrBinaryArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiDeleteGrrBinaryArgs(
    rdf: binary_management.ApiDeleteGrrBinaryArgs,
) -> binary_management_pb2.ApiDeleteGrrBinaryArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiDeleteGrrBinaryArgs(
    proto: binary_management_pb2.ApiDeleteGrrBinaryArgs,
) -> binary_management.ApiDeleteGrrBinaryArgs:
  return binary_management.ApiDeleteGrrBinaryArgs.FromSerializedBytes(
      proto.SerializeToString()
  )
