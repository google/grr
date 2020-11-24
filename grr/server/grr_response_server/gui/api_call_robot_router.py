#!/usr/bin/env python
# Lint as: python3
"""Implementation of a router class that should be used by robot users."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from typing import Optional

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import paths as rdf_paths

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import api_call_router_pb2
from grr_response_server import access_control

from grr_response_server import data_store
from grr_response_server import throttle
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import file_finder

from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import metadata as api_metadata
from grr_response_server.gui.api_plugins import reflection as api_reflection


class RobotRouterSearchClientsParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.RobotRouterSearchClientsParams


class RobotRouterFileFinderFlowParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.RobotRouterFileFinderFlowParams
  rdf_deps = [
      rdfvalue.DurationSeconds,
  ]


class RobotRouterArtifactCollectorFlowParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.RobotRouterArtifactCollectorFlowParams
  rdf_deps = [
      rdfvalue.DurationSeconds,
  ]


class RobotRouterGetFlowParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.RobotRouterGetFlowParams


class RobotRouterListFlowResultsParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.RobotRouterListFlowResultsParams


class RobotRouterListFlowLogsParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.RobotRouterListFlowLogsParams


class RobotRouterGetFlowFilesArchiveParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.RobotRouterGetFlowFilesArchiveParams
  rdf_deps = [
      rdf_paths.GlobExpression,
  ]


class ApiCallRobotRouterParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.ApiCallRobotRouterParams
  rdf_deps = [
      RobotRouterArtifactCollectorFlowParams,
      RobotRouterFileFinderFlowParams,
      RobotRouterGetFlowFilesArchiveParams,
      RobotRouterGetFlowParams,
      RobotRouterListFlowLogsParams,
      RobotRouterListFlowResultsParams,
      RobotRouterSearchClientsParams,
  ]


LABEL_NAME_PREFIX = "robotapi-"


class ApiRobotCreateFlowHandler(api_call_handler_base.ApiCallHandler):
  """CreateFlow handler for a robot router.

  This handler filters out all the passed parameters, leaving just the essential
  arguments: client id, flow name and the arguments. It then delegates
  the call to a standard ApiCreateFlowHandler.
  """

  args_type = api_flow.ApiCreateFlowArgs
  result_type = api_flow.ApiFlow

  def __init__(self,
               override_flow_name=None,
               override_flow_args=None):
    super().__init__()

    self.override_flow_name = override_flow_name
    self.override_flow_args = override_flow_args

  def Handle(self, args, context=None):
    if not args.client_id:
      raise RuntimeError("Client id has to be specified.")

    if not args.flow.name:
      raise RuntimeError("Flow name is not specified.")

    delegate = api_flow.ApiCreateFlowHandler()
    # Note that runner_args are dropped. From all the arguments We use only
    # the flow name and the arguments.
    delegate_args = api_flow.ApiCreateFlowArgs(client_id=args.client_id)
    delegate_args.flow.name = self.override_flow_name or args.flow.name
    delegate_args.flow.args = self.override_flow_args or args.flow.args
    return delegate.Handle(delegate_args, context=context)


class ApiRobotReturnDuplicateFlowHandler(api_call_handler_base.ApiCallHandler):
  """CreateFlow handler for cases when similar flow did run recently.

  This handler is used when throttler signals that a similar flow has already
  executed within min_interval_between_duplicate_flows time. In this case
  we just return a descriptor of a previously executed flow.
  """

  args_type = api_flow.ApiCreateFlowArgs
  result_type = api_flow.ApiFlow

  def __init__(self, flow_id):
    super().__init__()

    if not flow_id:
      raise ValueError("flow_id can't be empty.")
    self.flow_id = flow_id

  def Handle(self, args, context=None):
    return api_flow.ApiGetFlowHandler().Handle(
        api_flow.ApiGetFlowArgs(client_id=args.client_id, flow_id=self.flow_id),
        context=context)


class ApiCallRobotRouter(api_call_router.ApiCallRouterStub):
  """Restricted router to be used by robots."""

  params_type = ApiCallRobotRouterParams

  def __init__(self, params=None, delegate=None):
    super().__init__(params=params)

    if params is None:
      raise ValueError("Router params are mandatory for ApiCallRobotRouter.")
    self.params = params or self.__class__.params_type()

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
          self.params.artifact_collector_flow.artifact_collector_flow_name)

    return result

  @property
  def effective_file_finder_flow_name(self):
    return (self.params.file_finder_flow.file_finder_flow_name or
            file_finder.FileFinder.__name__)

  @property
  def effective_artifact_collector_flow_name(self):
    return (self.params.artifact_collector_flow.artifact_collector_flow_name or
            collectors.ArtifactCollectorFlow.__name__)

  def SearchClients(self, args, context=None):
    if not self.params.search_clients.enabled:
      raise access_control.UnauthorizedAccess(
          "SearchClients is not allowed by the configuration.")

    return api_client.ApiSearchClientsHandler()

  def _CheckFileFinderArgs(self, flow_args, context=None):
    ffparams = self.params.file_finder_flow

    if not ffparams.enabled:
      raise access_control.UnauthorizedAccess(
          "FileFinder flow is not allowed by the configuration.")

    if not ffparams.globs_allowed:
      for path in flow_args.paths:
        str_path = str(path)
        if "*" in str_path:
          raise access_control.UnauthorizedAccess(
              "Globs are not allowed by the configuration.")

    if not ffparams.interpolations_allowed:
      for path in flow_args.paths:
        str_path = str(path)
        if "%%" in str_path:
          raise access_control.UnauthorizedAccess(
              "Interpolations are not allowed by the configuration.")

  def _GetFileFinderThrottler(self):
    ffparams = self.params.file_finder_flow

    return throttle.FlowThrottler(
        daily_req_limit=ffparams.max_flows_per_client_daily,
        dup_interval=rdfvalue.Duration(
            ffparams.min_interval_between_duplicate_flows))

  def _CheckArtifactCollectorFlowArgs(self, flow_args):
    if not self.params.artifact_collector_flow.enabled:
      raise access_control.UnauthorizedAccess(
          "ArtifactCollectorFlow flow is not allowed by the configuration")

    for name in flow_args.artifact_list:
      if name not in self.params.artifact_collector_flow.allow_artifacts:
        raise access_control.UnauthorizedAccess(
            "Artifact %s is not whitelisted." % name)

  def _GetArtifactCollectorFlowThrottler(self):
    acparams = self.params.artifact_collector_flow

    return throttle.FlowThrottler(
        daily_req_limit=acparams.max_flows_per_client_daily,
        dup_interval=rdfvalue.Duration(
            acparams.min_interval_between_duplicate_flows))

  def _CheckFlowRobotId(self, client_id, flow_id, context=None):
    # We don't use robot ids in REL_DB, but simply check that flow's creator is
    # equal to the user making the request.
    # TODO(user): get rid of robot id logic as soon as AFF4 is gone.
    flow_obj = data_store.REL_DB.ReadFlowObject(str(client_id), str(flow_id))
    if flow_obj.creator != context.username:
      raise access_control.UnauthorizedAccess(
          "Flow %s (client %s) has to be created "
          "by the user making the request." % (flow_id, client_id))
    return flow_obj.flow_class_name

  def _FixFileFinderArgs(self, source_args):
    ffparams = self.params.file_finder_flow
    if not ffparams.max_file_size:
      return

    new_args = source_args.Copy()
    if new_args.action.action_type == new_args.action.Action.HASH:
      ha = new_args.action.hash
      ha.oversized_file_policy = ha.OversizedFilePolicy.SKIP
      ha.max_size = ffparams.max_file_size
    elif new_args.action.action_type == new_args.action.Action.DOWNLOAD:
      da = new_args.action.download
      da.oversized_file_policy = da.OversizedFilePolicy.SKIP
      da.max_size = ffparams.max_file_size
    elif new_args.action.action_type == new_args.action.Action.STAT:
      pass
    else:
      raise ValueError("Unknown action type: %s" % new_args.action)

    return new_args

  def CreateFlow(self, args, context=None):
    if not args.client_id:
      raise ValueError("client_id must be provided")

    if args.flow.name in self.allowed_file_finder_flow_names:
      self._CheckFileFinderArgs(args.flow.args)
      override_flow_name = self.effective_file_finder_flow_name
      override_flow_args = self._FixFileFinderArgs(args.flow.args)
      throttler = self._GetFileFinderThrottler()
    elif args.flow.name in self.allowed_artifact_collector_flow_names:
      self._CheckArtifactCollectorFlowArgs(args.flow.args)
      override_flow_name = self.effective_artifact_collector_flow_name
      override_flow_args = None
      throttler = self._GetArtifactCollectorFlowThrottler()
    else:
      raise access_control.UnauthorizedAccess(
          "Creating arbitrary flows (%s) is not allowed." % args.flow.name)

    try:
      throttler.EnforceLimits(args.client_id.ToString(), context.username,
                              args.flow.name, args.flow.args)
    except throttle.DuplicateFlowError as e:
      # If a similar flow did run recently, just return it.
      return ApiRobotReturnDuplicateFlowHandler(flow_id=e.flow_id)
    except throttle.DailyFlowRequestLimitExceededError as e:
      # Raise UnauthorizedAccess so that the user gets an HTTP 403.
      raise access_control.UnauthorizedAccess(str(e))

    return ApiRobotCreateFlowHandler(
        override_flow_name=override_flow_name,
        override_flow_args=override_flow_args)

  def GetFlow(self, args, context=None):
    if not self.params.get_flow.enabled:
      raise access_control.UnauthorizedAccess(
          "GetFlow is not allowed by the configuration.")

    self._CheckFlowRobotId(args.client_id, args.flow_id, context=context)

    return api_flow.ApiGetFlowHandler()

  def ListFlowResults(self, args, context=None):
    if not self.params.list_flow_results.enabled:
      raise access_control.UnauthorizedAccess(
          "ListFlowResults is not allowed by the configuration.")

    self._CheckFlowRobotId(args.client_id, args.flow_id, context=context)

    return api_flow.ApiListFlowResultsHandler()

  def ListFlowLogs(self, args, context=None):
    if not self.params.list_flow_logs.enabled:
      raise access_control.UnauthorizedAccess(
          "ListFlowLogs is not allowed by the configuration.")

    self._CheckFlowRobotId(args.client_id, args.flow_id, context=context)

    return api_flow.ApiListFlowLogsHandler()

  def GetFlowFilesArchive(self, args, context=None):
    if not self.params.get_flow_files_archive.enabled:
      raise access_control.UnauthorizedAccess(
          "GetFlowFilesArchive is not allowed by the configuration.")

    flow_name = self._CheckFlowRobotId(
        args.client_id, args.flow_id, context=context)

    options = self.params.get_flow_files_archive

    if (options.skip_glob_checks_for_artifact_collector and
        flow_name == self.effective_artifact_collector_flow_name):
      return api_flow.ApiGetFlowFilesArchiveHandler()
    else:
      return api_flow.ApiGetFlowFilesArchiveHandler(
          exclude_path_globs=options.exclude_path_globs,
          include_only_path_globs=options.include_only_path_globs)

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
