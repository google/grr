#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import rdf_primitives


def ToProtoExportedBytes(
    rdf: rdf_primitives.ExportedBytes,
) -> export_pb2.ExportedBytes:
  return rdf.AsPrimitiveProto()


def ToRDFExportedBytes(
    proto: export_pb2.ExportedBytes,
) -> rdf_primitives.ExportedBytes:
  return rdf_primitives.ExportedBytes.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExportedString(
    rdf: rdf_primitives.ExportedString,
) -> export_pb2.ExportedString:
  return rdf.AsPrimitiveProto()


def ToRDFExportedString(
    proto: export_pb2.ExportedString,
) -> rdf_primitives.ExportedString:
  return rdf_primitives.ExportedString.FromSerializedBytes(
      proto.SerializeToString()
  )
