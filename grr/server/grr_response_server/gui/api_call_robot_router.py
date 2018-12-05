#!/usr/bin/env python
"""Implementation of a router class that should be used by robot users."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import paths as rdf_paths

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import api_call_router_pb2
from grr_response_server import access_control

from grr_response_server import aff4
from grr_response_server import flow
from grr_response_server import throttle
from grr_response_server.flows.general import collectors
from grr_response_server.flows.general import file_finder

from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_router
from grr_response_server.gui import api_call_router_without_checks
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import reflection as api_reflection


class RobotRouterSearchClientsParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.RobotRouterSearchClientsParams


class RobotRouterFileFinderFlowParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.RobotRouterFileFinderFlowParams
  rdf_deps = [
      rdfvalue.Duration,
  ]


class RobotRouterArtifactCollectorFlowParams(rdf_structs.RDFProtoStruct):
  protobuf = api_call_router_pb2.RobotRouterArtifactCollectorFlowParams
  rdf_deps = [
      rdfvalue.Duration,
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

  def __init__(self, robot_id=None, override_flow_args=None):
    super(ApiRobotCreateFlowHandler, self).__init__()

    if not robot_id:
      raise ValueError("Robot id can't be empty.")
    self.robot_id = robot_id

    self.override_flow_args = override_flow_args

  def Handle(self, args, token=None):
    if not args.client_id:
      raise RuntimeError("Client id has to be specified.")

    if not args.flow.name:
      raise RuntimeError("Flow name is not specified.")

    # Note that runner_args are dropped. From all the arguments We use only
    # the flow name and the arguments.
    flow_id = flow.StartAFF4Flow(
        client_id=args.client_id.ToClientURN(),
        flow_name=args.flow.name,
        token=token,
        args=self.override_flow_args or args.flow.args)

    with aff4.FACTORY.Open(
        flow_id, aff4_type=flow.GRRFlow, mode="rw", token=token) as fd:
      fd.AddLabel(LABEL_NAME_PREFIX + self.robot_id)
      return api_flow.ApiFlow().InitFromAff4Object(
          fd, flow_id=flow_id.Basename())


class ApiRobotReturnDuplicateFlowHandler(api_call_handler_base.ApiCallHandler):
  """CreateFlow handler for cases when similar flow did run recently.

  This handler is used when throttler signals that a similar flow has already
  executed within min_interval_between_duplicate_flows time. In this case
  we just return a descriptor of a previously executed flow.
  """

  args_type = api_flow.ApiCreateFlowArgs
  result_type = api_flow.ApiFlow

  def __init__(self, flow_id):
    super(ApiRobotReturnDuplicateFlowHandler, self).__init__()

    if not flow_id:
      raise ValueError("flow_id can't be empty.")
    self.flow_id = flow_id

  def Handle(self, args, token=None):
    return api_flow.ApiGetFlowHandler().Handle(
        api_flow.ApiGetFlowArgs(client_id=args.client_id, flow_id=self.flow_id),
        token=token)


class ApiCallRobotRouter(api_call_router.ApiCallRouterStub):
  """Restricted router to be used by robots."""

  params_type = ApiCallRobotRouterParams

  def __init__(self, params=None, delegate=None):
    super(ApiCallRobotRouter, self).__init__(params=params)

    if params is None:
      raise ValueError("Router params are mandatory for ApiCallRobotRouter.")
    if not params.robot_id:
      raise ValueError("robot_id has to be specified in ApiCallRobotRouter "
                       "parameters.")
    self.params = params = params or self.__class__.params_type()

    if not delegate:
      delegate = api_call_router_without_checks.ApiCallRouterWithoutChecks()
    self.delegate = delegate

  @property
  def file_finder_flow_name(self):
    return (self.params.file_finder_flow.file_finder_flow_name or
            file_finder.FileFinder.__name__)

  @property
  def artifact_collector_flow_name(self):
    return (self.params.artifact_collector_flow.artifact_collector_flow_name or
            collectors.ArtifactCollectorFlow.__name__)

  def SearchClients(self, args, token=None):
    if not self.params.search_clients.enabled:
      raise access_control.UnauthorizedAccess(
          "SearchClients is not allowed by the configuration.")

    return api_client.ApiSearchClientsHandler()

  def _CheckFileFinderArgs(self, flow_args, token=None):
    ffparams = self.params.file_finder_flow

    if not ffparams.enabled:
      raise access_control.UnauthorizedAccess(
          "FileFinder flow is not allowed by the configuration.")

    if not ffparams.globs_allowed:
      for path in flow_args.paths:
        str_path = utils.SmartStr(path)
        if "*" in str_path:
          raise access_control.UnauthorizedAccess(
              "Globs are not allowed by the configuration.")

    if not ffparams.interpolations_allowed:
      for path in flow_args.paths:
        str_path = utils.SmartStr(path)
        if "%%" in str_path:
          raise access_control.UnauthorizedAccess(
              "Interpolations are not allowed by the configuration.")

  def _GetFileFinderThrottler(self):
    ffparams = self.params.file_finder_flow

    return throttle.FlowThrottler(
        daily_req_limit=ffparams.max_flows_per_client_daily,
        dup_interval=ffparams.min_interval_between_duplicate_flows)

  def _CheckArtifactCollectorFlowArgs(self, flow_args):
    if not self.params.artifact_collector_flow.enabled:
      raise access_control.UnauthorizedAccess(
          "ArtifactCollectorFlow flow is not allowed by the configuration")

    for name in flow_args.artifact_list:
      if name not in self.params.artifact_collector_flow.artifacts_whitelist:
        raise access_control.UnauthorizedAccess(
            "Artifact %s is not whitelisted." % name)

  def _GetArtifactCollectorFlowThrottler(self):
    acparams = self.params.artifact_collector_flow

    return throttle.FlowThrottler(
        daily_req_limit=acparams.max_flows_per_client_daily,
        dup_interval=acparams.min_interval_between_duplicate_flows)

  def _CheckFlowRobotId(self, client_id, flow_id, token=None):
    flow_urn = flow_id.ResolveClientFlowURN(client_id, token=token)
    fd = aff4.FACTORY.Open(flow_urn, aff4_type=flow.GRRFlow, token=token)

    needed_label_name = LABEL_NAME_PREFIX + self.params.robot_id
    if needed_label_name not in fd.GetLabelsNames():
      raise access_control.UnauthorizedAccess(
          "Flow %s (client %s) does not have a proper robot id label set." %
          (flow_id, client_id))

    return fd

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

  def CreateFlow(self, args, token=None):
    if not args.client_id:
      raise ValueError("client_id must be provided")

    override_flow_args = None
    throttler = None
    if args.flow.name == self.file_finder_flow_name:
      self._CheckFileFinderArgs(args.flow.args)
      override_flow_args = self._FixFileFinderArgs(args.flow.args)
      throttler = self._GetFileFinderThrottler()
    elif args.flow.name == self.artifact_collector_flow_name:
      self._CheckArtifactCollectorFlowArgs(args.flow.args)
      throttler = self._GetArtifactCollectorFlowThrottler()
    else:
      raise access_control.UnauthorizedAccess(
          "Creating arbitrary flows (%s) is not allowed." % args.flow.name)

    try:
      throttler.EnforceLimits(
          args.client_id.ToClientURN(),
          token.username,
          args.flow.name,
          args.flow.args,
          token=token)
    except throttle.DuplicateFlowError as e:
      # If a similar flow did run recently, just return it.
      return ApiRobotReturnDuplicateFlowHandler(flow_id=e.flow_id)
    except throttle.DailyFlowRequestLimitExceededError as e:
      # Raise UnauthorizedAccess so that the user gets an HTTP 403.
      raise access_control.UnauthorizedAccess(str(e))

    return ApiRobotCreateFlowHandler(
        robot_id=self.params.robot_id, override_flow_args=override_flow_args)

  def GetFlow(self, args, token=None):
    if not self.params.get_flow.enabled:
      raise access_control.UnauthorizedAccess(
          "GetFlow is not allowed by the configuration.")

    self._CheckFlowRobotId(args.client_id, args.flow_id, token=token)

    return api_flow.ApiGetFlowHandler()

  def ListFlowResults(self, args, token=None):
    if not self.params.list_flow_results.enabled:
      raise access_control.UnauthorizedAccess(
          "ListFlowResults is not allowed by the configuration.")

    self._CheckFlowRobotId(args.client_id, args.flow_id, token=token)

    return api_flow.ApiListFlowResultsHandler()

  def ListFlowLogs(self, args, token=None):
    if not self.params.list_flow_logs.enabled:
      raise access_control.UnauthorizedAccess(
          "ListFlowLogs is not allowed by the configuration.")

    self._CheckFlowRobotId(args.client_id, args.flow_id, token=token)

    return api_flow.ApiListFlowLogsHandler()

  def GetFlowFilesArchive(self, args, token=None):
    if not self.params.get_flow_files_archive.enabled:
      raise access_control.UnauthorizedAccess(
          "GetFlowFilesArchive is not allowed by the configuration.")

    fd = self._CheckFlowRobotId(args.client_id, args.flow_id, token=token)

    options = self.params.get_flow_files_archive

    if (options.skip_glob_checks_for_artifact_collector and
        fd.Name() == self.artifact_collector_flow_name):
      return api_flow.ApiGetFlowFilesArchiveHandler()
    else:
      return api_flow.ApiGetFlowFilesArchiveHandler(
          path_globs_blacklist=options.path_globs_blacklist,
          path_globs_whitelist=options.path_globs_whitelist)

  # Reflection methods.
  # ==================
  #
  # NOTE: Only the ListApiMethods is enabled as it may be used by client
  # API libraries.
  def ListApiMethods(self, args, token=None):
    return api_reflection.ApiListApiMethodsHandler(self)
