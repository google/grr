#!/usr/bin/env python
"""RDFValues used to communicate with the Rekall memory analysis framework."""


from grr.lib import rdfvalue
from grr.proto import jobs_pb2


class PluginRequest(rdfvalue.RDFProtoStruct):
  """A request to the Rekall subsystem on the client."""
  protobuf = jobs_pb2.PluginRequest


class RekallRequest(rdfvalue.RDFProtoStruct):
  """A request to the Rekall subsystem on the client."""
  protobuf = jobs_pb2.RekallRequest


class MemoryInformation(rdfvalue.RDFProtoStruct):
  """Information about the client's memory geometry."""
  protobuf = jobs_pb2.MemoryInformation


class RekallResponse(rdfvalue.RDFProtoStruct):
  """The result of running a plugin."""
  protobuf = jobs_pb2.RekallResponse


class RekallProfile(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.RekallProfile
