#!/usr/bin/env python
"""RDFValues describing web history artifacts."""

from grr.lib import rdfvalue
from grr.lib.rdfvalues import structs
from grr_response_proto import sysinfo_pb2


class BrowserHistoryItem(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.BrowserHistoryItem
  rdf_deps = [
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
  ]
