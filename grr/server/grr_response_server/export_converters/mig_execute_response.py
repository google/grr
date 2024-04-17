#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import execute_response


def ToProtoExportedExecuteResponse(
    rdf: execute_response.ExportedExecuteResponse,
) -> export_pb2.ExportedExecuteResponse:
  return rdf.AsPrimitiveProto()


def ToRDFExportedExecuteResponse(
    proto: export_pb2.ExportedExecuteResponse,
) -> execute_response.ExportedExecuteResponse:
  return execute_response.ExportedExecuteResponse.FromSerializedBytes(
      proto.SerializeToString()
  )
