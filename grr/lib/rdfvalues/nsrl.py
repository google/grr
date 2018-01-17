#!/usr/bin/env python
"""RDFValues for the NSRL file store."""

from grr.lib import rdfvalue
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2


class NSRLInformation(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.NSRLInformation
  rdf_deps = [
      rdfvalue.HashDigest,
  ]
