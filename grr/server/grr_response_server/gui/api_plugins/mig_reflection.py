#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto.api import reflection_pb2
from grr_response_server.gui.api_plugins import reflection


def ToProtoApiGetRDFValueDescriptorArgs(
    rdf: reflection.ApiGetRDFValueDescriptorArgs,
) -> reflection_pb2.ApiGetRDFValueDescriptorArgs:
  return rdf.AsPrimitiveProto()


def ToRDFApiGetRDFValueDescriptorArgs(
    proto: reflection_pb2.ApiGetRDFValueDescriptorArgs,
) -> reflection.ApiGetRDFValueDescriptorArgs:
  return reflection.ApiGetRDFValueDescriptorArgs.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiListRDFValueDescriptorsResult(
    rdf: reflection.ApiListRDFValueDescriptorsResult,
) -> reflection_pb2.ApiListRDFValueDescriptorsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListRDFValueDescriptorsResult(
    proto: reflection_pb2.ApiListRDFValueDescriptorsResult,
) -> reflection.ApiListRDFValueDescriptorsResult:
  return reflection.ApiListRDFValueDescriptorsResult.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoApiMethod(rdf: reflection.ApiMethod) -> reflection_pb2.ApiMethod:
  return rdf.AsPrimitiveProto()


def ToRDFApiMethod(proto: reflection_pb2.ApiMethod) -> reflection.ApiMethod:
  return reflection.ApiMethod.FromSerializedBytes(proto.SerializeToString())


def ToProtoApiListApiMethodsResult(
    rdf: reflection.ApiListApiMethodsResult,
) -> reflection_pb2.ApiListApiMethodsResult:
  return rdf.AsPrimitiveProto()


def ToRDFApiListApiMethodsResult(
    proto: reflection_pb2.ApiListApiMethodsResult,
) -> reflection.ApiListApiMethodsResult:
  return reflection.ApiListApiMethodsResult.FromSerializedBytes(
      proto.SerializeToString()
  )
