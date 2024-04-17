#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import file


def ToProtoExportedFile(rdf: file.ExportedFile) -> export_pb2.ExportedFile:
  return rdf.AsPrimitiveProto()


def ToRDFExportedFile(proto: export_pb2.ExportedFile) -> file.ExportedFile:
  return file.ExportedFile.FromSerializedBytes(proto.SerializeToString())


def ToProtoExportedRegistryKey(
    rdf: file.ExportedRegistryKey,
) -> export_pb2.ExportedRegistryKey:
  return rdf.AsPrimitiveProto()


def ToRDFExportedRegistryKey(
    proto: export_pb2.ExportedRegistryKey,
) -> file.ExportedRegistryKey:
  return file.ExportedRegistryKey.FromSerializedBytes(proto.SerializeToString())


def ToProtoExportedArtifactFilesDownloaderResult(
    rdf: file.ExportedArtifactFilesDownloaderResult,
) -> export_pb2.ExportedArtifactFilesDownloaderResult:
  return rdf.AsPrimitiveProto()


def ToRDFExportedArtifactFilesDownloaderResult(
    proto: export_pb2.ExportedArtifactFilesDownloaderResult,
) -> file.ExportedArtifactFilesDownloaderResult:
  return file.ExportedArtifactFilesDownloaderResult.FromSerializedBytes(
      proto.SerializeToString()
  )
