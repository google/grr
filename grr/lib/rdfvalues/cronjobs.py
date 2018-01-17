#!/usr/bin/env python
"""RDFValues for cronjobs."""

from grr.lib import rdfvalue
from grr.lib.rdfvalues import structs
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2


class CronTabEntry(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.CronTabEntry


class CronTabFile(structs.RDFProtoStruct):
  protobuf = sysinfo_pb2.CronTabFile
  rdf_deps = [
      CronTabEntry,
      rdfvalue.RDFURN,
  ]


class CronJobRunStatus(structs.RDFProtoStruct):
  protobuf = jobs_pb2.CronJobRunStatus
