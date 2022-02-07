#!/usr/bin/env python
"""The various ReadLowLevel rdfvalues."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import read_low_level_pb2


class ReadLowLevelArgs(rdf_structs.RDFProtoStruct):
  """Arguments for ReadLowLevel flow."""
  protobuf = read_low_level_pb2.ReadLowLevelArgs
  rdf_deps = [
      rdfvalue.ByteSize,
  ]

  # MAX_RAW_DATA_BYTES sets the limit for requesting raw data for the client.
  # This limit amounts to 10 GiB. If the user needs more than that, they will
  # need to schedule more than one read and concatenate the data themselves.
  MAX_RAW_DATA_BYTES = 10 * 1024 * 1024 * 1024  # 10 GiB

  def Validate(self):
    if not self.HasField("path"):
      raise ValueError("No path provided")

    if not self.HasField("length"):
      raise ValueError("No length provided")

    if self.length <= 0:
      raise ValueError(f"Negative length ({self.length})")

    if self.length > self.MAX_RAW_DATA_BYTES:
      raise ValueError(f"Cannot read more than {self.MAX_RAW_DATA_BYTES} bytes "
                       f"({self.length} bytes requested")


class ReadLowLevelFlowResult(rdf_structs.RDFProtoStruct):
  """Result returned by ReadLowLevel."""
  protobuf = read_low_level_pb2.ReadLowLevelFlowResult
  rdf_deps = []


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
