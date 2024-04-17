#!/usr/bin/env python
"""Implementation of configuration_file types."""

from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import config_file_pb2


class LogTarget(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of a logging target."""

  protobuf = config_file_pb2.LogTarget


class LogConfig(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of a logging configuration."""

  protobuf = config_file_pb2.LogConfig
  rdf_deps = [
      LogTarget,
  ]


class NfsClient(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of an NFS Client configuration."""

  protobuf = config_file_pb2.NfsClient


class NfsExport(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of an NFS Export entry."""

  protobuf = config_file_pb2.NfsExport
  rdf_deps = [
      NfsClient,
  ]


class NtpConfig(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of a ntp config file."""

  protobuf = config_file_pb2.NtpConfig
  rdf_deps = [
      rdf_protodict.AttributedDict,
  ]


class PamConfigEntry(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of a single entry in a PAM configuration."""

  protobuf = config_file_pb2.PamConfigEntry


class PamConfig(rdf_structs.RDFProtoStruct):
  """An RDFValue representation of an entire PAM configuration."""

  protobuf = config_file_pb2.PamConfig
  rdf_deps = [
      PamConfigEntry,
  ]
