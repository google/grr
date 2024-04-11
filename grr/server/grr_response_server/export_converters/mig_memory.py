#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import memory


def ToProtoExportedYaraProcessScanMatch(
    rdf: memory.ExportedYaraProcessScanMatch,
) -> export_pb2.ExportedYaraProcessScanMatch:
  return rdf.AsPrimitiveProto()


def ToRDFExportedYaraProcessScanMatch(
    proto: export_pb2.ExportedYaraProcessScanMatch,
) -> memory.ExportedYaraProcessScanMatch:
  return memory.ExportedYaraProcessScanMatch.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExportedProcessMemoryError(
    rdf: memory.ExportedProcessMemoryError,
) -> export_pb2.ExportedProcessMemoryError:
  return rdf.AsPrimitiveProto()


def ToRDFExportedProcessMemoryError(
    proto: export_pb2.ExportedProcessMemoryError,
) -> memory.ExportedProcessMemoryError:
  return memory.ExportedProcessMemoryError.FromSerializedBytes(
      proto.SerializeToString()
  )
