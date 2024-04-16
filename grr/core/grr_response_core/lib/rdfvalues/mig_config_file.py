#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import config_file as rdf_config_file
from grr_response_proto import config_file_pb2


def ToProtoLogTarget(
    rdf: rdf_config_file.LogTarget,
) -> config_file_pb2.LogTarget:
  return rdf.AsPrimitiveProto()


def ToRDFLogTarget(
    proto: config_file_pb2.LogTarget,
) -> rdf_config_file.LogTarget:
  return rdf_config_file.LogTarget.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoLogConfig(
    rdf: rdf_config_file.LogConfig,
) -> config_file_pb2.LogConfig:
  return rdf.AsPrimitiveProto()


def ToRDFLogConfig(
    proto: config_file_pb2.LogConfig,
) -> rdf_config_file.LogConfig:
  return rdf_config_file.LogConfig.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoNfsClient(
    rdf: rdf_config_file.NfsClient,
) -> config_file_pb2.NfsClient:
  return rdf.AsPrimitiveProto()


def ToRDFNfsClient(
    proto: config_file_pb2.NfsClient,
) -> rdf_config_file.NfsClient:
  return rdf_config_file.NfsClient.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoNfsExport(
    rdf: rdf_config_file.NfsExport,
) -> config_file_pb2.NfsExport:
  return rdf.AsPrimitiveProto()


def ToRDFNfsExport(
    proto: config_file_pb2.NfsExport,
) -> rdf_config_file.NfsExport:
  return rdf_config_file.NfsExport.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoNtpConfig(
    rdf: rdf_config_file.NtpConfig,
) -> config_file_pb2.NtpConfig:
  return rdf.AsPrimitiveProto()


def ToRDFNtpConfig(
    proto: config_file_pb2.NtpConfig,
) -> rdf_config_file.NtpConfig:
  return rdf_config_file.NtpConfig.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoPamConfigEntry(
    rdf: rdf_config_file.PamConfigEntry,
) -> config_file_pb2.PamConfigEntry:
  return rdf.AsPrimitiveProto()


def ToRDFPamConfigEntry(
    proto: config_file_pb2.PamConfigEntry,
) -> rdf_config_file.PamConfigEntry:
  return rdf_config_file.PamConfigEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoPamConfig(
    rdf: rdf_config_file.PamConfig,
) -> config_file_pb2.PamConfig:
  return rdf.AsPrimitiveProto()


def ToRDFPamConfig(
    proto: config_file_pb2.PamConfig,
) -> rdf_config_file.PamConfig:
  return rdf_config_file.PamConfig.FromSerializedBytes(
      proto.SerializeToString()
  )
