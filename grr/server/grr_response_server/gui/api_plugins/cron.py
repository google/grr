#!/usr/bin/env python
"""API handlers for dealing with cron jobs."""

from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto.api import cron_pb2
from grr_response_server import cronjobs
from grr_response_server.databases import db
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.gui import mig_api_call_handler_utils
from grr_response_server.models import protobuf_utils as models_utils
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import hunts as rdf_hunts
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


class CronJobNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a cron job could not be found."""


class CronJobRunNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a cron job run could not be found."""


class ApiCronJobId(rdfvalue.RDFString):
  """Class encapsulating cron job ids."""


class ApiCronJobRunId(rdfvalue.RDFString):
  """Class encapsulating cron job run ids."""


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
      rdfvalue.DurationSeconds,
      rdfvalue.RDFDatetime,
  ]

  def GetArgsClass(self):
    if self.flow_name:
      flow_cls = registry.FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


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


class ApiCronJobRun(rdf_structs.RDFProtoStruct):
  """ApiCronJobRun represents individual cron job runs."""

  protobuf = cron_pb2.ApiCronJobRun
  rdf_deps = [
      ApiCronJobId,
      ApiCronJobRunId,
      rdfvalue.RDFDatetime,
  ]


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


class ApiGetCronJobArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiGetCronJobArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiGetCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Retrieves a specific cron job."""

  args_type = ApiGetCronJobArgs
  result_type = ApiCronJob
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


class ApiCreateCronJobArgs(rdf_structs.RDFProtoStruct):
  """Arguments for CreateCronJob API call."""

  protobuf = cron_pb2.ApiCreateCronJobArgs
  rdf_deps = [
      rdfvalue.DurationSeconds,
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

    # Clear all fields marked with HIDDEN.
    args = ToRDFApiCreateCronJobArgs(args)
    args.flow_args.ClearFieldsWithLabel(
        rdf_structs.SemanticDescriptor.Labels.HIDDEN
    )
    # Clear all fields marked with HIDDEN, except for output_plugins - they are
    # marked HIDDEN, because we have a separate UI for them, not because they
    # shouldn't be shown to the user at all.
    #
    # TODO(user): Refactor the code to remove the HIDDEN label from
    # FlowRunnerArgs.output_plugins.
    args.hunt_runner_args.ClearFieldsWithLabel(
        rdf_structs.SemanticDescriptor.Labels.HIDDEN,
        exceptions="output_plugins",
    )

    cron_manager = cronjobs.CronManager()
    cron_args = rdf_cronjobs.CreateCronJobArgs.FromApiCreateCronJobArgs(args)
    cron_job_id = cron_manager.CreateJob(cron_args=cron_args, enabled=False)

    cron_obj = cron_manager.ReadJob(cron_job_id)
    cron_obj = mig_cronjobs.ToProtoCronJob(cron_obj)
    return InitApiCronJobFromCronJob(cron_obj)


class ApiForceRunCronJobArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiForceRunCronJobArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiForceRunCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Force-runs a given cron job."""

  args_type = ApiForceRunCronJobArgs
  proto_args_type = cron_pb2.ApiForceRunCronJobArgs

  def Handle(
      self,
      args: cron_pb2.ApiForceRunCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    cronjobs.CronManager().RequestForcedRun(args.cron_job_id)


class ApiModifyCronJobArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiModifyCronJobArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiModifyCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Enables or disables a given cron job."""

  args_type = ApiModifyCronJobArgs
  result_type = ApiCronJob
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


class ApiDeleteCronJobArgs(rdf_structs.RDFProtoStruct):
  protobuf = cron_pb2.ApiDeleteCronJobArgs
  rdf_deps = [
      ApiCronJobId,
  ]


class ApiDeleteCronJobHandler(api_call_handler_base.ApiCallHandler):
  """Deletes a given cron job."""

  args_type = ApiDeleteCronJobArgs
  proto_args_type = cron_pb2.ApiDeleteCronJobArgs

  def Handle(
      self,
      args: cron_pb2.ApiDeleteCronJobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> None:
    cronjobs.CronManager().DeleteJob(args.cron_job_id)


# Copy of migration function to avoid circular dependency.
def ToRDFApiCreateCronJobArgs(
    proto: cron_pb2.ApiCreateCronJobArgs,
) -> ApiCreateCronJobArgs:
  return ApiCreateCronJobArgs.FromSerializedBytes(proto.SerializeToString())
