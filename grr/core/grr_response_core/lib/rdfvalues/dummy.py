#!/usr/bin/env python
"""The various Dummy example rdfvalues."""

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import dummy_pb2


class DummyRequest(rdf_structs.RDFProtoStruct):
  """Request for Dummy action."""

  protobuf = dummy_pb2.DummyRequest
  rdf_deps = []


class DummyResult(rdf_structs.RDFProtoStruct):
  """Result for Dummy action."""

  protobuf = dummy_pb2.DummyResult
  rdf_deps = []
