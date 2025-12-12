#!/usr/bin/env python
"""API handlers for dealing with cron jobs."""

from typing import Optional

from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_proto import flows_pb2
from grr_response_proto.api import cron_pb2
from grr_response_server import cronjobs
from grr_response_server.databases import db
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.gui import mig_api_call_handler_utils
from grr_response_server.models import protobuf_utils as models_utils
from grr_response_server.rdfvalues import mig_cronjobs


def InitApiCronJobFromCronJob(
    cron_job: flows_pb2.CronJob,
) -> cron_pb2.ApiCronJob:
  """Initializes ApiCronJob from CronJob."""

  api_cron_job = cron_pb2.ApiCronJob()
  models_utils.CopyAttr(cron_job, api_cron_job, "cron_job_id")
  if cron_job.HasField("args"):
    api_cron_job.args.CopyFrom(cron_job.args)
  models_utils.CopyAttr(cron_job, api_cron_job, "current_run_id")
  models_utils.CopyAttr(cron_job, api_cron_job, "description")
  models_utils.CopyAttr(cron_job, api_cron_job, "enabled")
  models_utils.CopyAttr(cron_job, api_cron_job, "last_run_status")
  models_utils.CopyAttr(cron_job, api_cron_job, "last_run_time")
  models_utils.CopyAttr(cron_job, api_cron_job, "frequency")
  models_utils.CopyAttr(cron_job, api_cron_job, "lifetime")
  models_utils.CopyAttr(cron_job, api_cron_job, "allow_overruns")

  api_cron_job.is_failing = cron_job.last_run_status in [
      flows_pb2.CronJobRun.CronJobRunStatus.ERROR,
      flows_pb2.CronJobRun.CronJobRunStatus.LIFETIME_EXCEEDED,
  ]

  if cron_job.forced_run_requested:
    api_cron_job.forced_run_requested = True

  rdf_state = mig_protodict.ToRDFAttributedDict(cron_job.state)
  state_dict = rdf_state.ToDict()
  if state_dict:
    state = api_call_handler_utils.ApiDataObject()
    state.InitFromDataObject(state_dict)
    api_cron_job.state.CopyFrom(
        mig_api_call_handler_utils.ToProtoApiDataObject(state)
    )
  return api_cron_job


def CreateCronJobArgsFromApiCreateCronJobArgs(
    api_create: cron_pb2.ApiCreateCronJobArgs,
) -> flows_pb2.CreateCronJobArgs:
  """Creates a CreateCronJobArgs from an ApiCronJob."""
  create_args = flows_pb2.CreateCronJobArgs()
  models_utils.CopyAttr(api_create, create_args, "flow_name")
  if api_create.HasField("flow_args"):
    create_args.flow_args.CopyFrom(api_create.flow_args)
  if api_create.HasField("hunt_runner_args"):
    create_args.hunt_runner_args.CopyFrom(api_create.hunt_runner_args)
  models_utils.CopyAttr(api_create, create_args, "description")
  models_utils.CopyAttr(api_create, create_args, "periodicity", "frequency")
  models_utils.CopyAttr(api_create, create_args, "lifetime")
  models_utils.CopyAttr(api_create, create_args, "allow_overruns")

  return create_args


class CronJobNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a cron job could not be found."""


class CronJobRunNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a cron job run could not be found."""


def InitApiCronJobRunFromRunObject(
    run: flows_pb2.CronJobRun,
) -> cron_pb2.ApiCronJobRun:
  api_run_job = cron_pb2.ApiCronJobRun()
  models_utils.CopyAttr(run, api_run_job, "run_id")
  models_utils.CopyAttr(run, api_run_job, "cron_job_id")
  models_utils.CopyAttr(run, api_run_job, "started_at")
  models_utils.CopyAttr(run, api_run_job, "finished_at")
  models_utils.CopyAttr(run, api_run_job, "status")
  models_utils.CopyAttr(run, api_run_job, "log_message")
  models_utils.CopyAttr(run, api_run_job, "backtrace")
  return api_run_job


class ApiListCronJobsHandler(api_call_handler_base.ApiCallHandler):
  """Lists flows launched on a given client."""

  proto_args_type = cron_pb2.ApiListCronJobsArgs
  proto_result_type = cron_pb2.ApiListCronJobsResult

  def Handle(
      self,
      args: cron_pb2.ApiListCronJobsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> cron_pb2.ApiListCronJobsResult:
    if not args.count:
      stop = None
    else:
      stop = args.offset + args.count

    cron_manager = cronjobs.CronManager()
    all_jobs = list(cron_manager.ReadJobs())
    all_jobs.sort(
        key=lambda job: (getattr(job, "cron_job_id", None) or job.urn)
    )
    all_jobs = [mig_cronjobs.ToProtoCronJob(job) for job in all_jobs]
    cron_jobs = all_jobs[args.offset : stop]

    items = [InitApiCronJobFromCronJob(cron_job) for cron_job in cron_jobs]

    return cron_pb2.ApiListCronJobsResult(
        items=items, total_count=len(all_jobs)
    )


class ApiGetCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves a specific cron job."""

  proto_args_type = cron_pb2.ApiGetCronJobArgs
  proto_result_type = cron_pb2.ApiCronJob

  def Handle(
      self,
      args: cron_pb2.ApiGetCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> cron_pb2.ApiCronJob:
    try:
      cron_job = cronjobs.CronManager().ReadJob(str(args.cron_job_id))
      cron_job = mig_cronjobs.ToProtoCronJob(cron_job)
      return InitApiCronJobFromCronJob(cron_job)
    except db.UnknownCronJobError as e:
      raise CronJobNotFoundError(
          "Cron job with id %s could not be found" % args.cron_job_id
      ) from e


class ApiListCronJobRunsHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves the given cron job's runs."""

  proto_args_type = cron_pb2.ApiListCronJobRunsArgs
  proto_result_type = cron_pb2.ApiListCronJobRunsResult

  def Handle(
      self,
      args: cron_pb2.ApiListCronJobRunsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> cron_pb2.ApiListCronJobRunsResult:
    runs = cronjobs.CronManager().ReadJobRuns(args.cron_job_id)
    runs = [mig_cronjobs.ToProtoCronJobRun(run) for run in runs]
    start = args.offset
    if args.count:
      end = args.offset + args.count
    else:
      end = db.MAX_COUNT
    return cron_pb2.ApiListCronJobRunsResult(
        items=[InitApiCronJobRunFromRunObject(run) for run in runs[start:end]]
    )


class ApiGetCronJobRunHandler(api_call_handler_base.ApiCallHandler):
  """Renders given cron run."""

  proto_args_type = cron_pb2.ApiGetCronJobRunArgs
  proto_result_type = cron_pb2.ApiCronJobRun

  def Handle(
      self,
      args: cron_pb2.ApiGetCronJobRunArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> cron_pb2.ApiCronJobRun:
    run = cronjobs.CronManager().ReadJobRun(args.cron_job_id, args.run_id)
    if not run:
      raise CronJobRunNotFoundError(
          "Cron job run with id %s could not be found" % args.run_id
      )
    run = mig_cronjobs.ToProtoCronJobRun(run)
    return InitApiCronJobRunFromRunObject(run)


class ApiCreateCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Creates a new cron job."""

  proto_args_type = cron_pb2.ApiCreateCronJobArgs
  proto_result_type = cron_pb2.ApiCronJob

  def Handle(
      self,
      source_args: cron_pb2.ApiCreateCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> cron_pb2.ApiCronJob:
    # Make sure we don't modify source arguments.
    args = cron_pb2.ApiCreateCronJobArgs()
    args.CopyFrom(source_args)
    args.hunt_runner_args.ClearField("original_object")

    cron_manager = cronjobs.CronManager()
    cron_args = CreateCronJobArgsFromApiCreateCronJobArgs(args)
    cron_args = mig_cronjobs.ToRDFCreateCronJobArgs(cron_args)
    cron_job_id = cron_manager.CreateJob(cron_args=cron_args, enabled=False)

    cron_obj = cron_manager.ReadJob(cron_job_id)
    cron_obj = mig_cronjobs.ToProtoCronJob(cron_obj)
    return InitApiCronJobFromCronJob(cron_obj)


class ApiForceRunCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Force-runs a given cron job."""

  proto_args_type = cron_pb2.ApiForceRunCronJobArgs

  def Handle(
      self,
      args: cron_pb2.ApiForceRunCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    cronjobs.CronManager().RequestForcedRun(args.cron_job_id)


class ApiModifyCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Enables or disables a given cron job."""

  proto_args_type = cron_pb2.ApiModifyCronJobArgs
  proto_result_type = cron_pb2.ApiCronJob

  def Handle(
      self,
      args: cron_pb2.ApiModifyCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> cron_pb2.ApiCronJob:
    cron_id = args.cron_job_id
    if args.enabled:
      cronjobs.CronManager().EnableJob(cron_id)
    else:
      cronjobs.CronManager().DisableJob(cron_id)

    cron_job_obj = cronjobs.CronManager().ReadJob(cron_id)
    cron_job_obj = mig_cronjobs.ToProtoCronJob(cron_job_obj)
    return InitApiCronJobFromCronJob(cron_job_obj)


class ApiDeleteCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Deletes a given cron job."""

  proto_args_type = cron_pb2.ApiDeleteCronJobArgs

  def Handle(
      self,
      args: cron_pb2.ApiDeleteCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    cronjobs.CronManager().DeleteJob(args.cron_job_id)
