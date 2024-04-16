#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import process


def ToProtoExportedProcess(
    rdf: process.ExportedProcess,
) -> export_pb2.ExportedProcess:
  return rdf.AsPrimitiveProto()


def ToRDFExportedProcess(
    proto: export_pb2.ExportedProcess,
) -> process.ExportedProcess:
  return process.ExportedProcess.FromSerializedBytes(proto.SerializeToString())


def ToProtoExportedOpenFile(
    rdf: process.ExportedOpenFile,
) -> export_pb2.ExportedOpenFile:
  return rdf.AsPrimitiveProto()


def ToRDFExportedOpenFile(
    proto: export_pb2.ExportedOpenFile,
) -> process.ExportedOpenFile:
  return process.ExportedOpenFile.FromSerializedBytes(proto.SerializeToString())
