#!/usr/bin/env python
# Lint as: python3
"""API handlers for accessing hunts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import functools
import os
import re


from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_proto.api import hunt_pb2
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import foreman_rules
from grr_response_server import hunt
from grr_response_server import instant_output_plugin
from grr_response_server import notification
from grr_response_server import output_plugin
from grr_response_server.databases import db
from grr_response_server.flows.general import export
from grr_response_server.flows.general import transfer
from grr_response_server.gui import api_call_context
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.gui import archive_generator
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import output_plugin as api_output_plugin
from grr_response_server.gui.api_plugins import vfs as api_vfs
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import hunts as rdf_hunts
from grr_response_server.rdfvalues import objects as rdf_objects

HUNTS_ROOT_PATH = rdfvalue.RDFURN("aff4:/hunts")


class HuntNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a hunt could not be found."""


class HuntFileNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a hunt file could not be found."""


class Error(Exception):
  pass


class InvalidHuntStateError(Error):
  pass


class HuntNotStartableError(Error):
  pass


class HuntNotStoppableError(Error):
  pass


class HuntNotModifiableError(Error):
  pass


class HuntNotDeletableError(Error):
  pass


class ApiHuntId(rdfvalue.RDFString):
  """Class encapsulating hunt ids."""

  def __init__(self, initializer=None):
    super().__init__(initializer=initializer)

    # TODO(user): move this to a separate validation method when
    # common RDFValues validation approach is implemented.
    if self._value:
      try:
        rdfvalue.SessionID.ValidateID(self._value)
      except ValueError as e:
        raise ValueError("Invalid hunt id: %s (%s)" % (self._value, e))

  def ToString(self):
    if not self._value:
      raise ValueError("can't call ToString() on an empty hunt id.")

    return self._value


class ApiHuntReference(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiHuntReference
  rdf_deps = [
      ApiHuntId,
  ]

  def FromHuntReference(self, reference):
    self.hunt_id = reference.hunt_id
    return self


class ApiFlowLikeObjectReference(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiFlowLikeObjectReference
  rdf_deps = [
      ApiHuntReference,
      api_flow.ApiFlowReference,
  ]

  def FromFlowLikeObjectReference(self, reference):
    self.object_type = reference.object_type
    if reference.object_type == "HUNT_REFERENCE":
      self.hunt_reference = ApiHuntReference().FromHuntReference(
          reference.hunt_reference)
    elif reference.object_type == "FLOW_REFERENCE":
      self.flow_reference = api_flow.ApiFlowReference().FromFlowReference(
          reference.flow_reference)
    return self


class ApiHunt(rdf_structs.RDFProtoStruct):
  """ApiHunt is used when rendering responses.

  ApiHunt is meant to be more lightweight than automatically generated AFF4
  representation. It's also meant to contain only the information needed by
  the UI and to not expose implementation defails.
  """
  protobuf = hunt_pb2.ApiHunt
  rdf_deps = [
      ApiHuntId,
      ApiFlowLikeObjectReference,
      foreman_rules.ForemanClientRuleSet,
      rdf_hunts.HuntRunnerArgs,
      rdfvalue.DurationSeconds,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]

  def GetFlowArgsClass(self):
    if self.hunt_type == ApiHunt.HuntType.STANDARD and self.flow_name:
      flow_cls = registry.FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type
    elif self.hunt_type == ApiHunt.HuntType.VARIABLE:
      return rdf_hunt_objects.HuntArgumentsVariable

  def InitFromHuntObject(self,
                         hunt_obj,
                         hunt_counters=None,
                         with_full_summary=False):
    """Initialize API hunt object from a database hunt object.

    Args:
      hunt_obj: rdf_hunt_objects.Hunt to read the data from.
      hunt_counters: Optional db.HuntCounters object with counters information.
      with_full_summary: if True, hunt_runner_args, completion counts and a few
        other fields will be filled in. The way to think about it is that with
        with_full_summary==True ApiHunt will have the data to render "Hunt
        Overview" page and with with_full_summary==False it will have enough
        data to be rendered as a hunts list row.

    Returns:
      Self.
    """

    self.urn = rdfvalue.RDFURN("hunts").Add(str(hunt_obj.hunt_id))
    self.hunt_id = hunt_obj.hunt_id
    if (hunt_obj.args.hunt_type ==
        rdf_hunt_objects.HuntArguments.HuntType.STANDARD):
      self.name = "GenericHunt"
      self.hunt_type = self.HuntType.STANDARD
    else:
      self.name = "VariableGenericHunt"
      self.hunt_type = self.HuntType.VARIABLE
    self.state = str(hunt_obj.hunt_state)
    self.crash_limit = hunt_obj.crash_limit
    self.client_limit = hunt_obj.client_limit
    self.client_rate = hunt_obj.client_rate
    self.created = hunt_obj.create_time
    self.duration = hunt_obj.duration
    self.creator = hunt_obj.creator
    self.init_start_time = hunt_obj.init_start_time
    self.last_start_time = hunt_obj.last_start_time
    self.description = hunt_obj.description
    self.is_robot = hunt_obj.creator in ["GRRWorker", "Cron"]
    if hunt_counters is not None:
      self.results_count = hunt_counters.num_results
      self.clients_with_results_count = hunt_counters.num_clients_with_results
      self.remaining_clients_count = hunt_counters.num_running_clients
      # TODO(user): remove this hack when AFF4 is gone. For regression tests
      # compatibility only.
      self.total_cpu_usage = hunt_counters.total_cpu_seconds or 0
      self.total_net_usage = hunt_counters.total_network_bytes_sent

      if with_full_summary:
        self.all_clients_count = hunt_counters.num_clients
        self.completed_clients_count = (
            hunt_counters.num_successful_clients +
            hunt_counters.num_failed_clients)
    else:
      self.results_count = 0
      self.clients_with_results_count = 0
      self.remaining_clients_count = 0
      self.total_cpu_usage = 0
      self.total_net_usage = 0

      if with_full_summary:
        self.all_clients_count = 0
        self.completed_clients_count = 0

    if hunt_obj.original_object.object_type != "UNKNOWN":
      ref = ApiFlowLikeObjectReference()
      self.original_object = ref.FromFlowLikeObjectReference(
          hunt_obj.original_object)

    if with_full_summary:
      hra = self.hunt_runner_args = rdf_hunts.HuntRunnerArgs(
          hunt_name=self.name,
          description=hunt_obj.description,
          client_rule_set=hunt_obj.client_rule_set,
          crash_limit=hunt_obj.crash_limit,
          expiry_time=hunt_obj.duration,
          avg_results_per_client_limit=hunt_obj.avg_results_per_client_limit,
          avg_cpu_seconds_per_client_limit=hunt_obj
          .avg_cpu_seconds_per_client_limit,
          avg_network_bytes_per_client_limit=hunt_obj
          .avg_network_bytes_per_client_limit,
          client_rate=hunt_obj.client_rate,
          original_object=hunt_obj.original_object)

      if hunt_obj.HasField("output_plugins"):
        hra.output_plugins = hunt_obj.output_plugins

      # TODO(user): This is a backwards compatibility code. Remove
      # HuntRunnerArgs from ApiHunt.
      if hunt_obj.client_limit != 100:
        hra.client_limit = hunt_obj.client_limit

      if hunt_obj.HasField("per_client_cpu_limit"):
        hra.per_client_cpu_limit = hunt_obj.per_client_cpu_limit

      if hunt_obj.HasField("per_client_network_limit_bytes"):
        hra.per_client_network_limit_bytes = (
            hunt_obj.per_client_network_bytes_limit)

      if hunt_obj.HasField("total_network_bytes_limit"):
        hra.network_bytes_limit = hunt_obj.total_network_bytes_limit

      self.client_rule_set = hunt_obj.client_rule_set

      if (hunt_obj.args.hunt_type ==
          rdf_hunt_objects.HuntArguments.HuntType.STANDARD):
        self.flow_name = hunt_obj.args.standard.flow_name
        self.flow_args = hunt_obj.args.standard.flow_args
      elif (hunt_obj.args.hunt_type ==
            rdf_hunt_objects.HuntArguments.HuntType.VARIABLE):
        self.flow_args = hunt_obj.args.variable

    return self

  def InitFromHuntMetadata(self, hunt_metadata):
    """Initialize API hunt object from a hunt metadata object.

    Args:
      hunt_metadata: rdf_hunt_objects.HuntMetadata to read the data from.

    Returns:
      Self.
    """
    self.urn = rdfvalue.RDFURN("hunts").Add(str(hunt_metadata.hunt_id))
    self.hunt_id = hunt_metadata.hunt_id
    self.state = str(hunt_metadata.hunt_state)
    self.client_limit = hunt_metadata.client_limit
    self.client_rate = hunt_metadata.client_rate
    self.created = hunt_metadata.create_time
    self.init_start_time = hunt_metadata.init_start_time
    self.last_start_time = hunt_metadata.last_start_time
    self.duration = hunt_metadata.duration
    self.creator = hunt_metadata.creator
    self.description = hunt_metadata.description
    self.is_robot = hunt_metadata.creator in ["GRRWorker", "Cron"]

    return self

  def ObjectReference(self):
    return rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.HUNT,
        hunt=rdf_objects.HuntReference(hunt_id=str(self.hunt_id)))


class ApiHuntResult(rdf_structs.RDFProtoStruct):
  """API hunt results object."""

  protobuf = hunt_pb2.ApiHuntResult
  rdf_deps = [
      api_client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]

  def GetPayloadClass(self):
    return rdfvalue.RDFValue.classes[self.payload_type]

  def InitFromFlowResult(self, flow_result):
    """Init from rdf_flow_objects.FlowResult."""

    self.payload_type = compatibility.GetName(flow_result.payload.__class__)
    self.payload = flow_result.payload
    self.client_id = flow_result.client_id
    self.timestamp = flow_result.timestamp

    return self


class ApiHuntClient(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiHuntClient
  rdf_deps = [
      api_client.ApiClientId,
      api_flow.ApiFlowId,
  ]


class ApiHuntLog(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiHuntLog
  rdf_deps = [
      api_client.ApiClientId,
      api_flow.ApiFlowId,
      rdfvalue.RDFDatetime,
  ]

  def InitFromFlowLog(self, fl):
    if fl.HasField("client_id"):
      self.client_id = fl.client_id.Basename()
      if fl.HasField("urn"):
        self.flow_id = fl.urn.RelativeName(fl.client_id)

    self.timestamp = fl.age
    self.log_message = fl.log_message
    self.flow_name = fl.flow_name

    return self

  def InitFromFlowLogEntry(self, fle):
    """Init from FlowLogEntry rdfvalue."""

    # TODO(user): putting this stub value for backwards compatibility.
    # Remove as soon as AFF4 is gone.
    self.flow_name = "GenericHunt"

    self.client_id = fle.client_id
    self.flow_id = fle.flow_id
    self.timestamp = fle.timestamp
    self.log_message = fle.message

    return self


class ApiHuntError(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiHuntError
  rdf_deps = [
      api_client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]

  def InitFromFlowObject(self, fo):
    """Initialize from rdf_flow_objects.Flow corresponding to a failed flow."""

    self.client_id = fo.client_id
    if fo.HasField("backtrace"):
      self.backtrace = fo.backtrace
    self.log_message = fo.error_message
    self.timestamp = fo.last_update_time

    return self


class ApiListHuntsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntsArgs
  rdf_deps = [
      rdfvalue.DurationSeconds,
  ]


class ApiListHuntsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntsResult
  rdf_deps = [
      ApiHunt,
  ]


class ApiListHuntsHandler(api_call_handler_base.ApiCallHandler):
  """Renders list of available hunts."""

  args_type = ApiListHuntsArgs
  result_type = ApiListHuntsResult

  def _CreatedByFilterRelational(self, username, hunt_obj):
    return hunt_obj.creator == username

  def _DescriptionContainsFilterRelational(self, substring, hunt_obj):
    return substring in hunt_obj.description

  def _Username(self, username, context):
    if username == "me":
      return context.username
    else:
      return username

  def _BuildFilter(self, args, context):
    filters = []

    if ((args.created_by or args.description_contains) and
        not args.active_within):
      raise ValueError("created_by/description_contains filters have to be "
                       "used together with active_within filter (to prevent "
                       "queries of death)")

    if args.created_by:
      filters.append(
          functools.partial(self._CreatedByFilterRelational,
                            self._Username(args.created_by, context)))

    if args.description_contains:
      filters.append(
          functools.partial(self._DescriptionContainsFilterRelational,
                            args.description_contains))

    if filters:

      def Filter(x):
        for f in filters:
          if not f(x):
            return False

        return True

      return Filter
    else:
      return None

  def Handle(self, args, context=None):
    if args.description_contains and not args.active_within:
      raise ValueError("description_contains filter has to be "
                       "used together with active_within filter")

    kw_args = {}
    if args.created_by:
      kw_args["with_creator"] = self._Username(args.created_by, context)
    if args.description_contains:
      kw_args["with_description_match"] = args.description_contains
    if args.active_within:
      kw_args["created_after"] = rdfvalue.RDFDatetime.Now() - args.active_within

    hunt_metadatas = data_store.REL_DB.ListHuntObjects(
        args.offset, args.count or db.MAX_COUNT, **kw_args)

    # TODO(user): total_count is not returned by the current implementation.
    # It's not clear, if it's needed - GRR UI doesn't show total number of
    # available hunts anywhere. Adding it would require implementing
    # an additional data_store.REL_DB.CountHuntObjects method.
    return ApiListHuntsResult(
        items=[ApiHunt().InitFromHuntMetadata(h) for h in hunt_metadatas])


class ApiGetHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's summary."""

  args_type = ApiGetHuntArgs
  result_type = ApiHunt

  def Handle(self, args, context=None):
    try:
      hunt_id = str(args.hunt_id)
      hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
      hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)

      return ApiHunt().InitFromHuntObject(
          hunt_obj, hunt_counters=hunt_counters, with_full_summary=True)
    except db.UnknownHuntError:
      raise HuntNotFoundError("Hunt with id %s could not be found" %
                              args.hunt_id)


class ApiListHuntResultsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntResultsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntResultsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntResultsResult
  rdf_deps = [
      ApiHuntResult,
  ]


class ApiListHuntResultsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt results."""

  args_type = ApiListHuntResultsArgs
  result_type = ApiListHuntResultsResult

  def Handle(self, args, context=None):
    results = data_store.REL_DB.ReadHuntResults(
        str(args.hunt_id),
        args.offset,
        args.count or db.MAX_COUNT,
        with_substring=args.filter or None)

    total_count = data_store.REL_DB.CountHuntResults(str(args.hunt_id))

    return ApiListHuntResultsResult(
        items=[ApiHuntResult().InitFromFlowResult(r) for r in results],
        total_count=total_count)


class ApiListHuntCrashesArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntCrashesArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntCrashesResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntCrashesResult
  rdf_deps = [
      rdf_client.ClientCrash,
  ]


class ApiListHuntCrashesHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of client crashes for the given hunt."""

  args_type = ApiListHuntCrashesArgs
  result_type = ApiListHuntCrashesResult

  def Handle(self, args, context=None):
    flows = data_store.REL_DB.ReadHuntFlows(
        str(args.hunt_id),
        args.offset,
        args.count or db.MAX_COUNT,
        filter_condition=db.HuntFlowsCondition.CRASHED_FLOWS_ONLY)
    total_count = data_store.REL_DB.CountHuntFlows(
        str(args.hunt_id),
        filter_condition=db.HuntFlowsCondition.CRASHED_FLOWS_ONLY)

    return ApiListHuntCrashesResult(
        items=[f.client_crash_info for f in flows], total_count=total_count)


class ApiGetHuntResultsExportCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntResultsExportCommandArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntResultsExportCommandResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntResultsExportCommandResult


class ApiGetHuntResultsExportCommandHandler(api_call_handler_base.ApiCallHandler
                                           ):
  """Renders GRR export tool command line that exports hunt results."""

  args_type = ApiGetHuntResultsExportCommandArgs
  result_type = ApiGetHuntResultsExportCommandResult

  def Handle(self, args, context=None):
    output_fname = re.sub("[^0-9a-zA-Z]+", "_", str(args.hunt_id))
    code_to_execute = ("""grrapi.Hunt("%s").GetFilesArchive()."""
                       """WriteToFile("./hunt_results_%s.zip")""") % (
                           args.hunt_id, output_fname)

    export_command_str = " ".join([
        config.CONFIG["AdminUI.export_command"], "--exec_code",
        utils.ShellQuote(code_to_execute)
    ])

    return ApiGetHuntResultsExportCommandResult(command=export_command_str)


class ApiListHuntOutputPluginsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntOutputPluginsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginsResult
  rdf_deps = [
      api_output_plugin.ApiOutputPlugin,
  ]


class ApiListHuntOutputPluginsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's output plugins states."""

  args_type = ApiListHuntOutputPluginsArgs
  result_type = ApiListHuntOutputPluginsResult

  def Handle(self, args, context=None):
    used_names = collections.Counter()
    result = []
    try:
      plugin_states = data_store.REL_DB.ReadHuntOutputPluginsStates(
          str(args.hunt_id))
    except db.UnknownHuntError:
      raise HuntNotFoundError("Hunt with id %s could not be found" %
                              str(args.hunt_id))
    for s in plugin_states:
      name = s.plugin_descriptor.plugin_name
      plugin_id = "%s_%d" % (name, used_names[name])
      used_names[name] += 1

      state = s.plugin_state.Copy()
      if "source_urn" in state:
        del state["source_urn"]
      if "token" in state:
        del state["token"]
      if "errors" in state and not state["errors"]:
        del state["errors"]
      if "logs" in state and not state["logs"]:
        del state["logs"]
      if "error_count" in state and not state["error_count"]:
        del state["error_count"]
      if "success_count" in state and not state["success_count"]:
        del state["success_count"]

      api_plugin = api_output_plugin.ApiOutputPlugin(
          id=plugin_id, plugin_descriptor=s.plugin_descriptor, state=state)
      result.append(api_plugin)

    return ApiListHuntOutputPluginsResult(items=result, total_count=len(result))


class ApiListHuntOutputPluginLogsHandlerBase(
    api_call_handler_base.ApiCallHandler):
  """Base class used to define log and status messages handlers."""

  __abstract = True  # pylint: disable=g-bad-name

  log_entry_type = None
  collection_type = None
  collection_counter = None

  def Handle(self, args, context=None):
    h = data_store.REL_DB.ReadHuntObject(str(args.hunt_id))

    if self.__class__.log_entry_type is None:
      raise ValueError(
          "log_entry_type has to be overridden and set to a meaningful value.")

    index = api_flow.GetOutputPluginIndex(h.output_plugins, args.plugin_id)
    output_plugin_id = "%d" % index

    logs = data_store.REL_DB.ReadHuntOutputPluginLogEntries(
        str(args.hunt_id),
        output_plugin_id,
        args.offset,
        args.count or db.MAX_COUNT,
        with_type=self.__class__.log_entry_type)
    total_count = data_store.REL_DB.CountHuntOutputPluginLogEntries(
        str(args.hunt_id),
        output_plugin_id,
        with_type=self.__class__.log_entry_type)

    return self.result_type(
        total_count=total_count,
        items=[l.ToOutputPluginBatchProcessingStatus() for l in logs])


class ApiListHuntOutputPluginLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginLogsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntOutputPluginLogsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginLogsResult
  rdf_deps = [
      output_plugin.OutputPluginBatchProcessingStatus,
  ]


class ApiListHuntOutputPluginLogsHandler(ApiListHuntOutputPluginLogsHandlerBase
                                        ):
  """Renders hunt's output plugin's log."""

  args_type = ApiListHuntOutputPluginLogsArgs
  result_type = ApiListHuntOutputPluginLogsResult

  log_entry_type = rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.LOG

  collection_type = "logs"
  collection_counter = "success_count"


class ApiListHuntOutputPluginErrorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginErrorsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntOutputPluginErrorsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntOutputPluginErrorsResult
  rdf_deps = [
      output_plugin.OutputPluginBatchProcessingStatus,
  ]


class ApiListHuntOutputPluginErrorsHandler(
    ApiListHuntOutputPluginLogsHandlerBase):
  """Renders hunt's output plugin's errors."""

  args_type = ApiListHuntOutputPluginErrorsArgs
  result_type = ApiListHuntOutputPluginErrorsResult

  log_entry_type = rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.ERROR

  collection_type = "errors"
  collection_counter = "error_count"


class ApiListHuntLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntLogsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntLogsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntLogsResult
  rdf_deps = [ApiHuntLog]


class ApiListHuntLogsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of log elements for the given hunt."""

  args_type = ApiListHuntLogsArgs
  result_type = ApiListHuntLogsResult

  def Handle(self, args, context=None):
    results = data_store.REL_DB.ReadHuntLogEntries(
        str(args.hunt_id),
        args.offset,
        args.count or db.MAX_COUNT,
        with_substring=args.filter or None)

    total_count = data_store.REL_DB.CountHuntLogEntries(str(args.hunt_id))

    return ApiListHuntLogsResult(
        items=[ApiHuntLog().InitFromFlowLogEntry(r) for r in results],
        total_count=total_count)


class ApiListHuntErrorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntErrorsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntErrorsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntErrorsResult
  rdf_deps = [
      ApiHuntError,
  ]


class ApiListHuntErrorsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of errors for the given hunt."""

  args_type = ApiListHuntErrorsArgs
  result_type = ApiListHuntErrorsResult

  _FLOW_ATTRS_TO_MATCH = ["flow_id", "client_id", "error_message", "backtrace"]

  def _MatchFlowAgainstFilter(self, flow_obj, filter_str):
    for attr in self._FLOW_ATTRS_TO_MATCH:
      if filter_str in flow_obj.Get(attr):
        return True

    return False

  def Handle(self, args, context=None):
    total_count = data_store.REL_DB.CountHuntFlows(
        str(args.hunt_id),
        filter_condition=db.HuntFlowsCondition.FAILED_FLOWS_ONLY)
    if args.filter:
      flows = data_store.REL_DB.ReadHuntFlows(
          str(args.hunt_id),
          args.offset,
          total_count,
          filter_condition=db.HuntFlowsCondition.FAILED_FLOWS_ONLY)
      flows = [f for f in flows if self._MatchFlowAgainstFilter(f, args.filter)]
    else:
      flows = data_store.REL_DB.ReadHuntFlows(
          str(args.hunt_id),
          args.offset,
          args.count or db.MAX_COUNT,
          filter_condition=db.HuntFlowsCondition.FAILED_FLOWS_ONLY)

    return ApiListHuntErrorsResult(
        items=[ApiHuntError().InitFromFlowObject(f) for f in flows],
        total_count=total_count)


class ApiGetHuntClientCompletionStatsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntClientCompletionStatsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntClientCompletionStatsResult(rdf_structs.RDFProtoStruct):
  """Result for getting the client completions of a hunt."""
  protobuf = hunt_pb2.ApiGetHuntClientCompletionStatsResult
  rdf_deps = [
      rdf_stats.SampleFloat,
  ]

  def InitFromDataPoints(self, start_stats, complete_stats):
    """Check that this approval applies to the given context.

    Args:
      start_stats: A list of lists, each containing two values (a timestamp and
        the number of clients started at this time).
      complete_stats: A list of lists, each containing two values (a timestamp
        and the number of clients completed at this time).

    Returns:
      A reference to the current instance to allow method chaining.
    """
    self.start_points = self._ConvertToResultList(start_stats)
    self.complete_points = self._ConvertToResultList(complete_stats)
    return self

  def _ConvertToResultList(self, stats):
    result = []
    for stat in stats:
      data_point = rdf_stats.SampleFloat()
      data_point.x_value = stat[0]
      data_point.y_value = stat[1]
      result.append(data_point)
    return result


class ApiGetHuntClientCompletionStatsHandler(
    api_call_handler_base.ApiCallHandler):
  """Calculates hunt's client completion stats."""

  args_type = ApiGetHuntClientCompletionStatsArgs
  result_type = ApiGetHuntClientCompletionStatsResult

  def Handle(self, args, context=None):
    target_size = args.size
    if target_size <= 0:
      target_size = 1000

    states_and_timestamps = data_store.REL_DB.ReadHuntFlowsStatesAndTimestamps(
        str(args.hunt_id))

    started_clients = []
    completed_clients = []

    # TODO(user): keeping using RDFURNs only to share _SampleClients and
    # _Resample code between legacy and relational implementations.
    # Get rid of RDFURNs as soon as AFF4 is gone.
    for i, sat in enumerate(states_and_timestamps):
      started_clients.append((rdfvalue.RDFURN(str(i)), sat.create_time))
      if sat.flow_state != rdf_flow_objects.Flow.FlowState.RUNNING:
        completed_clients.append(
            (rdfvalue.RDFURN(str(i)), sat.last_update_time))

    (start_stats, complete_stats) = self._SampleClients(started_clients,
                                                        completed_clients)

    if len(start_stats) > target_size:
      # start_stats and complete_stats are equally big, so resample both
      start_stats = self._Resample(start_stats, target_size)
      complete_stats = self._Resample(complete_stats, target_size)

    return ApiGetHuntClientCompletionStatsResult().InitFromDataPoints(
        start_stats, complete_stats)

  def _SampleClients(self, started_clients, completed_clients):
    # immediately return on empty client data
    if not started_clients and not completed_clients:
      return ([], [])

    cdict = {}
    for client, timestamp in started_clients:
      cdict.setdefault(client, []).append(timestamp)

    fdict = {}
    for client, timestamp in completed_clients:
      fdict.setdefault(client, []).append(timestamp)

    cl_age = [min(x).AsSecondsSinceEpoch() for x in cdict.values()]
    fi_age = [min(x).AsSecondsSinceEpoch() for x in fdict.values()]

    cl_hist = {}
    fi_hist = {}

    for age in cl_age:
      cl_hist.setdefault(age, 0)
      cl_hist[age] += 1

    for age in fi_age:
      fi_hist.setdefault(age, 0)
      fi_hist[age] += 1

    t0 = min(cl_age) - 1
    times = [t0]
    cl = [0]
    fi = [0]

    all_times = set(cl_age) | set(fi_age)
    cl_count = 0
    fi_count = 0

    for time in sorted(all_times):
      cl_count += cl_hist.get(time, 0)
      fi_count += fi_hist.get(time, 0)

      times.append(time)
      cl.append(cl_count)
      fi.append(fi_count)

    return (list(zip(times, cl)), list(zip(times, fi)))

  def _Resample(self, stats, target_size):
    """Resamples the stats to have a specific number of data points."""
    t_first = stats[0][0]
    t_last = stats[-1][0]
    interval = (t_last - t_first) / target_size

    result = []

    current_t = t_first
    current_v = 0
    i = 0
    while i < len(stats):
      stat_t = stats[i][0]
      stat_v = stats[i][1]
      if stat_t <= (current_t + interval):
        # Always add the last value in an interval to the result.
        current_v = stat_v
        i += 1
      else:
        result.append([current_t + interval, current_v])
        current_t += interval

    result.append([current_t + interval, current_v])
    return result


class ApiGetHuntFilesArchiveArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntFilesArchiveArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntFilesArchiveHandler(api_call_handler_base.ApiCallHandler):
  """Generates archive with all files referenced in flow's results."""

  args_type = ApiGetHuntFilesArchiveArgs

  def _WrapContentGenerator(self, generator, collection, args, context=None):
    try:

      for item in generator.Generate(collection):
        yield item

      notification.Notify(
          context.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED,
          "Downloaded archive of hunt %s results (archived %d "
          "out of %d items, archive size is %d)" %
          (args.hunt_id, len(generator.archived_files), generator.total_files,
           generator.output_size), None)
    except Exception as e:
      notification.Notify(
          context.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
          "Archive generation failed for hunt %s: %s" % (args.hunt_id, e), None)

      raise

  def _LoadData(self, args, context=None):
    hunt_id = str(args.hunt_id)
    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    hunt_api_object = ApiHunt().InitFromHuntObject(hunt_obj)
    description = ("Files downloaded by hunt %s (%s, '%s') created by user %s "
                   "on %s" % (hunt_api_object.name, hunt_api_object.hunt_id,
                              hunt_api_object.description,
                              hunt_api_object.creator, hunt_api_object.created))
    # TODO(user): write general-purpose batcher for such cases.
    results = data_store.REL_DB.ReadHuntResults(
        hunt_id, offset=0, count=db.MAX_COUNT)
    return results, description

  def Handle(self, args, context=None):
    collection, description = self._LoadData(args, context=context)
    target_file_prefix = "hunt_" + str(args.hunt_id).replace(":", "_")

    if args.archive_format == args.ArchiveFormat.ZIP:
      archive_format = archive_generator.CollectionArchiveGenerator.ZIP
      file_extension = ".zip"
    elif args.archive_format == args.ArchiveFormat.TAR_GZ:
      archive_format = archive_generator.CollectionArchiveGenerator.TAR_GZ
      file_extension = ".tar.gz"
    else:
      raise ValueError("Unknown archive format: %s" % args.archive_format)

    generator = archive_generator.CollectionArchiveGenerator(
        prefix=target_file_prefix,
        description=description,
        archive_format=archive_format)
    content_generator = self._WrapContentGenerator(
        generator, collection, args, context=context)
    return api_call_handler_base.ApiBinaryStream(
        target_file_prefix + file_extension,
        content_generator=content_generator)


class ApiGetHuntFileArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntFileArgs
  rdf_deps = [
      api_client.ApiClientId,
      ApiHuntId,
      rdfvalue.RDFDatetime,
  ]


class ApiGetHuntFileHandler(api_call_handler_base.ApiCallHandler):
  """Downloads a file referenced in the hunt results."""

  args_type = ApiGetHuntFileArgs

  MAX_RECORDS_TO_CHECK = 1024
  CHUNK_SIZE = 1024 * 1024 * 4

  def _GenerateFile(self, fd):
    while True:
      chunk = fd.read(self.CHUNK_SIZE)
      if chunk:
        yield chunk
      else:
        break

  def Handle(self, args, context=None):
    if not args.hunt_id:
      raise ValueError("ApiGetHuntFileArgs.hunt_id can't be unset")

    if not args.client_id:
      raise ValueError("ApiGetHuntFileArgs.client_id can't be unset")

    if not args.vfs_path:
      raise ValueError("ApiGetHuntFileArgs.vfs_path can't be unset")

    if not args.timestamp:
      raise ValueError("ApiGetHuntFileArgs.timestamp can't be unset")

    api_vfs.ValidateVfsPath(args.vfs_path)

    path_type, components = rdf_objects.ParseCategorizedPath(args.vfs_path)
    expected_client_path = db.ClientPath(
        str(args.client_id), path_type, components)

    results = data_store.REL_DB.ReadHuntResults(
        str(args.hunt_id),
        offset=0,
        count=self.MAX_RECORDS_TO_CHECK,
        with_timestamp=args.timestamp)
    for item in results:
      try:
        # Do not pass the client id we got from the caller. This will
        # get filled automatically from the hunt results and we check
        # later that the aff4_path we get is the same as the one that
        # was requested.
        client_path = export.CollectionItemToClientPath(item, client_id=None)
      except export.ItemNotExportableError:
        continue

      if client_path != expected_client_path:
        continue

      try:
        # TODO(user): this effectively downloads the latest version of
        # the file and always disregards the timestamp. Reconsider this logic
        # after AFF4 implementation is gone. We also most likely don't need
        # the MAX_RECORDS_TO_CHECK logic in the new implementation.
        file_obj = file_store.OpenFile(client_path)
        return api_call_handler_base.ApiBinaryStream(
            "%s_%s" % (args.client_id, os.path.basename(file_obj.Path())),
            content_generator=self._GenerateFile(file_obj),
            content_length=file_obj.size)
      except (file_store.FileHasNoContentError, file_store.FileNotFoundError):
        break

    raise HuntFileNotFoundError(
        "File %s with timestamp %s and client %s "
        "wasn't found among the results of hunt %s" %
        (args.vfs_path, args.timestamp, args.client_id, args.hunt_id))


class ApiGetHuntStatsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntStatsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntStatsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntStatsResult
  rdf_deps = [
      rdf_stats.ClientResourcesStats,
  ]


class ApiGetHuntStatsHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt stats request."""

  args_type = ApiGetHuntStatsArgs
  result_type = ApiGetHuntStatsResult

  def Handle(self, args, context=None):
    del context  # Unused.
    stats = data_store.REL_DB.ReadHuntClientResourcesStats(str(args.hunt_id))
    return ApiGetHuntStatsResult(stats=stats)


class ApiListHuntClientsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntClientsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntClientsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntClientsResult
  rdf_deps = [
      ApiHuntClient,
  ]


class ApiListHuntClientsHandler(api_call_handler_base.ApiCallHandler):
  """Handles requests for hunt clients."""

  args_type = ApiListHuntClientsArgs
  result_type = ApiListHuntClientsResult

  def Handle(self, args, context=None):
    hunt_id = str(args.hunt_id)

    filter_condition = db.HuntFlowsCondition.UNSET
    if args.client_status == args.ClientStatus.OUTSTANDING:
      filter_condition = db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY
    elif args.client_status == args.ClientStatus.COMPLETED:
      filter_condition = db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY

    total_count = data_store.REL_DB.CountHuntFlows(
        hunt_id, filter_condition=filter_condition)
    hunt_flows = data_store.REL_DB.ReadHuntFlows(
        hunt_id,
        args.offset,
        args.count or db.MAX_COUNT,
        filter_condition=filter_condition)
    results = [
        ApiHuntClient(client_id=hf.client_id, flow_id=hf.flow_id)
        for hf in hunt_flows
    ]

    return ApiListHuntClientsResult(items=results, total_count=total_count)


class ApiGetHuntContextArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntContextArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntContextResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntContextResult
  rdf_deps = [
      api_call_handler_utils.ApiDataObject,
      rdf_hunts.HuntContext,
  ]


class ApiGetHuntContextHandler(api_call_handler_base.ApiCallHandler):
  """Handles requests for hunt contexts."""

  args_type = ApiGetHuntContextArgs
  result_type = ApiGetHuntContextResult

  def Handle(self, args, context=None):
    hunt_id = str(args.hunt_id)
    h = data_store.REL_DB.ReadHuntObject(hunt_id)
    h_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
    context = rdf_hunts.HuntContext(
        session_id=rdfvalue.RDFURN("hunts").Add(h.hunt_id),
        create_time=h.create_time,
        creator=h.creator,
        duration=h.duration,
        network_bytes_sent=h_counters.total_network_bytes_sent,
        next_client_due=h.last_start_time,
        start_time=h.last_start_time,
        # TODO(user): implement proper hunt client resources starts support
        # for REL_DB hunts.
        # usage_stats=h.client_resources_stats
    )
    return ApiGetHuntContextResult(
        context=context, state=api_call_handler_utils.ApiDataObject())


class ApiCreateHuntArgs(rdf_structs.RDFProtoStruct):
  """Args for the ApiCreateHuntHandler."""
  protobuf = hunt_pb2.ApiCreateHuntArgs
  rdf_deps = [
      rdf_hunts.HuntRunnerArgs,
      ApiHuntReference,
      api_flow.ApiFlowReference,
  ]

  def GetFlowArgsClass(self):
    if self.flow_name:
      flow_cls = registry.FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class ApiCreateHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt creation request."""

  args_type = ApiCreateHuntArgs
  result_type = ApiHunt

  def Handle(self, args, context=None):
    hra = args.hunt_runner_args

    hunt_obj = rdf_hunt_objects.Hunt(
        args=rdf_hunt_objects.HuntArguments(
            hunt_type=rdf_hunt_objects.HuntArguments.HuntType.STANDARD,
            standard=rdf_hunt_objects.HuntArgumentsStandard(
                flow_name=args.flow_name, flow_args=args.flow_args)),
        description=hra.description,
        client_rule_set=hra.client_rule_set,
        client_limit=hra.client_limit,
        crash_limit=hra.crash_limit,
        avg_results_per_client_limit=hra.avg_results_per_client_limit,
        avg_cpu_seconds_per_client_limit=hra.avg_cpu_seconds_per_client_limit,
        avg_network_bytes_per_client_limit=hra
        .avg_network_bytes_per_client_limit,
        duration=hra.expiry_time,
        client_rate=hra.client_rate,
        per_client_cpu_limit=hra.per_client_cpu_limit,
        per_client_network_bytes_limit=hra.per_client_network_limit_bytes,
        creator=context.username,
    )

    if args.original_hunt and args.original_flow:
      raise ValueError(
          "A hunt can't be a copy of a flow and a hunt at the same time.")

    if args.original_hunt:
      ref = rdf_hunts.FlowLikeObjectReference.FromHuntId(
          args.original_hunt.hunt_id)
      hunt_obj.original_object = ref
    elif args.original_flow:
      ref = rdf_hunts.FlowLikeObjectReference.FromFlowIdAndClientId(
          args.original_flow.flow_id, args.original_flow.client_id)
      hunt_obj.original_object = ref

    if hra.HasField("output_plugins"):
      hunt_obj.output_plugins = hra.output_plugins

    hunt.CreateHunt(hunt_obj)

    return ApiHunt().InitFromHuntObject(hunt_obj, with_full_summary=True)


class ApiModifyHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiModifyHuntArgs
  rdf_deps = [
      ApiHuntId,
      rdfvalue.DurationSeconds,
      rdfvalue.RDFDatetime,
  ]


class ApiModifyHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt modifys (this includes starting/stopping the hunt)."""

  args_type = ApiModifyHuntArgs
  result_type = ApiHunt

  def Handle(self, args, context=None):
    hunt_id = str(args.hunt_id)

    has_change = False
    for field_name in ["client_limit", "client_rate", "expires"]:
      if args.HasField(field_name):
        has_change = True
        break

    try:
      hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
      if has_change:
        kw_args = {}
        if hunt_obj.hunt_state != hunt_obj.HuntState.PAUSED:
          raise HuntNotModifiableError(
              "Hunt's client limit/client rate/expiry time attributes "
              "can only be changed if hunt's current state is "
              "PAUSED")

        if args.HasField("client_limit"):
          kw_args["client_limit"] = args.client_limit

        if args.HasField("client_rate"):
          kw_args["client_rate"] = args.client_rate

        if args.duration is None:
          kw_args["duration"] = None
        else:
          kw_args["duration"] = rdfvalue.Duration(args.duration)

        data_store.REL_DB.UpdateHuntObject(hunt_id, **kw_args)
        hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    except db.UnknownHuntError:
      raise HuntNotFoundError("Hunt with id %s could not be found" %
                              args.hunt_id)

    if args.HasField("state"):
      if args.state == ApiHunt.State.STARTED:
        if hunt_obj.hunt_state != hunt_obj.HuntState.PAUSED:
          raise HuntNotStartableError(
              "Hunt can only be started from PAUSED state.")
        hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)

      elif args.state == ApiHunt.State.STOPPED:
        if hunt_obj.hunt_state not in [
            hunt_obj.HuntState.PAUSED, hunt_obj.HuntState.STARTED
        ]:
          raise HuntNotStoppableError(
              "Hunt can only be stopped from STARTED or "
              "PAUSED states.")
        hunt_obj = hunt.StopHunt(hunt_obj.hunt_id)

      else:
        raise InvalidHuntStateError(
            "Hunt's state can only be updated to STARTED or STOPPED")

    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_obj.hunt_id)
    return ApiHunt().InitFromHuntObject(
        hunt_obj, hunt_counters=hunt_counters, with_full_summary=True)


class ApiDeleteHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiDeleteHuntArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiDeleteHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt deletions."""

  args_type = ApiDeleteHuntArgs

  def Handle(self, args, context=None):
    try:
      h = data_store.REL_DB.ReadHuntObject(str(args.hunt_id))
      h_flows_count = data_store.REL_DB.CountHuntFlows(h.hunt_id)

      if h.hunt_state != h.HuntState.PAUSED or h_flows_count > 0:
        raise HuntNotDeletableError("Can only delete a paused hunt without "
                                    "scheduled clients.")

      data_store.REL_DB.DeleteHuntObject(h.hunt_id)
    except db.UnknownHuntError:
      raise HuntNotFoundError("Hunt with id %s could not be found" %
                              args.hunt_id)


class ApiGetExportedHuntResultsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetExportedHuntResultsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetExportedHuntResultsHandler(api_call_handler_base.ApiCallHandler):
  """Exports results of a given hunt with an instant output plugin."""

  args_type = ApiGetExportedHuntResultsArgs

  _RESULTS_PAGE_SIZE = 1000

  def Handle(self, args, context=None):
    hunt_id = str(args.hunt_id)
    source_urn = rdfvalue.RDFURN("hunts").Add(hunt_id)

    iop_cls = instant_output_plugin.InstantOutputPlugin
    plugin_cls = iop_cls.GetPluginClassByPluginName(args.plugin_name)
    # TODO(user): Instant output plugins shouldn't depend on contexts
    # and URNs.
    plugin = plugin_cls(
        source_urn=source_urn,
        token=access_control.ACLToken(username=context.username))

    types = data_store.REL_DB.CountHuntResultsByType(hunt_id)

    def FetchFn(type_name):
      """Fetches all hunt results of a given type."""
      offset = 0
      while True:
        results = data_store.REL_DB.ReadHuntResults(
            hunt_id,
            offset=offset,
            count=self._RESULTS_PAGE_SIZE,
            with_type=type_name)

        if not results:
          break

        for r in results:
          msg = r.AsLegacyGrrMessage()
          msg.source_urn = source_urn
          yield msg

        offset += self._RESULTS_PAGE_SIZE

    content_generator = instant_output_plugin.ApplyPluginToTypedCollection(
        plugin, types, FetchFn)

    return api_call_handler_base.ApiBinaryStream(
        plugin.output_file_name, content_generator=content_generator)


class PerClientFileCollectionArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.PerClientFileCollectionArgs
  rdf_deps = [
      api_client.ApiClientId,
  ]


class ApiCreatePerClientFileCollectionHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiCreatePerClientFileCollectionHuntArgs
  rdf_deps = [
      rdfvalue.DurationSeconds,
      PerClientFileCollectionArgs,
  ]


class ApiCreatePerClientFileCollectionHuntHandler(
    api_call_handler_base.ApiCallHandler):
  """Creates a variable hunt to collect files across multiple clients."""

  args_type = ApiCreatePerClientFileCollectionHuntArgs
  result_type = ApiHunt

  MAX_CLIENTS = 250
  MAX_FILES = 1000

  def _ArgsToHuntArgs(
      self, args: ApiCreatePerClientFileCollectionHuntArgs
  ) -> rdf_hunt_objects.HuntArguments:
    flow_groups = []
    for client_arg in args.per_client_args:
      pathspecs = []
      for p in client_arg.paths:
        pathspecs.append(
            rdf_paths.PathSpec(path=p, pathtype=client_arg.path_type))

      flow_group = rdf_hunt_objects.VariableHuntFlowGroup(
          client_ids=[client_arg.client_id],
          flow_name=transfer.MultiGetFile.__name__,
          flow_args=transfer.MultiGetFileArgs(pathspecs=pathspecs))
      flow_groups.append(flow_group)

    return rdf_hunt_objects.HuntArguments(
        hunt_type=rdf_hunt_objects.HuntArguments.HuntType.VARIABLE,
        variable=rdf_hunt_objects.HuntArgumentsVariable(
            flow_groups=flow_groups))

  def Handle(self, args: ApiCreatePerClientFileCollectionHuntArgs,
             context: api_call_context.ApiCallContext):
    if len(args.per_client_args) > self.MAX_CLIENTS:
      raise ValueError(f"At most {self.MAX_CLIENTS} clients can be specified "
                       "in a per-client file colletion hunt.")

    if sum(len(pca.paths) for pca in args.per_client_args) > self.MAX_FILES:
      raise ValueError(f"At most {self.MAX_FILES} file paths can be specified "
                       "in a per-client file colletion hunt.")

    hunt_obj = rdf_hunt_objects.Hunt(
        args=self._ArgsToHuntArgs(args),
        description=args.description,
        duration=args.duration_secs,
        creator=context.username,
        client_rate=0,
    )
    hunt.CreateHunt(hunt_obj)

    return ApiHunt().InitFromHuntObject(hunt_obj, with_full_summary=True)
