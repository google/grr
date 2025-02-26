#!/usr/bin/env python
"""A module with RDF values wrapping container protobufs."""

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import containers_pb2


class ListContainersOutput(rdf_structs.RDFProtoStruct):
  """An RDF wrapper class for the `ListContainersOutput` proto."""

  protobuf = containers_pb2.ListContainersOutput
  rdf_deps = []


class ListContainersRequest(rdf_structs.RDFProtoStruct):
  """Request for the `ListContainers` client action."""

  protobuf = containers_pb2.ListContainersRequest
  rdf_deps = []


class ListContainersResult(rdf_structs.RDFProtoStruct):
  """Result for the `ListContainers` client action."""

  protobuf = containers_pb2.ListContainersResult
  rdf_deps = [ListContainersOutput]
