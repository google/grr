#!/usr/bin/env python
"""RDFValues for GRR client-side cron jobs parsing."""

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import sysinfo_pb2


class CronTabEntry(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.CronTabEntry


class CronTabFile(rdf_structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.CronTabFile
  rdf_deps = [
      CronTabEntry,
  ]
