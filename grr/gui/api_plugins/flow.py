#!/usr/bin/env python
"""API handlers for dealing with flows."""

import itertools

from grr.gui import api_call_handler_base
from grr.gui import api_call_handler_utils
from grr.gui.api_plugins import output_plugin as api_output_plugin

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import client_index
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import rdfvalue
from grr.lib import throttle
from grr.lib import utils
from grr.lib.aff4_objects import collects as aff4_collects
from grr.lib.aff4_objects import users as aff4_users
from grr.lib.flows.general import file_finder
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2

CATEGORY = "Flows"


class RobotGetFilesOperationNotFoundError(
    api_call_handler_base.ResourceNotFoundError):
  """Raises when "get files" operation is not found."""


class ApiFlowDescriptor(rdf_structs.RDFProtoStruct):
  """Descriptor containing information about a flow class."""

  protobuf = api_pb2.ApiFlowDescriptor

  def GetDefaultArgsClass(self):
    return rdfvalue.RDFValue.classes.get(self.args_type)

  def InitFromFlowClass(self, flow_cls, token=None):
    if not token:
      raise ValueError("token can't be None")

    self.name = flow_cls.__name__
    self.friendly_name = flow_cls.friendly_name
    self.category = flow_cls.category.strip("/")
    self.doc = flow_cls.__doc__
    self.args_type = flow_cls.args_type.__name__
    self.default_args = flow_cls.GetDefaultArgs(token=token)
    self.behaviours = sorted(flow_cls.behaviours)

    return self


class ApiFlow(rdf_structs.RDFProtoStruct):
  """ApiFlow is used when rendering responses.

  ApiFlow is meant to be more lightweight than automatically generated AFF4
  representation. It's also meant to contain only the information needed by
  the UI and and to not expose implementation defails.
  """
  protobuf = api_pb2.ApiFlow

  def GetArgsClass(self):
    flow_name = self.name
    if not flow_name:
      flow_name = self.runner_args.flow_name

    if flow_name:
      flow_cls = flow.GRRFlow.classes.get(flow_name)
      if flow_cls is None:
        raise ValueError("Flow %s not known by this implementation." %
                         flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type

  def InitFromAff4Object(self, flow_obj):
    # If the flow object is in fact a symlink, then we want to report the
    # symlink's URN as a flow's URN. Otherwise you may get unexpected
    # URNs while listing client's flows. For example, this may happend when
    # a hunt was running on a client and a flow itself is located in the
    # hunt's namespace, but was symlinked into the client's namespace:
    #
    # aff4:/hunts/H:123456/flows/H:987654 ->
    #   aff4:/C.0000111122223333/flows/H:987654
    if hasattr(flow_obj, "symlink_urn"):
      self.urn = flow_obj.symlink_urn
    else:
      self.urn = flow_obj.urn

    self.name = flow_obj.state.context.args.flow_name
    self.started_at = flow_obj.state.context.create_time
    self.last_active_at = flow_obj.Get(flow_obj.Schema.LAST)
    self.creator = flow_obj.state.context.creator

    if flow_obj.Get(flow_obj.Schema.CLIENT_CRASH):
      self.state = "CLIENT_CRASHED"
    else:
      self.state = flow_obj.state.context.state

    try:
      self.args = flow_obj.args
    except ValueError:
      # If args class name has changed, ValueError will be raised. Handling
      # this gracefully - we should still try to display some useful info
      # about the flow.
      pass

    return self


class ApiFlowResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiFlowResult

  def GetPayloadClass(self):
    return rdfvalue.RDFValue.classes[self.payload_type]

  def InitFromRdfValue(self, value):
    self.payload_type = value.__class__.__name__
    self.payload = value
    self.timestamp = value.age

    return self


class ApiGetFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFlowArgs


class ApiGetFlowHandler(api_call_handler_base.ApiCallHandler):
  """Renders given flow.

  Only top-level flows can be targeted. Times returned in the response are micro
  seconds since epoch.
  """

  category = CATEGORY

  args_type = ApiGetFlowArgs
  result_type = ApiFlow
  strip_json_root_fields_types = False

  def Handle(self, args, token=None):
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    flow_obj = aff4.FACTORY.Open(flow_urn,
                                 aff4_type=flow.GRRFlow,
                                 mode="r",
                                 token=token)

    return ApiFlow().InitFromAff4Object(flow_obj)


class ApiListFlowResultsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowResultsArgs


class ApiListFlowResultsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowResultsResult


class ApiListFlowResultsHandler(api_call_handler_base.ApiCallHandler):
  """Renders results of a given flow."""

  category = CATEGORY
  args_type = ApiListFlowResultsArgs
  result_type = ApiListFlowResultsResult

  def Handle(self, args, token=None):
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    flow_obj = aff4.FACTORY.Open(flow_urn,
                                 aff4_type=flow.GRRFlow,
                                 mode="r",
                                 token=token)

    output_urn = flow_obj.GetRunner().output_urn
    # TODO(user): RDFValueCollection is a deprecated type.
    output_collection = aff4.FACTORY.Create(
        output_urn,
        aff4_type=aff4_collects.RDFValueCollection,
        mode="r",
        token=token)

    items = api_call_handler_utils.FilterAff4Collection(output_collection,
                                                        args.offset, args.count,
                                                        args.filter)
    wrapped_items = [ApiFlowResult().InitFromRdfValue(item) for item in items]
    return ApiListFlowResultsResult(items=wrapped_items,
                                    total_count=len(output_collection))


class ApiListFlowLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowLogsArgs


class ApiListFlowLogsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowLogsResult


class ApiListFlowLogsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of logs for the current client and flow."""

  category = CATEGORY
  args_type = ApiListFlowLogsArgs
  result_type = ApiListFlowLogsResult

  def Handle(self, args, token=None):
    logs_collection_urn = args.client_id.Add("flows").Add(args.flow_id.Basename(
    )).Add("Logs")
    logs_collection = aff4.FACTORY.Create(
        logs_collection_urn,
        aff4_type=flow_runner.FlowLogCollection,
        mode="r",
        token=token)

    result = api_call_handler_utils.FilterAff4Collection(logs_collection,
                                                         args.offset,
                                                         args.count,
                                                         args.filter)

    return ApiListFlowLogsResult(items=result, total_count=len(logs_collection))


class ApiGetFlowResultsExportCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFlowResultsExportCommandArgs


class ApiGetFlowResultsExportCommandResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFlowResultsExportCommandResult


class ApiGetFlowResultsExportCommandHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders GRR export tool command line that exports flow results."""

  category = CATEGORY
  args_type = ApiGetFlowResultsExportCommandArgs
  result_type = ApiGetFlowResultsExportCommandResult

  def Handle(self, args, token=None):
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    flow_obj = aff4.FACTORY.Open(flow_urn,
                                 aff4_type=flow.GRRFlow,
                                 mode="r",
                                 token=token)
    output_urn = flow_obj.GetRunner().output_urn

    export_command_str = " ".join([
        config_lib.CONFIG["AdminUI.export_command"], "--username",
        utils.ShellQuote(token.username), "collection_files", "--path",
        utils.ShellQuote(output_urn), "--output", "."
    ])

    return ApiGetFlowResultsExportCommandResult(command=export_command_str)


class ApiGetFlowFilesArchiveArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetFlowFilesArchiveArgs


class ApiGetFlowFilesArchiveHandler(api_call_handler_base.ApiCallHandler):
  """Generates archive with all files referenced in flow's results."""

  args_type = ApiGetFlowFilesArchiveArgs

  def _WrapContentGenerator(self, generator, collection, args, token=None):
    user = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(token.username),
        aff4_type=aff4_users.GRRUser,
        mode="rw",
        token=token)
    try:
      for item in generator.Generate(collection, token=token):
        yield item

      user.Notify("ArchiveGenerationFinished", None,
                  "Downloaded archive of flow %s from client %s (archived %d "
                  "out of %d items, archive size is %d)" %
                  (args.flow_id.Basename(), args.client_id.Basename(),
                   generator.archived_files, generator.total_files,
                   generator.output_size), self.__class__.__name__)
    except Exception as e:
      user.Notify("Error", None,
                  "Archive generation failed for flow %s on client %s: %s" %
                  (args.flow_id.Basename(), args.client_id.Basename(),
                   utils.SmartStr(e)), self.__class__.__name__)
      raise
    finally:
      user.Close()

  def Handle(self, args, token=None):
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    flow_obj = aff4.FACTORY.Open(flow_urn,
                                 aff4_type=flow.GRRFlow,
                                 mode="r",
                                 token=token)

    flow_api_object = ApiFlow().InitFromAff4Object(flow_obj)
    description = ("Files downloaded by flow %s (%s) that ran on client %s by "
                   "user %s on %s" % (flow_api_object.name,
                                      args.flow_id.Basename(),
                                      args.client_id.Basename(),
                                      flow_api_object.creator,
                                      flow_api_object.started_at))

    collection_urn = flow_obj.GetRunner().output_urn
    target_file_prefix = "%s_flow_%s_%s" % (
        args.client_id.Basename(), flow_obj.state.context.args.flow_name,
        flow_urn.Basename().replace(":", "_"))

    collection = aff4.FACTORY.Open(collection_urn, token=token)

    if args.archive_format == args.ArchiveFormat.ZIP:
      archive_format = api_call_handler_utils.CollectionArchiveGenerator.ZIP
      file_extension = ".zip"
    elif args.archive_format == args.ArchiveFormat.TAR_GZ:
      archive_format = api_call_handler_utils.CollectionArchiveGenerator.TAR_GZ
      file_extension = ".tar.gz"
    else:
      raise ValueError("Unknown archive format: %s" % args.archive_format)

    generator = api_call_handler_utils.CollectionArchiveGenerator(
        prefix=target_file_prefix,
        description=description,
        archive_format=archive_format)
    content_generator = self._WrapContentGenerator(generator,
                                                   collection,
                                                   args,
                                                   token=token)
    return api_call_handler_base.ApiBinaryStream(
        target_file_prefix + file_extension,
        content_generator=content_generator)


class ApiListFlowOutputPluginsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowOutputPluginsArgs


class ApiListFlowOutputPluginsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowOutputPluginsResult


class ApiListFlowOutputPluginsHandler(api_call_handler_base.ApiCallHandler):
  """Renders output plugins descriptors and states for a given flow."""

  category = CATEGORY

  args_type = ApiListFlowOutputPluginsArgs
  result_type = ApiListFlowOutputPluginsResult

  def Handle(self, args, token=None):
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    flow_obj = aff4.FACTORY.Open(flow_urn,
                                 aff4_type=flow.GRRFlow,
                                 mode="r",
                                 token=token)

    output_plugins_states = flow_obj.GetRunner().context.output_plugins_states

    type_indices = {}
    result = []
    for plugin_descriptor, plugin_state in output_plugins_states:
      type_index = type_indices.setdefault(plugin_descriptor.plugin_name, 0)
      type_indices[plugin_descriptor.plugin_name] += 1

      # Output plugins states are stored differently for hunts and for flows:
      # as a dictionary for hunts and as a simple list for flows.
      #
      # TODO(user): store output plugins states in the same way for flows
      # and hunts. Until this is done, we can emulate the same interface in
      # the HTTP API.
      api_plugin = api_output_plugin.ApiOutputPlugin(
          id=plugin_descriptor.plugin_name + "_%d" % type_index,
          plugin_descriptor=plugin_descriptor,
          state=plugin_state)
      result.append(api_plugin)

    return ApiListFlowOutputPluginsResult(items=result)


class ApiListFlowOutputPluginLogsHandlerBase(
    api_call_handler_base.ApiCallHandler):
  """Base class used to define log and error messages handlers."""

  __abstract = True  # pylint: disable=g-bad-name

  attribute_name = None
  category = CATEGORY

  def Handle(self, args, token=None):
    if not self.attribute_name:
      raise ValueError("attribute_name can't be None")

    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    flow_obj = aff4.FACTORY.Open(flow_urn,
                                 aff4_type=flow.GRRFlow,
                                 mode="r",
                                 token=token)

    output_plugins_states = flow_obj.GetRunner().context.output_plugins_states

    # Flow output plugins don't use collections to store status/error
    # information. Instead, it's stored in plugin's state. Nevertheless,
    # we emulate collections API here. Having similar API interface allows
    # one to reuse the code when handling hunts and flows output plugins.
    # Good example is the UI code.
    type_indices = {}
    found_state = None
    for plugin_descriptor, plugin_state in output_plugins_states:
      type_index = type_indices.setdefault(plugin_descriptor.plugin_name, 0)
      type_indices[plugin_descriptor.plugin_name] += 1

      if args.plugin_id == plugin_descriptor.plugin_name + "_%d" % type_index:
        found_state = plugin_state
        break

    if not found_state:
      raise RuntimeError("Flow %s doesn't have output plugin %s" %
                         (flow_urn, args.plugin_id))

    stop = None
    if args.count:
      stop = args.offset + args.count

    logs_collection = found_state.get(self.attribute_name, [])
    sliced_collection = logs_collection[args.offset:stop]

    return self.result_type(total_count=len(logs_collection),
                            items=sliced_collection)


class ApiListFlowOutputPluginLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowOutputPluginLogsArgs


class ApiListFlowOutputPluginLogsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowOutputPluginLogsResult


class ApiListFlowOutputPluginLogsHandler(
    ApiListFlowOutputPluginLogsHandlerBase):
  """Renders flow's output plugin's logs."""

  attribute_name = "logs"
  args_type = ApiListFlowOutputPluginLogsArgs
  result_type = ApiListFlowOutputPluginLogsResult


class ApiListFlowOutputPluginErrorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowOutputPluginErrorsArgs


class ApiListFlowOutputPluginErrorsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowOutputPluginErrorsResult


class ApiListFlowOutputPluginErrorsHandler(
    ApiListFlowOutputPluginLogsHandlerBase):
  """Renders flow's output plugin's errors."""

  attribute_name = "errors"
  args_type = ApiListFlowOutputPluginErrorsArgs
  result_type = ApiListFlowOutputPluginErrorsResult


class ApiListFlowsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowsArgs


class ApiListFlowsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowsResult


class ApiListFlowsHandler(api_call_handler_base.ApiCallHandler):
  """Lists flows launched on a given client."""

  category = CATEGORY

  args_type = ApiListFlowsArgs
  result_type = ApiListFlowsResult

  def _GetCreationTime(self, obj):
    try:
      return obj.state.context.get("create_time")
    except AttributeError:
      return obj.Get(obj.Schema.LAST, 0)

  def Handle(self, args, token=None):
    client_root_urn = args.client_id.Add("flows")

    if not args.count:
      stop = None
    else:
      stop = args.offset + args.count

    root_children_urns = aff4.FACTORY.Open(client_root_urn,
                                           token=token).ListChildren()
    root_children_urns = sorted(root_children_urns,
                                key=lambda x: x.age,
                                reverse=True)
    root_children_urns = root_children_urns[args.offset:stop]

    root_children = aff4.FACTORY.MultiOpen(root_children_urns,
                                           aff4_type=flow.GRRFlow,
                                           token=token)
    root_children = sorted(root_children,
                           key=self._GetCreationTime,
                           reverse=True)

    nested_children_urns = dict(aff4.FACTORY.RecursiveMultiListChildren(
        [fd.urn for fd in root_children],
        token=token))
    nested_children = aff4.FACTORY.MultiOpen(
        set(itertools.chain(*nested_children_urns.values())),
        aff4_type=flow.GRRFlow,
        token=token)
    nested_children_map = dict((x.urn, x) for x in nested_children)

    def BuildList(fds):
      """Builds list of flows recursively."""
      result = []
      for fd in fds:
        api_flow = ApiFlow().InitFromAff4Object(fd)

        try:
          children_urns = nested_children_urns[fd.urn]
        except KeyError:
          children_urns = []

        children = []
        for urn in children_urns:
          try:
            children.append(nested_children_map[urn])
          except KeyError:
            pass

        children = sorted(children, key=self._GetCreationTime, reverse=True)
        try:
          api_flow.nested_flows = BuildList(children)
        except KeyError:
          pass
        result.append(api_flow)

      return result

    return ApiListFlowsResult(items=BuildList(root_children))


class ApiStartRobotGetFilesOperationArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiStartRobotGetFilesOperationArgs


class ApiStartRobotGetFilesOperationResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiStartRobotGetFilesOperationResult


class ApiStartRobotGetFilesOperationHandler(
    api_call_handler_base.ApiCallHandler):
  """Downloads files from specified machine without requiring approval."""

  category = CATEGORY
  args_type = ApiStartRobotGetFilesOperationArgs
  result_type = ApiStartRobotGetFilesOperationResult

  def GetClientTarget(self, args, token=None):
    # Find the right client to target using a hostname search.
    index = aff4.FACTORY.Create(client_index.MAIN_INDEX,
                                aff4_type=client_index.ClientIndex,
                                mode="rw",
                                token=token)

    client_list = index.LookupClients([args.hostname])
    if not client_list:
      raise ValueError("No client found matching %s" % args.hostname)

    # If we get more than one, take the one with the most recent poll.
    if len(client_list) > 1:
      return client_index.GetMostRecentClient(client_list, token=token)
    else:
      return client_list[0]

  def Handle(self, args, token=None):
    client_urn = self.GetClientTarget(args, token=token)

    size_condition = file_finder.FileFinderCondition(
        condition_type=file_finder.FileFinderCondition.Type.SIZE,
        size=file_finder.FileFinderSizeCondition(
            max_file_size=args.max_file_size))

    file_finder_args = file_finder.FileFinderArgs(
        paths=args.paths,
        action=file_finder.FileFinderAction(action_type=args.action),
        conditions=[size_condition])

    # Check our flow throttling limits, will raise if there are problems.
    throttler = throttle.FlowThrottler()
    throttler.EnforceLimits(client_urn,
                            token.username,
                            file_finder.FileFinder.__name__,
                            file_finder_args,
                            token=token)

    # Limit the whole flow to 200MB so if a glob matches lots of small files we
    # still don't have too much impact.
    runner_args = flow_runner.FlowRunnerArgs(
        client_id=client_urn,
        flow_name=file_finder.FileFinder.__name__,
        network_bytes_limit=200 * 1000 * 1000)

    flow_id = flow.GRRFlow.StartFlow(runner_args=runner_args,
                                     token=token,
                                     args=file_finder_args)

    return ApiStartRobotGetFilesOperationResult(
        operation_id=utils.SmartUnicode(flow_id))


class ApiGetRobotGetFilesOperationStateArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetRobotGetFilesOperationStateArgs


class ApiGetRobotGetFilesOperationStateResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetRobotGetFilesOperationStateResult


class ApiGetRobotGetFilesOperationStateHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders summary of a given flow.

  Only top-level flows can be targeted. Times returned in the response are micro
  seconds since epoch.
  """

  category = CATEGORY
  args_type = ApiGetRobotGetFilesOperationStateArgs
  result_type = ApiGetRobotGetFilesOperationStateResult

  def Handle(self, args, token=None):
    """Render robot "get files" operation status.

    This handler relies on URN validation and flow type checking to check the
    input parameters to avoid allowing arbitrary reads into the client aff4
    space. This handler filters out only the attributes that are appropriate to
    release without authorization (authentication is still required).

    Args:
      args: ApiGetRobotGetFilesOperationStateArgs object.
      token: access token.
    Returns:
      ApiGetRobotGetFilesOperationStateResult object.
    Raises:
      RobotGetFilesOperationNotFoundError: if operation is not found (i.e.
          if the flow is not found or is not a FileFinder flow).
      ValueError: if operation id is incorrect. It should match the
          aff4:/<client id>/flows/<flow session id> pattern exactly.
    """

    # We deconstruct the operation id and rebuild it as a URN to ensure
    # that it points to the flow on a client.
    urn = rdfvalue.RDFURN(args.operation_id)
    urn_components = urn.Split()

    if len(urn_components) != 3 or urn_components[1] != "flows":
      raise ValueError("Invalid operation id.")

    client_id = rdf_client.ClientURN(urn_components[0])

    rdfvalue.SessionID.ValidateID(urn_components[2])
    flow_id = rdfvalue.SessionID(urn_components[2])

    # flow_id looks like aff4:/F:ABCDEF12, convert it into a flow urn for
    # the target client.
    flow_urn = client_id.Add("flows").Add(flow_id.Basename())
    try:
      flow_obj = aff4.FACTORY.Open(flow_urn,
                                   aff4_type=file_finder.FileFinder,
                                   token=token)
    except aff4.InstantiationError:
      raise RobotGetFilesOperationNotFoundError()

    flow_state = flow_obj.Get(flow_obj.Schema.FLOW_STATE)
    try:
      result_collection = aff4.FACTORY.Open(
          flow_state.context.output_urn,
          aff4_type=aff4_collects.RDFValueCollection,
          token=token)
      result_count = len(result_collection)
    except aff4.InstantiationError:
      result_count = 0

    api_flow_obj = ApiFlow().InitFromAff4Object(flow_obj)
    return ApiGetRobotGetFilesOperationStateResult(state=api_flow_obj.state,
                                                   result_count=result_count)


class ApiCreateFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiCreateFlowArgs


class ApiCreateFlowHandler(api_call_handler_base.ApiCallHandler):
  """Starts a flow on a given client with given parameters."""

  category = CATEGORY

  args_type = ApiCreateFlowArgs
  result_type = ApiFlow
  strip_json_root_fields_types = False

  def Handle(self, args, token=None):
    flow_name = args.flow.name
    if not flow_name:
      flow_name = args.flow.runner_args.flow_name
    if not flow_name:
      raise RuntimeError("Flow name is not specified.")

    flow_id = flow.GRRFlow.StartFlow(client_id=args.client_id,
                                     flow_name=flow_name,
                                     token=token,
                                     args=args.flow.args,
                                     runner_args=args.flow.runner_args)

    fd = aff4.FACTORY.Open(flow_id, aff4_type=flow.GRRFlow, token=token)
    return ApiFlow().InitFromAff4Object(fd)


class ApiCancelFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiCancelFlowArgs


class ApiCancelFlowHandler(api_call_handler_base.ApiCallHandler):
  """Cancels given flow on a given client."""

  category = CATEGORY
  args_type = ApiCancelFlowArgs
  privileged = True

  def Handle(self, args, token=None):
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    # If we can read the flow, we're allowed to terminate it.
    data_store.DB.security_manager.CheckDataStoreAccess(token.RealUID(),
                                                        [flow_urn], "r")

    flow.GRRFlow.TerminateFlow(flow_urn,
                               reason="Cancelled in GUI",
                               token=token,
                               force=True)


class ApiListFlowDescriptorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowDescriptorsArgs


class ApiListFlowDescriptorsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListFlowDescriptorsResult


class ApiListFlowDescriptorsHandler(api_call_handler_base.ApiCallHandler):
  """Renders all available flows descriptors."""

  category = CATEGORY
  args_type = ApiListFlowDescriptorsArgs
  result_type = ApiListFlowDescriptorsResult

  client_flow_behavior = flow.FlowBehaviour("Client Flow")
  global_flow_behavior = flow.FlowBehaviour("Global Flow")

  def _FlowTypeToBehavior(self, flow_type):
    if flow_type == self.args_type.FlowType.CLIENT:
      return self.client_flow_behavior
    elif flow_type == self.args_type.FlowType.GLOBAL:
      return self.global_flow_behavior
    else:
      raise ValueError("Unexpected flow type: " + str(flow_type))

  def Handle(self, args, token=None):
    """Renders list of descriptors for all the flows."""

    result = []
    for name in sorted(flow.GRRFlow.classes.keys()):
      cls = flow.GRRFlow.classes[name]

      # Flows without a category do not show up in the GUI.
      if not getattr(cls, "category", None):
        continue

      # Only show flows that the user is allowed to start.
      can_be_started_on_client = False
      try:
        data_store.DB.security_manager.CheckIfCanStartFlow(token,
                                                           name,
                                                           with_client_id=True)
        can_be_started_on_client = True
      except access_control.UnauthorizedAccess:
        pass

      can_be_started_globally = False
      try:
        data_store.DB.security_manager.CheckIfCanStartFlow(token,
                                                           name,
                                                           with_client_id=False)
        can_be_started_globally = True
      except access_control.UnauthorizedAccess:
        pass

      if args.HasField("flow_type"):
        # Skip if there are behaviours that are not supported by the class.
        behavior = self._FlowTypeToBehavior(args.flow_type)
        if not behavior.IsSupported(cls.behaviours):
          continue

        if (args.flow_type == self.args_type.FlowType.CLIENT and
            not can_be_started_on_client):
          continue

        if (args.flow_type == self.args_type.FlowType.GLOBAL and
            not can_be_started_globally):
          continue
      elif not (can_be_started_on_client or can_be_started_globally):
        continue

      result.append(ApiFlowDescriptor().InitFromFlowClass(cls, token=token))

    return ApiListFlowDescriptorsResult(items=result)
