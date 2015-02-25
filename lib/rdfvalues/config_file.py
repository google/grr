#!/usr/bin/env python
"""Implementation of configuration_file types."""
from grr.lib import rdfvalue
from grr.proto import config_file_pb2


class Config(rdfvalue.RDFProtoStruct):
  """An RDFValue representation of a generic key/val configuration file."""
  protobuf = config_file_pb2.Config

  def __init__(self, initializer=None, age=None, **kwargs):
    # A dict passed in as an initializer needs to be converted to kwargs.
    if isinstance(initializer, dict):
      settings = initializer
      duplicates = [k for k in initializer if k in kwargs]
      if duplicates:
        raise ValueError("Duplicate setting definitions in Config: %s" %
                         ",".join(duplicates))
      settings.update(kwargs)
      initializer = None
    # If kwargs explicitly includes settings, use that. Otherwise, use all the
    # kwargs as settings.
    elif kwargs:
      settings = kwargs.get("settings", kwargs)
    else:
      settings = {}
    super(Config, self).__init__(initializer=initializer, age=age,
                                 settings=settings)

  def __getattr__(self, item):
    if item == "settings":
      return getattr(self, item)
    else:
      return self.settings.GetItem(item)


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
