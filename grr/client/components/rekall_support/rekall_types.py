#!/usr/bin/env python
"""RDFValues used to communicate with the Rekall memory analysis framework."""


import gzip
import StringIO
import zlib

import rekall_pb2

from grr.lib import rdfvalue
from grr.lib.rdfvalues import structs as rdf_structs


class PluginRequest(rdf_structs.RDFProtoStruct):
  """A request to the Rekall subsystem on the client."""
  protobuf = rekall_pb2.PluginRequest


class RekallRequest(rdf_structs.RDFProtoStruct):
  """A request to the Rekall subsystem on the client."""
  protobuf = rekall_pb2.RekallRequest


class MemoryInformation(rdf_structs.RDFProtoStruct):
  """Information about the client's memory geometry."""
  protobuf = rekall_pb2.MemoryInformation


class RekallResponse(rdf_structs.RDFProtoStruct):
  """The result of running a plugin."""
  protobuf = rekall_pb2.RekallResponse

  def SerializeToString(self):
    json_messages = self.Get("json_messages")
    if json_messages:
      self.Set("compressed_json_messages", zlib.compress(json_messages))
      self.Set("json_messages", None)

    return super(RekallResponse, self).SerializeToString()

  @property
  def json_messages(self):
    json_messages = self.Get("compressed_json_messages")
    if json_messages:
      return json_messages.Uncompress()

    json_messages = self.Get("json_messages")
    if json_messages:
      return json_messages

    return ""

  @json_messages.setter
  def json_messages(self, value):
    self.Set("json_messages", value)

    # Clear any compressed data the proto already has.
    self.Set("compressed_json_messages", None)


class ZippedJSONBytes(rdfvalue.RDFZippedBytes):
  """Byte array containing zipped JSON bytes."""


class RekallProfile(rdf_structs.RDFProtoStruct):
  protobuf = rekall_pb2.RekallProfile

  @property
  def payload(self):
    if self.compression == "GZIP":
      return gzip.GzipFile(fileobj=StringIO.StringIO(self.data)).read()

    return self.data
