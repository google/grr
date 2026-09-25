#!/usr/bin/env python
"""RDFValues for GRR server-side cron jobs."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import random
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.rdfvalues import hunts as rdf_hunts


class CronJobRunStatus(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.CronJobRunStatus


class SystemCronAction(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.SystemCronAction
  rdf_deps = []


class HuntCronAction(rdf_structs.RDFProtoStruct):
  """Cron Action that starts a hunt."""

  protobuf = flows_pb2.HuntCronAction
  rdf_deps = [
      rdf_hunts.HuntRunnerArgs,
  ]


class CronJobAction(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.CronJobAction

  rdf_deps = [
      SystemCronAction,
      HuntCronAction,
  ]


class CronJob(rdf_structs.RDFProtoStruct):
  """The cron job class."""

  protobuf = flows_pb2.CronJob
  rdf_deps = [
      CronJobAction,
      rdf_protodict.AttributedDict,
      rdfvalue.DurationSeconds,
      rdfvalue.RDFDatetime,
  ]


class CronJobRun(rdf_structs.RDFProtoStruct):
  """A single run of a cron job."""

  protobuf = flows_pb2.CronJobRun
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  def GenerateRunId(self):
    self.run_id = "%08X" % random.UInt32()
    return self.run_id
