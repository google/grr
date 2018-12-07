#!/usr/bin/env python
"""API handlers for dealing with flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
import re
import sys


from future.utils import iteritems
from future.utils import itervalues

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import flow_pb2
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import instant_output_plugin
from grr_response_server import notification
from grr_response_server import output_plugin
from grr_response_server import queue_manager
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.gui import archive_generator
from grr_response_server.gui.api_plugins import client
from grr_response_server.gui.api_plugins import output_plugin as api_output_plugin
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects


class FlowNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a flow is not found."""


class ApiFlowId(rdfvalue.RDFString):
  """Class encapsulating flows ids."""

  def __init__(self, initializer=None, age=None):
    super(ApiFlowId, self).__init__(initializer=initializer, age=age)

    # TODO(user): move this to a separate validation method when
    # common RDFValues validation approach is implemented.
    if self._value:
      components = self.Split()
      for component in components:
        try:
          rdfvalue.SessionID.ValidateID(component)
        except ValueError as e:
          raise ValueError(
              "Invalid flow id: %s (%s)" % (utils.SmartStr(self._value), e))

  def _FlowIdToUrn(self, flow_id, client_id):
    return client_id.ToClientURN().Add("flows").Add(flow_id)

  def ResolveCronJobFlowURN(self, cron_job_id):
    """Resolve a URN of a flow with this id belonging to a given cron job."""
    if not self._value:
      raise ValueError("Can't call ResolveCronJobFlowURN on an empty "
                       "client id.")

    return cron_job_id.ToURN().Add(self._value)

  def ResolveClientFlowURN(self, client_id, token=None):
    """Resolve a URN of a flow with this id belonging to a given client.

    Note that this may need a roundtrip to the datastore. Resolving algorithm
    is the following:
    1.  If the flow id doesn't contain slashes (flow is not nested), we just
        append it to the <client id>/flows.
    2.  If the flow id has slashes (flow is nested), we check if the root
        flow pointed to by <client id>/flows/<flow id> is a symlink.
    2a. If it's a symlink, we append the rest of the flow id to the symlink
        target.
    2b. If it's not a symlink, we just append the whole id to
        <client id>/flows (meaning we do the same as in 1).

    Args:
      client_id: Id of a client where this flow is supposed to be found on.
      token: Credentials token.

    Returns:
      RDFURN pointing to a flow identified by this flow id and client id.
    Raises:
      ValueError: if this flow id is not initialized.
    """
    if not self._value:
      raise ValueError("Can't call ResolveClientFlowURN on an empty client id.")

    components = self.Split()
    if len(components) == 1:
      return self._FlowIdToUrn(self._value, client_id)
    else:
      root_urn = self._FlowIdToUrn(components[0], client_id)
      try:
        flow_symlink = aff4.FACTORY.Open(
            root_urn,
            aff4_type=aff4.AFF4Symlink,
            follow_symlinks=False,
            token=token)

        return flow_symlink.Get(flow_symlink.Schema.SYMLINK_TARGET).Add(
            "/".join(components[1:]))
      except aff4.InstantiationError:
        return self._FlowIdToUrn(self._value, client_id)

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
    output.append("flow.StartAFF4Flow(client_id=client_id, ")
    output.append("flow_name=\"%s\", " % flow_cls.__name__)
    prototypes = []
    if flow_cls.args_type:
      for type_descriptor in flow_cls.args_type.type_infos:
        if not type_descriptor.hidden:
          prototypes.append(
              "%s=%s" % (type_descriptor.name, type_descriptor.name))
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
        iteritems(self._GetArgsDescription(flow_cls.args_type)),
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
    return "%s\n\n%s" % (getattr(flow_cls, "__doc__", ""),
                         self._GetFlowArgsHelpAsString(flow_cls))

  def InitFromFlowClass(self, flow_cls, token=None):
    if not token:
      raise ValueError("token can't be None")

    self.name = flow_cls.__name__
    self.friendly_name = flow_cls.friendly_name
    self.category = flow_cls.category.strip("/")
    self.doc = self._GetFlowDocumentation(flow_cls)
    self.args_type = flow_cls.args_type.__name__
    self.default_args = flow_cls.GetDefaultArgs(username=token.username)
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

  def GetArgsClass(self):
    flow_name = self.name
    if not flow_name:
      flow_name = self.runner_args.flow_name

    if flow_name:
      flow_cls = registry.AFF4FlowRegistry.FlowClassByName(flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type

  def InitFromAff4Object(self,
                         flow_obj,
                         flow_id=None,
                         with_state_and_context=False):
    try:
      # TODO(user): we should be able to infer flow id from the
      # URN. Currently it's not possible due to an inconsistent way in
      # which we create symlinks and name them.
      self.flow_id = flow_id
      self.urn = flow_obj.urn

      first_component = self.urn.Split()[0]
      try:
        self.client_id = first_component
      except ValueError:
        # This is not a client-based flow, nothing to be done here.
        pass

      self.name = flow_obj.runner_args.flow_name
      self.started_at = flow_obj.context.create_time
      self.last_active_at = flow_obj.Get(flow_obj.Schema.LAST)
      self.creator = flow_obj.context.creator

      if flow_obj.Get(flow_obj.Schema.CLIENT_CRASH):
        self.state = "CLIENT_CRASHED"
      elif flow_obj.Get(flow_obj.Schema.PENDING_TERMINATION):
        self.state = flow_obj.context.state = "ERROR"
        reason = flow_obj.Get(flow_obj.Schema.PENDING_TERMINATION).reason
        flow_obj.context.status = "Pending termination: %s" % reason
      else:
        self.state = flow_obj.context.state

      try:
        self.args = flow_obj.args
      except ValueError:
        # If args class name has changed, ValueError will be raised. Handling
        # this gracefully - we should still try to display some useful info
        # about the flow.
        pass

      self.runner_args = flow_obj.runner_args

      if self.runner_args.original_flow.flow_id:
        self.original_flow = ApiFlowReference().FromFlowReference(
            self.runner_args.original_flow)
      else:
        self.runner_args.original_flow = None

      if with_state_and_context:
        try:
          self.context = flow_obj.context
        except ValueError:
          pass

        flow_state_dict = flow_obj.Get(flow_obj.Schema.FLOW_STATE_DICT)
        if flow_state_dict is not None:
          flow_state_data = flow_state_dict.ToDict()

          if flow_state_data:
            self.state_data = (
                api_call_handler_utils.ApiDataObject().InitFromDataObject(
                    flow_state_data))
    except Exception as e:  # pylint: disable=broad-except
      self.internal_error = "Error while opening flow: %s" % str(e)

    return self

  def InitFromFlowObject(self, flow_obj, with_state_and_context=False):
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
        self.status = (
            "Pending termination: %s" % flow_obj.pending_termination.reason)
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
            output_plugins_states=flow_obj.output_plugins_states,
            outstanding_requests=outstanding_requests,
            state=self.state,
            # TODO(amoser): Get rid of all urns.
            session_id=flow_obj.long_flow_id,
        )
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

      try:
        self.args = flow_obj.args
      except ValueError:
        # If args class name has changed, ValueError will be raised. Handling
        # this gracefully - we should still try to display some useful info
        # about the flow.
        pass

      self.runner_args = rdf_flow_runner.FlowRunnerArgs(
          client_id=flow_obj.client_id,
          flow_name=flow_obj.flow_class_name,
          output_plugins=flow_obj.output_plugins,
          notify_to_user=flow_base.FlowBase(flow_obj).ShouldSendNotifications())

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

  def InitFromRdfValue(self, value):
    self.payload_type = value.__class__.__name__
    self.payload = value
    self.timestamp = value.age

    return self


class ApiFlowLog(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiFlowLog
  rdf_deps = [ApiFlowId, rdfvalue.RDFDatetime]

  def InitFromFlowLog(self, fl):
    self.log_message = fl.log_message
    self.flow_id = fl.urn.RelativeName(fl.client_id.Add("flows"))
    self.timestamp = fl.age

    return self

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

  def Handle(self, args, token=None):
    if data_store.RelationalDBFlowsEnabled():
      flow_obj = data_store.REL_DB.ReadFlowObject(
          unicode(args.client_id), unicode(args.flow_id))
      return ApiFlow().InitFromFlowObject(flow_obj, with_state_and_context=True)
    else:
      flow_urn = args.flow_id.ResolveClientFlowURN(args.client_id, token=token)
      flow_obj = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, mode="r", token=token)

      return ApiFlow().InitFromAff4Object(
          flow_obj, flow_id=args.flow_id, with_state_and_context=True)


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

  def Handle(self, args, token=None):
    if data_store.RelationalDBFlowsEnabled():
      return self._HandleRelational(args)
    else:
      return self._HandleAFF4(args, token=token)

  def _HandleAFF4(self, args, token=None):
    flow_urn = args.flow_id.ResolveClientFlowURN(args.client_id, token=token)

    # Check if this flow really exists.
    try:
      aff4.FACTORY.Open(flow_urn, aff4_type=flow.GRRFlow, mode="r", token=token)
    except aff4.InstantiationError:
      raise FlowNotFoundError()

    result = ApiListFlowRequestsResult()
    manager = queue_manager.QueueManager(token=token)
    requests_responses = manager.FetchRequestsAndResponses(flow_urn)

    stop = None
    if args.count:
      stop = args.offset + args.count

    for request, responses in itertools.islice(requests_responses, args.offset,
                                               stop):
      if request.id == 0:
        continue

      # This field only contains internal information that doesn't make sense to
      # end users.
      request.request = None

      # TODO(amoser): The request_id field should be an int.
      api_request = ApiFlowRequest(
          request_id=str(request.id), request_state=request)

      if responses:
        for r in responses:
          # Clear out some internal fields.
          r.task_id = None
          r.ClearPayload()
          r.auth_state = None
          r.name = None

        api_request.responses = responses

      result.items.append(api_request)

    return result

  def _HandleRelational(self, args):
    requests_and_responses = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
        unicode(args.client_id), unicode(args.flow_id))

    result = ApiListFlowRequestsResult()
    stop = None
    if args.count:
      stop = args.offset + args.count

    for request, response_dict in itertools.islice(requests_and_responses,
                                                   args.offset, stop):
      client_urn = args.client_id.ToClientURN()
      request_state = rdf_flow_runner.RequestState(
          client_id=client_urn,
          id=request.request_id,
          next_state=request.next_state,
          session_id=client_urn.Add("flows").Add(unicode(request.flow_id)))
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

  def Handle(self, args, token=None):
    if data_store.RelationalDBFlowsEnabled():
      results = data_store.REL_DB.ReadFlowResults(
          unicode(args.client_id), unicode(args.flow_id), args.offset,
          args.count or sys.maxsize)
      total_count = data_store.REL_DB.CountFlowResults(
          unicode(args.client_id), unicode(args.flow_id))
      items = [r.payload for r in results]
    else:
      flow_urn = args.flow_id.ResolveClientFlowURN(args.client_id, token=token)
      output_collection = flow.GRRFlow.ResultCollectionForFID(flow_urn)
      total_count = len(output_collection)

      items = api_call_handler_utils.FilterCollection(
          output_collection, args.offset, args.count, args.filter)

    wrapped_items = [ApiFlowResult().InitFromRdfValue(item) for item in items]
    return ApiListFlowResultsResult(
        items=wrapped_items, total_count=total_count)


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

  def Handle(self, args, token=None):
    if data_store.RelationalDBFlowsEnabled():
      count = args.count or sys.maxsize

      logs = data_store.REL_DB.ReadFlowLogEntries(
          unicode(args.client_id), unicode(args.flow_id), args.offset, count,
          args.filter)
      total_count = data_store.REL_DB.CountFlowLogEntries(
          unicode(args.client_id), unicode(args.flow_id))
      return ApiListFlowLogsResult(
          items=[
              ApiFlowLog().InitFromFlowLogEntry(log, unicode(args.flow_id))
              for log in logs
          ],
          total_count=total_count)
    else:
      flow_urn = args.flow_id.ResolveClientFlowURN(args.client_id, token=token)
      logs_collection = flow.GRRFlow.LogCollectionForFID(flow_urn)

      result = api_call_handler_utils.FilterCollection(
          logs_collection, args.offset, args.count, args.filter)

      return ApiListFlowLogsResult(
          items=[ApiFlowLog().InitFromFlowLog(x) for x in result],
          total_count=len(logs_collection))


class ApiGetFlowResultsExportCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiGetFlowResultsExportCommandArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiGetFlowResultsExportCommandResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiGetFlowResultsExportCommandResult


class ApiGetFlowResultsExportCommandHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders GRR export tool command line that exports flow results."""

  args_type = ApiGetFlowResultsExportCommandArgs
  result_type = ApiGetFlowResultsExportCommandResult

  def Handle(self, args, token=None):
    output_fname = re.sub(
        "[^0-9a-zA-Z]+", "_", "%s_%s" % (utils.SmartStr(args.client_id),
                                         utils.SmartStr(args.flow_id)))
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

  def __init__(self, path_globs_blacklist=None, path_globs_whitelist=None):
    """Constructor.

    Args:
      path_globs_blacklist: List of paths.GlobExpression values. Blacklist will
        be applied before the whitelist.
      path_globs_whitelist: List of paths.GlobExpression values. Whitelist will
        be applied after the blacklist.

    Raises:
      ValueError: If path_globs_blacklist/whitelist is passed, but
          the other blacklist/whitelist argument is not.

    Note that path_globs_blacklist/whitelist arguments can only be passed
    together. The algorithm of applying the lists is the following:
    1. If the lists are not set, include the file into the archive. Otherwise:
    2. If the file matches the blacklist, skip the file. Otherwise:
    3. If the file does match the whitelist, skip the file.
    """
    super(api_call_handler_base.ApiCallHandler, self).__init__()

    if len([
        x for x in (path_globs_blacklist, path_globs_whitelist) if x is None
    ]) == 1:
      raise ValueError("path_globs_blacklist/path_globs_whitelist have to "
                       "set/unset together.")

    self.path_globs_blacklist = path_globs_blacklist
    self.path_globs_whitelist = path_globs_whitelist

  def _WrapContentGenerator(self, generator, flow_results, args, token=None):
    try:
      for item in generator.Generate(flow_results, token=token):
        yield item

      notification.Notify(
          token.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED,
          "Downloaded archive of flow %s from client %s (archived %d "
          "out of %d items, archive size is %d)" %
          (args.flow_id, args.client_id, generator.archived_files,
           generator.total_files, generator.output_size), None)

    except Exception as e:
      notification.Notify(
          token.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
          "Archive generation failed for flow %s on client %s: %s" %
          (args.flow_id, args.client_id, utils.SmartStr(e)), None)

      raise

  def _BuildPredicate(self, client_id, token=None):
    if self.path_globs_whitelist is None:
      return None

    client_obj = aff4.FACTORY.Open(
        client_id.ToClientURN(), aff4_type=aff4_grr.VFSGRRClient, token=token)

    blacklist_regexes = []
    for expression in self.path_globs_blacklist:
      for pattern in expression.Interpolate(client=client_obj):
        blacklist_regexes.append(rdf_paths.GlobExpression(pattern).AsRegEx())

    whitelist_regexes = []
    for expression in self.path_globs_whitelist:
      for pattern in expression.Interpolate(client=client_obj):
        whitelist_regexes.append(rdf_paths.GlobExpression(pattern).AsRegEx())

    def Predicate(client_path):
      # Enforce leading / since Regexes require it.
      path = "/" + client_path.Path().lstrip("/")
      return (not any(r.Match(path) for r in blacklist_regexes) and
              any(r.Match(path) for r in whitelist_regexes))

    return Predicate

  def _GetFlow(self, args, token=None):
    if data_store.RelationalDBFlowsEnabled():
      client_id = unicode(args.client_id)
      flow_id = unicode(args.flow_id)
      flow_obj = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
      flow_api_object = ApiFlow().InitFromFlowObject(flow_obj)
      flow_results = data_store.REL_DB.ReadFlowResults(client_id, flow_id, 0,
                                                       sys.maxsize)
      flow_results = [r.payload for r in flow_results]
      return flow_api_object, flow_results
    else:
      flow_urn = args.flow_id.ResolveClientFlowURN(args.client_id, token=token)
      flow_obj = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, mode="r", token=token)
      flow_api_object = ApiFlow().InitFromAff4Object(
          flow_obj, flow_id=args.flow_id)
      flow_results = flow.GRRFlow.ResultCollectionForFID(flow_urn)
      return flow_api_object, flow_results

  def Handle(self, args, token=None):
    flow_api_object, flow_results = self._GetFlow(args, token)

    description = (
        "Files downloaded by flow %s (%s) that ran on client %s by "
        "user %s on %s" % (flow_api_object.name, args.flow_id, args.client_id,
                           flow_api_object.creator, flow_api_object.started_at))

    target_file_prefix = "%s_flow_%s_%s" % (
        args.client_id, flow_api_object.name, unicode(
            flow_api_object.flow_id).replace(":", "_"))

    if args.archive_format == args.ArchiveFormat.ZIP:
      archive_format = archive_generator.CollectionArchiveGenerator.ZIP
      file_extension = ".zip"
    elif args.archive_format == args.ArchiveFormat.TAR_GZ:
      archive_format = archive_generator.CollectionArchiveGenerator.TAR_GZ
      file_extension = ".tar.gz"
    else:
      raise ValueError("Unknown archive format: %s" % args.archive_format)

    generator = archive_generator.CompatCollectionArchiveGenerator(
        prefix=target_file_prefix,
        description=description,
        archive_format=archive_format,
        predicate=self._BuildPredicate(args.client_id, token=token),
        client_id=args.client_id.ToClientURN())
    content_generator = self._WrapContentGenerator(
        generator, flow_results, args, token=token)
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

  def Handle(self, args, token=None):
    if data_store.RelationalDBFlowsEnabled():
      flow_obj = data_store.REL_DB.ReadFlowObject(
          unicode(args.client_id), unicode(args.flow_id))
      output_plugins_states = flow_obj.output_plugins_states
    else:
      flow_urn = args.flow_id.ResolveClientFlowURN(args.client_id, token=token)
      flow_obj = aff4.FACTORY.Open(
          flow_urn, aff4_type=flow.GRRFlow, mode="r", token=token)

      output_plugins_states = flow_obj.GetRunner().context.output_plugins_states

    type_indices = {}
    result = []
    for output_plugin_state in output_plugins_states:
      plugin_descriptor = output_plugin_state.plugin_descriptor
      plugin_state = output_plugin_state.plugin_state
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

  def Handle(self, args, token=None):
    if not self.attribute_name:
      raise ValueError("attribute_name can't be None")

    flow_urn = args.flow_id.ResolveClientFlowURN(args.client_id, token=token)
    flow_obj = aff4.FACTORY.Open(
        flow_urn, aff4_type=flow.GRRFlow, mode="r", token=token)

    output_plugins_states = flow_obj.GetRunner().context.output_plugins_states

    # Flow output plugins don't use collections to store status/error
    # information. Instead, it's stored in plugin's state. Nevertheless,
    # we emulate collections API here. Having similar API interface allows
    # one to reuse the code when handling hunts and flows output plugins.
    # Good example is the UI code.
    type_indices = {}
    found_state = None

    for output_plugin_state in output_plugins_states:
      plugin_descriptor = output_plugin_state.plugin_descriptor
      plugin_state = output_plugin_state.plugin_state
      type_index = type_indices.setdefault(plugin_descriptor.plugin_name, 0)
      type_indices[plugin_descriptor.plugin_name] += 1

      if args.plugin_id == plugin_descriptor.plugin_name + "_%d" % type_index:
        found_state = plugin_state
        break

    if not found_state:
      raise RuntimeError(
          "Flow %s doesn't have output plugin %s" % (flow_urn, args.plugin_id))

    stop = None
    if args.count:
      stop = args.offset + args.count

    logs_collection = found_state.get(self.attribute_name, [])
    sliced_collection = logs_collection[args.offset:stop]

    return self.result_type(
        total_count=len(logs_collection), items=sliced_collection)


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


class ApiListFlowOutputPluginLogsHandler(
    ApiListFlowOutputPluginLogsHandlerBase):
  """Renders flow's output plugin's logs."""

  attribute_name = "logs"
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

  attribute_name = "errors"
  args_type = ApiListFlowOutputPluginErrorsArgs
  result_type = ApiListFlowOutputPluginErrorsResult


class ApiListFlowsArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowsArgs
  rdf_deps = [
      client.ApiClientId,
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

  @staticmethod
  def _GetCreationTime(obj):
    if obj.context:
      return obj.context.create_time
    else:
      return obj.Get(obj.Schema.LAST, 0)

  @staticmethod
  def BuildFlowList(root_urn,
                    count,
                    offset,
                    with_state_and_context=False,
                    token=None):
    if not count:
      stop = None
    else:
      stop = offset + count

    root_children_urns = aff4.FACTORY.Open(root_urn, token=token).ListChildren()
    root_children_urns = sorted(
        root_children_urns, key=lambda x: x.age, reverse=True)
    root_children_urns = root_children_urns[offset:stop]

    root_children = aff4.FACTORY.MultiOpen(
        root_children_urns, aff4_type=flow.GRRFlow, token=token)
    root_children = sorted(
        root_children, key=ApiListFlowsHandler._GetCreationTime, reverse=True)

    nested_children_urns = dict(
        aff4.FACTORY.RecursiveMultiListChildren(
            [fd.urn for fd in root_children]))
    nested_children = aff4.FACTORY.MultiOpen(
        set(itertools.chain.from_iterable(itervalues(nested_children_urns))),
        aff4_type=flow.GRRFlow,
        token=token)
    nested_children_map = dict((x.urn, x) for x in nested_children)

    def BuildList(fds, parent_id=None):
      """Builds list of flows recursively."""
      result = []
      for fd in fds:

        try:
          urn = fd.symlink_urn or fd.urn
          if parent_id:
            flow_id = "%s/%s" % (parent_id, urn.Basename())
          else:
            flow_id = urn.Basename()
          api_flow = ApiFlow().InitFromAff4Object(
              fd,
              flow_id=flow_id,
              with_state_and_context=with_state_and_context)
        except AttributeError:
          # If this doesn't work there's no way to recover.
          continue

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

        children = sorted(
            children, key=ApiListFlowsHandler._GetCreationTime, reverse=True)
        try:
          api_flow.nested_flows = BuildList(children, parent_id=flow_id)
        except KeyError:
          pass
        result.append(api_flow)

      return result

    return ApiListFlowsResult(items=BuildList(root_children))

  def _BuildRelationalFlowList(self, client_id, offset, count):
    all_flows = data_store.REL_DB.ReadAllFlowObjects(client_id)
    api_flow_dict = {
        rdf_flow.flow_id: ApiFlow().InitFromFlowObject(rdf_flow)
        for rdf_flow in all_flows
    }

    child_flow_ids = set()
    for rdf_flow in all_flows:
      if not rdf_flow.parent_flow_id:
        continue

      if rdf_flow.parent_flow_id in api_flow_dict:
        parent_flow = api_flow_dict[rdf_flow.parent_flow_id]
        parent_flow.nested_flows.Append(api_flow_dict[rdf_flow.flow_id])
        child_flow_ids.add(rdf_flow.flow_id)

    result = [
        f for f in itervalues(api_flow_dict) if f.flow_id not in child_flow_ids
    ]
    result.sort(key=lambda f: f.started_at, reverse=True)
    result = result[offset:]
    if count:
      result = result[:count]
    return ApiListFlowsResult(items=result)

  def Handle(self, args, token=None):
    if data_store.RelationalDBFlowsEnabled():
      return self._BuildRelationalFlowList(
          unicode(args.client_id), args.offset, args.count)
    else:
      client_root_urn = args.client_id.ToClientURN().Add("flows")
      return self.BuildFlowList(
          client_root_urn, args.count, args.offset, token=token)


class ApiCreateFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiCreateFlowArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlow,
      ApiFlowReference,
  ]


class ApiCreateFlowHandler(api_call_handler_base.ApiCallHandler):
  """Starts a flow on a given client with given parameters."""

  args_type = ApiCreateFlowArgs
  result_type = ApiFlow

  def Handle(self, args, token=None):
    if not args.client_id:
      raise ValueError("client_id must be provided")

    runner_args = args.flow.runner_args
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
        rdf_structs.SemanticDescriptor.Labels.HIDDEN,
        exceptions="output_plugins")

    if args.original_flow:
      runner_args.original_flow = rdf_objects.FlowReference(
          flow_id=utils.SmartStr(args.original_flow.flow_id),
          client_id=utils.SmartStr(args.original_flow.client_id))

    if data_store.RelationalDBFlowsEnabled():
      flow_cls = registry.FlowRegistry.FlowClassByName(flow_name)
      cpu_limit = None
      if runner_args.HasField("cpu_limit"):
        cpu_limit = runner_args.cpu_limit
      network_bytes_limit = None
      if runner_args.HasField("network_bytes_limit"):
        network_bytes_limit = runner_args.network_bytes_limit

      flow_id = flow.StartFlow(
          client_id=unicode(args.client_id),
          cpu_limit=cpu_limit,
          creator=token.username,
          flow_args=args.flow.args,
          flow_cls=flow_cls,
          network_bytes_limit=network_bytes_limit,
          original_flow=runner_args.original_flow,
          output_plugins=runner_args.output_plugins,
          parent_flow_obj=None,
      )
      flow_obj = data_store.REL_DB.ReadFlowObject(
          unicode(args.client_id), flow_id)

      res = ApiFlow().InitFromFlowObject(flow_obj)
      res.context = None
      return res
    else:
      flow_id = flow.StartAFF4Flow(
          client_id=args.client_id.ToClientURN(),
          flow_name=flow_name,
          token=token,
          args=args.flow.args,
          runner_args=runner_args)

      fd = aff4.FACTORY.Open(flow_id, aff4_type=flow.GRRFlow, token=token)
      return ApiFlow().InitFromAff4Object(fd, flow_id=flow_id.Basename())


class ApiCancelFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiCancelFlowArgs
  rdf_deps = [
      client.ApiClientId,
      ApiFlowId,
  ]


class ApiCancelFlowHandler(api_call_handler_base.ApiCallHandler):
  """Cancels given flow on a given client."""

  args_type = ApiCancelFlowArgs

  def Handle(self, args, token=None):
    reason = "Cancelled in GUI"

    if data_store.RelationalDBFlowsEnabled():
      flow_base.TerminateFlow(
          unicode(args.client_id), unicode(args.flow_id), reason=reason)
    else:
      flow_urn = args.flow_id.ResolveClientFlowURN(args.client_id, token=token)

      flow.GRRFlow.TerminateAFF4Flow(flow_urn, reason=reason, token=token)


class ApiListFlowDescriptorsResult(rdf_structs.RDFProtoStruct):
  protobuf = flow_pb2.ApiListFlowDescriptorsResult
  rdf_deps = [
      ApiFlowDescriptor,
  ]


class ApiListFlowDescriptorsHandler(api_call_handler_base.ApiCallHandler):
  """Renders all available flows descriptors."""

  result_type = ApiListFlowDescriptorsResult

  def __init__(self, access_check_fn=None):
    super(ApiListFlowDescriptorsHandler, self).__init__()
    self.access_check_fn = access_check_fn

  def Handle(self, args, token=None):
    """Renders list of descriptors for all the flows."""

    if data_store.RelationalDBFlowsEnabled():
      flow_iterator = iteritems(registry.FlowRegistry.FLOW_REGISTRY)
    else:
      flow_iterator = iteritems(registry.AFF4FlowRegistry.FLOW_REGISTRY)

    result = []
    for name, cls in sorted(flow_iterator):

      # Flows without a category do not show up in the GUI.
      if not getattr(cls, "category", None):
        continue

      # Only show flows that the user is allowed to start.
      try:
        if self.access_check_fn:
          self.access_check_fn(token.username, name)
      except access_control.UnauthorizedAccess:
        continue

      result.append(ApiFlowDescriptor().InitFromFlowClass(cls, token=token))

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

  def Handle(self, args, token=None):
    iop_cls = instant_output_plugin.InstantOutputPlugin
    plugin_cls = iop_cls.GetPluginClassByPluginName(args.plugin_name)

    flow_urn = args.flow_id.ResolveClientFlowURN(args.client_id, token=token)

    output_collection = flow.GRRFlow.TypedResultCollectionForFID(flow_urn)

    plugin = plugin_cls(source_urn=flow_urn, token=token)
    content_generator = instant_output_plugin.ApplyPluginToMultiTypeCollection(
        plugin, output_collection, source_urn=args.client_id.ToClientURN())
    return api_call_handler_base.ApiBinaryStream(
        plugin.output_file_name, content_generator=content_generator)
