#!/usr/bin/env python
"""A module with RDF wrappers for Protocol Buffers Well-Known Types."""

from google.protobuf import timestamp_pb2
from grr_response_core.lib.rdfvalues import structs as rdf_structs


class Timestamp(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the `Timestamp` Well-Known Type."""

  protobuf = timestamp_pb2.Timestamp
