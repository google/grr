#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""RDFValues used to communicate with the memory analysis framework."""


from grr.lib import rdfvalue
from grr.lib import type_info
from grr.proto import jobs_pb2


class InstallDriverRequest(rdfvalue.RDFProtoStruct):
  """A request to the client to install a driver."""
  protobuf = jobs_pb2.InstallDriverRequest


class VolatilityRequest(rdfvalue.RDFProtoStruct):
  """A request to the volatility subsystem on the client."""
  protobuf = jobs_pb2.VolatilityRequest


class MemoryInformation(rdfvalue.RDFProtoStruct):
  """Information about the client's memory geometry."""
  protobuf = jobs_pb2.MemoryInformation


# The following define the data returned by Volatility plugins in a structured
# way. Volatility plugins typically produce tables, these are modeled using the
# following types.

# A Volatility plugin will produce a list of sections, each section refers to a
# different entity (e.g. information about about a different PID). Each section
# is then split into a list of tables. Tables in turn consist of a header (which
# represent the list of column names), and rows. Each row consists of a list of
# values.


class VolatilityFormattedValue(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.VolatilityFormattedValue


class VolatilityFormattedValues(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.VolatilityFormattedValues


class VolatilityValue(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.VolatilityValue


class VolatilityValues(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.VolatilityValues


class VolatilityTable(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.VolatilityTable


class VolatilityHeader(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.VolatilityHeader


class VolatilitySection(rdfvalue.RDFProtoStruct):
  """A Volatility response returns multiple sections.

  Each section typically covers a single object (e.g. a PID).
  """
  protobuf = jobs_pb2.VolatilitySection


class VolatilityResult(rdfvalue.RDFProtoStruct):
  """The result of running a plugin."""
  protobuf = jobs_pb2.VolatilityResponse


class VolatilityRequestType(type_info.RDFValueType):
  """A type for the Volatility request."""

  child_descriptor = type_info.TypeDescriptorSet(
      type_info.String(
          description="Profile to use.",
          name="profile",
          friendly_name="Volatility profile",
          default=""),
      type_info.GenericProtoDictType(
          description="Volatility Arguments.",
          name="args"),
      type_info.MemoryPathspecType(
          description="Path to the device.",
          default=rdfvalue.PathSpec(
              path=r"\\.\pmem",
              pathtype=rdfvalue.PathSpec.PathType.MEMORY),
          name="device",
          )
      )

  def __init__(self, **kwargs):
    default_request = rdfvalue.VolatilityRequest()
    default_request.device.path = r"\\.\pmem"
    default_request.device.pathtype = rdfvalue.PathSpec.PathType.MEMORY

    defaults = dict(name="request",
                    default=default_request,
                    rdfclass=rdfvalue.VolatilityRequest)

    defaults.update(kwargs)
    super(VolatilityRequestType, self).__init__(**defaults)
