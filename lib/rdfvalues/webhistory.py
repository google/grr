#!/usr/bin/env python
"""RDFValues describing web history artifacts."""

from grr.lib.rdfvalues import structs

from grr.proto import sysinfo_pb2


class BrowserHistoryItem(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.BrowserHistoryItem
