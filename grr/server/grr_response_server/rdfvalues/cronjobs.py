#!/usr/bin/env python
"""RDFValues for GRR server-side cron jobs."""

from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr.server.grr_response_server.rdfvalues import flow_runner as rdf_flow_runner


class CronJobRunStatus(structs.RDFProtoStruct):
  protobuf = jobs_pb2.CronJobRunStatus


class CreateCronJobFlowArgs(structs.RDFProtoStruct):
  """Args to create a run for a cron job."""
  protobuf = flows_pb2.CreateCronJobFlowArgs
  rdf_deps = [
      rdfvalue.Duration,
      rdf_flow_runner.FlowRunnerArgs,
      rdfvalue.RDFDatetime,
  ]

  def GetFlowArgsClass(self):
    if self.flow_runner_args.flow_name:
      flow_cls = registry.FlowRegistry.FlowClassByName(
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
