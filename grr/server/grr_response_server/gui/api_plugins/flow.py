#!/usr/bin/env python
"""API handlers for dealing with flows."""

import collections
from collections.abc import Callable, Iterable, Iterator, Sequence
import itertools
import logging
import re
from typing import Any, Optional, Union

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import mig_flows
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import mig_structs
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_proto.api import flow_pb2
from grr_response_proto.api import output_plugin_pb2 as api_output_plugin_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import data_store_utils
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import instant_output_plugin
from grr_response_server import instant_output_plugin_registry
from grr_response_server import notification
from grr_response_server.databases import db
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.gui import archive_generator
from grr_response_server.gui import mig_api_call_handler_utils
from grr_response_server.gui.api_plugins import client
from grr_response_server.models import protobuf_utils as models_utils
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import mig_flow_runner


class FlowNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a flow is not found."""


class OutputPluginNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when an output plugin is not found."""


class InstantOutputPluginNotFoundError(
    api_call_handler_base.ResourceNotFoundError
):
  """Raised when an instant output plugin is not found."""


def GetFlowContextStateFromFlowObject(
    flow_obj: flows_pb2.Flow,
) -> Optional["flows_pb2.FlowContext.State"]:
  """Returns the state of the ApiFlow based on the flow_obj."""
  if flow_obj.HasField("client_crash_info"):
    return flows_pb2.FlowContext.State.CLIENT_CRASHED
  elif flow_obj.flow_state == flows_pb2.Flow.FlowState.RUNNING:
    return flows_pb2.FlowContext.State.RUNNING
  elif flow_obj.flow_state == flows_pb2.Flow.FlowState.FINISHED:
    return flows_pb2.FlowContext.State.TERMINATED
  elif flow_obj.flow_state == flows_pb2.Flow.FlowState.ERROR:
    return flows_pb2.FlowContext.State.ERROR


def GetApiFlowStateFromFlowObject(
    flow_obj: flows_pb2.Flow,
) -> Optional["flow_pb2.ApiFlow.State"]:
  """Returns the state of the ApiFlow based on the flow_obj."""
  if flow_obj.HasField("client_crash_info"):
    return flow_pb2.ApiFlow.State.CLIENT_CRASHED
  elif flow_obj.flow_state == flows_pb2.Flow.FlowState.RUNNING:
    return flow_pb2.ApiFlow.State.RUNNING
  elif flow_obj.flow_state == flows_pb2.Flow.FlowState.FINISHED:
    return flow_pb2.ApiFlow.State.TERMINATED
  elif flow_obj.flow_state == flows_pb2.Flow.FlowState.ERROR:
    return flow_pb2.ApiFlow.State.ERROR


def InitFlowContextFromFlowObject(
    flow_obj: flows_pb2.Flow,
) -> flows_pb2.FlowContext:
  """Creates a FlowContext from a Flow object."""

  flow_context = flows_pb2.FlowContext()
  models_utils.CopyAttr(flow_obj, flow_context, "create_time")
  models_utils.CopyAttr(flow_obj, flow_context, "creator")
  models_utils.CopyAttr(flow_obj, flow_context, "current_state")
  models_utils.CopyAttr(flow_obj, flow_context, "next_outbound_id")
  models_utils.CopyAttr(flow_obj, flow_context, "backtrace")
  models_utils.CopyAttr(flow_obj, flow_context, "error_message", "status")

  # TODO(amoser): No need to set this in all cases once the legacy API
  # is removed.
  flow_context.outstanding_requests = (
      flow_obj.next_outbound_id - flow_obj.next_request_to_process
  )
  if flow_obj.HasField("network_bytes_sent") and flow_obj.network_bytes_sent:
    flow_context.network_bytes_sent = flow_obj.network_bytes_sent
    flow_context.client_resources.network_bytes_sent = (
        flow_obj.network_bytes_sent
    )
  if flow_obj.HasField("cpu_time_used"):
    flow_context.client_resources.cpu_usage.CopyFrom(flow_obj.cpu_time_used)

  state = GetFlowContextStateFromFlowObject(flow_obj)
  if state is not None:
    flow_context.state = state

  if flow_obj.HasField("long_flow_id"):
    flow_context.session_id = str(rdfvalue.SessionID(flow_obj.long_flow_id))

  if flow_obj.output_plugins_states:
    flow_context.output_plugins_states.extend(flow_obj.output_plugins_states)

  return flow_context


def InitRunnerArgsFromFlowObject(
    flow_obj: flows_pb2.Flow,
) -> flows_pb2.FlowRunnerArgs:
  """Creates FlowRunnerArgs from a Flow object."""

  runner_args = flows_pb2.FlowRunnerArgs()
  if flow_obj.HasField("client_id"):
    runner_args.client_id = str(rdfvalue.RDFURN(flow_obj.client_id))

  models_utils.CopyAttr(flow_obj, runner_args, "flow_class_name", "flow_name")
  models_utils.CopyAttr(flow_obj, runner_args, "cpu_limit")
  models_utils.CopyAttr(flow_obj, runner_args, "network_bytes_limit")

  if flow_obj.disable_rrg_support:
    runner_args.disable_rrg_support = flow_obj.disable_rrg_support

  if flow_obj.output_plugins:
    runner_args.output_plugins.extend(flow_obj.output_plugins)

  return runner_args


def InitApiFlowFromFlowObject(
    flow_obj: flows_pb2.Flow,
    with_progress: bool = False,
    with_state_and_context: bool = False,
) -> flow_pb2.ApiFlow:
  """Creates an ApiFlow from a Flow object."""

  api_flow = flow_pb2.ApiFlow()

  models_utils.CopyAttr(flow_obj, api_flow, "flow_id")
  models_utils.CopyAttr(flow_obj, api_flow, "client_id")
  if flow_obj.HasField("long_flow_id"):
    api_flow.urn = str(rdfvalue.SessionID(flow_obj.long_flow_id))
  models_utils.CopyAttr(flow_obj, api_flow, "flow_class_name", "name")
  models_utils.CopyAttr(flow_obj, api_flow, "create_time", "started_at")
  models_utils.CopyAttr(
      flow_obj, api_flow, "last_update_time", "last_active_at"
  )
  api_flow.creator = flow_obj.creator
  api_flow.is_robot = flow_obj.creator in access_control.SYSTEM_USERS

  state = GetApiFlowStateFromFlowObject(flow_obj)
  if state is not None:
    api_flow.state = state
  else:
    api_flow.internal_error = (
        f"Error while opening flow: invalid state: {flow_obj.flow_state}"
    )

  flow_error = flow_obj.error_message or flow_obj.backtrace
  if flow_error:
    max_len = 4000
    if len(flow_error) > max_len:
      flow_error = flow_error[:max_len] + "…"
    api_flow.error_description = flow_error

  api_flow.runner_args.CopyFrom(InitRunnerArgsFromFlowObject(flow_obj))

  if flow_obj.original_flow.flow_id:
    api_flow.original_flow.flow_id = flow_obj.original_flow.flow_id
    if flow_obj.original_flow.HasField("client_id"):
      flow_obj.original_flow.client_id = str(
          rdfvalue.RDFURN(flow_obj.original_flow.client_id)
      )

  if with_state_and_context:
    api_flow.context.CopyFrom(InitFlowContextFromFlowObject(flow_obj))

  api_flow.args.CopyFrom(flow_obj.args)

  if with_progress:
    # TODO: Once all `Progress` is reported with a proto, start
    # calling `GetProgressProto()` here instead.
    flow_cls = _GetFlowClass(api_flow)
    if flow_cls:
      flow_instance = flow_cls(mig_flow_objects.ToRDFFlow(flow_obj))
      api_flow.progress.Pack(flow_instance.GetProgress().AsPrimitiveProto())
    api_flow.result_metadata.CopyFrom(flow_obj.result_metadata)

  if with_state_and_context and flow_obj.HasField("persistent_data"):
    rdf_persistend_data = mig_protodict.ToRDFAttributedDict(
        flow_obj.persistent_data
    )
    rdf_api_data = api_call_handler_utils.ApiDataObject().InitFromDataObject(
        rdf_persistend_data
    )
    api_flow.state_data.CopyFrom(
        mig_api_call_handler_utils.ToProtoApiDataObject(rdf_api_data)
    )
  if flow_obj.HasField("store"):
    api_flow.store.CopyFrom(flow_obj.store)

  return api_flow


def InitApiFlowLogFromFlowLogEntry(
    log_entry: flows_pb2.FlowLogEntry,
    flow_id: str,
) -> flow_pb2.ApiFlowLog:
  """Creates an ApiFlowLog from a FlowLogEntry."""

  api_flow_log = flow_pb2.ApiFlowLog()
  api_flow_log.flow_id = flow_id
  models_utils.CopyAttr(log_entry, api_flow_log, "message", "log_message")
  models_utils.CopyAttr(log_entry, api_flow_log, "timestamp")

  return api_flow_log


def InitApiFlowDescriptorFromFlowClass(
    flow_cls: type[flow_base.FlowBase],
    context: api_call_context.ApiCallContext,
) -> flow_pb2.ApiFlowDescriptor:
  """Creates an ApiFlowDescriptor from a flow class."""

  def _GetCallingPrototypeAsString(flow_cls) -> str:
    """Get a description of the calling prototype for this flow class."""

    flow_args = []
    flow_args.append("client_id=client_id")
    flow_args.append(
        f"flow_cls={flow_cls.__module__.split('.')[-1]}.{flow_cls.__name__}"
    )
    prototypes = []
    if flow_cls.args_type:
      for type_descriptor in flow_cls.args_type.type_infos:
        if not type_descriptor.hidden:
          prototypes.append(f"{type_descriptor.name}={type_descriptor.name}")

    flow_args = ", ".join(flow_args + prototypes)
    return "".join(["flow.StartFlow(", flow_args, ")"])

  def _GetFlowArgsHelpAsString(flow_cls: type[flow_base.FlowBase]) -> str:
    """Get a string description of the calling prototype for this flow."""
    output = []
    output.append("  Call Spec:")
    output.append(f"    {_GetCallingPrototypeAsString(flow_cls)}")
    output.append("")

    arg_list = sorted(
        _GetArgsDescription(flow_cls.args_type).items(), key=lambda x: x[0]
    )
    if not arg_list:
      output.append("  Args: None")
    else:
      output.append("  Args:")
      for arg, val in arg_list:
        output.append(f"    {arg}")
        output.append(f"      description: {val['description']}")
        output.append(f"      type: {val['type']}")
        output.append(f"      default: {val['default']}")
        output.append("")
    return "\n".join(output)

  def _GetArgsDescription(
      args_type: rdf_flows.EmptyFlowArgs,
  ) -> dict[str, dict[str, Any]]:
    """Get a simplified description of the args_type for a flow."""
    args: dict[str, dict[str, Any]] = {}
    if args_type:
      for type_descriptor in args_type.type_infos:
        if not type_descriptor.hidden:
          args[type_descriptor.name] = {
              "description": type_descriptor.description,
              "default": type_descriptor.default,
              "type": (
                  type_descriptor.type.__name__ if type_descriptor.type else ""
              ),
          }
    return args

  def GetFlowDocumentation(flow_cls: type[flow_base.FlowBase]) -> str:
    """Get a string description of the flow documentation."""
    return (
        f"{getattr(flow_cls, '__doc__', '')}\n\n"
        f"{_GetFlowArgsHelpAsString(flow_cls)}"
    )

  flow_descriptor = flow_pb2.ApiFlowDescriptor()
  flow_descriptor.name = flow_cls.__name__
  if flow_cls.friendly_name:
    flow_descriptor.friendly_name = flow_cls.friendly_name
  flow_descriptor.category = flow_cls.category.strip("/")
  flow_descriptor.doc = GetFlowDocumentation(flow_cls)
  flow_descriptor.args_type = flow_cls.args_type.__name__
  flow_default_args = flow_cls.GetDefaultArgs(context.username)
  flow_descriptor.default_args.Pack(flow_default_args.AsPrimitiveProto())
  flow_descriptor.behaviours.extend(sorted(flow_cls.behaviours))
  flow_descriptor.block_hunt_creation = flow_cls.block_hunt_creation

  return flow_descriptor


def InitApiScheduledFlowFromScheduledFlow(
    scheduled_flow: flows_pb2.ScheduledFlow,
) -> flow_pb2.ApiScheduledFlow:
  """Creates an ApiScheduledFlow from a ScheduledFlow."""
  api_scheduled_flow = flow_pb2.ApiScheduledFlow()
  models_utils.CopyAttr(scheduled_flow, api_scheduled_flow, "scheduled_flow_id")
  models_utils.CopyAttr(scheduled_flow, api_scheduled_flow, "client_id")
  models_utils.CopyAttr(scheduled_flow, api_scheduled_flow, "creator")
  models_utils.CopyAttr(scheduled_flow, api_scheduled_flow, "flow_name")
  models_utils.CopyAttr(scheduled_flow, api_scheduled_flow, "create_time")
  if scheduled_flow.HasField("flow_args"):
    api_scheduled_flow.flow_args.CopyFrom(scheduled_flow.flow_args)
  if scheduled_flow.HasField("runner_args"):
    api_scheduled_flow.runner_args.CopyFrom(scheduled_flow.runner_args)
  return api_scheduled_flow


def _GetFlowClass(
    api_flow: flow_pb2.ApiFlow,
) -> Optional[type[flow_base.FlowBase]]:
  flow_name = api_flow.name
  if not flow_name:
    flow_name = api_flow.runner_args.flow_name

  if flow_name:
    try:
      return registry.FlowRegistry.FlowClassByName(flow_name)
    except ValueError as e:
      logging.warning("Failed to get flow class for %s: %s", flow_name, e)


def InitApiFlowResultFromFlowResult(
    result: flows_pb2.FlowResult,
) -> flow_pb2.ApiFlowResult:
  """Creates an ApiFlowResult from a FlowResult."""
  api_flow_result = flow_pb2.ApiFlowResult()
  if result.HasField("payload"):
    api_flow_result.payload.CopyFrom(result.payload)
  models_utils.CopyAttr(result, api_flow_result, "timestamp")
  models_utils.CopyAttr(result, api_flow_result, "tag")
  return api_flow_result


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
      rdf_flow_objects.FlowResultMetadata,
      rdf_flow_runner.FlowRunnerArgs,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]

  def _GetFlowClass(self) -> Optional[type[flow_base.FlowBase]]:
    flow_name = self.name
    if not flow_name:
      flow_name = self.runner_args.flow_name

    if flow_name:
      try:
        return registry.FlowRegistry.FlowClassByName(flow_name)
      except ValueError as e:
        logging.warning("Failed to get flow class for %s: %s", flow_name, e)

  def GetArgsClass(self) -> Optional[type[rdf_structs.RDFProtoStruct]]:
    cls = self._GetFlowClass()
    if cls is not None:
      return cls.args_type

  def GetProgressClass(self) -> Optional[type[rdf_structs.RDFProtoStruct]]:
    cls = self._GetFlowClass()
    if cls is not None:
      return cls.progress_type


class ApiGetFlowHandler(api_call_handler_base.ApiCallHandler):
  """Renders given flow.

  Only top-level flows can be targeted.
  """

  proto_args_type = flow_pb2.ApiGetFlowArgs
  proto_result_type = flow_pb2.ApiFlow

  def Handle(
      self,
      args: flow_pb2.ApiGetFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiFlow:
    flow_obj = data_store.REL_DB.ReadFlowObject(args.client_id, args.flow_id)

    return InitApiFlowFromFlowObject(
        flow_obj, with_state_and_context=True, with_progress=True
    )


class ApiListFlowRequestsHandler(api_call_handler_base.ApiCallHandler):
  """Renders list of requests of a given flow."""

  proto_args_type = flow_pb2.ApiListFlowRequestsArgs
  proto_result_type = flow_pb2.ApiListFlowRequestsResult

  def Handle(
      self,
      args: flow_pb2.ApiListFlowRequestsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiListFlowRequestsResult:

    requests_and_responses = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
        args.client_id, args.flow_id
    )

    result = flow_pb2.ApiListFlowRequestsResult()
    stop = None
    if args.HasField("count"):
      stop = args.offset + args.count

    for request, response_dict in itertools.islice(
        requests_and_responses, args.offset, stop
    ):
      request_state = jobs_pb2.RequestState(
          client_id=str(rdfvalue.RDFURN(args.client_id)),
          id=request.request_id,
          next_state=request.next_state,
          session_id=str(
              rdfvalue.SessionID(
                  "{}/flows/{}".format(args.client_id, request.flow_id)
              )
          ),
      )
      api_request = flow_pb2.ApiFlowRequest(
          request_id=str(request.request_id), request_state=request_state
      )

      responses = []
      if response_dict:
        for _, response in sorted(response_dict.items()):
          if isinstance(response, flows_pb2.FlowResponse):
            response = mig_flow_objects.ToRDFFlowResponse(response)
          if isinstance(response, flows_pb2.FlowStatus):
            response = mig_flow_objects.ToRDFFlowStatus(response)
          if isinstance(response, flows_pb2.FlowIterator):
            response = mig_flow_objects.ToRDFFlowIterator(response)
          responses.append(
              mig_flows.ToProtoGrrMessage(response.AsLegacyGrrMessage())
          )

        for r in responses:
          r.ClearField("args_rdf_name")
          r.ClearField("args")

        api_request.responses.extend(responses)

      result.items.append(api_request)

    return result


class ApiListFlowResultsHandler(api_call_handler_base.ApiCallHandler):
  """Renders results of a given flow."""

  proto_args_type = flow_pb2.ApiListFlowResultsArgs
  proto_result_type = flow_pb2.ApiListFlowResultsResult

  def Handle(
      self,
      args: flow_pb2.ApiListFlowResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiListFlowResultsResult:
    results = data_store.REL_DB.ReadFlowResults(
        args.client_id,
        args.flow_id,
        args.offset,
        args.count or db.MAX_COUNT,
        with_substring=args.filter or None,
        with_tag=args.with_tag or None,
        with_type=args.with_type or None,
    )

    if args.filter:
      # TODO: with_substring is implemented in a hacky way,
      #   searching for a string in the serialized protobuf bytes. We decided
      #   to omit the same hacky implementation in CountFlowResults. Until
      #   CountFlowResults implements the same, or we generally improve this
      #   string search, total_count will be unset if `filter` is specified.
      total_count = None
    else:
      total_count = data_store.REL_DB.CountFlowResults(
          args.client_id,
          args.flow_id,
          # TODO: Add with_substring to CountFlowResults().
          with_tag=args.with_tag or None,
          with_type=args.with_type or None,
      )

    wrapped_items = [InitApiFlowResultFromFlowResult(r) for r in results]

    return flow_pb2.ApiListFlowResultsResult(
        items=wrapped_items, total_count=total_count
    )


class ApiListFlowLogsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of logs for the current client and flow."""

  proto_args_type = flow_pb2.ApiListFlowLogsArgs
  proto_result_type = flow_pb2.ApiListFlowLogsResult

  def Handle(
      self,
      args: flow_pb2.ApiListFlowLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiListFlowLogsResult:
    count = args.count or db.MAX_COUNT

    logs = data_store.REL_DB.ReadFlowLogEntries(
        args.client_id, args.flow_id, args.offset, count, args.filter
    )
    total_count = data_store.REL_DB.CountFlowLogEntries(
        str(args.client_id), str(args.flow_id)
    )
    return flow_pb2.ApiListFlowLogsResult(
        items=[
            InitApiFlowLogFromFlowLogEntry(log, args.flow_id) for log in logs
        ],
        total_count=total_count,
    )


class ApiGetFlowResultsExportCommandHandler(
    api_call_handler_base.ApiCallHandler
):
  """Renders GRR export tool command line that exports flow results."""

  proto_args_type = flow_pb2.ApiGetFlowResultsExportCommandArgs
  proto_result_type = flow_pb2.ApiGetFlowResultsExportCommandResult

  def Handle(
      self,
      args: flow_pb2.ApiGetFlowResultsExportCommandArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiGetFlowResultsExportCommandResult:
    output_fname = re.sub(
        "[^0-9a-zA-Z]+", "_", "%s_%s" % (args.client_id, args.flow_id)
    )
    code_to_execute = (
        """grrapi.Client("%s").Flow("%s").GetFilesArchive()."""
        """WriteToFile("./flow_results_%s.zip")"""
    ) % (args.client_id, args.flow_id, output_fname)

    export_command_str = " ".join([
        config.CONFIG["AdminUI.export_command"],
        "--exec_code",
        utils.ShellQuote(code_to_execute),
    ])

    return flow_pb2.ApiGetFlowResultsExportCommandResult(
        command=export_command_str
    )


# TODO: Check further usages and remove this RDFValue.
class ApiGetFlowFilesArchiveArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiGetFlowFilesArchiveArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiGetFlowFilesArchiveHandler(api_call_handler_base.ApiCallHandler):
  """Generates archive with all files referenced in flow's results."""

  proto_args_type = flow_pb2.ApiGetFlowFilesArchiveArgs

  def __init__(
      self,
      exclude_path_globs: Optional[Sequence[rdf_paths.GlobExpression]] = None,
      include_only_path_globs: Optional[
          Sequence[rdf_paths.GlobExpression]
      ] = None,
  ) -> None:
    """Constructor.

    Args:
      exclude_path_globs: Exclusion will be applied before
        include_only_path_globs.
      include_only_path_globs: Inclusion will be applied after the
        exclude_path_globs.

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

    if (
        len([
            x
            for x in (exclude_path_globs, include_only_path_globs)
            if x is None
        ])
        == 1
    ):
      raise ValueError(
          "exclude_path_globs/include_only_path_globs have to be "
          "set/unset together."
      )

    self.exclude_path_globs = exclude_path_globs
    self.include_only_path_globs = include_only_path_globs

  def _WrapContentGenerator(
      self,
      generator: archive_generator.CollectionArchiveGenerator,
      flow_results: list[flows_pb2.FlowResult],
      args: ApiGetFlowFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> Iterator[flows_pb2.FlowResult]:
    assert context is not None
    flow_ref = objects_pb2.FlowReference(
        client_id=args.client_id, flow_id=args.flow_id
    )
    object_reference = objects_pb2.ObjectReference(
        reference_type=objects_pb2.ObjectReference.Type.FLOW, flow=flow_ref
    )
    try:
      for item in generator.Generate(flow_results):
        yield item

      notification.Notify(
          context.username,
          objects_pb2.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED,
          "Downloaded archive of flow %s from client %s (archived %d "
          "out of %d items, archive size is %d)"
          % (
              args.flow_id,
              args.client_id,
              len(generator.archived_files),
              generator.total_files,
              generator.output_size,
          ),
          object_reference,
      )

    except Exception as e:
      notification.Notify(
          context.username,
          objects_pb2.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
          "Archive generation failed for flow %s on client %s: %s"
          % (args.flow_id, args.client_id, e),
          object_reference,
      )

      raise

  def _WrapContentGeneratorWithMappings(
      self,
      generator: archive_generator.FlowArchiveGenerator,
      mappings: Iterator[flow_base.ClientPathArchiveMapping],
      args: flow_pb2.ApiGetFlowFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    flow_ref = objects_pb2.FlowReference(
        client_id=args.client_id, flow_id=args.flow_id
    )
    object_reference = objects_pb2.ObjectReference(
        reference_type=objects_pb2.ObjectReference.Type.FLOW, flow=flow_ref
    )
    try:
      for item in generator.Generate(mappings):
        yield item

      notification.Notify(
          context.username,
          objects_pb2.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED,
          "Downloaded archive of flow %s from client %s (archived %d files, "
          "archive size is %d)"
          % (
              args.flow_id,
              args.client_id,
              generator.num_archived_files,
              generator.output_size,
          ),
          object_reference,
      )

    except Exception as e:
      notification.Notify(
          context.username,
          objects_pb2.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
          "Archive generation failed for flow %s on client %s: %s"
          % (args.flow_id, args.client_id, e),
          object_reference,
      )

      raise

  def _BuildPredicate(self, client_id: str):
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
      return not any(r.Match(path) for r in exclude_regexes) and any(
          r.Match(path) for r in include_only_regexes
      )

    return Predicate

  def Handle(
      self,
      args: flow_pb2.ApiGetFlowFilesArchiveArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ):
    flow_object = data_store.REL_DB.ReadFlowObject(args.client_id, args.flow_id)
    flow_results = data_store.REL_DB.ReadFlowResults(
        args.client_id, args.flow_id, 0, db.MAX_COUNT
    )
    flow_instance = flow_base.FlowBase.CreateFlowInstance(
        mig_flow_objects.ToRDFFlow(flow_object)
    )
    try:
      mappings = flow_instance.GetFilesArchiveMappings(
          mig_flow_objects.ToRDFFlowResult(flow_result)
          for flow_result in flow_results
      )
    except NotImplementedError:
      mappings = None

    description = (
        "Files downloaded by flow %s (%s) that ran on client %s by "
        "user %s on %s"
        % (
            flow_object.flow_class_name,
            args.flow_id,
            args.client_id,
            flow_object.creator,
            flow_object.create_time,
        )
    )

    target_file_prefix = "%s_flow_%s_%s" % (
        args.client_id,
        flow_object.flow_class_name,
        flow_object.flow_id,
    )

    if (
        args.archive_format
        == flow_pb2.ApiGetFlowFilesArchiveArgs.ArchiveFormat.ZIP
    ):
      archive_format = archive_generator.ArchiveFormat.ZIP
      file_extension = ".zip"
    elif (
        args.archive_format
        == flow_pb2.ApiGetFlowFilesArchiveArgs.ArchiveFormat.TAR_GZ
    ):
      archive_format = archive_generator.ArchiveFormat.TAR_GZ
      file_extension = ".tar.gz"
    else:
      raise ValueError("Unknown archive format: %s" % args.archive_format)

    # Only use the new-style flow archive generator for the flows that
    # have the GetFilesArchiveMappings defined.
    if mappings:
      a_gen = archive_generator.FlowArchiveGenerator(
          flow_object, archive_format
      )
      content_generator = self._WrapContentGeneratorWithMappings(
          a_gen, mappings, args, context=context
      )
    else:
      a_gen = archive_generator.CollectionArchiveGenerator(
          prefix=target_file_prefix,
          description=description,
          archive_format=archive_format,
          predicate=self._BuildPredicate(str(args.client_id)),
      )
      content_generator = self._WrapContentGenerator(
          a_gen, flow_results, args, context=context
      )

    return api_call_handler_base.ApiBinaryStream(
        target_file_prefix + file_extension, content_generator=content_generator
    )


class ApiListFlowOutputPluginsHandler(api_call_handler_base.ApiCallHandler):
  """Renders output plugins descriptors and states for a given flow."""

  proto_args_type = flow_pb2.ApiListFlowOutputPluginsArgs
  proto_result_type = flow_pb2.ApiListFlowOutputPluginsResult

  def Handle(
      self,
      args: flow_pb2.ApiListFlowOutputPluginsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiListFlowOutputPluginsResult:
    flow_obj = data_store.REL_DB.ReadFlowObject(args.client_id, args.flow_id)

    plugin_results: list[api_output_plugin_pb2.ApiOutputPlugin] = []

    type_indices = {}
    for output_plugin_state in flow_obj.output_plugins_states:
      plugin_descriptor = output_plugin_state.plugin_descriptor

      type_index = type_indices.setdefault(plugin_descriptor.plugin_name, 0)
      type_indices[plugin_descriptor.plugin_name] += 1

      api_plugin = api_output_plugin_pb2.ApiOutputPlugin()
      api_plugin.id = f"{plugin_descriptor.plugin_name}_{type_index}"
      api_plugin.plugin_descriptor.CopyFrom(plugin_descriptor)
      api_plugin.state.Pack(output_plugin_state.plugin_state)

      plugin_results.append(api_plugin)

    return flow_pb2.ApiListFlowOutputPluginsResult(items=plugin_results)


def GetOutputPluginIndex(
    plugin_descriptors: Iterable[output_plugin_pb2.OutputPluginDescriptor],
    plugin_id: str,
) -> int:
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
  identifying plugins with same plugin ids as before.

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
  for index, desc in enumerate(plugin_descriptors):
    cur_plugin_id = "%s_%d" % (desc.plugin_name, used_names[desc.plugin_name])
    used_names[desc.plugin_name] += 1

    if cur_plugin_id == plugin_id:
      return index

  raise OutputPluginNotFoundError("Can't find output plugin %s" % plugin_id)


class ApiListFlowOutputPluginLogsHandlerBase(
    api_call_handler_base.ApiCallHandler
):
  """Base class used to define log and error messages handlers."""

  __abstract = True  # pylint: disable=g-bad-name

  log_entry_type = None

  def Handle(
      self,
      args: Union[
          flow_pb2.ApiListFlowOutputPluginLogsArgs,
          flow_pb2.ApiListFlowOutputPluginErrorsArgs,
      ],
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> Union[
      flow_pb2.ApiListFlowOutputPluginLogsResult,
      flow_pb2.ApiListFlowOutputPluginErrorsResult,
  ]:
    flow_obj = data_store.REL_DB.ReadFlowObject(args.client_id, args.flow_id)
    index = GetOutputPluginIndex(flow_obj.output_plugins, args.plugin_id)
    output_plugin_id = "%d" % index

    logs = data_store.REL_DB.ReadFlowOutputPluginLogEntries(
        args.client_id,
        args.flow_id,
        output_plugin_id,
        args.offset,
        args.count or db.MAX_COUNT,
        with_type=self.__class__.log_entry_type,
    )
    total_count = data_store.REL_DB.CountFlowOutputPluginLogEntries(
        args.client_id,
        args.flow_id,
        output_plugin_id,
        with_type=self.__class__.log_entry_type,
    )

    return self.proto_result_type(
        total_count=total_count,
        items=[
            rdf_flow_objects.ToOutputPluginBatchProcessingStatus(l)
            for l in logs
        ],
    )


class ApiListFlowOutputPluginLogsHandler(
    ApiListFlowOutputPluginLogsHandlerBase
):
  """Renders flow's output plugin's logs."""

  log_entry_type = flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG

  proto_args_type = flow_pb2.ApiListFlowOutputPluginLogsArgs
  proto_result_type = flow_pb2.ApiListFlowOutputPluginLogsResult


class ApiListFlowOutputPluginErrorsHandler(
    ApiListFlowOutputPluginLogsHandlerBase
):
  """Renders flow's output plugin's errors."""

  log_entry_type = flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR

  proto_args_type = flow_pb2.ApiListFlowOutputPluginErrorsArgs
  proto_result_type = flow_pb2.ApiListFlowOutputPluginErrorsResult


class ApiListAllFlowOutputPluginLogsHandler(
    api_call_handler_base.ApiCallHandler
):
  """Renders flow's output plugin's logs for all plugins."""

  proto_args_type = flow_pb2.ApiListAllFlowOutputPluginLogsArgs
  proto_result_type = flow_pb2.ApiListAllFlowOutputPluginLogsResult

  def Handle(
      self,
      args: flow_pb2.ApiListAllFlowOutputPluginLogsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiListAllFlowOutputPluginLogsResult:
    logs = data_store.REL_DB.ReadAllFlowOutputPluginLogEntries(
        args.client_id,
        args.flow_id,
        args.offset,
        args.count or db.MAX_COUNT,
    )
    total_count = data_store.REL_DB.CountAllFlowOutputPluginLogEntries(
        args.client_id,
        args.flow_id,
    )

    return self.proto_result_type(
        total_count=total_count,
        items=logs,
    )


class ApiListFlowsHandler(api_call_handler_base.ApiCallHandler):
  """Lists flows launched on a given client."""

  proto_args_type = flow_pb2.ApiListFlowsArgs
  proto_result_type = flow_pb2.ApiListFlowsResult

  def _HandleTopFlowsOnly(
      self,
      args: flow_pb2.ApiListFlowsArgs,
  ) -> flow_pb2.ApiListFlowsResult:
    min_started_at, max_started_at = None, None
    if args.HasField("min_started_at"):
      min_started_at = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          args.min_started_at
      )
    if args.HasField("max_started_at"):
      max_started_at = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          args.max_started_at
      )
    top_flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id=args.client_id,
        min_create_time=min_started_at,
        max_create_time=max_started_at,
        include_child_flows=False,
        not_created_by=access_control.SYSTEM_USERS
        if args.human_flows_only
        else None,
    )
    result = [
        InitApiFlowFromFlowObject(
            f_data,
            with_progress=True,
        )
        for f_data in top_flows
    ]
    # TODO(hanuszczak): Consult with the team what should we do in case of flows
    # with missing information.
    # TODO: Refactor sorting andfiltering of flows to DB layer.
    result.sort(key=lambda f: f.started_at or 0, reverse=True)
    result = result[args.offset :]
    if args.HasField("count"):
      result = result[: args.count]
    return flow_pb2.ApiListFlowsResult(items=result)

  def _HandleAllFlows(
      self,
      args: flow_pb2.ApiListFlowsArgs,
  ) -> flow_pb2.ApiListFlowsResult:
    min_started_at, max_started_at = None, None
    if args.HasField("min_started_at"):
      min_started_at = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          args.min_started_at
      )
    if args.HasField("max_started_at"):
      max_started_at = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          args.max_started_at
      )
    all_flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id=args.client_id,
        min_create_time=min_started_at,
        max_create_time=max_started_at,
        include_child_flows=True,
        not_created_by=access_control.SYSTEM_USERS
        if args.human_flows_only
        else None,
    )

    root_flows: list[flow_pb2.ApiFlow] = []
    parent_to_children_map: dict[str, list[flow_pb2.ApiFlow]] = (
        collections.defaultdict(list)
    )
    for f in all_flows:
      api_flow = InitApiFlowFromFlowObject(f, with_progress=True)
      if not f.parent_flow_id:
        root_flows.append(api_flow)
      else:
        parent_to_children_map[f.parent_flow_id].append(api_flow)

    root_flows.sort(key=lambda f: f.started_at or 0, reverse=True)
    root_flows = root_flows[args.offset :]
    if args.HasField("count"):
      root_flows = root_flows[: args.count]

    def _AddNestedFlows(f: flow_pb2.ApiFlow):
      for child in parent_to_children_map[f.flow_id]:
        _AddNestedFlows(child)
        f.nested_flows.append(child)

    for root in root_flows:
      _AddNestedFlows(root)

    # TODO(hanuszczak): Consult with the team what should we do in case of flows
    # with missing information.
    return flow_pb2.ApiListFlowsResult(items=root_flows)

  def Handle(
      self,
      args: flow_pb2.ApiListFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiListFlowsResult:
    if args.top_flows_only:
      return self._HandleTopFlowsOnly(args)
    else:
      return self._HandleAllFlows(args)


def _SanitizeApiCreateFlowArgs(
    args: flow_pb2.ApiCreateFlowArgs,
) -> tuple[type[flow_base.FlowBase], flows_pb2.FlowRunnerArgs]:
  """Validates and sanitizes args for flow scheduling and starting."""

  if not args.client_id:
    raise ValueError("client_id must be provided")

  runner_args = flows_pb2.FlowRunnerArgs()
  runner_args.CopyFrom(args.flow.runner_args)

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
  runner_args = mig_flow_runner.ToRDFFlowRunnerArgs(runner_args)
  runner_args.ClearFieldsWithLabel(
      rdf_structs.SemanticDescriptor.Labels.HIDDEN, exceptions="output_plugins"
  )
  runner_args = mig_flow_runner.ToProtoFlowRunnerArgs(runner_args)

  if args.HasField("original_flow"):
    runner_args.original_flow.flow_id = args.original_flow.flow_id
    runner_args.original_flow.client_id = args.original_flow.client_id

  flow_cls = registry.FlowRegistry.FlowClassByName(flow_name)
  return flow_cls, runner_args


class ApiCreateFlowHandler(api_call_handler_base.ApiCallHandler):
  """Starts a flow on a given client with given parameters."""

  proto_args_type = flow_pb2.ApiCreateFlowArgs
  proto_result_type = flow_pb2.ApiFlow

  def Handle(
      self,
      args: flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiFlow:
    assert context is not None
    flow_cls, runner_args = _SanitizeApiCreateFlowArgs(args)

    cpu_limit = None
    if runner_args.HasField("cpu_limit"):
      cpu_limit = runner_args.cpu_limit
    network_bytes_limit = None
    if runner_args.HasField("network_bytes_limit"):
      network_bytes_limit = runner_args.network_bytes_limit

    rdf_runner_args = mig_flow_runner.ToRDFFlowRunnerArgs(runner_args)
    rdf_flow_args = mig_structs.ToRDFAnyValue(args.flow.args)
    flow_id = flow.StartFlow(
        client_id=args.client_id,
        cpu_limit=cpu_limit,
        creator=context.username,
        flow_args=rdf_flow_args.Unpack(flow_cls.args_type),
        flow_cls=flow_cls,
        network_bytes_limit=network_bytes_limit,
        original_flow=rdf_runner_args.original_flow,
        output_plugins=rdf_runner_args.output_plugins,
        disable_rrg_support=runner_args.disable_rrg_support,
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(str(args.client_id), flow_id)

    res = InitApiFlowFromFlowObject(flow_obj)
    res.ClearField("context")
    return res


class ApiCancelFlowHandler(api_call_handler_base.ApiCallHandler):
  """Cancels given flow on a given client."""

  proto_args_type = flow_pb2.ApiCancelFlowArgs
  proto_result_type = flow_pb2.ApiFlow

  def Handle(
      self,
      args: flow_pb2.ApiCancelFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiFlow:
    flow_base.TerminateFlow(
        args.client_id, args.flow_id, reason="Cancelled by user"
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(args.client_id, args.flow_id)
    return InitApiFlowFromFlowObject(flow_obj)


class ApiListFlowDescriptorsHandler(api_call_handler_base.ApiCallHandler):
  """Renders all available flows descriptors."""

  proto_result_type = flow_pb2.ApiListFlowDescriptorsResult

  def __init__(
      self,
      access_check_fn: Optional[Callable[[str, str], None]] = None,
  ) -> None:
    super().__init__()
    self.access_check_fn = access_check_fn

  def Handle(
      self,
      args: Optional[None] = None,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiListFlowDescriptorsResult:
    """Renders list of descriptors for all the flows."""
    assert context is not None

    result: list[flow_pb2.ApiFlowDescriptor] = []
    for name, cls in sorted(registry.FlowRegistry.FLOW_REGISTRY.items()):

      # Skip if it is not visible to GUI/API.
      if not cls.CanUseViaAPI():
        continue

      # Only show flows that the user is allowed to start.
      try:
        if self.access_check_fn:
          self.access_check_fn(context.username, name)
      except access_control.UnauthorizedAccess:
        continue

      result.append(InitApiFlowDescriptorFromFlowClass(cls, context))

    return flow_pb2.ApiListFlowDescriptorsResult(items=result)


class ApiGetExportedFlowResultsHandler(api_call_handler_base.ApiCallHandler):
  """Exports results of a given flow with an instant output plugin."""

  proto_args_type = flow_pb2.ApiGetExportedFlowResultsArgs

  _RESULTS_PAGE_SIZE = 1000

  def Handle(
      self,
      args: flow_pb2.ApiGetExportedFlowResultsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> api_call_handler_base.ApiBinaryStream:
    try:
      plugin_cls = instant_output_plugin_registry.GetPluginClassByNameProto(
          args.plugin_name
      )
    except KeyError as e:
      raise InstantOutputPluginNotFoundError(
          f"Can't find instant output plugin {args.plugin_name}."
      ) from e

    client_id = args.client_id
    flow_id = args.flow_id
    flow_urn = rdfvalue.RDFURN("{}/flows/{}".format(client_id, flow_id))
    plugin = plugin_cls(source_urn=flow_urn)
    type_url_counts = data_store.REL_DB.CountFlowResultsByProtoTypeUrl(
        client_id, flow_id
    )

    def FetchFlowResultsByTypeUrl(
        type_url: str,
    ) -> Iterator[flows_pb2.FlowResult]:
      """Fetches all flow results of a given type."""
      offset = 0
      while True:
        results = data_store.REL_DB.ReadFlowResults(
            client_id,
            flow_id,
            offset=offset,
            count=self._RESULTS_PAGE_SIZE,
            with_proto_type_url=type_url,
        )

        if not results:
          break

        for r in results:
          yield r

        offset += self._RESULTS_PAGE_SIZE

    content_generator = instant_output_plugin.GetExportedFlowResults(
        plugin, list(type_url_counts.keys()), FetchFlowResultsByTypeUrl
    )

    return api_call_handler_base.ApiBinaryStream(
        plugin.output_file_name, content_generator=content_generator
    )


class ApiExplainGlobExpressionHandler(api_call_handler_base.ApiCallHandler):
  """Gives examples for the components of a GlobExpression."""

  proto_args_type = flow_pb2.ApiExplainGlobExpressionArgs
  proto_result_type = flow_pb2.ApiExplainGlobExpressionResult

  def Handle(
      self,
      args: flow_pb2.ApiExplainGlobExpressionArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiExplainGlobExpressionResult:

    glob_expression = rdf_paths.GlobExpression(args.glob_expression)
    glob_expression.Validate()

    kb = data_store_utils.GetClientKnowledgeBase(args.client_id)
    components = glob_expression.ExplainComponents(args.example_count, kb)
    return flow_pb2.ApiExplainGlobExpressionResult(components=components)


class ApiScheduleFlowHandler(api_call_handler_base.ApiCallHandler):
  """Schedules a flow on a client, to be started upon approval grant."""

  proto_args_type = flow_pb2.ApiCreateFlowArgs
  proto_result_type = flow_pb2.ApiScheduledFlow

  def Handle(
      self,
      args: flow_pb2.ApiCreateFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiScheduledFlow:
    assert context is not None

    flow_cls, runner_args = _SanitizeApiCreateFlowArgs(args)

    # TODO: Handle the case where the requesting user already has
    # approval to start the flow on the client.
    scheduled_flow = flow.ScheduleFlow(
        client_id=args.client_id,
        creator=context.username,
        flow_name=flow_cls.__name__,
        flow_args=args.flow.args,
        runner_args=runner_args,
    )
    return InitApiScheduledFlowFromScheduledFlow(scheduled_flow)


class ApiListScheduledFlowsHandler(api_call_handler_base.ApiCallHandler):
  """Lists all scheduled flows from a user on a client."""

  proto_args_type = flow_pb2.ApiListScheduledFlowsArgs
  proto_result_type = flow_pb2.ApiListScheduledFlowsResult

  def Handle(
      self,
      args: flow_pb2.ApiListScheduledFlowsArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiListScheduledFlowsResult:
    results = flow.ListScheduledFlows(
        client_id=args.client_id, creator=args.creator
    )
    results = sorted(results, key=lambda sf: sf.create_time)
    results = [InitApiScheduledFlowFromScheduledFlow(sf) for sf in results]

    return flow_pb2.ApiListScheduledFlowsResult(scheduled_flows=results)


class ApiUnscheduleFlowHandler(api_call_handler_base.ApiCallHandler):
  """Unschedules and deletes a previously scheduled flow."""

  proto_args_type = flow_pb2.ApiUnscheduleFlowArgs
  proto_result_type = flow_pb2.ApiUnscheduleFlowResult

  def Handle(
      self,
      args: flow_pb2.ApiUnscheduleFlowArgs,
      context: Optional[api_call_context.ApiCallContext] = None,
  ) -> flow_pb2.ApiUnscheduleFlowResult:
    assert context is not None

    flow.UnscheduleFlow(
        client_id=args.client_id,
        creator=context.username,
        scheduled_flow_id=args.scheduled_flow_id,
    )
    return flow_pb2.ApiUnscheduleFlowResult()
