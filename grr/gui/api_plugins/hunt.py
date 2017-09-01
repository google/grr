#!/usr/bin/env python
"""API handlers for accessing hunts."""

import functools
import itertools
import logging
import operator
import re

from grr import config
from grr.gui import api_call_handler_base
from grr.gui import api_call_handler_utils
from grr.gui.api_plugins import client as api_client
from grr.gui.api_plugins import output_plugin as api_output_plugin

from grr.gui.api_plugins import vfs as api_vfs
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import hunts as rdf_hunts
from grr.lib.rdfvalues import stats as rdf_stats
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto.api import hunt_pb2
from grr.server import aff4
from grr.server import data_store

from grr.server import events

from grr.server import flow
from grr.server import foreman
from grr.server import instant_output_plugin
from grr.server import output_plugin
from grr.server.aff4_objects import aff4_grr
from grr.server.aff4_objects import users as aff4_users
from grr.server.flows.general import export

from grr.server.hunts import implementation
from grr.server.hunts import standard

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
  """Class encapsulating client ids."""

  def __init__(self, initializer=None, age=None):
    super(ApiHuntId, self).__init__(initializer=initializer, age=age)

    # TODO(user): move this to a separate validation method when
    # common RDFValues validation approach is implemented.
    if self._value:
      try:
        rdfvalue.SessionID.ValidateID(self._value)
      except ValueError as e:
        raise ValueError("Invalid hunt id: %s (%s)" %
                         (utils.SmartStr(self._value), e))

  def ToURN(self):
    if not self._value:
      raise ValueError("can't call ToURN() on an empty hunt id.")

    return HUNTS_ROOT_PATH.Add(self._value)


class ApiHunt(rdf_structs.RDFProtoStruct):
  """ApiHunt is used when rendering responses.

  ApiHunt is meant to be more lightweight than automatically generated AFF4
  representation. It's also meant to contain only the information needed by
  the UI and and to not expose implementation defails.
  """
  protobuf = hunt_pb2.ApiHunt
  rdf_deps = [
      foreman.ForemanClientRuleSet,
      rdf_hunts.HuntRunnerArgs,
      rdfvalue.RDFDatetime,
      rdfvalue.SessionID,
  ]

  def GetFlowArgsClass(self):
    if self.flow_name:
      flow_cls = flow.GRRFlow.classes.get(self.flow_name)
      if flow_cls is None:
        raise ValueError(
            "Flow %s not known by this implementation." % self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type

  def InitFromAff4Object(self, hunt, with_full_summary=False):
    runner = hunt.GetRunner()
    context = runner.context

    self.urn = hunt.urn
    self.name = hunt.runner_args.hunt_name
    self.state = str(hunt.Get(hunt.Schema.STATE))
    self.crash_limit = hunt.runner_args.crash_limit
    self.client_limit = hunt.runner_args.client_limit
    self.client_rate = hunt.runner_args.client_rate
    self.created = context.create_time
    self.expires = context.expires
    self.creator = context.creator
    self.description = hunt.runner_args.description
    self.is_robot = context.creator == "GRRWorker"
    self.results_count = context.results_count
    self.clients_with_results_count = context.clients_with_results_count

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

    return self


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


class ApiHuntClientPendingRequest(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiHuntClientPendingRequest
  rdf_deps = [
      rdfvalue.RDFURN,
  ]


class ApiHuntClient(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiHuntClient
  rdf_deps = [
      api_client.ApiClientId,
      ApiHuntClientPendingRequest,
      rdf_client.CpuSeconds,
      rdfvalue.RDFURN,
  ]


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
        args.hunt_id.ToURN(), token=token)
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
    crashes = implementation.GRRHunt.CrashCollectionForHID(
        args.hunt_id.ToURN(), token=token)
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
    for plugin_name, (plugin_descriptor, plugin_state) in plugins.items():
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

  def CreateCollection(self, hunt_id, token=None):
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

    logs_collection = self.CreateCollection(args.hunt_id.ToURN(), token=token)

    if len(plugins) == 1:
      total_count = len(logs_collection)
      logs = list(
          itertools.islice(
              logs_collection.GenerateItems(offset=args.offset),
              args.count or None))
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

  def CreateCollection(self, hunt_id, token=None):
    return implementation.GRRHunt.PluginStatusCollectionForHID(
        hunt_id, token=token)


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

  def CreateCollection(self, hunt_id, token=None):
    return implementation.GRRHunt.PluginErrorCollectionForHID(
        hunt_id, token=token)


class ApiListHuntLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntLogsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntLogsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntLogsResult
  rdf_deps = [
      rdf_flows.FlowLog,
  ]


class ApiListHuntLogsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of log elements for the given hunt."""

  args_type = ApiListHuntLogsArgs
  result_type = ApiListHuntLogsResult

  def Handle(self, args, token=None):
    # TODO(user): handle cases when hunt doesn't exists.
    logs_collection = implementation.GRRHunt.LogCollectionForHID(
        args.hunt_id.ToURN(), token=token)

    result = api_call_handler_utils.FilterCollection(
        logs_collection, args.offset, args.count, args.filter)

    return ApiListHuntLogsResult(items=result, total_count=len(logs_collection))


class ApiListHuntErrorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntErrorsArgs
  rdf_deps = [
      ApiHuntId,
  ]


class ApiListHuntErrorsResult(rdf_structs.RDFProtoStruct):
  protobuf = hunt_pb2.ApiListHuntErrorsResult
  rdf_deps = [
      rdf_hunts.HuntError,
  ]


class ApiListHuntErrorsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of errors for the given hunt."""

  args_type = ApiListHuntErrorsArgs
  result_type = ApiListHuntErrorsResult

  def Handle(self, args, token=None):
    # TODO(user): handle cases when hunt doesn't exists.
    errors_collection = implementation.GRRHunt.ErrorCollectionForHID(
        args.hunt_id.ToURN(), token=token)

    result = api_call_handler_utils.FilterCollection(
        errors_collection, args.offset, args.count, args.filter)

    return ApiListHuntErrorsResult(
        items=result, total_count=len(errors_collection))


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
      start_stats: A list of lists, each containing two values (a timestamp
        and the number of clients started at this time).
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

    cl_age = [int(min(x) / 1e6) for x in cdict.values()]
    fi_age = [int(min(x) / 1e6) for x in fdict.values()]

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
    return (zip(times, cl), zip(times, fi))

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
    user = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("users").Add(token.username),
        aff4_type=aff4_users.GRRUser,
        mode="rw",
        token=token)
    try:
      for item in generator.Generate(collection, token=token):
        yield item

      user.Notify("ArchiveGenerationFinished", None,
                  "Downloaded archive of hunt %s results (archived %d "
                  "out of %d items, archive size is %d)" %
                  (args.hunt_id, generator.archived_files,
                   generator.total_files,
                   generator.output_size), self.__class__.__name__)
    except Exception as e:
      user.Notify("Error", None, "Archive generation failed for hunt %s: %s" %
                  (args.hunt_id, utils.SmartStr(e)), self.__class__.__name__)
      raise
    finally:
      user.Close()

  def Handle(self, args, token=None):
    hunt_urn = args.hunt_id.ToURN()
    hunt = aff4.FACTORY.Open(
        hunt_urn, aff4_type=implementation.GRRHunt, token=token)

    hunt_api_object = ApiHunt().InitFromAff4Object(hunt)
    description = ("Files downloaded by hunt %s (%s, '%s') created by user %s "
                   "on %s" %
                   (hunt_api_object.name, hunt_api_object.urn.Basename(),
                    hunt_api_object.description, hunt_api_object.creator,
                    hunt_api_object.created))

    collection = implementation.GRRHunt.ResultCollectionForHID(
        hunt_urn, token=token)

    target_file_prefix = "hunt_" + hunt.urn.Basename().replace(":", "_")

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
        args.hunt_id.ToURN(), token=token)

    expected_aff4_path = args.client_id.ToClientURN().Add(args.vfs_path)
    # TODO(user): should after_timestamp be strictly less than the desired
    # timestamp.
    timestamp = rdfvalue.RDFDatetime(int(args.timestamp) - 1)

    # If the entry corresponding to a given path is not found within
    # MAX_RECORDS_TO_CHECK from a given timestamp, we report a 404.
    for _, item in results.Scan(
        after_timestamp=timestamp.AsMicroSecondsFromEpoch(),
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

  def IncludeRequestInformationInResults(self, hunt_urn, results, token=None):
    all_clients_urns = [i.client_id.ToClientURN() for i in results]
    clients_to_results_map = {i.client_id: i for i in results}

    all_flow_urns = implementation.GRRHunt.GetAllSubflowUrns(
        hunt_urn, all_clients_urns, token=token)
    flow_requests = flow.GRRFlow.GetFlowRequests(all_flow_urns, token)
    client_requests = aff4_grr.VFSGRRClient.GetClientRequests(
        all_clients_urns, token)

    waitingfor = {}
    status_by_request = {}

    for flow_urn in flow_requests:
      for obj in flow_requests[flow_urn]:
        if isinstance(obj, rdf_flows.RequestState):
          waitingfor.setdefault(flow_urn, obj)
          if waitingfor[flow_urn].id > obj.id:
            waitingfor[flow_urn] = obj
        elif isinstance(obj, rdf_flows.GrrMessage):
          status_by_request.setdefault(flow_urn, {})[obj.request_id] = obj

    response_urns = []

    for request_base_urn, request in waitingfor.iteritems():
      response_urns.append(
          rdfvalue.RDFURN(request_base_urn).Add("request:%08X" % request.id))

    response_dict = dict(
        data_store.DB.MultiResolvePrefix(response_urns, "flow:", token=token))

    for flow_urn in sorted(all_flow_urns):
      request_urn = flow_urn.Add("state")
      client_id = flow_urn.Split()[2]

      try:
        request_obj = waitingfor[request_urn]
      except KeyError:
        request_obj = None

      if request_obj:
        response_urn = rdfvalue.RDFURN(request_urn).Add(
            "request:%08X" % request_obj.id)
        responses_available = len(response_dict.setdefault(response_urn, []))
        status_available = False
        responses_expected = "Unknown"
        if request_obj.id in status_by_request.setdefault(request_urn, {}):
          status_available = True
          status = status_by_request[request_urn][request_obj.id]
          responses_expected = status.response_id

        client_requests_available = 0
        for client_req in client_requests.setdefault(client_id, []):
          if request_obj.request.session_id == client_req.session_id:
            client_requests_available += 1

        pending_request = ApiHuntClientPendingRequest(
            flow_urn=flow_urn,
            incomplete_request_id=str(request_obj.id),
            next_state=request_obj.next_state,
            expected_args=request_obj.request.args_rdf_name,
            available_responses_count=responses_available,
            expected_responses=responses_expected,
            is_status_available=status_available,
            available_client_requests_count=client_requests_available)
        clients_to_results_map[client_id].pending_requests.append(
            pending_request)

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

    top_level_flow_urns = implementation.GRRHunt.GetAllSubflowUrns(
        hunt_urn, hunt_clients, top_level_only=True, token=token)
    top_level_flows = list(
        aff4.FACTORY.MultiOpen(
            top_level_flow_urns, aff4_type=flow.GRRFlow, token=token))

    results = []
    for flow_fd in sorted(top_level_flows, key=lambda f: f.urn):
      runner = flow_fd.GetRunner()
      item = ApiHuntClient(
          client_id=flow_fd.client_id,
          flow_urn=flow_fd.urn,
          cpu_usage=runner.context.client_resources.cpu_usage,
          network_bytes_sent=runner.context.network_bytes_sent)
      results.append(item)

    self.IncludeRequestInformationInResults(hunt_urn, results, token=token)

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
        raise ValueError(
            "Hunt %s not known by this implementation." % hunt_name)

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
      # TODO(user): Hunt state will go away soon, we don't render it anymore.
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
  protobuf = hunt_pb2.ApiCreateHuntArgs
  rdf_deps = [
      rdf_hunts.HuntRunnerArgs,
  ]

  def GetFlowArgsClass(self):
    if self.flow_name:
      flow_cls = flow.GRRFlow.classes.get(self.flow_name)
      if flow_cls is None:
        raise ValueError(
            "Flow %s not known by this implementation." % self.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class ApiCreateHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt creation request."""

  args_type = ApiCreateHuntArgs
  result_type = ApiHunt

  def Handle(self, args, token=None):
    """Creates a new hunt."""

    # We only create generic hunts with /hunts/create requests.
    generic_hunt_args = standard.GenericHuntArgs()
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

    # Anyone can create the hunt but it will be created in the paused
    # state. Permissions are required to actually start it.
    with implementation.GRRHunt.StartHunt(
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
      hunt_changes.append("Expires: Old=%s, New=%s" % (runner.context.expires,
                                                       args.expires))
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
    event = events.AuditEvent(
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
        hunt_urn, token=token)

    plugin = plugin_cls(source_urn=hunt_urn, token=token)
    return api_call_handler_base.ApiBinaryStream(
        plugin.output_file_name,
        content_generator=instant_output_plugin.
        ApplyPluginToMultiTypeCollection(plugin, output_collection))
