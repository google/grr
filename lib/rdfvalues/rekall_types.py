#!/usr/bin/env python
"""RDFValues used to communicate with the Rekall memory analysis framework."""


from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import jobs_pb2


class PluginRequest(rdf_structs.RDFProtoStruct):
  """A request to the Rekall subsystem on the client."""
  protobuf = jobs_pb2.PluginRequest


class RekallRequest(rdf_structs.RDFProtoStruct):
  """A request to the Rekall subsystem on the client."""
  protobuf = jobs_pb2.RekallRequest


class MemoryInformation(rdf_structs.RDFProtoStruct):
  """Information about the client's memory geometry."""
  protobuf = jobs_pb2.MemoryInformation


class RekallResponse(rdf_structs.RDFProtoStruct):
  """The result of running a plugin."""
  protobuf = jobs_pb2.RekallResponse


class RekallProfile(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.RekallProfile
