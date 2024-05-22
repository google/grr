#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import api_utils_pb2
from grr_response_server.gui import api_call_handler_utils


def ToProtoApiDataObjectKeyValuePair(
    rdf: api_call_handler_utils.ApiDataObjectKeyValuePair,
) -> api_utils_pb2.ApiDataObjectKeyValuePair:
  return rdf.AsPrimitiveProto()


def ToRDFApiDataObjectKeyValuePair(
    proto: api_utils_pb2.ApiDataObjectKeyValuePair,
) -> api_call_handler_utils.ApiDataObjectKeyValuePair:
  return api_call_handler_utils.ApiDataObjectKeyValuePair.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiDataObject(
    rdf: api_call_handler_utils.ApiDataObject,
) -> api_utils_pb2.ApiDataObject:
  return rdf.AsPrimitiveProto()


def ToRDFApiDataObject(
    proto: api_utils_pb2.ApiDataObject,
) -> api_call_handler_utils.ApiDataObject:
  return api_call_handler_utils.ApiDataObject.FromSerializedBytes(
      proto.SerializeToString()
  )
