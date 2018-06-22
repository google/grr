#!/usr/bin/env python
"""RDFValues for cronjobs."""

from grr.lib import rdfvalue
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2
from grr.server.grr_response_server import flow


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


class CreateCronJobFlowArgs(structs.RDFProtoStruct):
  """Args to create a run for a cron job."""
  protobuf = flows_pb2.CreateCronJobFlowArgs
  rdf_deps = [
      rdfvalue.Duration,
      rdf_flows.FlowRunnerArgs,
      rdfvalue.RDFDatetime,
  ]

  def GetFlowArgsClass(self):
    if self.flow_runner_args.flow_name:
      flow_cls = flow.GRRFlow.classes.get(self.flow_runner_args.flow_name)
      if flow_cls is None:
        raise ValueError("Flow '%s' not known by this implementation." %
                         self.flow_runner_args.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class CronJob(structs.RDFProtoStruct):
  """The cron job class."""
  protobuf = flows_pb2.CronJob
  rdf_deps = [
      rdfvalue.RDFDatetime,
      CreateCronJobFlowArgs,
      rdf_protodict.AttributedDict,
  ]

  def __init__(self, *args, **kw):
    self.leased_until = None
    self.leased_by = None
    super(CronJob, self).__init__(*args, **kw)

    if not self.create_time:
      self.create_time = rdfvalue.RDFDatetime.Now()
