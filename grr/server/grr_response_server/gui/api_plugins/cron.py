#!/usr/bin/env python
"""API handlers for dealing with cron jobs."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import sys

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import cron_pb2
from grr_response_server import aff4
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import flow
from grr_response_server.aff4_objects import cronjobs as aff4_cronjobs
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.gui.api_plugins import flow as api_plugins_flow
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import objects as rdf_objects


class CronJobNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a cron job could not be found."""


class CronJobRunNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a cron job run could not be found."""


class ApiCronJobId(rdfvalue.RDFString):
  """Class encapsulating cron job ids."""

  def ToURN(self):
    if not self._value:
      raise ValueError("Can't call ToURN() on an empty cron job id.")

    return aff4_cronjobs.CronManager.CRON_JOBS_PATH.Add(self._value)


class ApiCronJobRunId(rdfvalue.RDFString):
  """Class encapsulating cron job run ids."""

  def ToURN(self, cron_job_id):
    return cron_job_id.ToURN().Add(self._value)


class ApiCronJob(rdf_structs.RDFProtoStruct):
  """ApiCronJob is used when rendering responses.

  ApiCronJob is meant to be more lightweight than automatically generated AFF4
  representation. It's also meant to contain only the information needed by
  the UI and to not expose implementation details.
  """
  protobuf = cron_pb2.ApiCronJob
  rdf_deps = [
      ApiCronJobId,
      api_call_handler_utils.ApiDataObject,
      rdf_cronjobs.CronJobAction,
      rdfvalue.Duration,
      rdfvalue.RDFDatetime,
  ]

  def GetArgsClass(self):
    if self.flow_name:
      flow_cls = registry.AFF4FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type

  def _IsCronJobFailing(self, cron_job):
    """Returns True if the last run failed."""
    status = cron_job.Get(cron_job.Schema.LAST_RUN_STATUS)
    if status is None:
      return False

    return status.status != rdf_cronjobs.CronJobRunStatus.Status.OK

  status_map = {
      rdf_cronjobs.CronJobRunStatus.Status.OK:
          rdf_cronjobs.CronJobRun.CronJobRunStatus.FINISHED,
      rdf_cronjobs.CronJobRunStatus.Status.ERROR:
          rdf_cronjobs.CronJobRun.CronJobRunStatus.ERROR,
      rdf_cronjobs.CronJobRunStatus.Status.TIMEOUT:
          rdf_cronjobs.CronJobRun.CronJobRunStatus.LIFETIME_EXCEEDED,
  }

  def _StatusFromCronJobRunStatus(self, status):
    if status is None:
      return None

    return self.status_map[status.status]

  # TODO(hanuszczak): Why is this an instance method?
  def InitFromAff4Object(self, cron_job):
    cron_args = cron_job.Get(cron_job.Schema.CRON_ARGS)

    flow_name = cron_args.flow_runner_args.flow_name
    if flow_name == "CreateAndRunGenericHuntFlow":
      action_type = rdf_cronjobs.CronJobAction.ActionType.HUNT_CRON_ACTION
      hunt_args = cron_args.flow_args.hunt_args
      # Hunt name is always GenericHunt, no need to keep it around.
      cron_args.flow_args.hunt_runner_args.hunt_name = None
      args = rdf_cronjobs.CronJobAction(
          action_type=action_type,
          hunt_cron_action=rdf_cronjobs.HuntCronAction(
              hunt_runner_args=cron_args.flow_args.hunt_runner_args,
              flow_args=hunt_args.flow_args,
              flow_name=hunt_args.flow_runner_args.flow_name,
          ))
    else:
      action_type = rdf_cronjobs.CronJobAction.ActionType.SYSTEM_CRON_ACTION
      args = rdf_cronjobs.CronJobAction(
          action_type=action_type,
          system_cron_action=rdf_cronjobs.SystemCronAction(
              job_class_name=cron_args.flow_runner_args.flow_name))

    api_cron_job = ApiCronJob(
        cron_job_id=cron_job.urn.Basename(),
        args=args,
        enabled=not cron_job.Get(cron_job.Schema.DISABLED),
        last_run_status=self._StatusFromCronJobRunStatus(
            cron_job.Get(cron_job.Schema.LAST_RUN_STATUS)),
        last_run_time=cron_job.Get(cron_job.Schema.LAST_RUN_TIME),
        frequency=cron_args.periodicity,
        lifetime=cron_args.lifetime or None,
        allow_overruns=cron_args.allow_overruns,
        description=cron_args.description,
        is_failing=self._IsCronJobFailing(cron_job))

    state_dict = cron_job.Get(cron_job.Schema.STATE_DICT)
    if state_dict:
      state = api_call_handler_utils.ApiDataObject()
      state.InitFromDataObject(state_dict)
      api_cron_job.state = state

    current_flow_urn = cron_job.Get(cron_job.Schema.CURRENT_FLOW_URN)
    if current_flow_urn:
      api_cron_job.current_run_id = current_flow_urn.Basename()

    return api_cron_job

  def _IsCronJobObjectFailing(self, cron_job):
    status = cron_job.last_run_status
    if status is None:
      return False
    return status in [
        rdf_cronjobs.CronJobRun.CronJobRunStatus.ERROR,
        rdf_cronjobs.CronJobRun.CronJobRunStatus.LIFETIME_EXCEEDED
    ]

  # TODO(hanuszczak): Why is this an instance method?
  def InitFromCronObject(self, cron_job):
    api_cron_job = ApiCronJob(
        cron_job_id=cron_job.cron_job_id,
        args=cron_job.args,
        # TODO(amoser): AFF4 does not keep this data. Enable once we don't have
        # aff4 to support anymore.
        # created_at=cron_job.created_at,
        current_run_id=cron_job.current_run_id or None,
        description=cron_job.description,
        enabled=cron_job.enabled,
        last_run_status=cron_job.last_run_status or None,
        last_run_time=cron_job.last_run_time,
        frequency=cron_job.frequency,
        lifetime=cron_job.lifetime or None,
        allow_overruns=cron_job.allow_overruns,
        is_failing=self._IsCronJobObjectFailing(cron_job))

    if cron_job.forced_run_requested:
      api_cron_job.forced_run_requested = True

    state_dict = cron_job.state.ToDict()
    if state_dict:
      state = api_call_handler_utils.ApiDataObject()
      state.InitFromDataObject(state_dict)
      api_cron_job.state = state

    return api_cron_job

  def InitFromObject(self, obj):
    if isinstance(obj, aff4.AFF4Object):
      return self.InitFromAff4Object(obj)
    else:
      return self.InitFromCronObject(obj)

  def ObjectReference(self):
    return rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.CRON_JOB,
        cron_job=rdf_objects.CronJobReference(
            cron_job_id=utils.SmartStr(self.cron_job_id)))


class ApiCronJobRun(rdf_structs.RDFProtoStruct):
  """ApiCronJobRun represents individual cron job runs."""
  protobuf = cron_pb2.ApiCronJobRun
  rdf_deps = [
      ApiCronJobId,
      ApiCronJobRunId,
      rdfvalue.RDFDatetime,
  ]

  def InitFromRunObject(self, run):
    self.run_id = run.run_id
    self.cron_job_id = run.cron_job_id
    self.started_at = run.started_at
    self.finished_at = run.finished_at
    self.status = run.status
    self.log_message = run.log_message or None
    self.backtrace = run.backtrace or None
    return self

  def InitFromApiFlow(self, f, cron_job_id=None):
    """Shortcut method for easy legacy cron jobs support."""
    if f.flow_id:
      self.run_id = f.flow_id
    elif f.urn:
      self.run_id = f.urn.Basename()
    self.started_at = f.started_at
    self.cron_job_id = cron_job_id

    flow_state_enum = api_plugins_flow.ApiFlow.State
    cron_enum = rdf_cronjobs.CronJobRun.CronJobRunStatus
    errors_map = {
        flow_state_enum.RUNNING: cron_enum.RUNNING,
        flow_state_enum.TERMINATED: cron_enum.FINISHED,
        flow_state_enum.ERROR: cron_enum.ERROR,
        flow_state_enum.CLIENT_CRASHED: cron_enum.ERROR
    }
    self.status = errors_map[f.state]

    if f.state != f.State.RUNNING:
      self.finished_at = f.last_active_at

    if f.context.kill_timestamp:
      self.status = self.Status.LIFETIME_EXCEEDED

    if f.context.HasField("status"):
      self.log_message = f.context.status

    if f.context.HasField("backtrace"):
      self.backtrace = f.context.backtrace

    return self


class ApiListCronJobsArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiListCronJobsArgs


class ApiListCronJobsResult(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiListCronJobsResult
  rdf_deps = [
      ApiCronJob,
  ]


class ApiListCronJobsHandler(api_call_handler_base.ApiCallHandler):
  """Lists flows launched on a given client."""

  args_type = ApiListCronJobsArgs
  result_type = ApiListCronJobsResult

  def Handle(self, args, token=None):
    if not args.count:
      stop = None
    else:
      stop = args.offset + args.count

    cron_manager = aff4_cronjobs.GetCronManager()
    all_jobs = list(cron_manager.ReadJobs(token=token))
    all_jobs.sort(
        key=lambda job: (getattr(job, "cron_job_id", None) or job.urn))
    cron_jobs = all_jobs[args.offset:stop]

    items = [ApiCronJob().InitFromObject(cron_job) for cron_job in cron_jobs]

    return ApiListCronJobsResult(items=items, total_count=len(all_jobs))


class ApiGetCronJobArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiGetCronJobArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiGetCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves a specific cron job."""

  args_type = ApiGetCronJobArgs
  result_type = ApiCronJob

  def Handle(self, args, token=None):
    try:
      cron_job = aff4_cronjobs.GetCronManager().ReadJob(
          unicode(args.cron_job_id), token=token)

      return ApiCronJob().InitFromObject(cron_job)
    except (aff4.InstantiationError, db.UnknownCronJobError):
      raise CronJobNotFoundError(
          "Cron job with id %s could not be found" % args.cron_job_id)


class ApiListCronJobRunsArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiListCronJobRunsArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiListCronJobRunsResult(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiListCronJobRunsResult
  rdf_deps = [
      ApiCronJobRun,
  ]


class ApiListCronJobRunsHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the given cron job's runs."""

  args_type = ApiListCronJobRunsArgs
  result_type = ApiListCronJobRunsResult

  def Handle(self, args, token=None):
    if data_store.RelationalDBReadEnabled(category="cronjobs"):
      runs = cronjobs.CronManager().ReadJobRuns(unicode(args.cron_job_id))
      start = args.offset
      if args.count:
        end = args.offset + args.count
      else:
        end = sys.maxsize
      return ApiListCronJobRunsResult(items=[
          ApiCronJobRun().InitFromRunObject(run) for run in runs[start:end]
      ])
    else:
      # Note: this is a legacy AFF4 implementation.
      flows_result = api_plugins_flow.ApiListFlowsHandler.BuildFlowList(
          args.cron_job_id.ToURN(),
          args.count,
          args.offset,
          with_state_and_context=True,
          token=token)
      return ApiListCronJobRunsResult(items=[
          ApiCronJobRun().InitFromApiFlow(f, cron_job_id=args.cron_job_id)
          for f in flows_result.items
      ])


class ApiGetCronJobRunArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiGetCronJobRunArgs
  rdf_deps = [
      ApiCronJobId,
      ApiCronJobRunId,
  ]


class ApiGetCronJobRunHandler(api_call_handler_base.ApiCallHandler):
  """Renders given cron run."""

  args_type = ApiGetCronJobRunArgs
  result_type = ApiCronJobRun

  def Handle(self, args, token=None):
    if data_store.RelationalDBReadEnabled(category="cronjobs"):
      run = cronjobs.CronManager().ReadJobRun(
          unicode(args.cron_job_id), unicode(args.run_id))
      if not run:
        raise CronJobRunNotFoundError(
            "Cron job run with id %s could not be found" % args.run_id)

      return ApiCronJobRun().InitFromRunObject(run)
    else:
      # Note: this is a legacy AFF4 implementation.
      flow_urn = args.run_id.ToURN(args.cron_job_id)
      flow_obj = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, mode="r", token=token)
      f = api_plugins_flow.ApiFlow().InitFromAff4Object(
          flow_obj, with_state_and_context=True)

      return ApiCronJobRun().InitFromApiFlow(f, cron_job_id=args.cron_job_id)


class ApiCreateCronJobArgs(rdf_structs.RDFProtoStruct):
  """Arguments for CreateCronJob API call."""

  protobuf = cron_pb2.ApiCreateCronJobArgs
  rdf_deps = [
      rdfvalue.Duration,
      rdf_hunts.HuntRunnerArgs,
  ]

  def GetFlowArgsClass(self):
    if self.flow_name:
      flow_cls = registry.AFF4FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class ApiCreateCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Creates a new cron job."""

  args_type = ApiCreateCronJobArgs
  result_type = ApiCronJob

  def Handle(self, source_args, token=None):
    # Make sure we don't modify source arguments.
    args = source_args.Copy()

    # Clear all fields marked with HIDDEN.
    args.flow_args.ClearFieldsWithLabel(
        rdf_structs.SemanticDescriptor.Labels.HIDDEN)
    # Clear all fields marked with HIDDEN, except for output_plugins - they are
    # marked HIDDEN, because we have a separate UI for them, not because they
    # shouldn't be shown to the user at all.
    #
    # TODO(user): Refactor the code to remove the HIDDEN label from
    # FlowRunnerArgs.output_plugins.
    args.hunt_runner_args.ClearFieldsWithLabel(
        rdf_structs.SemanticDescriptor.Labels.HIDDEN,
        exceptions="output_plugins")
    cron_manager = aff4_cronjobs.GetCronManager()

    cron_args = rdf_cronjobs.CreateCronJobArgs.FromApiCreateCronJobArgs(args)
    cron_job_id = cron_manager.CreateJob(
        cron_args=cron_args, enabled=False, token=token)

    cron_obj = cron_manager.ReadJob(cron_job_id)

    return ApiCronJob().InitFromObject(cron_obj)


class ApiForceRunCronJobArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiForceRunCronJobArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiForceRunCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Force-runs a given cron job."""

  args_type = ApiForceRunCronJobArgs

  def Handle(self, args, token=None):
    job_id = unicode(args.cron_job_id)
    if data_store.RelationalDBReadEnabled(category="cronjobs"):
      aff4_cronjobs.GetCronManager().RequestForcedRun(job_id)
    else:
      aff4_cronjobs.GetCronManager().RunOnce(
          names=[job_id], token=token, force=True)


class ApiModifyCronJobArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiModifyCronJobArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiModifyCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Enables or disables a given cron job."""

  args_type = ApiModifyCronJobArgs
  result_type = ApiCronJob

  def Handle(self, args, token=None):
    cron_id = unicode(args.cron_job_id)
    if args.enabled:
      aff4_cronjobs.GetCronManager().EnableJob(cron_id, token=token)
    else:
      aff4_cronjobs.GetCronManager().DisableJob(cron_id, token=token)

    cron_job_obj = aff4_cronjobs.GetCronManager().ReadJob(cron_id, token=token)
    return ApiCronJob().InitFromObject(cron_job_obj)


class ApiDeleteCronJobArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiDeleteCronJobArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiDeleteCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Deletes a given cron job."""

  args_type = ApiDeleteCronJobArgs

  def Handle(self, args, token=None):
    aff4_cronjobs.GetCronManager().DeleteJob(
        unicode(args.cron_job_id), token=token)
