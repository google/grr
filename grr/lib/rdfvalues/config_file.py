#!/usr/bin/env python
"""Implementation of configuration_file types."""
from grr.lib.rdfvalues import protodict
from grr.lib.rdfvalues import structs
from grr_response_proto import config_file_pb2


class LogTarget(structs.RDFProtoStruct):
  """An RDFValue represenation of a logging target."""
  protobuf = config_file_pb2.LogTarget


class LogConfig(structs.RDFProtoStruct):
  """An RDFValue represenation of a logging configuration."""
  protobuf = config_file_pb2.LogConfig
  rdf_deps = [
      LogTarget,
  ]


class NfsClient(structs.RDFProtoStruct):
  """An RDFValue representation of an NFS Client configuration."""
  protobuf = config_file_pb2.NfsClient


class NfsExport(structs.RDFProtoStruct):
  """An RDFValue representation of an NFS Export entry."""
  protobuf = config_file_pb2.NfsExport
  rdf_deps = [
      NfsClient,
  ]


class SshdMatchBlock(structs.RDFProtoStruct):
  """An RDFValue representation of an sshd config match block."""
  protobuf = config_file_pb2.SshdMatchBlock
  rdf_deps = [
      protodict.AttributedDict,
  ]


class SshdConfig(structs.RDFProtoStruct):
  """An RDFValue representation of a sshd config file."""
  protobuf = config_file_pb2.SshdConfig
  rdf_deps = [
      protodict.AttributedDict,
      SshdMatchBlock,
  ]


class NtpConfig(structs.RDFProtoStruct):
  """An RDFValue representation of a ntp config file."""
  protobuf = config_file_pb2.NtpConfig
  rdf_deps = [
      protodict.AttributedDict,
  ]


class PamConfigEntry(structs.RDFProtoStruct):
  """An RDFValue representation of a single entry in a PAM configuration."""
  protobuf = config_file_pb2.PamConfigEntry


class PamConfig(structs.RDFProtoStruct):
  """An RDFValue representation of an entire PAM configuration."""
  protobuf = config_file_pb2.PamConfig
  rdf_deps = [
      PamConfigEntry,
  ]


class SudoersAlias(structs.RDFProtoStruct):
  """An RDFValue representation of a sudoers alias."""
  protobuf = config_file_pb2.SudoersAlias


class SudoersDefault(structs.RDFProtoStruct):
  """An RDFValue representation of a sudoers default."""
  protobuf = config_file_pb2.SudoersDefault


class SudoersEntry(structs.RDFProtoStruct):
  """An RDFValue representation of a sudoers file command list entry."""
  protobuf = config_file_pb2.SudoersEntry


class SudoersConfig(structs.RDFProtoStruct):
  """An RDFValue representation of a sudoers config file."""
  protobuf = config_file_pb2.SudoersConfig
  rdf_deps = [
      SudoersAlias,
      SudoersDefault,
      SudoersEntry,
  ]
