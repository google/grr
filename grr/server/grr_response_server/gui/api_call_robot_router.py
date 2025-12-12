#!/usr/bin/env python
"""Implementation of a router class that should be used by robot users."""

from typing import Optional

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import api_call_router_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import timeline_pb2
from grr_response_proto.api import client_pb2 as api_client_pb2
from grr_response_proto.api import flow_pb2 as api_flow_pb2
from grr_response_proto.api import timeline_pb2 as api_timeline_pb2
from grr_response_proto.api import vfs_pb2 as api_vfs_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import throttle
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.local import MITIGATION_FLOWS
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import metadata as api_metadata
from grr_response_server.gui.api_plugins import reflection as api_reflection
from grr_response_server.gui.api_plugins import timeline as api_timeline
from grr_response_server.gui.api_plugins import vfs as api_vfs


LABEL_NAME_PREFIX = "robotapi-"


class ApiRobotCreateFlowHandler(api_call_handler_base.ApiCallHandler):
  """CreateFlow handler for a robot router.

  This handler filters out all the passed parameters, leaving just the essential
  arguments: client id, flow name and the arguments. It then delegates
  the call to a standard ApiCreateFlowHandler.
  """

  proto_args_type = api_flow_pb2.ApiCreateFlowArgs
  proto_result_type = api_flow_pb2.ApiFlow

  def __init__(
      self,
      override_flow_name: str = None,
      override_flow_args: Optional[any_pb2.Any] = None,
  ) -> None:
    super().__init__()

    self.override_flow_name = override_flow_name
    self.override_flow_args = override_flow_args

  def Handle(
      self,
      args: api_flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow_pb2.ApiFlow:
    if not args.client_id:
      raise RuntimeError("Client id has to be specified.")

    if not args.flow.name:
      raise RuntimeError("Flow name is not specified.")

    delegate = api_flow.ApiCreateFlowHandler()
    # Note that runner_args are dropped. From all the arguments We use only
    # the flow name and the arguments.
    delegate_args = api_flow_pb2.ApiCreateFlowArgs(client_id=args.client_id)
    delegate_args.flow.name = self.override_flow_name or args.flow.name
    if self.override_flow_args:
      delegate_args.flow.args.CopyFrom(self.override_flow_args)
    else:
      delegate_args.flow.args.CopyFrom(args.flow.args)

    return delegate.Handle(delegate_args, context=context)


class ApiRobotReturnDuplicateFlowHandler(api_call_handler_base.ApiCallHandler):
  """CreateFlow handler for cases when similar flow did run recently.

  This handler is used when throttler signals that a similar flow has already
  executed within min_interval_between_duplicate_flows time. In this case
  we just return a descriptor of a previously executed flow.
  """

  proto_args_type = api_flow_pb2.ApiCreateFlowArgs
  proto_result_type = api_flow_pb2.ApiFlow

  def __init__(self, flow_id: str):
    super().__init__()

    if not flow_id:
      raise ValueError("flow_id can't be empty.")
    self.flow_id = flow_id

  def Handle(
      self,
      args: api_flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow_pb2.ApiFlow:
    return api_flow.ApiGetFlowHandler().Handle(
        api_flow_pb2.ApiGetFlowArgs(
            client_id=args.client_id, flow_id=self.flow_id
        ),
        context=context,
    )


class ApiCallRobotRouter(api_call_router.ApiCallRouterStub):
  """Restricted router to be used by robots."""

  proto_params_type = api_call_router_pb2.ApiCallRobotRouterParams

  def __init__(
      self,
      params: Optional[api_call_router_pb2.ApiCallRobotRouterParams] = None,
      delegate: Optional[api_call_router.ApiCallRouter] = None,
  ):
    super().__init__(params=params)

    if params is None:
      raise ValueError("Router params are mandatory for ApiCallRobotRouter.")
    self.params: api_call_router_pb2.ApiCallRobotRouterParams = (
        params or api_call_router_pb2.ApiCallRobotRouterParams()
    )

    if not delegate:
      delegate = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self.delegate = delegate

  @property
  def allowed_file_finder_flow_names(self):
    result = [file_finder.FileFinder.__name__]
    if self.params.file_finder_flow.file_finder_flow_name:
      result.append(self.params.file_finder_flow.file_finder_flow_name)

    return result

  @property
  def allowed_artifact_collector_flow_names(self):
    result = [collectors.ArtifactCollectorFlow.__name__]

    if self.params.artifact_collector_flow.artifact_collector_flow_name:
      result.append(
          self.params.artifact_collector_flow.artifact_collector_flow_name
      )

    return result

  @property
  def effective_file_finder_flow_name(self):
    return (
        self.params.file_finder_flow.file_finder_flow_name
        or file_finder.FileFinder.__name__
    )

  @property
  def effective_artifact_collector_flow_name(self):
    return (
        self.params.artifact_collector_flow.artifact_collector_flow_name
        or collectors.ArtifactCollectorFlow.__name__
    )

  def SearchClients(
      self,
      args: api_client_pb2.ApiSearchClientsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    if not self.params.search_clients.enabled:
      raise access_control.UnauthorizedAccess(
          "SearchClients is not allowed by the configuration."
      )

    return api_client.ApiSearchClientsHandler()

  def _CheckFileFinderArgs(
      self,
      flow_args: any_pb2.Any,
  ):
    unpacked = flows_pb2.FileFinderArgs()
    unpacked.ParseFromString(flow_args.value)
    flow_args = unpacked

    ffparams = self.params.file_finder_flow

    if not ffparams.enabled:
      raise access_control.UnauthorizedAccess(
          "FileFinder flow is not allowed by the configuration."
      )

    if not ffparams.globs_allowed:
      for path in flow_args.paths:
        str_path = str(path)
        if "*" in str_path:
          raise access_control.UnauthorizedAccess(
              "Globs are not allowed by the configuration."
          )

    if not ffparams.interpolations_allowed:
      for path in flow_args.paths:
        str_path = str(path)
        if "%%" in str_path:
          raise access_control.UnauthorizedAccess(
              "Interpolations are not allowed by the configuration."
          )

  def _GetFileFinderThrottler(self):
    ffparams = self.params.file_finder_flow

    return throttle.FlowThrottler(
        daily_req_limit=ffparams.max_flows_per_client_daily,
        dup_interval=rdfvalue.Duration.From(
            ffparams.min_interval_between_duplicate_flows, rdfvalue.SECONDS
        ),
        flow_args_type=flows_pb2.FileFinderArgs,
    )

  def _CheckArtifactCollectorFlowArgs(self, flow_args: any_pb2.Any):
    unpacked = flows_pb2.ArtifactCollectorFlowArgs()
    unpacked.ParseFromString(flow_args.value)
    flow_args = unpacked

    if not self.params.artifact_collector_flow.enabled:
      raise access_control.UnauthorizedAccess(
          "ArtifactCollectorFlow flow is not allowed by the configuration"
      )

    for name in flow_args.artifact_list:
      if name not in self.params.artifact_collector_flow.allow_artifacts:
        raise access_control.UnauthorizedAccess(
            "Artifact %s is not whitelisted." % name
        )

  def _GetArtifactCollectorFlowThrottler(self):
    acparams = self.params.artifact_collector_flow

    return throttle.FlowThrottler(
        daily_req_limit=acparams.max_flows_per_client_daily,
        dup_interval=rdfvalue.Duration.From(
            acparams.min_interval_between_duplicate_flows, rdfvalue.SECONDS
        ),
        flow_args_type=flows_pb2.ArtifactCollectorFlowArgs,
    )

  def _GetTimelineFlowThrottler(self):
    tfparams = self.params.timeline_flow

    return throttle.FlowThrottler(
        daily_req_limit=tfparams.max_flows_per_client_daily,
        dup_interval=rdfvalue.Duration.From(
            tfparams.min_interval_between_duplicate_flows, rdfvalue.SECONDS
        ),
        flow_args_type=timeline_pb2.TimelineArgs,
    )

  def _CheckMitigationActionAccess(self):
    mitigation_actions_params = self.params.mitigation_actions

    if not mitigation_actions_params.enabled:
      raise access_control.UnauthorizedAccess(
          "Mitigation actions are not allowed by the configuration."
      )

  def _CheckFlowRobotId(self, client_id, flow_id, context=None):
    # We don't use robot ids in REL_DB, but simply check that flow's creator is
    # equal to the user making the request.
    # TODO(user): get rid of robot id logic as soon as AFF4 is gone.
    flow_obj = data_store.REL_DB.ReadFlowObject(str(client_id), str(flow_id))
    if flow_obj.creator != context.username:
      raise access_control.UnauthorizedAccess(
          "Flow %s (client %s) has to be created "
          "by the user making the request." % (flow_id, client_id)
      )
    return flow_obj.flow_class_name

  def _FixFileFinderArgs(
      self, source_args: any_pb2.Any
  ) -> flows_pb2.FileFinderArgs:
    unpacked = flows_pb2.FileFinderArgs()
    unpacked.ParseFromString(source_args.value)
    source_args = unpacked

    ffparams = self.params.file_finder_flow
    if not ffparams.max_file_size:
      return

    new_args = flows_pb2.FileFinderArgs()
    new_args.CopyFrom(source_args)
    if new_args.action.action_type == flows_pb2.FileFinderAction.Action.HASH:
      ha = new_args.action.hash
      ha.oversized_file_policy = ha.OversizedFilePolicy.SKIP
      ha.max_size = ffparams.max_file_size
    elif (
        new_args.action.action_type
        == flows_pb2.FileFinderAction.Action.DOWNLOAD
    ):
      da = new_args.action.download
      da.oversized_file_policy = da.OversizedFilePolicy.SKIP
      da.max_size = ffparams.max_file_size
    elif new_args.action.action_type == flows_pb2.FileFinderAction.Action.STAT:
      pass
    else:
      raise ValueError("Unknown action type: %s" % new_args.action)

    return new_args

  def CreateFlow(
      self,
      args: api_flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> ApiRobotCreateFlowHandler:
    if not args.client_id:
      raise ValueError("client_id must be provided")

    if args.flow.name in self.allowed_file_finder_flow_names:
      self._CheckFileFinderArgs(args.flow.args)
      override_flow_name = self.effective_file_finder_flow_name
      if file_finder_args := self._FixFileFinderArgs(args.flow.args):
        override_flow_args = any_pb2.Any()
        override_flow_args.Pack(file_finder_args)
      else:
        override_flow_args = None
      throttler = self._GetFileFinderThrottler()
    elif args.flow.name in self.allowed_artifact_collector_flow_names:
      self._CheckArtifactCollectorFlowArgs(args.flow.args)
      override_flow_name = self.effective_artifact_collector_flow_name
      override_flow_args = None
      throttler = self._GetArtifactCollectorFlowThrottler()
    elif args.flow.name == "TimelineFlow" and self.params.timeline_flow.enabled:
      override_flow_name = "TimelineFlow"
      override_flow_args = None
      throttler = self._GetTimelineFlowThrottler()
    elif args.flow.name in [flow.__name__ for flow in MITIGATION_FLOWS]:
      self._CheckMitigationActionAccess()
      override_flow_name = args.flow.name
      override_flow_args = args.flow.args
      throttler = throttle.FlowThrottler()
    else:
      raise access_control.UnauthorizedAccess(
          "Creating arbitrary flows (%s) is not allowed." % args.flow.name
      )

    try:
      throttler.EnforceLimits(
          args.client_id,
          context.username,
          args.flow.name,
          args.flow.args,
      )
    except throttle.DuplicateFlowError as e:
      # If a similar flow did run recently, just return it.
      return ApiRobotReturnDuplicateFlowHandler(flow_id=e.flow_id)
    except throttle.DailyFlowRequestLimitExceededError as e:
      # Raise ResourceExhaustedError so that the user gets an HTTP 429.
      raise api_call_handler_base.ResourceExhaustedError(str(e))

    return ApiRobotCreateFlowHandler(
        override_flow_name=override_flow_name,
        override_flow_args=override_flow_args,
    )

  def GetFlow(
      self,
      args: api_flow_pb2.ApiGetFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiGetFlowHandler:
    if not self.params.get_flow.enabled:
      raise access_control.UnauthorizedAccess(
          "GetFlow is not allowed by the configuration."
      )

    self._CheckFlowRobotId(args.client_id, args.flow_id, context=context)

    return api_flow.ApiGetFlowHandler()

  def ListFlowResults(
      self,
      args: api_flow_pb2.ApiListFlowResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListFlowResultsHandler:
    if not self.params.list_flow_results.enabled:
      raise access_control.UnauthorizedAccess(
          "ListFlowResults is not allowed by the configuration."
      )

    self._CheckFlowRobotId(args.client_id, args.flow_id, context=context)

    return api_flow.ApiListFlowResultsHandler()

  def ListFlowLogs(
      self,
      args: api_flow_pb2.ApiListFlowLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiListFlowLogsHandler:
    if not self.params.list_flow_logs.enabled:
      raise access_control.UnauthorizedAccess(
          "ListFlowLogs is not allowed by the configuration."
      )

    self._CheckFlowRobotId(args.client_id, args.flow_id, context=context)

    return api_flow.ApiListFlowLogsHandler()

  def GetFlowFilesArchive(
      self,
      args: api_flow_pb2.ApiGetFlowFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_flow.ApiGetFlowFilesArchiveHandler:
    if not self.params.get_flow_files_archive.enabled:
      raise access_control.UnauthorizedAccess(
          "GetFlowFilesArchive is not allowed by the configuration."
      )

    flow_name = self._CheckFlowRobotId(
        args.client_id, args.flow_id, context=context
    )

    options = self.params.get_flow_files_archive

    if (
        options.skip_glob_checks_for_artifact_collector
        and flow_name == self.effective_artifact_collector_flow_name
    ):
      return api_flow.ApiGetFlowFilesArchiveHandler()
    else:
      return api_flow.ApiGetFlowFilesArchiveHandler(
          exclude_path_globs=[
              rdf_paths.GlobExpression(ep) for ep in options.exclude_path_globs
          ],
          include_only_path_globs=[
              rdf_paths.GlobExpression(ip)
              for ip in options.include_only_path_globs
          ],
      )

  def GetCollectedTimeline(
      self,
      args: api_timeline_pb2.ApiGetCollectedTimelineArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_timeline.ApiGetCollectedTimelineHandler:
    """Exports results of a timeline flow to the specific format."""
    if not self.params.get_collected_timeline.enabled:
      raise access_control.UnauthorizedAccess(
          "GetCollectedTimeline is not allowed by the configuration."
      )

    self._CheckFlowRobotId(args.client_id, args.flow_id, context=context)

    return api_timeline.ApiGetCollectedTimelineHandler()

  def GetFileBlob(
      self,
      args: api_vfs_pb2.ApiGetFileBlobArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_vfs.ApiGetFileBlobHandler:
    """Get byte contents of a VFS file on a given client."""
    if not self.params.get_file_blob.enabled:
      raise access_control.UnauthorizedAccess(
          "GetFileBlob is not allowed by the configuration."
      )

    return api_vfs.ApiGetFileBlobHandler()

  # Reflection methods.
  # ==================
  #
  # NOTE: Only the ListApiMethods is enabled as it may be used by client
  # API libraries.
  def ListApiMethods(self, args, context=None):
    return api_reflection.ApiListApiMethodsHandler(self)

  # Metadata methods.
  def GetOpenApiDescription(
      self,
      args: None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_metadata.ApiGetOpenApiDescriptionHandler:
    del args, context  # Unused.
    return api_metadata.ApiGetOpenApiDescriptionHandler(self)
