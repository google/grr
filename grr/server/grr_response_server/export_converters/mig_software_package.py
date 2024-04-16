#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import software_package


def ToProtoExportedSoftwarePackage(
    rdf: software_package.ExportedSoftwarePackage,
) -> export_pb2.ExportedSoftwarePackage:
  return rdf.AsPrimitiveProto()


def ToRDFExportedSoftwarePackage(
    proto: export_pb2.ExportedSoftwarePackage,
) -> software_package.ExportedSoftwarePackage:
  return software_package.ExportedSoftwarePackage.FromSerializedBytes(
      proto.SerializeToString()
  )
