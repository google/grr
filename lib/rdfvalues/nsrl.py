#!/usr/bin/env python
"""RDFValues for the NSRL file store."""


from grr.lib import rdfvalue
from grr.proto import jobs_pb2


class NSRLInformation(rdfvalue.RDFProtoStruct):
  protobuf = jobs_pb2.NSRLInformation
