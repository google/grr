#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import buffer_reference


def ToProtoExportedMatch(
    rdf: buffer_reference.ExportedMatch,
) -> export_pb2.ExportedMatch:
  return rdf.AsPrimitiveProto()


def ToRDFExportedMatch(
    proto: export_pb2.ExportedMatch,
) -> buffer_reference.ExportedMatch:
  return buffer_reference.ExportedMatch.FromSerializedBytes(
      proto.SerializeToString()
  )
