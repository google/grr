#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import config_pb2
from grr_response_server.gui.api_plugins import config


def ToProtoApiConfigOption(
    rdf: config.ApiConfigOption,
) -> config_pb2.ApiConfigOption:
  return rdf.AsPrimitiveProto()


def ToRDFApiConfigOption(
    proto: config_pb2.ApiConfigOption,
) -> config.ApiConfigOption:
  return config.ApiConfigOption.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiConfigSection(
    rdf: config.ApiConfigSection,
) -> config_pb2.ApiConfigSection:
  return rdf.AsPrimitiveProto()


def ToRDFApiConfigSection(
    proto: config_pb2.ApiConfigSection,
) -> config.ApiConfigSection:
  return config.ApiConfigSection.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiGetConfigResult(
    rdf: config.ApiGetConfigResult,
) -> config_pb2.ApiGetConfigResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetConfigResult(
    proto: config_pb2.ApiGetConfigResult,
) -> config.ApiGetConfigResult:
  return config.ApiGetConfigResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetConfigOptionArgs(
    rdf: config.ApiGetConfigOptionArgs,
) -> config_pb2.ApiGetConfigOptionArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetConfigOptionArgs(
    proto: config_pb2.ApiGetConfigOptionArgs,
) -> config.ApiGetConfigOptionArgs:
  return config.ApiGetConfigOptionArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGrrBinary(rdf: config.ApiGrrBinary) -> config_pb2.ApiGrrBinary:
  return rdf.AsPrimitiveProto()


def ToRDFApiGrrBinary(proto: config_pb2.ApiGrrBinary) -> config.ApiGrrBinary:
  return config.ApiGrrBinary.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListGrrBinariesResult(
    rdf: config.ApiListGrrBinariesResult,
) -> config_pb2.ApiListGrrBinariesResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListGrrBinariesResult(
    proto: config_pb2.ApiListGrrBinariesResult,
) -> config.ApiListGrrBinariesResult:
  return config.ApiListGrrBinariesResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetGrrBinaryArgs(
    rdf: config.ApiGetGrrBinaryArgs,
) -> config_pb2.ApiGetGrrBinaryArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetGrrBinaryArgs(
    proto: config_pb2.ApiGetGrrBinaryArgs,
) -> config.ApiGetGrrBinaryArgs:
  return config.ApiGetGrrBinaryArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetGrrBinaryBlobArgs(
    rdf: config.ApiGetGrrBinaryBlobArgs,
) -> config_pb2.ApiGetGrrBinaryBlobArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetGrrBinaryBlobArgs(
    proto: config_pb2.ApiGetGrrBinaryBlobArgs,
) -> config.ApiGetGrrBinaryBlobArgs:
  return config.ApiGetGrrBinaryBlobArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiUiConfig(rdf: config.ApiUiConfig) -> config_pb2.ApiUiConfig:
  return rdf.AsPrimitiveProto()


def ToRDFApiUiConfig(proto: config_pb2.ApiUiConfig) -> config.ApiUiConfig:
  return config.ApiUiConfig.FromSerializedBytes(proto.SerializeToString())
