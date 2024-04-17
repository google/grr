#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import base


def ToProtoExportedMetadata(
    rdf: base.ExportedMetadata,
) -> export_pb2.ExportedMetadata:
  return rdf.AsPrimitiveProto()


def ToRDFExportedMetadata(
    proto: export_pb2.ExportedMetadata,
) -> base.ExportedMetadata:
  return base.ExportedMetadata.FromSerializedBytes(proto.SerializeToString())


def ToProtoExportOptions(rdf: base.ExportOptions) -> export_pb2.ExportOptions:
  return rdf.AsPrimitiveProto()


def ToRDFExportOptions(proto: export_pb2.ExportOptions) -> base.ExportOptions:
  return base.ExportOptions.FromSerializedBytes(proto.SerializeToString())
