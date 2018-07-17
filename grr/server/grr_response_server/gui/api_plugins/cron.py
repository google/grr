#!/usr/bin/env python
"""API handlers for dealing with cron jobs."""

from grr.core.grr_response_core.lib import rdfvalue
from grr.core.grr_response_core.lib import registry
from grr.core.grr_response_core.lib import utils
from grr.core.grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import cron_pb2
from grr_response_server import aff4
from grr_response_server import flow
from grr_response_server.aff4_objects import cronjobs as aff4_cronjobs
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui.api_plugins import flow as api_plugins_flow
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import objects as rdf_objects


class CronJobNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a cron job could not be found."""


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
      rdfvalue.Duration,
      rdf_flow_runner.FlowRunnerArgs,
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
  ]

  def GetArgsClass(self):
    if self.flow_name:
      flow_cls = registry.FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type

  def _GetCronJobState(self, cron_job):
    """Returns state (as ApiCronJob.State) of an AFF4 cron job object."""
    if cron_job.Get(cron_job.Schema.DISABLED):
      return ApiCronJob.State.DISABLED
    else:
      return ApiCronJob.State.ENABLED

  def _IsCronJobFailing(self, cron_job):
    """Returns True if the last run failed."""
    status = cron_job.Get(cron_job.Schema.LAST_RUN_STATUS)
    if status is None:
      return False

    return status.status != rdf_cronjobs.CronJobRunStatus.Status.OK

  def InitFromAff4Object(self, cron_job):
    cron_args = cron_job.Get(cron_job.Schema.CRON_ARGS)

    api_cron_job = ApiCronJob(
        cron_job_id=cron_job.urn.Basename(),
        urn=cron_job.urn,
        description=cron_args.description,
        flow_name=cron_args.flow_runner_args.flow_name,
        flow_runner_args=cron_args.flow_runner_args,
        periodicity=cron_args.periodicity,
        lifetime=cron_args.lifetime,
        allow_overruns=cron_args.allow_overruns,
        state=self._GetCronJobState(cron_job),
        last_run_time=cron_job.Get(cron_job.Schema.LAST_RUN_TIME),
        is_failing=self._IsCronJobFailing(cron_job))

    try:
      api_cron_job.flow_args = cron_args.flow_args
    except ValueError:
      # If args class name has changed, ValueError will be raised. Handling
      # this gracefully - we should still try to display some useful info
      # about the flow.
      pass

    return api_cron_job

  def _IsCronJobObjectFailing(self, cron_job):
    status = cron_job.last_run_status
    if status is None:
      return False
    return status != rdf_cronjobs.CronJobRunStatus.Status.OK

  def InitFromCronObject(self, cron_job):
    cron_args = cron_job.cron_args

    if cron_job.disabled:
      state = ApiCronJob.State.DISABLED
    else:
      state = ApiCronJob.State.ENABLED

    urn = aff4_cronjobs.CronManager.CRON_JOBS_PATH.Add(cron_job.job_id)

    api_cron_job = ApiCronJob(
        cron_job_id=cron_job.job_id,
        urn=urn,
        description=cron_args.description,
        flow_name=cron_args.flow_runner_args.flow_name,
        flow_runner_args=cron_args.flow_runner_args,
        periodicity=cron_args.periodicity,
        lifetime=cron_args.lifetime,
        allow_overruns=cron_args.allow_overruns,
        state=state,
        last_run_time=cron_job.last_run_time,
        is_failing=self._IsCronJobObjectFailing(cron_job))

    try:
      api_cron_job.flow_args = cron_args.flow_args
    except ValueError:
      # If args class name has changed, ValueError will be raised. Handling
      # this gracefully - we should still try to display some useful info
      # about the flow.
      pass

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
      ApiCronJobRunId,
      rdfvalue.RDFDatetime,
  ]

  def InitFromApiFlow(self, f):
    """Shortcut method for easy legacy cron jobs support."""

    self.run_id = f.flow_id
    self.started_at = f.started_at

    flow_state_enum = api_plugins_flow.ApiFlow.State
    errors_map = {
        flow_state_enum.RUNNING: self.Status.RUNNING,
        flow_state_enum.TERMINATED: self.Status.FINISHED,
        flow_state_enum.ERROR: self.Status.ERROR,
        flow_state_enum.CLIENT_CRASHED: self.Status.ERROR
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
    all_jobs.sort(key=lambda job: getattr(job, "job_id", None) or job.urn)
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
          str(args.cron_job_id), token=token)

      return ApiCronJob().InitFromObject(cron_job)
    except aff4.InstantiationError:
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
    # Note: this is a legacy AFF4 implementation.
    flows_result = api_plugins_flow.ApiListFlowsHandler.BuildFlowList(
        args.cron_job_id.ToURN(),
        args.count,
        args.offset,
        with_state_and_context=True,
        token=token)
    return ApiListCronJobRunsResult(
        items=[ApiCronJobRun().InitFromApiFlow(f) for f in flows_result.items])


class ApiGetCronJobRunArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiGetCronJobRunArgs
  rdf_deps = [
      ApiCronJobId,
      ApiCronJobRunId,
  ]


class ApiGetCronJobRunHandler(api_call_handler_base.ApiCallHandler):
  """Renders given cron run.

  Only top-level flows can be targeted. Times returned in the response are micro
  seconds since epoch.
  """

  args_type = ApiGetCronJobRunArgs
  result_type = ApiCronJobRun

  def Handle(self, args, token=None):
    # Note: this is a legacy AFF4 implementation.
    flow_urn = args.run_id.ToURN(args.cron_job_id)
    flow_obj = aff4.FACTORY.Open(
        flow_urn, aff4_type=flow.GRRFlow, mode="r", token=token)
    f = api_plugins_flow.ApiFlow().InitFromAff4Object(
        flow_obj, with_state_and_context=True)

    return ApiCronJobRun().InitFromApiFlow(f)


class ApiCreateCronJobArgs(rdf_structs.RDFProtoStruct):
  """Arguments for CreateCronJob API call."""

  protobuf = cron_pb2.ApiCreateCronJobArgs
  rdf_deps = [
      rdfvalue.Duration,
      rdf_hunts.HuntRunnerArgs,
  ]

  def GetFlowArgsClass(self):
    if self.flow_name:
      flow_cls = registry.FlowRegistry.FlowClassByName(self.flow_name)

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

    flow_runner_args = rdf_flow_runner.FlowRunnerArgs(
        flow_name="CreateAndRunGenericHuntFlow")

    flow_args = rdf_hunts.CreateGenericHuntFlowArgs()
    flow_args.hunt_args.flow_args = args.flow_args
    flow_args.hunt_args.flow_runner_args.flow_name = args.flow_name
    flow_args.hunt_runner_args = args.hunt_runner_args
    flow_args.hunt_runner_args.hunt_name = "GenericHunt"

    cron_args = rdf_cronjobs.CreateCronJobFlowArgs(
        description=args.description,
        periodicity=args.periodicity,
        flow_runner_args=flow_runner_args,
        flow_args=flow_args,
        allow_overruns=args.allow_overruns,
        lifetime=args.lifetime)
    name = aff4_cronjobs.GetCronManager().CreateJob(
        cron_args=cron_args, disabled=True, token=token)

    fd = aff4_cronjobs.GetCronManager().ReadJob(name)

    return ApiCronJob().InitFromObject(fd)


class ApiForceRunCronJobArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiForceRunCronJobArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiForceRunCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Force-runs a given cron job."""

  args_type = ApiForceRunCronJobArgs

  def Handle(self, args, token=None):
    aff4_cronjobs.GetCronManager().RunOnce(
        names=[str(args.cron_job_id)], token=token, force=True)


class ApiModifyCronJobArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiModifyCronJobArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiModifyCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Modifies given cron job (changes its state to ENABLED/DISABLED)."""

  args_type = ApiModifyCronJobArgs
  result_type = ApiCronJob

  def Handle(self, args, token=None):

    cron_id = str(args.cron_job_id)
    if args.state == "ENABLED":
      aff4_cronjobs.GetCronManager().EnableJob(cron_id, token=token)
    elif args.state == "DISABLED":
      aff4_cronjobs.GetCronManager().DisableJob(cron_id, token=token)
    else:
      raise ValueError("Invalid cron job state: %s" % str(args.state))

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
    aff4_cronjobs.GetCronManager().DeleteJob(str(args.cron_job_id), token=token)
