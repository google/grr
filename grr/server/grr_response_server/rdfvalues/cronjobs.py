#!/usr/bin/env python
"""RDFValues for GRR server-side cron jobs."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import random
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunts as rdf_hunts


class CronJobRunStatus(rdf_structs.RDFProtoStruct):
  protobuf = jobs_pb2.CronJobRunStatus


class CreateCronJobFlowArgs(rdf_structs.RDFProtoStruct):
  """Args to create a run for a cron job."""
  protobuf = flows_pb2.CreateCronJobFlowArgs
  rdf_deps = [
      rdfvalue.Duration,
      rdf_flow_runner.FlowRunnerArgs,
      rdfvalue.RDFDatetime,
  ]

  def GetFlowArgsClass(self):
    if self.flow_runner_args.flow_name:
      flow_cls = registry.AFF4FlowRegistry.FlowClassByName(
          self.flow_runner_args.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class SystemCronAction(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.SystemCronAction
  rdf_deps = []


class HuntCronAction(rdf_structs.RDFProtoStruct):
  """Cron Action that starts a hunt."""
  protobuf = flows_pb2.HuntCronAction
  rdf_deps = [
      rdf_hunts.HuntRunnerArgs,
  ]

  def GetFlowArgsClass(self):
    if self.flow_name:
      flow_cls = registry.AFF4FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


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
      rdfvalue.Duration,
      rdfvalue.RDFDatetime,
  ]

  def __init__(self, *args, **kw):
    self.leased_until = None
    self.leased_by = None
    super(CronJob, self).__init__(*args, **kw)

    if not self.created_at:
      self.created_at = rdfvalue.RDFDatetime.Now()


class CronJobRun(rdf_structs.RDFProtoStruct):
  """A single run of a cron job."""
  protobuf = flows_pb2.CronJobRun
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  def GenerateRunId(self):
    self.run_id = "%08X" % random.UInt32()
    return self.run_id


class CreateCronJobArgs(rdf_structs.RDFProtoStruct):
  """Arguments for the CreateJob function."""

  protobuf = flows_pb2.CreateCronJobArgs
  rdf_deps = [
      rdfvalue.Duration,
      rdf_hunts.HuntRunnerArgs,
  ]

  def GetFlowArgsClass(self):
    if self.flow_name:
      flow_cls = registry.AFF4FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type

  @classmethod
  def FromApiCreateCronJobArgs(cls, api_args):
    return cls(
        flow_name=api_args.flow_name,
        flow_args=api_args.flow_args,
        hunt_runner_args=api_args.hunt_runner_args,
        description=api_args.description,
        frequency=api_args.periodicity,
        lifetime=api_args.lifetime,
        allow_overruns=api_args.allow_overruns)
