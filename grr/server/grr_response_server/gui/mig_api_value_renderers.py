#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import reflection_pb2
from grr_response_server.gui import api_value_renderers


def ToProtoApiRDFAllowedEnumValueDescriptor(
    rdf: api_value_renderers.ApiRDFAllowedEnumValueDescriptor,
) -> reflection_pb2.ApiRDFAllowedEnumValueDescriptor:
  return rdf.AsPrimitiveProto()


def ToRDFApiRDFAllowedEnumValueDescriptor(
    proto: reflection_pb2.ApiRDFAllowedEnumValueDescriptor,
) -> api_value_renderers.ApiRDFAllowedEnumValueDescriptor:
  return (
      api_value_renderers.ApiRDFAllowedEnumValueDescriptor.FromSerializedBytes(
          proto.SerializeToString()
      )
  )


def ToProtoApiRDFValueFieldDescriptor(
    rdf: api_value_renderers.ApiRDFValueFieldDescriptor,
) -> reflection_pb2.ApiRDFValueFieldDescriptor:
  return rdf.AsPrimitiveProto()


def ToRDFApiRDFValueFieldDescriptor(
    proto: reflection_pb2.ApiRDFValueFieldDescriptor,
) -> api_value_renderers.ApiRDFValueFieldDescriptor:
  return api_value_renderers.ApiRDFValueFieldDescriptor.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiRDFValueDescriptor(
    rdf: api_value_renderers.ApiRDFValueDescriptor,
) -> reflection_pb2.ApiRDFValueDescriptor:
  return rdf.AsPrimitiveProto()


def ToRDFApiRDFValueDescriptor(
    proto: reflection_pb2.ApiRDFValueDescriptor,
) -> api_value_renderers.ApiRDFValueDescriptor:
  return api_value_renderers.ApiRDFValueDescriptor.FromSerializedBytes(
      proto.SerializeToString()
  )
