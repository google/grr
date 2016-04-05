#!/usr/bin/env python
"""RDFValues for the NSRL file store."""


from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import jobs_pb2


class NSRLInformation(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.NSRLInformation
