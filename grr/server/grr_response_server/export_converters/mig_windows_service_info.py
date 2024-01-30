#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""
from grr_response_proto import export_pb2
from grr_response_server.export_converters import windows_service_info


def ToProtoExportedWindowsServiceInformation(
    rdf: windows_service_info.ExportedWindowsServiceInformation,
) -> export_pb2.ExportedWindowsServiceInformation:
  return rdf.AsPrimitiveProto()


def ToRDFExportedWindowsServiceInformation(
    proto: export_pb2.ExportedWindowsServiceInformation,
) -> windows_service_info.ExportedWindowsServiceInformation:
  return windows_service_info.ExportedWindowsServiceInformation.FromSerializedBytes(
      proto.SerializeToString()
  )
