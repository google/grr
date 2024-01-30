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


def ToProtoSshdMatchBlock(
    rdf: rdf_config_file.SshdMatchBlock,
) -> config_file_pb2.SshdMatchBlock:
  return rdf.AsPrimitiveProto()


def ToRDFSshdMatchBlock(
    proto: config_file_pb2.SshdMatchBlock,
) -> rdf_config_file.SshdMatchBlock:
  return rdf_config_file.SshdMatchBlock.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoSshdConfig(
    rdf: rdf_config_file.SshdConfig,
) -> config_file_pb2.SshdConfig:
  return rdf.AsPrimitiveProto()


def ToRDFSshdConfig(
    proto: config_file_pb2.SshdConfig,
) -> rdf_config_file.SshdConfig:
  return rdf_config_file.SshdConfig.FromSerializedBytes(
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


def ToProtoSudoersAlias(
    rdf: rdf_config_file.SudoersAlias,
) -> config_file_pb2.SudoersAlias:
  return rdf.AsPrimitiveProto()


def ToRDFSudoersAlias(
    proto: config_file_pb2.SudoersAlias,
) -> rdf_config_file.SudoersAlias:
  return rdf_config_file.SudoersAlias.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoSudoersDefault(
    rdf: rdf_config_file.SudoersDefault,
) -> config_file_pb2.SudoersDefault:
  return rdf.AsPrimitiveProto()


def ToRDFSudoersDefault(
    proto: config_file_pb2.SudoersDefault,
) -> rdf_config_file.SudoersDefault:
  return rdf_config_file.SudoersDefault.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoSudoersEntry(
    rdf: rdf_config_file.SudoersEntry,
) -> config_file_pb2.SudoersEntry:
  return rdf.AsPrimitiveProto()


def ToRDFSudoersEntry(
    proto: config_file_pb2.SudoersEntry,
) -> rdf_config_file.SudoersEntry:
  return rdf_config_file.SudoersEntry.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoSudoersConfig(
    rdf: rdf_config_file.SudoersConfig,
) -> config_file_pb2.SudoersConfig:
  return rdf.AsPrimitiveProto()


def ToRDFSudoersConfig(
    proto: config_file_pb2.SudoersConfig,
) -> rdf_config_file.SudoersConfig:
  return rdf_config_file.SudoersConfig.FromSerializedBytes(
      proto.SerializeToString()
  )
