#!/usr/bin/env python
"""RDFValues for GRR client-side cron jobs parsing."""

from grr.lib import rdfvalue
from grr.lib.rdfvalues import structs
from grr_response_proto import sysinfo_pb2


class CronTabEntry(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.CronTabEntry


class CronTabFile(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.CronTabFile
  rdf_deps = [
      CronTabEntry,
      rdfvalue.RDFURN,
  ]
