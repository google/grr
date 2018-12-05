#!/usr/bin/env python
"""RDFValues for the NSRL file store."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import jobs_pb2


class NSRLInformation(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.NSRLInformation
  rdf_deps = [
      rdfvalue.HashDigest,
  ]
