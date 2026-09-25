#!/usr/bin/env python
"""The various ReadLowLevel rdfvalues."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import read_low_level_pb2


class ReadLowLevelRequest(rdf_structs.RDFProtoStruct):
  """Request for ReadLowLevel action."""

  protobuf = read_low_level_pb2.ReadLowLevelRequest
  rdf_deps = [
      rdfvalue.ByteSize,
  ]


class ReadLowLevelResult(rdf_structs.RDFProtoStruct):
  """Result for ReadLowLevel action."""

  protobuf = read_low_level_pb2.ReadLowLevelResult
  rdf_deps = [
      rdf_client.BufferReference,
      rdfvalue.HashDigest,
  ]
