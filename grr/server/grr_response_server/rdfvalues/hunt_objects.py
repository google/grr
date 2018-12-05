#!/usr/bin/env python
"""Rdfvalues for flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import hunts_pb2


class Hunt(rdf_structs.RDFProtoStruct):
  """Hunt object."""
  protobuf = hunts_pb2.Hunt
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]
