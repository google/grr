#!/usr/bin/env python
"""RDFValues used to communicate with the Rekall memory analysis framework."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import gzip
import io
import zlib

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs

from grr_response_proto import rekall_pb2


class RekallProfile(rdf_structs.RDFProtoStruct):
  protobuf = rekall_pb2.RekallProfile

  @property
  def payload(self):
    if self.compression == "GZIP":
      return gzip.GzipFile(fileobj=io.BytesIO(self.data)).read()

    return self.data


class ZippedJSONBytes(rdfvalue.RDFZippedBytes):
  """Byte array containing zipped JSON bytes."""


class PluginRequest(rdf_structs.RDFProtoStruct):
  """A request to the Rekall subsystem on the client."""
  protobuf = rekall_pb2.PluginRequest
  rdf_deps = [
      rdf_protodict.Dict,
  ]


class RekallRequest(rdf_structs.RDFProtoStruct):
  """A request to the Rekall subsystem on the client."""
  protobuf = rekall_pb2.RekallRequest
  rdf_deps = [
      rdf_protodict.Dict,
      rdf_client_action.Iterator,
      rdf_paths.PathSpec,
      PluginRequest,
      RekallProfile,
  ]


class MemoryInformation(rdf_structs.RDFProtoStruct):
  """Information about the client's memory geometry."""
  protobuf = rekall_pb2.MemoryInformation
  rdf_deps = [
      rdf_client.BufferReference,
      rdf_paths.PathSpec,
  ]


class RekallResponse(rdf_structs.RDFProtoStruct):
  """The result of running a plugin."""
  protobuf = rekall_pb2.RekallResponse
  rdf_deps = [
      rdf_client.ClientURN,
      rdfvalue.RDFURN,
      ZippedJSONBytes,
  ]

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
