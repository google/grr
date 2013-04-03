#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""RDFValues used to communicate with the memory analysis framework."""


from grr.lib import rdfvalue
from grr.lib import type_info
from grr.proto import jobs_pb2


class InstallDriverRequest(rdfvalue.RDFProto):
  """A request to the client to install a driver."""
  _proto = jobs_pb2.InstallDriverRequest

  rdf_map = dict(driver=rdfvalue.SignedBlob)


class VolatilityRequest(rdfvalue.RDFProto):
  """A request to the volatility subsystem on the client."""
  _proto = jobs_pb2.VolatilityRequest

  rdf_map = dict(args=rdfvalue.RDFProtoDict,
                 device=rdfvalue.RDFPathSpec,
                 session=rdfvalue.RDFProtoDict)


class MemoryInformation(rdfvalue.RDFProto):
  """Information about the client's memory geometry."""
  _proto = jobs_pb2.MemoryInformation

  rdf_map = dict(device=rdfvalue.RDFPathSpec,
                 runs=rdfvalue.BufferReference)


# The following define the data returned by Volatility plugins in a structured
# way. Volatility plugins typically produce tables, these are modeled using the
# following types.

# A Volatility plugin will produce a list of sections, each section refers to a
# different entity (e.g. information about about a different PID). Each section
# is then split into a list of tables. Tables in turn consist of a header (which
# represent the list of column names), and rows. Each row consists of a list of
# values.


class VolatilityValue(rdfvalue.RDFProto):
  _proto = jobs_pb2.VolatilityValue


class VolatilityValues(rdfvalue.RDFProto):
  _proto = jobs_pb2.VolatilityValues

  rdf_map = dict(values=VolatilityValue)


class VolatilitySection(rdfvalue.RDFProto):
  """A Volatility response returns multiple sections.

  Each section typically covers a single object (e.g. a PID).
  """
  _proto = jobs_pb2.VolatilitySection


class VolatilityResult(rdfvalue.RDFProto):
  """The result of running a plugin."""
  _proto = jobs_pb2.VolatilityResponse

  rdf_map = dict(sections=VolatilitySection)


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
          default=rdfvalue.RDFPathSpec(
              path=r"\\.\pmem",
              pathtype=rdfvalue.RDFPathSpec.Enum("MEMORY")),
          name="device",
          )
      )

  def __init__(self, **kwargs):
    default_request = rdfvalue.VolatilityRequest()
    default_request.device.path = r"\\.\pmem"
    default_request.device.pathtype = rdfvalue.RDFPathSpec.Enum("MEMORY")

    defaults = dict(name="request",
                    default=default_request,
                    rdfclass=rdfvalue.VolatilityRequest)

    defaults.update(kwargs)
    super(VolatilityRequestType, self).__init__(**defaults)
