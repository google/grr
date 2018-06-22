#!/usr/bin/env python
"""API handlers for dealing with cron jobs."""

from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import cronjobs as rdf_cronjobs
from grr.lib.rdfvalues import flows
from grr.lib.rdfvalues import objects as rdf_objects
from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import cron_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.aff4_objects import cronjobs as aff4_cronjobs
from grr.server.grr_response_server.gui import api_call_handler_base
from grr.server.grr_response_server.gui.api_plugins import flow as api_plugins_flow

from grr.server.grr_response_server.hunts import standard


class CronJobNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a cron job could not be found."""


class ApiCronJobId(rdfvalue.RDFString):
  """Class encapsulating cron job ids."""

  def ToURN(self):
    if not self._value:
      raise ValueError("Can't call ToURN() on an empty cron job id.")

    return aff4_cronjobs.CronManager.CRON_JOBS_PATH.Add(self._value)


class ApiCronJob(rdf_structs.RDFProtoStruct):
  """ApiCronJob is used when rendering responses.

  ApiCronJob is meant to be more lightweight than automatically generated AFF4
  representation. It's also meant to contain only the information needed by
  the UI and and to not expose implementation defails.
  """
  protobuf = cron_pb2.ApiCronJob
  rdf_deps = [
      ApiCronJobId,
      rdfvalue.Duration,
      flows.FlowRunnerArgs,
      rdfvalue.RDFDatetime,
      rdfvalue.RDFURN,
  ]

  def GetArgsClass(self):
    if self.flow_name:
      flow_cls = flow.GRRFlow.classes.get(self.flow_name)
      if flow_cls is None:
        raise ValueError(
            "Flow %s not known by this implementation." % self.flow_name)

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


class ApiListCronJobFlowsArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiListCronJobFlowsArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiListCronJobFlowsHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the given cron job's flows."""

  args_type = ApiListCronJobFlowsArgs
  result_type = api_plugins_flow.ApiListFlowsResult

  def Handle(self, args, token=None):
    return api_plugins_flow.ApiListFlowsHandler.BuildFlowList(
        args.cron_job_id.ToURN(), args.count, args.offset, token=token)


class ApiGetCronJobFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiGetCronJobFlowArgs
  rdf_deps = [
      ApiCronJobId,
      api_plugins_flow.ApiFlowId,
  ]


class ApiGetCronJobFlowHandler(api_call_handler_base.ApiCallHandler):
  """Renders given cron flow.

  Only top-level flows can be targeted. Times returned in the response are micro
  seconds since epoch.
  """

  args_type = ApiGetCronJobFlowArgs
  result_type = api_plugins_flow.ApiFlow

  def Handle(self, args, token=None):
    flow_urn = args.flow_id.ResolveCronJobFlowURN(args.cron_job_id)
    flow_obj = aff4.FACTORY.Open(
        flow_urn, aff4_type=flow.GRRFlow, mode="r", token=token)

    return api_plugins_flow.ApiFlow().InitFromAff4Object(
        flow_obj, with_state_and_context=True)


class ApiCreateCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Creates a new cron job."""

  args_type = ApiCronJob
  result_type = ApiCronJob

  def Handle(self, args, token=None):
    args.flow_args.hunt_runner_args.hunt_name = "GenericHunt"

    # TODO(user): The following should be asserted in a more elegant way.
    # Also, it's not clear whether cron job scheduling UI is used often enough
    # to justify its existence. We should check with opensource users whether
    # they find this feature useful and if not, deprecate it altogether.
    if args.flow_name != standard.CreateAndRunGenericHuntFlow.__name__:
      raise ValueError("Only CreateAndRunGenericHuntFlow flows are supported "
                       "here (got: %s)." % args.flow_name)

    # Clear all fields marked with HIDDEN, except for output_plugins - they are
    # marked HIDDEN, because we have a separate UI for them, not because they
    # shouldn't be shown to the user at all.
    #
    # TODO(user): Refactor the code to remove the HIDDEN label from
    # FlowRunnerArgs.output_plugins.
    args.flow_runner_args.ClearFieldsWithLabel(
        rdf_structs.SemanticDescriptor.Labels.HIDDEN,
        exceptions="output_plugins")
    if not args.flow_runner_args.flow_name:
      args.flow_runner_args.flow_name = args.flow_name

    cron_args = rdf_cronjobs.CreateCronJobFlowArgs(
        description=args.description,
        periodicity=args.periodicity,
        flow_runner_args=args.flow_runner_args,
        flow_args=args.flow_args,
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
