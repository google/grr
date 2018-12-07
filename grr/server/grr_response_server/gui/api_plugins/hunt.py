#!/usr/bin/env python
"""API handlers for accessing hunts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import itertools
import logging
import operator
import re


from builtins import zip  # pylint: disable=redefined-builtin
from future.utils import iteritems
from future.utils import itervalues

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto.api import hunt_pb2

from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import foreman_rules
from grr_response_server import instant_output_plugin
from grr_response_server import notification
from grr_response_server import output_plugin
from grr_response_server.flows.general import export
from grr_response_server.gui import api_call_handler_base
from grr_response_server.gui import api_call_handler_utils
from grr_response_server.gui import archive_generator
from grr_response_server.gui.api_plugins import client as api_client
from grr_response_server.gui.api_plugins import flow as api_flow
from grr_response_server.gui.api_plugins import output_plugin as api_output_plugin
from grr_response_server.gui.api_plugins import vfs as api_vfs
from grr_response_server.hunts import implementation
from grr_response_server.hunts import standard

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

  def __init__(self, initializer=None, age=None):
    super(ApiHuntId, self).__init__(initializer=initializer, age=age)

    # TODO(user): move this to a separate validation method when
    # common RDFValues validation approach is implemented.
    if self._value:
      try:
        rdfvalue.SessionID.ValidateID(self._value)
      except ValueError as e:
        raise ValueError(
            "Invalid hunt id: %s (%s)" % (utils.SmartStr(self._value), e))

  def ToURN(self):
    if not self._value:
      raise ValueError("can't call ToURN() on an empty hunt id.")

    return HUNTS_ROOT_PATH.Add(self._value)


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
  the UI and and to not expose implementation defails.
  """
  protobuf = hunt_pb2.ApiHunt
  rdf_deps = [
      ApiHuntId,
      ApiFlowLikeObjectReference,
      foreman_rules.ForemanClientRuleSet,
      rdf_hunts.HuntRunnerArgs,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]

  def GetFlowArgsClass(self):
    if self.flow_name:
      flow_cls = registry.AFF4FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type

  def InitFromAff4Object(self, hunt, with_full_summary=False):
    try:
      runner = hunt.GetRunner()
      context = runner.context

      self.urn = hunt.urn
      self.hunt_id = hunt.urn.Basename()
      self.name = hunt.runner_args.hunt_name
      self.state = str(hunt.Get(hunt.Schema.STATE))
      self.crash_limit = hunt.runner_args.crash_limit
      self.client_limit = hunt.runner_args.client_limit
      self.client_rate = hunt.runner_args.client_rate
      self.created = context.create_time
      self.expires = context.expires
      self.creator = context.creator
      self.description = hunt.runner_args.description
      self.is_robot = context.creator in ["GRRWorker", "Cron"]
      self.results_count = context.results_count
      self.clients_with_results_count = context.clients_with_results_count
      self.clients_queued_count = context.clients_queued_count
      if hunt.runner_args.original_object.object_type != "UNKNOWN":
        ref = ApiFlowLikeObjectReference()
        self.original_object = ref.FromFlowLikeObjectReference(
            hunt.runner_args.original_object)

      hunt_stats = context.usage_stats
      self.total_cpu_usage = hunt_stats.user_cpu_stats.sum
      self.total_net_usage = hunt_stats.network_bytes_sent_stats.sum

      if with_full_summary:
        # This is an expensive call. Avoid it if not needed.
        all_clients_count, completed_clients_count, _ = hunt.GetClientsCounts()
        self.all_clients_count = all_clients_count
        self.completed_clients_count = completed_clients_count
        self.remaining_clients_count = (
            all_clients_count - completed_clients_count)

        self.hunt_runner_args = hunt.runner_args
        self.client_rule_set = runner.runner_args.client_rule_set

        # We assume we deal here with a GenericHunt and hence hunt.args is a
        # GenericHuntArgs instance. But if we have another kind of hunt
        # (VariableGenericHunt is the only other kind of hunt at the
        # moment), then we shouldn't raise.
        if hunt.args.HasField("flow_runner_args"):
          self.flow_name = hunt.args.flow_runner_args.flow_name
        if self.flow_name and hunt.args.HasField("flow_args"):
          self.flow_args = hunt.args.flow_args
    except Exception as e:  # pylint: disable=broad-except
      self.internal_error = "Error while opening hunt: %s" % str(e)

    return self

  def ObjectReference(self):
    return rdf_objects.ObjectReference(
        reference_type=rdf_objects.ObjectReference.Type.HUNT,
        hunt=rdf_objects.HuntReference(hunt_id=utils.SmartStr(self.hunt_id)))


class ApiHuntResult(rdf_structs.RDFProtoStruct):
  """API hunt results object."""

  protobuf = hunt_pb2.ApiHuntResult
  rdf_deps = [
      api_client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]

  def GetPayloadClass(self):
    return rdfvalue.RDFValue.classes[self.payload_type]

  def InitFromGrrMessage(self, message):
    if message.source:
      self.client_id = message.source.Basename()
    self.payload_type = message.payload.__class__.__name__
    self.payload = message.payload
    self.timestamp = message.age

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


class ApiHuntError(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiHuntError
  rdf_deps = [
      api_client.ApiClientId,
      rdfvalue.RDFDatetime,
  ]

  def InitFromHuntError(self, he):
    if he.HasField("client_id"):
      self.client_id = he.client_id.Basename()

    if he.HasField("backtrace"):
      self.backtrace = he.backtrace

    self.log_message = he.log_message
    self.timestamp = he.age

    return self


class ApiListHuntsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntsArgs
  rdf_deps = [
      rdfvalue.Duration,
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

  def _BuildHuntList(self, hunt_list):
    hunt_list = sorted(
        hunt_list,
        reverse=True,
        key=lambda hunt: hunt.GetRunner().context.create_time)

    return [ApiHunt().InitFromAff4Object(hunt_obj) for hunt_obj in hunt_list]

  def _CreatedByFilter(self, username, hunt_obj):
    return hunt_obj.context.creator == username

  def _DescriptionContainsFilter(self, substring, hunt_obj):
    return substring in hunt_obj.runner_args.description

  def _Username(self, username, token):
    if username == "me":
      return token.username
    else:
      return username

  def _BuildFilter(self, args, token):
    filters = []

    if ((args.created_by or args.description_contains) and
        not args.active_within):
      raise ValueError("created_by/description_contains filters have to be "
                       "used together with active_within filter (to prevent "
                       "queries of death)")

    if args.created_by:
      filters.append(
          functools.partial(self._CreatedByFilter,
                            self._Username(args.created_by, token)))

    if args.description_contains:
      filters.append(
          functools.partial(self._DescriptionContainsFilter,
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

  def HandleNonFiltered(self, args, token):
    fd = aff4.FACTORY.Open("aff4:/hunts", mode="r", token=token)
    children = list(fd.ListChildren())
    total_count = len(children)
    children.sort(key=operator.attrgetter("age"), reverse=True)
    if args.count:
      children = children[args.offset:args.offset + args.count]
    else:
      children = children[args.offset:]

    hunt_list = []
    for hunt in fd.OpenChildren(children=children):
      # Legacy hunts may have hunt.context == None: we just want to skip them.
      if not isinstance(hunt, implementation.GRRHunt) or not hunt.context:
        continue

      hunt_list.append(hunt)

    return ApiListHuntsResult(
        total_count=total_count, items=self._BuildHuntList(hunt_list))

  def HandleFiltered(self, filter_func, args, token):
    fd = aff4.FACTORY.Open("aff4:/hunts", mode="r", token=token)
    children = list(fd.ListChildren())
    children.sort(key=operator.attrgetter("age"), reverse=True)

    if not args.active_within:
      raise ValueError("active_within filter has to be used when "
                       "any kind of filtering is done (to prevent "
                       "queries of death)")

    min_age = rdfvalue.RDFDatetime.Now() - args.active_within
    active_children = []
    for child in children:
      if child.age > min_age:
        active_children.append(child)
      else:
        break

    index = 0
    hunt_list = []
    active_children_map = {}
    for hunt in fd.OpenChildren(children=active_children):
      # Legacy hunts may have hunt.context == None: we just want to skip them.
      if (not isinstance(hunt, implementation.GRRHunt) or not hunt.context or
          not filter_func(hunt)):
        continue
      active_children_map[hunt.urn] = hunt

    for urn in active_children:
      try:
        hunt = active_children_map[urn]
      except KeyError:
        continue

      if index >= args.offset:
        hunt_list.append(hunt)

      index += 1
      if args.count and len(hunt_list) >= args.count:
        break

    return ApiListHuntsResult(items=self._BuildHuntList(hunt_list))

  def Handle(self, args, token=None):
    filter_func = self._BuildFilter(args, token)
    if not filter_func and args.active_within:
      # If no filters except for "active_within" were specified, just use
      # a stub filter function that always returns True. Filtering by
      # active_within is done by HandleFiltered code before other filters
      # are applied.
      filter_func = lambda x: True

    if filter_func:
      return self.HandleFiltered(filter_func, args, token)
    else:
      return self.HandleNonFiltered(args, token)


class ApiGetHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's summary."""

  args_type = ApiGetHuntArgs
  result_type = ApiHunt

  def Handle(self, args, token=None):
    try:
      hunt = aff4.FACTORY.Open(
          args.hunt_id.ToURN(), aff4_type=implementation.GRRHunt, token=token)

      return ApiHunt().InitFromAff4Object(hunt, with_full_summary=True)
    except aff4.InstantiationError:
      raise HuntNotFoundError(
          "Hunt with id %s could not be found" % args.hunt_id)


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

  def Handle(self, args, token=None):
    results_collection = implementation.GRRHunt.ResultCollectionForHID(
        args.hunt_id.ToURN())
    items = api_call_handler_utils.FilterCollection(
        results_collection, args.offset, args.count, args.filter)
    wrapped_items = [ApiHuntResult().InitFromGrrMessage(item) for item in items]

    return ApiListHuntResultsResult(
        items=wrapped_items, total_count=len(results_collection))


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

  def Handle(self, args, token=None):
    crashes = implementation.GRRHunt.CrashCollectionForHID(args.hunt_id.ToURN())
    total_count = len(crashes)
    result = api_call_handler_utils.FilterCollection(crashes, args.offset,
                                                     args.count, args.filter)
    return ApiListHuntCrashesResult(items=result, total_count=total_count)


class ApiGetHuntResultsExportCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntResultsExportCommandArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetHuntResultsExportCommandResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetHuntResultsExportCommandResult


class ApiGetHuntResultsExportCommandHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders GRR export tool command line that exports hunt results."""

  args_type = ApiGetHuntResultsExportCommandArgs
  result_type = ApiGetHuntResultsExportCommandResult

  def Handle(self, args, token=None):
    output_fname = re.sub("[^0-9a-zA-Z]+", "_", utils.SmartStr(args.hunt_id))
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

  def Handle(self, args, token=None):
    metadata = aff4.FACTORY.Create(
        args.hunt_id.ToURN().Add("ResultsMetadata"),
        mode="r",
        aff4_type=implementation.HuntResultsMetadata,
        token=token)

    plugins = metadata.Get(metadata.Schema.OUTPUT_PLUGINS, {})

    result = []
    for plugin_name, (plugin_descriptor, plugin_state) in iteritems(plugins):
      api_plugin = api_output_plugin.ApiOutputPlugin(
          id=plugin_name,
          plugin_descriptor=plugin_descriptor,
          state=plugin_state)
      result.append(api_plugin)

    return ApiListHuntOutputPluginsResult(items=result, total_count=len(result))


class ApiListHuntOutputPluginLogsHandlerBase(
    api_call_handler_base.ApiCallHandler):
  """Base class used to define log and status messages handlerers."""

  __abstract = True  # pylint: disable=g-bad-name

  def CreateCollection(self, hunt_id):
    raise NotImplementedError()

  def Handle(self, args, token=None):
    metadata = aff4.FACTORY.Create(
        args.hunt_id.ToURN().Add("ResultsMetadata"),
        mode="r",
        aff4_type=implementation.HuntResultsMetadata,
        token=token)
    plugins = metadata.Get(metadata.Schema.OUTPUT_PLUGINS, {})
    plugin_descriptor = plugins.get(args.plugin_id)[0]

    # Currently all logs and errors are written not in per-plugin
    # collections, but in per-hunt collections. This doesn't make
    # much sense, because to show errors of particular plugin, we have
    # to filter the collection. Still, things are not too bad, because
    # typically only one output plugin is used.
    #
    # TODO(user): Write errors/logs per-plugin, so that we don't
    # have to do the filtering.

    logs_collection = self.CreateCollection(args.hunt_id.ToURN())

    if len(plugins) == 1:
      total_count = len(logs_collection)
      logs = list(
          itertools.islice(
              logs_collection.GenerateItems(offset=args.offset), args.count or
              None))
    else:
      all_logs_for_plugin = [
          x for x in logs_collection if x.plugin_descriptor == plugin_descriptor
      ]
      total_count = len(all_logs_for_plugin)
      logs = all_logs_for_plugin[args.offset:]
      if args.count:
        logs = logs[:args.count]

    return self.result_type(total_count=total_count, items=logs)


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


class ApiListHuntOutputPluginLogsHandler(
    ApiListHuntOutputPluginLogsHandlerBase):
  """Renders hunt's output plugin's log."""

  args_type = ApiListHuntOutputPluginLogsArgs
  result_type = ApiListHuntOutputPluginLogsResult

  def CreateCollection(self, hunt_id):
    return implementation.GRRHunt.PluginStatusCollectionForHID(hunt_id)


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

  def CreateCollection(self, hunt_id):
    return implementation.GRRHunt.PluginErrorCollectionForHID(hunt_id)


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

  def Handle(self, args, token=None):
    # TODO(user): handle cases when hunt doesn't exists.
    logs_collection = implementation.GRRHunt.LogCollectionForHID(
        args.hunt_id.ToURN())

    result = api_call_handler_utils.FilterCollection(
        logs_collection, args.offset, args.count, args.filter)

    return ApiListHuntLogsResult(
        items=[ApiHuntLog().InitFromFlowLog(x) for x in result],
        total_count=len(logs_collection))


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

  def Handle(self, args, token=None):
    # TODO(user): handle cases when hunt doesn't exists.
    errors_collection = implementation.GRRHunt.ErrorCollectionForHID(
        args.hunt_id.ToURN())

    result = api_call_handler_utils.FilterCollection(
        errors_collection, args.offset, args.count, args.filter)

    return ApiListHuntErrorsResult(
        items=[ApiHuntError().InitFromHuntError(x) for x in result],
        total_count=len(errors_collection))


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
    """Check that this approval applies to the given token.

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

  def Handle(self, args, token=None):
    target_size = args.size
    if target_size <= 0:
      target_size = 1000

    hunt = aff4.FACTORY.Open(
        args.hunt_id.ToURN(),
        aff4_type=implementation.GRRHunt,
        mode="r",
        token=token)

    clients_by_status = hunt.GetClientsByStatus()
    started_clients = clients_by_status["STARTED"]
    completed_clients = clients_by_status["COMPLETED"]

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
    for client in started_clients:
      cdict.setdefault(client, []).append(client.age)

    fdict = {}
    for client in completed_clients:
      fdict.setdefault(client, []).append(client.age)

    cl_age = [min(x).AsSecondsSinceEpoch() for x in itervalues(cdict)]
    fi_age = [min(x).AsSecondsSinceEpoch() for x in itervalues(fdict)]

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

    # Convert to hours, starting from 0.
    times = [(t - t0) / 3600.0 for t in times]
    return (list(zip(times, cl)), list(zip(times, fi)))

  def _Resample(self, stats, target_size):
    """Resamples the stats to have a specific number of data points."""
    t_first = stats[0][0]
    t_last = stats[-1][0]
    interval = (t_last - t_first) / target_size

    result = []
    result.append([0, 0])  # always start at (0, 0)

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

  def _WrapContentGenerator(self, generator, collection, args, token=None):
    try:

      for item in generator.Generate(collection, token=token):
        yield item

      notification.Notify(
          token.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATED,
          "Downloaded archive of hunt %s results (archived %d "
          "out of %d items, archive size is %d)" %
          (args.hunt_id, generator.archived_files, generator.total_files,
           generator.output_size), None)
    except Exception as e:
      notification.Notify(
          token.username,
          rdf_objects.UserNotification.Type.TYPE_FILE_ARCHIVE_GENERATION_FAILED,
          "Archive generation failed for hunt %s: %s" % (args.hunt_id,
                                                         utils.SmartStr(e)),
          None)

      raise

  def Handle(self, args, token=None):
    hunt_urn = args.hunt_id.ToURN()
    hunt = aff4.FACTORY.Open(
        hunt_urn, aff4_type=implementation.GRRHunt, token=token)

    hunt_api_object = ApiHunt().InitFromAff4Object(hunt)
    description = (
        "Files downloaded by hunt %s (%s, '%s') created by user %s "
        "on %s" % (hunt_api_object.name, hunt_api_object.urn.Basename(),
                   hunt_api_object.description, hunt_api_object.creator,
                   hunt_api_object.created))

    collection = implementation.GRRHunt.ResultCollectionForHID(hunt_urn)

    target_file_prefix = "hunt_" + hunt.urn.Basename().replace(":", "_")

    if args.archive_format == args.ArchiveFormat.ZIP:
      archive_format = archive_generator.CollectionArchiveGenerator.ZIP
      file_extension = ".zip"
    elif args.archive_format == args.ArchiveFormat.TAR_GZ:
      archive_format = archive_generator.CollectionArchiveGenerator.TAR_GZ
      file_extension = ".tar.gz"
    else:
      raise ValueError("Unknown archive format: %s" % args.archive_format)

    generator = archive_generator.Aff4CollectionArchiveGenerator(
        prefix=target_file_prefix,
        description=description,
        archive_format=archive_format)
    content_generator = self._WrapContentGenerator(
        generator, collection, args, token=token)
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

  MAX_RECORDS_TO_CHECK = 100
  CHUNK_SIZE = 1024 * 1024 * 4

  def _GenerateFile(self, aff4_stream):
    while True:
      chunk = aff4_stream.Read(self.CHUNK_SIZE)
      if chunk:
        yield chunk
      else:
        break

  def Handle(self, args, token=None):
    if not args.hunt_id:
      raise ValueError("hunt_id can't be None")

    if not args.client_id:
      raise ValueError("client_id can't be None")

    if not args.vfs_path:
      raise ValueError("vfs_path can't be None")

    if not args.timestamp:
      raise ValueError("timestamp can't be None")

    api_vfs.ValidateVfsPath(args.vfs_path)

    results = implementation.GRRHunt.ResultCollectionForHID(
        args.hunt_id.ToURN())

    expected_aff4_path = args.client_id.ToClientURN().Add(args.vfs_path)
    # TODO(user): should after_timestamp be strictly less than the desired
    # timestamp.
    timestamp = rdfvalue.RDFDatetime(int(args.timestamp) - 1)

    # If the entry corresponding to a given path is not found within
    # MAX_RECORDS_TO_CHECK from a given timestamp, we report a 404.
    for _, item in results.Scan(
        after_timestamp=timestamp.AsMicrosecondsSinceEpoch(),
        max_records=self.MAX_RECORDS_TO_CHECK):
      try:
        # Do not pass the client id we got from the caller. This will
        # get filled automatically from the hunt results and we check
        # later that the aff4_path we get is the same as the one that
        # was requested.
        aff4_path = export.CollectionItemToAff4Path(item, client_id=None)
      except export.ItemNotExportableError:
        continue

      if aff4_path != expected_aff4_path:
        continue

      try:
        aff4_stream = aff4.FACTORY.Open(
            aff4_path, aff4_type=aff4.AFF4Stream, token=token)
        if not aff4_stream.GetContentAge():
          break

        return api_call_handler_base.ApiBinaryStream(
            "%s_%s" % (args.client_id, utils.SmartStr(aff4_path.Basename())),
            content_generator=self._GenerateFile(aff4_stream),
            content_length=len(aff4_stream))
      except aff4.InstantiationError:
        break

    raise HuntFileNotFoundError(
        "File %s with timestamp %s and client %s "
        "wasn't found among the results of hunt %s" %
        (utils.SmartStr(args.vfs_path), utils.SmartStr(args.timestamp),
         utils.SmartStr(args.client_id), utils.SmartStr(args.hunt_id)))


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

  def Handle(self, args, token=None):
    """Retrieves the stats for a hunt."""
    hunt = aff4.FACTORY.Open(
        args.hunt_id.ToURN(), aff4_type=implementation.GRRHunt, token=token)

    stats = hunt.GetRunner().context.usage_stats

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

  def Handle(self, args, token=None):
    """Retrieves the clients for a hunt."""
    hunt_urn = args.hunt_id.ToURN()
    hunt = aff4.FACTORY.Open(
        hunt_urn, aff4_type=implementation.GRRHunt, token=token)

    clients_by_status = hunt.GetClientsByStatus()
    hunt_clients = clients_by_status[args.client_status.name]
    total_count = len(hunt_clients)

    if args.count:
      hunt_clients = sorted(hunt_clients)[args.offset:args.offset + args.count]
    else:
      hunt_clients = sorted(hunt_clients)[args.offset:]

    if data_store.RelationalDBFlowsEnabled():
      flow_id = None
    else:
      flow_id = "%s:hunt" % hunt_urn.Basename()
    results = [
        ApiHuntClient(client_id=c.Basename(), flow_id=flow_id)
        for c in hunt_clients
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

  def GetArgsClass(self):
    hunt_name = self.runner_args.hunt_name

    if hunt_name:
      hunt_cls = implementation.GRRHunt.classes.get(hunt_name)
      if hunt_cls is None:
        raise ValueError("Hunt %s not known." % hunt_name)

      # The required protobuf for this class is in args_type.
      return hunt_cls.args_type


class ApiGetHuntContextHandler(api_call_handler_base.ApiCallHandler):
  """Handles requests for hunt contexts."""

  args_type = ApiGetHuntContextArgs
  result_type = ApiGetHuntContextResult

  def Handle(self, args, token=None):
    """Retrieves the context for a hunt."""
    hunt = aff4.FACTORY.Open(
        args.hunt_id.ToURN(), aff4_type=implementation.GRRHunt, token=token)

    if isinstance(hunt.context, rdf_hunts.HuntContext):  # New style hunt.
      # TODO(amoser): Hunt state will go away soon, we don't render it anymore.
      state = api_call_handler_utils.ApiDataObject()
      result = ApiGetHuntContextResult(context=hunt.context, state=state)
      # Assign args last since it needs the other fields set to
      # determine the args protobuf.
      result.args = hunt.args
      return result

    else:
      # Just pack the whole context data object in the state
      # field. This contains everything for old style hunts so we at
      # least show the data somehow.
      context = api_call_handler_utils.ApiDataObject().InitFromDataObject(
          hunt.context)

      return ApiGetHuntContextResult(state=context)


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
      flow_cls = registry.AFF4FlowRegistry.FlowClassByName(self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class ApiCreateHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt creation request."""

  args_type = ApiCreateHuntArgs
  result_type = ApiHunt

  def Handle(self, args, token=None):
    """Creates a new hunt."""

    # We only create generic hunts with /hunts/create requests.
    generic_hunt_args = rdf_hunts.GenericHuntArgs()
    generic_hunt_args.flow_runner_args.flow_name = args.flow_name
    generic_hunt_args.flow_args = args.flow_args

    # Clear all fields marked with HIDDEN, except for output_plugins - they are
    # marked HIDDEN, because we have a separate UI for them, not because they
    # shouldn't be shown to the user at all.
    #
    # TODO(user): Refactor the code to remove the HIDDEN label from
    # HuntRunnerArgs.output_plugins.
    args.hunt_runner_args.ClearFieldsWithLabel(
        rdf_structs.SemanticDescriptor.Labels.HIDDEN,
        exceptions="output_plugins")
    args.hunt_runner_args.hunt_name = standard.GenericHunt.__name__

    if args.original_hunt and args.original_flow:
      raise ValueError(
          "A hunt can't be a copy of a flow and a hunt at the same time.")
    if args.original_hunt:
      ref = rdf_hunts.FlowLikeObjectReference.FromHuntId(
          utils.SmartStr(args.original_hunt.hunt_id))
      args.hunt_runner_args.original_object = ref
    elif args.original_flow:
      ref = rdf_hunts.FlowLikeObjectReference.FromFlowIdAndClientId(
          utils.SmartStr(args.original_flow.flow_id),
          utils.SmartStr(args.original_flow.client_id))
      args.hunt_runner_args.original_object = ref

    # Anyone can create the hunt but it will be created in the paused
    # state. Permissions are required to actually start it.
    with implementation.StartHunt(
        runner_args=args.hunt_runner_args, args=generic_hunt_args,
        token=token) as hunt:

      # Nothing really to do here - hunts are always created in the paused
      # state.
      logging.info("User %s created a new %s hunt (%s)", token.username,
                   hunt.args.flow_runner_args.flow_name, hunt.urn)

      return ApiHunt().InitFromAff4Object(hunt, with_full_summary=True)


class ApiModifyHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiModifyHuntArgs
  rdf_deps = [
      ApiHuntId,
      rdfvalue.RDFDatetime,
  ]


class ApiModifyHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt modifys (this includes starting/stopping the hunt)."""

  args_type = ApiModifyHuntArgs
  result_type = ApiHunt

  def Handle(self, args, token=None):
    hunt_urn = args.hunt_id.ToURN()
    try:
      hunt = aff4.FACTORY.Open(
          hunt_urn, aff4_type=implementation.GRRHunt, mode="rw", token=token)
    except aff4.InstantiationError:
      raise HuntNotFoundError(
          "Hunt with id %s could not be found" % args.hunt_id)

    current_state = hunt.Get(hunt.Schema.STATE)
    hunt_changes = []
    runner = hunt.GetRunner()

    if args.HasField("client_limit"):
      hunt_changes.append("Client Limit: Old=%s, New=%s" %
                          (runner.runner_args.client_limit, args.client_limit))
      runner.runner_args.client_limit = args.client_limit

    if args.HasField("client_rate"):
      hunt_changes.append("Client Rate: Old=%s, New=%s" %
                          (runner.runner_args.client_rate, args.client_limit))
      runner.runner_args.client_rate = args.client_rate

    if args.HasField("expires"):
      hunt_changes.append(
          "Expires: Old=%s, New=%s" % (runner.context.expires, args.expires))
      runner.context.expires = args.expires

    if hunt_changes and current_state != "PAUSED":
      raise HuntNotModifiableError(
          "Hunt's client limit/client rate/expiry time attributes "
          "can only be changed if hunt's current state is "
          "PAUSED")

    if args.HasField("state"):
      hunt_changes.append("State: Old=%s, New=%s" % (current_state, args.state))

      if args.state == ApiHunt.State.STARTED:
        if current_state != "PAUSED":
          raise HuntNotStartableError(
              "Hunt can only be started from PAUSED state.")
        hunt.Run()

      elif args.state == ApiHunt.State.STOPPED:
        if current_state not in ["PAUSED", "STARTED"]:
          raise HuntNotStoppableError(
              "Hunt can only be stopped from STARTED or "
              "PAUSED states.")
        hunt.Stop()

      else:
        raise InvalidHuntStateError(
            "Hunt's state can only be updated to STARTED or STOPPED")

    # Publish an audit event.
    # TODO(user): this should be properly tested.
    event = rdf_events.AuditEvent(
        user=token.username,
        action="HUNT_MODIFIED",
        urn=hunt_urn,
        description=", ".join(hunt_changes))
    events.Events.PublishEvent("Audit", event, token=token)

    hunt.Close()

    hunt = aff4.FACTORY.Open(
        hunt_urn, aff4_type=implementation.GRRHunt, mode="rw", token=token)
    return ApiHunt().InitFromAff4Object(hunt, with_full_summary=True)


class ApiDeleteHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiDeleteHuntArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiDeleteHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt deletions."""

  args_type = ApiDeleteHuntArgs

  def Handle(self, args, token=None):
    hunt_urn = args.hunt_id.ToURN()
    try:
      with aff4.FACTORY.Open(
          hunt_urn, aff4_type=implementation.GRRHunt, mode="rw",
          token=token) as hunt:

        all_clients_count, _, _ = hunt.GetClientsCounts()
        # We can only delete hunts that have no scheduled clients or are in the
        # PAUSED state.
        if hunt.Get(hunt.Schema.STATE) != "PAUSED" or all_clients_count != 0:
          raise HuntNotDeletableError("Can only delete a paused hunt without "
                                      "scheduled clients.")

        # If some clients reported back to the hunt, it can only be deleted
        # if AdminUI.allow_hunt_results_delete is True.
        if (not config.CONFIG["AdminUI.allow_hunt_results_delete"] and
            hunt.client_count):
          raise HuntNotDeletableError(
              "Unable to delete a hunt with results while "
              "AdminUI.allow_hunt_results_delete is disabled.")

      # If we got here, it means that the hunt was found, deletion
      # is allowed in the config, and the hunt is paused and has no
      # scheduled clients.
      # This means that we can safely delete the hunt.
      aff4.FACTORY.Delete(hunt_urn, token=token)

    except aff4.InstantiationError:
      # Raise standard NotFoundError if the hunt object can't be opened.
      raise HuntNotFoundError(
          "Hunt with id %s could not be found" % args.hunt_id)


class ApiGetExportedHuntResultsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiGetExportedHuntResultsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiGetExportedHuntResultsHandler(api_call_handler_base.ApiCallHandler):
  """Exports results of a given hunt with an instant output plugin."""

  args_type = ApiGetExportedHuntResultsArgs

  def Handle(self, args, token=None):
    iop_cls = instant_output_plugin.InstantOutputPlugin
    plugin_cls = iop_cls.GetPluginClassByPluginName(args.plugin_name)

    hunt_urn = args.hunt_id.ToURN()
    try:
      aff4.FACTORY.Open(
          hunt_urn, aff4_type=implementation.GRRHunt, mode="rw", token=token)
    except aff4.InstantiationError:
      raise HuntNotFoundError(
          "Hunt with id %s could not be found" % args.hunt_id)

    output_collection = implementation.GRRHunt.TypedResultCollectionForHID(
        hunt_urn)

    plugin = plugin_cls(source_urn=hunt_urn, token=token)
    return api_call_handler_base.ApiBinaryStream(
        plugin.output_file_name,
        content_generator=instant_output_plugin
        .ApplyPluginToMultiTypeCollection(plugin, output_collection))
