#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import rdf_dict


def ToProtoExportedDictItem(
    rdf: rdf_dict.ExportedDictItem,
) -> export_pb2.ExportedDictItem:
  return rdf.AsPrimitiveProto()


def ToRDFExportedDictItem(
    proto: export_pb2.ExportedDictItem,
) -> rdf_dict.ExportedDictItem:
  return rdf_dict.ExportedDictItem.FromSerializedBytes(
      proto.SerializeToString()
  )
