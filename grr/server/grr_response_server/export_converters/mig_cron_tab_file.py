#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import cron_tab_file


def ToProtoExportedCronTabEntry(
    rdf: cron_tab_file.ExportedCronTabEntry,
) -> export_pb2.ExportedCronTabEntry:
  return rdf.AsPrimitiveProto()


def ToRDFExportedCronTabEntry(
    proto: export_pb2.ExportedCronTabEntry,
) -> cron_tab_file.ExportedCronTabEntry:
  return cron_tab_file.ExportedCronTabEntry.FromSerializedBytes(
      proto.SerializeToString()
  )
