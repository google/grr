#!/usr/bin/env python
"""Stats-related client rdfvalues."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2


class CpuSeconds(rdf_structs.RDFProtoStruct):
  """CPU usage is reported as both a system and user components."""

  protobuf = jobs_pb2.CpuSeconds


class ClientResources(rdf_structs.RDFProtoStruct):
  """An RDFValue class representing the client resource usage."""

  protobuf = jobs_pb2.ClientResources
  rdf_deps = [
      rdf_client.ClientURN,
      CpuSeconds,
      rdfvalue.SessionID,
  ]
