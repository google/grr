#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import metadata_pb2
from grr_response_server.gui.api_plugins import metadata


def ToProtoApiGetGrrVersionResult(
    rdf: metadata.ApiGetGrrVersionResult,
) -> metadata_pb2.ApiGetGrrVersionResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetGrrVersionResult(
    proto: metadata_pb2.ApiGetGrrVersionResult,
) -> metadata.ApiGetGrrVersionResult:
  return metadata.ApiGetGrrVersionResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiGetOpenApiDescriptionResult(
    rdf: metadata.ApiGetOpenApiDescriptionResult,
) -> metadata_pb2.ApiGetOpenApiDescriptionResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetOpenApiDescriptionResult(
    proto: metadata_pb2.ApiGetOpenApiDescriptionResult,
) -> metadata.ApiGetOpenApiDescriptionResult:
  return metadata.ApiGetOpenApiDescriptionResult.FromSerializedBytes(
      proto.SerializeToString()
  )
