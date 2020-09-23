#!/usr/bin/env python
# Lint as: python3
"""API handlers for dealing with flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import itertools
import re
from typing import Iterable, Optional, Tuple, Type


from grr_response_core import config
from grr_response_core.lib import parsers
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_proto.api import flow_pb2
from grr_response_server import access_control
from grr_response_server import artifact
from grr_response_server import data_store
from grr_response_server import data_store_utils
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import instant_output_plugin
from grr_response_server import notification
from grr_response_server import output_plugin
from grr_response_server.databases import db
from grr_response_server.flows.general import collectors
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.gui import archive_generator
from grr_response_server.gui.api_plugins import client
from grr_response_server.gui.api_plugins import output_plugin as api_output_plugin
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin


class FlowNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a flow is not found."""


class OutputPluginNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when an output plugin is not found."""


class ApiFlowId(rdfvalue.RDFString):
  """Class encapsulating flows ids."""

  def __init__(self, initializer=None):
    super().__init__(initializer=initializer)

    # TODO(user): move this to a separate validation method when
    # common RDFValues validation approach is implemented.
    if self._value:
      components = self.Split()
      for component in components:
        try:
          rdfvalue.SessionID.ValidateID(component)
        except ValueError as e:
          raise ValueError("Invalid flow id: %s (%s)" % (self._value, e))

  def Split(self):
    if not self._value:
      raise ValueError("Can't call Split() on an empty client id.")

    return self._value.split("/")


class ApiFlowDescriptor(rdf_structs.RDFProtoStruct):
  """Descriptor containing information about a flow class."""

  protobuf = flow_pb2.ApiFlowDescriptor

  def GetDefaultArgsClass(self):
    return rdfvalue.RDFValue.classes.get(self.args_type)

  def _GetArgsDescription(self, args_type):
    """Get a simplified description of the args_type for a flow."""
    args = {}
    if args_type:
      for type_descriptor in args_type.type_infos:
        if not type_descriptor.hidden:
          args[type_descriptor.name] = {
              "description": type_descriptor.description,
              "default": type_descriptor.default,
              "type": "",
          }
          if type_descriptor.type:
            args[type_descriptor.name]["type"] = type_descriptor.type.__name__
    return args

  def _GetCallingPrototypeAsString(self, flow_cls):
    """Get a description of the calling prototype for this flow class."""
    output = []
    output.append("flow.StartFlow(client_id=client_id, ")
    output.append("flow_cls=%s.%s, " %
                  (flow_cls.__module__.split(".")[-1], flow_cls.__name__))
    prototypes = []
    if flow_cls.args_type:
      for type_descriptor in flow_cls.args_type.type_infos:
        if not type_descriptor.hidden:
          prototypes.append("%s=%s" %
                            (type_descriptor.name, type_descriptor.name))
    output.append(", ".join(prototypes))
    output.append(")")
    return "".join(output)

  def _GetFlowArgsHelpAsString(self, flow_cls):
    """Get a string description of the calling prototype for this flow."""
    output = [
        "  Call Spec:",
        "    %s" % self._GetCallingPrototypeAsString(flow_cls), ""
    ]
    arg_list = sorted(
        self._GetArgsDescription(flow_cls.args_type).items(),
        key=lambda x: x[0])
    if not arg_list:
      output.append("  Args: None")
    else:
      output.append("  Args:")
      for arg, val in arg_list:
        output.append("    %s" % arg)
        output.append("      description: %s" % val["description"])
        output.append("      type: %s" % val["type"])
        output.append("      default: %s" % val["default"])
        output.append("")
    return "\n".join(output)

  def _GetFlowDocumentation(self, flow_cls):
    return "%s\n\n%s" % (getattr(flow_cls, "__doc__",
                                 ""), self._GetFlowArgsHelpAsString(flow_cls))

  def InitFromFlowClass(self, flow_cls, context=None):
    if not context:
      raise ValueError("context can't be None")

    self.name = flow_cls.__name__
    self.friendly_name = flow_cls.friendly_name
    self.category = flow_cls.category.strip("/")
    self.doc = self._GetFlowDocumentation(flow_cls)
    self.args_type = flow_cls.args_type.__name__
    self.default_args = flow_cls.GetDefaultArgs(username=context.username)
    self.behaviours = sorted(flow_cls.behaviours)

    return self


class ApiFlowReference(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiFlowReference
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]

  def FromFlowReference(self, reference):
    self.flow_id = reference.flow_id
    self.client_id = reference.client_id
    return self


class ApiFlow(rdf_structs.RDFProtoStruct):
  """ApiFlow is used when rendering responses.

  ApiFlow is meant to be more lightweight than automatically generated AFF4
  representation. It's also meant to contain only the information needed by
  the UI and and to not expose implementation defails.
  """
  protobuf = flow_pb2.ApiFlow
  rdf_deps = [
      api_call_handler_utils.ApiDataObject,
      client.ApiClientId,
      "ApiFlow",  # TODO(user): recursive dependency.
      ApiFlowId,
      ApiFlowReference,
      rdf_flow_runner.FlowContext,
      rdf_flow_runner.FlowRunnerArgs,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]

  def _GetFlowClass(self) -> Optional[Type[flow_base.FlowBase]]:
    flow_name = self.name
    if not flow_name:
      flow_name = self.runner_args.flow_name

    if flow_name:
      return registry.FlowRegistry.FlowClassByName(flow_name)

  def GetArgsClass(self) -> Optional[Type[rdf_structs.RDFProtoStruct]]:
    cls = self._GetFlowClass()
    if cls is not None:
      return cls.args_type

  def GetProgressClass(self) -> Optional[Type[rdf_structs.RDFProtoStruct]]:
    cls = self._GetFlowClass()
    if cls is not None:
      return cls.progress_type

  def InitFromFlowObject(self,
                         flow_obj,
                         with_args=True,
                         with_progress=False,
                         with_state_and_context=False):
    try:
      self.flow_id = flow_obj.flow_id
      self.client_id = flow_obj.client_id

      # TODO(amoser): Get rid of all urns.
      self.urn = flow_obj.long_flow_id

      self.name = flow_obj.flow_class_name
      self.started_at = flow_obj.create_time
      self.last_active_at = flow_obj.last_update_time
      self.creator = flow_obj.creator

      if flow_obj.client_crash_info:
        self.state = "CLIENT_CRASHED"
      elif flow_obj.pending_termination:
        self.state = "ERROR"
        self.status = ("Pending termination: %s" %
                       flow_obj.pending_termination.reason)
      else:
        context_state_map = {1: "RUNNING", 2: "TERMINATED", 3: "ERROR"}
        self.state = context_state_map[int(flow_obj.flow_state)]

      if with_state_and_context:
        outstanding_requests = (
            flow_obj.next_outbound_id - flow_obj.next_request_to_process)
        self.context = rdf_flow_runner.FlowContext(
            # TODO(amoser): No need to set this in all cases once the legacy API
            # is removed.
            client_resources=rdf_client_stats.ClientResources(
                cpu_usage=rdf_client_stats.CpuSeconds()),
            create_time=flow_obj.create_time,
            creator=flow_obj.creator,
            current_state=flow_obj.current_state,
            next_outbound_id=flow_obj.next_outbound_id,
            outstanding_requests=outstanding_requests,
            state=self.state,
            # TODO(amoser): Get rid of all urns.
            session_id=flow_obj.long_flow_id,
        )
        if flow_obj.output_plugins_states:
          self.context.output_plugins_states = flow_obj.output_plugins_states
        if flow_obj.network_bytes_sent:
          self.context.network_bytes_sent = flow_obj.network_bytes_sent
          self.context.client_resources.network_bytes_sent = (
              flow_obj.network_bytes_sent)
        if flow_obj.cpu_time_used:
          self.context.client_resources.cpu_time_used = flow_obj.cpu_time_used
        if flow_obj.error_message:
          self.context.status = flow_obj.error_message
        if flow_obj.backtrace:
          self.context.backtrace = flow_obj.backtrace

      if with_args:
        try:
          self.args = flow_obj.args
        except ValueError:
          # If args class name has changed, ValueError will be raised. Handling
          # this gracefully - we should still try to display some useful info
          # about the flow.
          pass

      if with_progress:
        flow_cls = self._GetFlowClass()
        if flow_cls:
          self.progress = flow_cls(flow_obj).GetProgress()

      self.runner_args = rdf_flow_runner.FlowRunnerArgs(
          client_id=flow_obj.client_id,
          flow_name=flow_obj.flow_class_name,
          notify_to_user=flow_base.FlowBase(flow_obj).ShouldSendNotifications())

      if flow_obj.output_plugins:
        self.runner_args.output_plugins = flow_obj.output_plugins

      if flow_obj.HasField("cpu_limit"):
        self.runner_args.cpu_limit = flow_obj.cpu_limit

      if flow_obj.HasField("network_bytes_limit"):
        self.runner_args.cpu_limit = flow_obj.network_bytes_limit

      if flow_obj.original_flow.flow_id:
        self.original_flow = ApiFlowReference().FromFlowReference(
            flow_obj.original_flow)

      if with_state_and_context and flow_obj.persistent_data.ToDict():
        self.state_data = (
            api_call_handler_utils.ApiDataObject().InitFromDataObject(
                flow_obj.persistent_data))

    except Exception as e:  # pylint: disable=broad-except
      self.internal_error = "Error while opening flow: %s" % str(e)

    return self


class ApiFlowRequest(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiFlowRequest
  rdf_deps = [
      rdf_flows.GrrMessage,
      rdf_flow_runner.RequestState,
  ]


class ApiFlowResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiFlowResult
  rdf_deps = [
      rdfvalue.RDFDatetime,
  ]

  def GetPayloadClass(self):
    return rdfvalue.RDFValue.classes[self.payload_type]

  def InitFromFlowResult(self, result):
    p = result.payload
    self.payload_type = compatibility.GetName(p.__class__)
    self.payload = p
    self.timestamp = result.timestamp
    if result.tag:
      self.tag = result.tag

    return self


class ApiFlowLog(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiFlowLog
  rdf_deps = [ApiFlowId, rdfvalue.RDFDatetime]

  def InitFromFlowLogEntry(self, fl, flow_id):
    self.log_message = fl.message
    self.flow_id = flow_id
    self.timestamp = fl.timestamp

    return self


class ApiGetFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiGetFlowArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiGetFlowHandler(api_call_handler_base.ApiCallHandler):
  """Renders given flow.

  Only top-level flows can be targeted.
  """

  args_type = ApiGetFlowArgs
  result_type = ApiFlow

  def Handle(self, args, context=None):
    flow_obj = data_store.REL_DB.ReadFlowObject(
        str(args.client_id), str(args.flow_id))
    return ApiFlow().InitFromFlowObject(
        flow_obj, with_state_and_context=True, with_progress=True)


class ApiListFlowRequestsArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowRequestsArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiListFlowRequestsResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowRequestsResult
  rdf_deps = [
      ApiFlowRequest,
  ]


class ApiListFlowRequestsHandler(api_call_handler_base.ApiCallHandler):
  """Renders list of requests of a given flow."""

  args_type = ApiListFlowRequestsArgs
  result_type = ApiListFlowRequestsResult

  def Handle(self, args, context=None):
    client_id = args.client_id.ToString()
    requests_and_responses = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
        client_id, str(args.flow_id))

    result = ApiListFlowRequestsResult()
    stop = None
    if args.count:
      stop = args.offset + args.count

    for request, response_dict in itertools.islice(requests_and_responses,
                                                   args.offset, stop):
      request_state = rdf_flow_runner.RequestState(
          client_id=client_id,
          id=request.request_id,
          next_state=request.next_state,
          session_id="{}/flows/{}".format(client_id, str(request.flow_id)))
      api_request = ApiFlowRequest(
          request_id=str(request.request_id), request_state=request_state)

      if response_dict:
        responses = [
            response_dict[i].AsLegacyGrrMessage() for i in sorted(response_dict)
        ]
        for r in responses:
          r.ClearPayload()

        api_request.responses = responses

      result.items.append(api_request)

    return result


class ApiListFlowResultsArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowResultsArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiListFlowResultsResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowResultsResult
  rdf_deps = [
      ApiFlowResult,
  ]


class ApiListFlowResultsHandler(api_call_handler_base.ApiCallHandler):
  """Renders results of a given flow."""

  args_type = ApiListFlowResultsArgs
  result_type = ApiListFlowResultsResult

  def Handle(self, args, context=None):
    results = data_store.REL_DB.ReadFlowResults(
        str(args.client_id),
        str(args.flow_id),
        args.offset,
        args.count or db.MAX_COUNT,
        with_substring=args.filter or None,
        with_tag=args.with_tag or None)
    total_count = data_store.REL_DB.CountFlowResults(
        str(args.client_id), str(args.flow_id))
    wrapped_items = [ApiFlowResult().InitFromFlowResult(r) for r in results]

    return ApiListFlowResultsResult(
        items=wrapped_items, total_count=total_count)


class ApiListParsedFlowResultsArgs(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the arguments of the method for parsing flow results."""

  protobuf = flow_pb2.ApiListParsedFlowResultsArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiListParsedFlowResultsResult(rdf_structs.RDFProtoStruct):
  """An RDF wrapper for the results of the method for parsing flow results."""

  protobuf = flow_pb2.ApiListParsedFlowResultsResult
  rdf_deps = [
      ApiFlowResult,
  ]


class ApiListParsedFlowResultsHandler(api_call_handler_base.ApiCallHandler):
  """An API handler for the method for on-demand parsing of flow results."""

  args_type = ApiListParsedFlowResultsArgs
  result_type = ApiListParsedFlowResultsResult

  _FLOW_RESULTS_BATCH_SIZE = 5000
  _TAG_ARTIFACT_NAME = re.compile(r"artifact:(?P<name>\w+)")

  def Handle(
      self,
      args: ApiListParsedFlowResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> ApiListParsedFlowResultsResult:
    client_id = str(args.client_id)
    flow_id = str(args.flow_id)

    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    if flow_obj.flow_class_name != collectors.ArtifactCollectorFlow.__name__:
      message = "Not an artifact-collector flow: {}"
      raise ValueError(message.format(flow_obj.flow_class_name))

    if flow_obj.args.apply_parsers:
      message = "Flow already parsed its results"
      raise ValueError(message)

    flow_results = data_store.REL_DB.ReadFlowResults(
        client_id=client_id,
        flow_id=flow_id,
        offset=args.offset,
        count=args.count)

    # We determine results collection timestamp as the maximum of timestamps of
    # individual flow results. We cannot use just the flow timestamp for this,
    # because flows can be modified, affecting the timestamp. We also don't want
    # to use flow start time, because it can be to "early" to do parsing.
    if flow_results:
      flow_results_timestamp = max([_.timestamp for _ in flow_results])
    else:
      flow_results_timestamp = None

    flow_results_by_artifact = {}

    for flow_result in flow_results:
      artifact_name_match = self._TAG_ARTIFACT_NAME.match(flow_result.tag)
      if artifact_name_match is None:
        continue

      artifact_name = artifact_name_match["name"]
      artifact_results = flow_results_by_artifact.setdefault(artifact_name, [])
      artifact_results.append(flow_result)

    knowledge_base = flow_obj.persistent_data["knowledge_base"]

    result = ApiListParsedFlowResultsResult()

    for artifact_name, flow_results in flow_results_by_artifact.items():
      factory = parsers.ArtifactParserFactory(artifact_name)

      applicator = artifact.ParserApplicator(
          factory,
          client_id=client_id,
          knowledge_base=knowledge_base,
          timestamp=flow_results_timestamp)
      applicator.Apply([flow_result.payload for flow_result in flow_results])

      for response in applicator.Responses():
        item = ApiFlowResult()
        item.payload_type = response.__class__.__name__
        item.payload = response
        item.tag = f"artifact:{artifact_name}"
        result.items.Append(item)

      result.errors.Extend(map(str, applicator.Errors()))

    return result


class ApiListFlowLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowLogsArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiListFlowLogsResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowLogsResult
  rdf_deps = [ApiFlowLog]


class ApiListFlowLogsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of logs for the current client and flow."""

  args_type = ApiListFlowLogsArgs
  result_type = ApiListFlowLogsResult

  def Handle(self, args, context=None):
    count = args.count or db.MAX_COUNT

    logs = data_store.REL_DB.ReadFlowLogEntries(
        str(args.client_id), str(args.flow_id), args.offset, count, args.filter)
    total_count = data_store.REL_DB.CountFlowLogEntries(
        str(args.client_id), str(args.flow_id))
    return ApiListFlowLogsResult(
        items=[
            ApiFlowLog().InitFromFlowLogEntry(log, str(args.flow_id))
            for log in logs
        ],
        total_count=total_count)


class ApiGetFlowResultsExportCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiGetFlowResultsExportCommandArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiGetFlowResultsExportCommandResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiGetFlowResultsExportCommandResult


class ApiGetFlowResultsExportCommandHandler(api_call_handler_base.ApiCallHandler
                                           ):
  """Renders GRR export tool command line that exports flow results."""

  args_type = ApiGetFlowResultsExportCommandArgs
  result_type = ApiGetFlowResultsExportCommandResult

  def Handle(self, args, context=None):
    output_fname = re.sub("[^0-9a-zA-Z]+", "_",
                          "%s_%s" % (args.client_id, args.flow_id))
    code_to_execute = ("""grrapi.Client("%s").Flow("%s").GetFilesArchive()."""
                       """WriteToFile("./flow_results_%s.zip")""") % (
                           args.client_id, args.flow_id, output_fname)

    export_command_str = " ".join([
        config.CONFIG["AdminUI.export_command"], "--exec_code",
        utils.ShellQuote(code_to_execute)
    ])

    return ApiGetFlowResultsExportCommandResult(command=export_command_str)


class ApiGetFlowFilesArchiveArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiGetFlowFilesArchiveArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiGetFlowFilesArchiveHandler(api_call_handler_base.ApiCallHandler):
  """Generates archive with all files referenced in flow's results."""

  args_type = ApiGetFlowFilesArchiveArgs

  def __init__(self, exclude_path_globs=None, include_only_path_globs=None):
    """Constructor.

    Args:
      exclude_path_globs: List of paths.GlobExpression values. Exclusion will
        be applied before include_only_path_globs.
      include_only_path_globs: List of paths.GlobExpression values. Inclusion
        will be applied after the exclude_path_globs.

    Raises:
      ValueError: If exactly one of exclude/include_only_path_globs is passed,
        but the other argument is not.

    Note that exclude/include_only_path_globs arguments can only be passed
    together. The algorithm of applying the lists is the following:
    1. If the lists are not set, include the file into the archive. Otherwise:
    2. If the file matches the exclude list, skip the file. Otherwise:
    3. If the file does match the include list, skip the file.
    """
    super(api_call_handler_base.ApiCallHandler, self).__init__()

    if len([
        x for x in (exclude_path_globs, include_only_path_globs) if x is None
    ]) == 1:
      raise ValueError("exclude_path_globs/include_only_path_globs have to be "
                       "set/unset together.")

    self.exclude_path_globs = exclude_path_globs
    self.include_only_path_globs = include_only_path_globs

  def _WrapContentGenerator(self, generator, flow_results, args, context=None):
    flow_ref = rdf_objects.FlowReference(
        client_id=args.client_id, flow_id=args.flow_id)
    object_reference = rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.FLOW, flow=flow_ref)
    try:
      for item in generator.Generate(flow_results):
        yield item

      notification.Notify(
          context.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED,
          "Downloaded archive of flow %s from client %s (archived %d "
          "out of %d items, archive size is %d)" %
          (args.flow_id, args.client_id, len(generator.archived_files),
           generator.total_files, generator.output_size), object_reference)

    except Exception as e:
      notification.Notify(
          context.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
          "Archive generation failed for flow %s on client %s: %s" %
          (args.flow_id, args.client_id, e), object_reference)

      raise

  def _WrapContentGeneratorWithMappings(self,
                                        generator,
                                        mappings,
                                        args,
                                        context=None):
    flow_ref = rdf_objects.FlowReference(
        client_id=args.client_id, flow_id=args.flow_id)
    object_reference = rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.FLOW, flow=flow_ref)
    try:
      for item in generator.Generate(mappings):
        yield item

      notification.Notify(
          context.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED,
          "Downloaded archive of flow %s from client %s (archived %d files, "
          "archive size is %d)" %
          (args.flow_id, args.client_id, generator.num_archived_files,
           generator.output_size), object_reference)

    except Exception as e:
      notification.Notify(
          context.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
          "Archive generation failed for flow %s on client %s: %s" %
          (args.flow_id, args.client_id, e), object_reference)

      raise

  def _BuildPredicate(self, client_id, context=None):
    if self.include_only_path_globs is None:
      return None

    kb = data_store_utils.GetClientKnowledgeBase(client_id)

    exclude_regexes = []
    for expression in self.exclude_path_globs:
      for pattern in expression.Interpolate(knowledge_base=kb):
        exclude_regexes.append(rdf_paths.GlobExpression(pattern).AsRegEx())

    include_only_regexes = []
    for expression in self.include_only_path_globs:
      for pattern in expression.Interpolate(knowledge_base=kb):
        include_only_regexes.append(rdf_paths.GlobExpression(pattern).AsRegEx())

    def Predicate(client_path):
      # Enforce leading / since Regexes require it.
      path = "/" + client_path.Path().lstrip("/")
      return (not any(r.Match(path) for r in exclude_regexes) and
              any(r.Match(path) for r in include_only_regexes))

    return Predicate

  def _GetFlow(self, args, context=None):
    client_id = str(args.client_id)
    flow_id = str(args.flow_id)
    flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0,
                                                     db.MAX_COUNT)

    return flow_obj, flow_results

  def Handle(self, args, context=None):
    flow_object, flow_results = self._GetFlow(args, context)
    flow_api_object = ApiFlow().InitFromFlowObject(flow_object)
    flow_instance = flow_base.FlowBase.CreateFlowInstance(flow_object)
    try:
      mappings = flow_instance.GetFilesArchiveMappings(flow_results)
    except NotImplementedError:
      mappings = None

    description = ("Files downloaded by flow %s (%s) that ran on client %s by "
                   "user %s on %s" %
                   (flow_api_object.name, args.flow_id, args.client_id,
                    flow_api_object.creator, flow_api_object.started_at))

    target_file_prefix = "%s_flow_%s_%s" % (
        args.client_id, flow_api_object.name, str(
            flow_api_object.flow_id).replace(":", "_"))

    if args.archive_format == args.ArchiveFormat.ZIP:
      archive_format = archive_generator.CollectionArchiveGenerator.ZIP
      file_extension = ".zip"
    elif args.archive_format == args.ArchiveFormat.TAR_GZ:
      archive_format = archive_generator.CollectionArchiveGenerator.TAR_GZ
      file_extension = ".tar.gz"
    else:
      raise ValueError("Unknown archive format: %s" % args.archive_format)

    # Only use the new-style flow archive generator for the flows that
    # have the GetFilesArchiveMappings defined.
    if mappings:
      a_gen = archive_generator.FlowArchiveGenerator(flow_object,
                                                     archive_format)
      content_generator = self._WrapContentGeneratorWithMappings(
          a_gen, mappings, args, context=context)
    else:
      a_gen = archive_generator.CollectionArchiveGenerator(
          prefix=target_file_prefix,
          description=description,
          archive_format=archive_format,
          predicate=self._BuildPredicate(str(args.client_id), context=context),
          client_id=args.client_id.ToString())
      content_generator = self._WrapContentGenerator(
          a_gen, flow_results, args, context=context)

    return api_call_handler_base.ApiBinaryStream(
        target_file_prefix + file_extension,
        content_generator=content_generator)


class ApiListFlowOutputPluginsArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowOutputPluginsArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiListFlowOutputPluginsResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowOutputPluginsResult
  rdf_deps = [
      api_output_plugin.ApiOutputPlugin,
  ]


class ApiListFlowOutputPluginsHandler(api_call_handler_base.ApiCallHandler):
  """Renders output plugins descriptors and states for a given flow."""

  args_type = ApiListFlowOutputPluginsArgs
  result_type = ApiListFlowOutputPluginsResult

  def Handle(self, args, context=None):
    flow_obj = data_store.REL_DB.ReadFlowObject(
        str(args.client_id), str(args.flow_id))
    output_plugins_states = flow_obj.output_plugins_states

    type_indices = {}
    result = []
    for output_plugin_state in output_plugins_states:
      plugin_state = output_plugin_state.plugin_state.Copy()
      if "source_urn" in plugin_state:
        del plugin_state["source_urn"]
      if "token" in plugin_state:
        del plugin_state["token"]

      plugin_descriptor = output_plugin_state.plugin_descriptor
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


def GetOutputPluginIndex(plugin_descriptors: Iterable[
    rdf_output_plugin.OutputPluginDescriptor], plugin_id: str) -> int:
  """Gets an output plugin index for a plugin with a given id.

  Historically output plugins descriptors were stored in dicts-like
  structures with unique identifiers as keys. In REL_DB-based implementation,
  however, both plugin descriptors and their states are stored in flat
  lists (see Flow definition in flows.proto).

  The ids were formed as "<plugin name>_<plugin index>" where plugin index
  was incremented for every plugin with a same name. For example, if we had
  EmailOutputPlugin and 2 BigQueryOutputPlugins, their ids would be:
  EmailOutputPlugin_0, BigQueryOutputPlugin_0, BigQueryOutputPlugin_1.

  To preserve backwards API compatibility, we emulate the old behavior by
  identifying plugins with same plugin ids as before..

  Args:
    plugin_descriptors: An iterable of OutputPluginDescriptor objects.
    plugin_id: Plugin id to search for.

  Returns:
    An index of a plugin in plugin_descriptors iterable corresponding to a
    given plugin_id.

  Raises:
    OutputPluginNotFoundError: if no plugin corresponding to a given plugin_id
    was found.
  """

  used_names = collections.Counter()
  for (index, desc) in enumerate(plugin_descriptors):
    cur_plugin_id = "%s_%d" % (desc.plugin_name, used_names[desc.plugin_name])
    used_names[desc.plugin_name] += 1

    if cur_plugin_id == plugin_id:
      return index

  raise OutputPluginNotFoundError("Can't find output plugin %s" % plugin_id)


class ApiListFlowOutputPluginLogsHandlerBase(
    api_call_handler_base.ApiCallHandler):
  """Base class used to define log and error messages handlers."""

  __abstract = True  # pylint: disable=g-bad-name

  log_entry_type = None

  def Handle(self, args, context=None):
    flow_obj = data_store.REL_DB.ReadFlowObject(
        str(args.client_id), str(args.flow_id))

    index = GetOutputPluginIndex(flow_obj.output_plugins, args.plugin_id)
    output_plugin_id = "%d" % index

    logs = data_store.REL_DB.ReadFlowOutputPluginLogEntries(
        str(args.client_id),
        str(args.flow_id),
        output_plugin_id,
        args.offset,
        args.count or db.MAX_COUNT,
        with_type=self.__class__.log_entry_type)
    total_count = data_store.REL_DB.CountFlowOutputPluginLogEntries(
        str(args.client_id),
        str(args.flow_id),
        output_plugin_id,
        with_type=self.__class__.log_entry_type)

    return self.result_type(
        total_count=total_count,
        items=[l.ToOutputPluginBatchProcessingStatus() for l in logs])


class ApiListFlowOutputPluginLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowOutputPluginLogsArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiListFlowOutputPluginLogsResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowOutputPluginLogsResult
  rdf_deps = [
      output_plugin.OutputPluginBatchProcessingStatus,
  ]


class ApiListFlowOutputPluginLogsHandler(ApiListFlowOutputPluginLogsHandlerBase
                                        ):
  """Renders flow's output plugin's logs."""

  log_entry_type = rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.LOG

  args_type = ApiListFlowOutputPluginLogsArgs
  result_type = ApiListFlowOutputPluginLogsResult


class ApiListFlowOutputPluginErrorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowOutputPluginErrorsArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiListFlowOutputPluginErrorsResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowOutputPluginErrorsResult
  rdf_deps = [
      output_plugin.OutputPluginBatchProcessingStatus,
  ]


class ApiListFlowOutputPluginErrorsHandler(
    ApiListFlowOutputPluginLogsHandlerBase):
  """Renders flow's output plugin's errors."""

  log_entry_type = rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.ERROR

  args_type = ApiListFlowOutputPluginErrorsArgs
  result_type = ApiListFlowOutputPluginErrorsResult


class ApiListFlowsArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowsArgs
  rdf_deps = [
      client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]


class ApiListFlowsResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowsResult
  rdf_deps = [
      ApiFlow,
  ]


class ApiListFlowsHandler(api_call_handler_base.ApiCallHandler):
  """Lists flows launched on a given client."""

  args_type = ApiListFlowsArgs
  result_type = ApiListFlowsResult

  def _HandleTopFlowsOnly(self, args, context=None):
    top_flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id=str(args.client_id),
        min_create_time=args.min_started_at,
        max_create_time=args.max_started_at,
        include_child_flows=False)

    result = [
        ApiFlow().InitFromFlowObject(
            f_data, with_args=True, with_progress=True) for f_data in top_flows
    ]
    # TODO(hanuszczak): Consult with the team what should we do in case of flows
    # with missing information.
    result.sort(key=lambda f: f.started_at or 0, reverse=True)
    result = result[args.offset:]
    if args.count:
      result = result[:args.count]
    return ApiListFlowsResult(items=result)

  def _HandleAllFlows(self, args, context=None):
    all_flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id=str(args.client_id),
        min_create_time=args.min_started_at,
        max_create_time=args.max_started_at,
        include_child_flows=True)
    api_flow_dict = {
        rdf_flow.flow_id:
        ApiFlow().InitFromFlowObject(rdf_flow, with_args=False)
        for rdf_flow in all_flows
    }
    # TODO(user): this is done for backwards API compatibility.
    # Remove when AFF4 is gone.
    for rdf_flow in api_flow_dict.values():
      rdf_flow.nested_flows = []

    child_flow_ids = set()

    for rdf_flow in all_flows:
      if not rdf_flow.parent_flow_id:
        continue

      if rdf_flow.parent_flow_id in api_flow_dict:
        parent_flow = api_flow_dict[rdf_flow.parent_flow_id]
        parent_flow.nested_flows.Append(api_flow_dict[rdf_flow.flow_id])
        child_flow_ids.add(rdf_flow.flow_id)

    result = [
        f for f in api_flow_dict.values() if f.flow_id not in child_flow_ids
    ]
    # TODO(hanuszczak): Consult with the team what should we do in case of flows
    # with missing information.
    result.sort(key=lambda f: f.started_at or 0, reverse=True)
    result = result[args.offset:]
    if args.count:
      result = result[:args.count]
    return ApiListFlowsResult(items=result)

  def Handle(self, args, context=None):
    if args.top_flows_only:
      return self._HandleTopFlowsOnly(args, context=context)
    else:
      return self._HandleAllFlows(args, context=context)


class ApiCreateFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiCreateFlowArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlow,
      ApiFlowReference,
  ]


def _SanitizeApiCreateFlowArgs(
    args: ApiCreateFlowArgs
) -> Tuple[Type[flow_base.FlowBase], rdf_flow_runner.FlowRunnerArgs]:
  """Validates and sanitizes args for flow scheduling and starting."""
  if not args.client_id:
    raise ValueError("client_id must be provided")

  runner_args = args.flow.runner_args.Copy()
  flow_name = args.flow.name
  if not flow_name:
    flow_name = runner_args.flow_name
  if not flow_name:
    raise RuntimeError("Flow name is not specified.")

  # Clear all fields marked with HIDDEN, except for output_plugins - they are
  # marked HIDDEN, because we have a separate UI for them, not because they
  # shouldn't be shown to the user at all.
  #
  # TODO(user): Refactor the code to remove the HIDDEN label from
  # FlowRunnerArgs.output_plugins.
  runner_args.ClearFieldsWithLabel(
      rdf_structs.SemanticDescriptor.Labels.HIDDEN, exceptions="output_plugins")

  if args.original_flow:
    runner_args.original_flow = rdf_objects.FlowReference(
        flow_id=str(args.original_flow.flow_id),
        client_id=str(args.original_flow.client_id))

  flow_cls = registry.FlowRegistry.FlowClassByName(flow_name)
  return flow_cls, runner_args


class ApiCreateFlowHandler(api_call_handler_base.ApiCallHandler):
  """Starts a flow on a given client with given parameters."""

  args_type = ApiCreateFlowArgs
  result_type = ApiFlow

  def Handle(self, args, context=None):
    flow_cls, runner_args = _SanitizeApiCreateFlowArgs(args)

    cpu_limit = None
    if runner_args.HasField("cpu_limit"):
      cpu_limit = runner_args.cpu_limit
    network_bytes_limit = None
    if runner_args.HasField("network_bytes_limit"):
      network_bytes_limit = runner_args.network_bytes_limit

    flow_id = flow.StartFlow(
        client_id=str(args.client_id),
        cpu_limit=cpu_limit,
        creator=context.username,
        flow_args=args.flow.args,
        flow_cls=flow_cls,
        network_bytes_limit=network_bytes_limit,
        original_flow=runner_args.original_flow,
        output_plugins=runner_args.output_plugins,
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(str(args.client_id), flow_id)

    res = ApiFlow().InitFromFlowObject(flow_obj)
    res.context = None
    return res


class ApiCancelFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiCancelFlowArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiCancelFlowHandler(api_call_handler_base.ApiCallHandler):
  """Cancels given flow on a given client."""

  args_type = ApiCancelFlowArgs
  result_type = ApiFlow

  def Handle(self, args, context=None):
    flow_base.TerminateFlow(
        str(args.client_id), str(args.flow_id), reason="Cancelled in GUI")
    flow_obj = data_store.REL_DB.ReadFlowObject(
        str(args.client_id), str(args.flow_id))
    return ApiFlow().InitFromFlowObject(flow_obj)


class ApiListFlowDescriptorsResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowDescriptorsResult
  rdf_deps = [
      ApiFlowDescriptor,
  ]


class ApiListFlowDescriptorsHandler(api_call_handler_base.ApiCallHandler):
  """Renders all available flows descriptors."""

  result_type = ApiListFlowDescriptorsResult

  def __init__(self, access_check_fn=None):
    super().__init__()
    self.access_check_fn = access_check_fn

  def Handle(self, args, context=None):
    """Renders list of descriptors for all the flows."""

    result = []
    for name, cls in sorted(registry.FlowRegistry.FLOW_REGISTRY.items()):

      # Flows without a category do not show up in the GUI.
      if not getattr(cls, "category", None):
        continue

      # Only show flows that the user is allowed to start.
      try:
        if self.access_check_fn:
          self.access_check_fn(context.username, name)
      except access_control.UnauthorizedAccess:
        continue

      result.append(ApiFlowDescriptor().InitFromFlowClass(cls, context=context))

    return ApiListFlowDescriptorsResult(items=result)


class ApiGetExportedFlowResultsArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiGetExportedFlowResultsArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiGetExportedFlowResultsHandler(api_call_handler_base.ApiCallHandler):
  """Exports results of a given flow with an instant output plugin."""

  args_type = ApiGetExportedFlowResultsArgs

  _RESULTS_PAGE_SIZE = 1000

  def Handle(self, args, context=None):
    iop_cls = instant_output_plugin.InstantOutputPlugin
    plugin_cls = iop_cls.GetPluginClassByPluginName(args.plugin_name)

    # TODO(user): Instant output plugins shouldn't depend on contexts
    # and URNs.
    flow_urn = rdfvalue.RDFURN("{}/flows/{}".format(args.client_id,
                                                    args.flow_id))
    plugin = plugin_cls(
        source_urn=flow_urn,
        token=access_control.ACLToken(username=context.username))

    client_id = str(args.client_id)
    flow_id = str(args.flow_id)
    types = data_store.REL_DB.CountFlowResultsByType(client_id, flow_id)

    def FetchFn(type_name):
      """Fetches all flow results of a given type."""
      offset = 0
      while True:
        results = data_store.REL_DB.ReadFlowResults(
            client_id,
            flow_id,
            offset=offset,
            count=self._RESULTS_PAGE_SIZE,
            with_type=type_name)
        if not results:
          break

        for r in results:
          msg = r.AsLegacyGrrMessage()
          msg.source = client_id
          yield msg

        offset += self._RESULTS_PAGE_SIZE

    content_generator = instant_output_plugin.ApplyPluginToTypedCollection(
        plugin, types, FetchFn)

    return api_call_handler_base.ApiBinaryStream(
        plugin.output_file_name, content_generator=content_generator)


class ApiExplainGlobExpressionArgs(rdf_structs.RDFProtoStruct):
  """Args for ApiExplainGlobExpressionHandler."""
  protobuf = flow_pb2.ApiExplainGlobExpressionArgs
  rdf_deps = [
      client.ApiClientId,
  ]


class ApiExplainGlobExpressionResult(rdf_structs.RDFProtoStruct):
  """Results of ApiExplainGlobExpressionHandler."""
  protobuf = flow_pb2.ApiExplainGlobExpressionResult
  rdf_deps = [
      rdf_paths.GlobComponentExplanation,
  ]


class ApiExplainGlobExpressionHandler(api_call_handler_base.ApiCallHandler):
  """Gives examples for the components of a GlobExpression."""

  args_type = ApiExplainGlobExpressionArgs
  result_type = ApiExplainGlobExpressionResult

  def Handle(self, args, context=None):
    ge = rdf_paths.GlobExpression(args.glob_expression)
    ge.Validate()

    kb = data_store_utils.GetClientKnowledgeBase(str(args.client_id))
    components = ge.ExplainComponents(args.example_count, kb)

    return ApiExplainGlobExpressionResult(components=components)


class ApiScheduledFlow(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiScheduledFlow
  rdf_deps = [
      rdf_flow_runner.FlowRunnerArgs,
      rdfvalue.RDFDatetime,
  ]

  @classmethod
  def FromScheduledFlow(cls, scheduled_flow):
    return cls(
        scheduled_flow_id=scheduled_flow.scheduled_flow_id,
        client_id=scheduled_flow.client_id,
        creator=scheduled_flow.creator,
        flow_name=scheduled_flow.flow_name,
        flow_args=scheduled_flow.flow_args,
        runner_args=scheduled_flow.runner_args,
        create_time=scheduled_flow.create_time)


class ApiScheduleFlowHandler(api_call_handler_base.ApiCallHandler):
  """Schedules a flow on a client, to be started upon approval grant."""

  args_type = ApiCreateFlowArgs
  result_type = ApiScheduledFlow

  def Handle(self, args, context=None):
    flow_cls, runner_args = _SanitizeApiCreateFlowArgs(args)

    args.flow.args.Validate()

    # TODO: Handle the case where the requesting user already has
    # approval to start the flow on the client.

    scheduled_flow = flow.ScheduleFlow(
        client_id=str(args.client_id),
        creator=context.username,
        flow_name=flow_cls.__name__,
        flow_args=args.flow.args,
        runner_args=runner_args)

    return ApiScheduledFlow.FromScheduledFlow(scheduled_flow)


class ApiListScheduledFlowsArgs(rdf_structs.RDFProtoStruct):
  """Args for ApiListScheduledFlowsHandler."""
  protobuf = flow_pb2.ApiListScheduledFlowsArgs
  rdf_deps = []


class ApiListScheduledFlowsResult(rdf_structs.RDFProtoStruct):
  """Results of ApiListScheduledFlowsHandler."""
  protobuf = flow_pb2.ApiListScheduledFlowsResult
  rdf_deps = [ApiScheduledFlow]


class ApiListScheduledFlowsHandler(api_call_handler_base.ApiCallHandler):
  """Lists all scheduled flows from a user on a client."""
  args_type = ApiListScheduledFlowsArgs
  result_type = ApiListScheduledFlowsResult

  def Handle(self, args, context=None):
    results = flow.ListScheduledFlows(
        client_id=args.client_id, creator=args.creator)
    results = sorted(results, key=lambda sf: sf.create_time)
    results = [ApiScheduledFlow.FromScheduledFlow(sf) for sf in results]

    return ApiListScheduledFlowsResult(scheduled_flows=results)


class ApiUnscheduleFlowArgs(rdf_structs.RDFProtoStruct):
  """Args for ApiUnscheduleFlowHandler."""
  protobuf = flow_pb2.ApiUnscheduleFlowArgs
  rdf_deps = []


class ApiUnscheduleFlowResult(rdf_structs.RDFProtoStruct):
  """Results of ApiUnscheduleFlowHandler."""
  protobuf = flow_pb2.ApiUnscheduleFlowResult
  rdf_deps = []


class ApiUnscheduleFlowHandler(api_call_handler_base.ApiCallHandler):
  """Unschedules and deletes a previously scheduled flow."""
  args_type = ApiUnscheduleFlowArgs
  result_type = ApiUnscheduleFlowResult

  def Handle(self, args, context=None):
    flow.UnscheduleFlow(
        client_id=args.client_id,
        creator=context.username,
        scheduled_flow_id=args.scheduled_flow_id)
    return ApiUnscheduleFlowResult()
