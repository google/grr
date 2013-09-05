#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""RDFValues used to communicate with the memory analysis framework."""


from grr.lib import rdfvalue
from grr.proto import jobs_pb2


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

  def GetValue(self):
    if self.HasField("svalue"):
      return self.svalue
    elif self.HasField("value"):
      return self.value
    else:
      raise RuntimeError("VolatilityValue without data.")


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
