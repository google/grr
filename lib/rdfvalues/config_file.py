#!/usr/bin/env python
"""Implementation of configuration_file types."""
from grr.lib import rdfvalue
from grr.proto import config_file_pb2


class NfsClient(rdfvalue.RDFProtoStruct):
  """An RDFValue representation of an NFS Client configuration."""
  protobuf = config_file_pb2.NfsClient


class NfsExport(rdfvalue.RDFProtoStruct):
  """An RDFValue representation of an NFS Export entry."""
  protobuf = config_file_pb2.NfsExport


class SshdMatchBlock(rdfvalue.RDFProtoStruct):
  """An RDFValue representation of an sshd config match block."""
  protobuf = config_file_pb2.SshdMatchBlock


class SshdConfig(rdfvalue.RDFProtoStruct):
  """An RDFValue representation of a sshd config file."""
  protobuf = config_file_pb2.SshdConfig
