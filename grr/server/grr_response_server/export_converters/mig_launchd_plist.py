#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import launchd_plist


def ToProtoExportedLaunchdPlist(
    rdf: launchd_plist.ExportedLaunchdPlist,
) -> export_pb2.ExportedLaunchdPlist:
  return rdf.AsPrimitiveProto()


def ToRDFExportedLaunchdPlist(
    proto: export_pb2.ExportedLaunchdPlist,
) -> launchd_plist.ExportedLaunchdPlist:
  return launchd_plist.ExportedLaunchdPlist.FromSerializedBytes(
      proto.SerializeToString()
  )
