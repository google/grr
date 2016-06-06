#!/usr/bin/env python
"""API handlers for accessing hunts."""

import functools
import itertools
import operator

import logging

from grr.gui import api_call_handler_base
from grr.gui import api_call_handler_utils
from grr.gui.api_plugins import output_plugin as api_output_plugin

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import users as aff4_users

from grr.lib.flows.general import export

from grr.lib.hunts import implementation
from grr.lib.hunts import results as hunts_results
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import stats as stats_rdf
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2

CATEGORY = "Hunts"

HUNTS_ROOT_PATH = rdfvalue.RDFURN("aff4:/hunts")


class HuntNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a hunt could not be found."""


class HuntFileNotFoundError(api_call_handler_base.ResourceNotFoundError):
  """Raised when a hunt file could not be found."""


class ApiHunt(rdf_structs.RDFProtoStruct):
  """ApiHunt is used when rendering responses.

  ApiHunt is meant to be more lightweight than automatically generated AFF4
  representation. It's also meant to contain only the information needed by
  the UI and and to not expose implementation defails.
  """
  protobuf = api_pb2.ApiHunt

  def GetArgsClass(self):
    hunt_name = self.name
    if not hunt_name:
      hunt_name = self.hunt_runner_args.hunt_name

    if hunt_name:
      hunt_cls = hunts.GRRHunt.classes.get(hunt_name)
      if hunt_cls is None:
        raise ValueError("Hunt %s not known by this implementation." %
                         hunt_name)

      # The required protobuf for this class is in args_type.
      return hunt_cls.args_type

  def InitFromAff4Object(self, hunt, with_full_summary=False):
    runner = hunt.GetRunner()
    context = runner.context

    self.urn = hunt.urn
    self.name = context.args.hunt_name
    self.state = str(hunt.Get(hunt.Schema.STATE))
    self.client_limit = context.args.client_limit
    self.client_rate = context.args.client_rate
    self.created = context.create_time
    self.expires = context.expires
    self.creator = context.creator
    self.description = context.args.description
    self.is_robot = context.creator == "GRRWorker"

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

      self.hunt_args = hunt.state.args
      self.hunt_runner_args = context.args
      self.client_rule_set = runner.args.client_rule_set

    return self


class ApiHuntResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiHuntResult

  def GetPayloadClass(self):
    return rdfvalue.RDFValue.classes[self.payload_type]

  def InitFromGrrMessage(self, message):
    self.client_id = message.source
    self.payload_type = message.payload.__class__.__name__
    self.payload = message.payload
    self.timestamp = message.age

    return self


class ApiListHuntsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntsArgs


class ApiListHuntsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntsResult


class ApiListHuntsHandler(api_call_handler_base.ApiCallHandler):
  """Renders list of available hunts."""

  category = CATEGORY
  args_type = ApiListHuntsArgs
  result_type = ApiListHuntsResult

  def _BuildHuntList(self, hunt_list):
    hunt_list = sorted(hunt_list,
                       reverse=True,
                       key=lambda hunt: hunt.GetRunner().context.create_time)

    return [ApiHunt().InitFromAff4Object(hunt_obj) for hunt_obj in hunt_list]

  def _CreatedByFilter(self, username, hunt_obj):
    return hunt_obj.creator == username

  def _DescriptionContainsFilter(self, substring, hunt_obj):
    return substring in hunt_obj.state.context.args.description

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
      filters.append(functools.partial(self._CreatedByFilter, self._Username(
          args.created_by, token)))

    if args.description_contains:
      filters.append(functools.partial(self._DescriptionContainsFilter,
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
      if not isinstance(hunt, hunts.GRRHunt) or not hunt.state:
        continue

      hunt_list.append(hunt)

    return ApiListHuntsResult(total_count=total_count,
                              items=self._BuildHuntList(hunt_list))

  def HandleFiltered(self, filter_func, args, token):
    fd = aff4.FACTORY.Open("aff4:/hunts", mode="r", token=token)
    children = list(fd.ListChildren())
    children.sort(key=operator.attrgetter("age"), reverse=True)

    if not args.active_within:
      raise ValueError("active_within filter has to be used when "
                       "any kind of filtering is done (to prevent "
                       "queries of death)")

    min_age = rdfvalue.RDFDatetime().Now() - args.active_within
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
      if (not isinstance(hunt, hunts.GRRHunt) or not hunt.state or
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
  protobuf = api_pb2.ApiGetHuntArgs


class ApiGetHuntHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's summary."""

  category = CATEGORY
  args_type = ApiGetHuntArgs
  result_type = ApiHunt

  def Handle(self, args, token=None):
    try:
      hunt = aff4.FACTORY.Open(
          HUNTS_ROOT_PATH.Add(args.hunt_id),
          aff4_type=hunts.GRRHunt,
          token=token)

      return ApiHunt().InitFromAff4Object(hunt, with_full_summary=True)
    except aff4.InstantiationError:
      raise HuntNotFoundError("Hunt with id %s could not be found" %
                              args.hunt_id)


class ApiListHuntResultsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntResultsArgs


class ApiListHuntResultsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntResultsResult


class ApiListHuntResultsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt results."""

  category = CATEGORY
  args_type = ApiListHuntResultsArgs
  result_type = ApiListHuntResultsResult

  def Handle(self, args, token=None):
    results_collection = aff4.FACTORY.Open(
        HUNTS_ROOT_PATH.Add(args.hunt_id).Add("Results"),
        mode="r",
        token=token)
    items = api_call_handler_utils.FilterAff4Collection(results_collection,
                                                        args.offset, args.count,
                                                        args.filter)
    wrapped_items = [ApiHuntResult().InitFromGrrMessage(item) for item in items]

    return ApiListHuntResultsResult(items=wrapped_items,
                                    total_count=len(results_collection))


class ApiListHuntCrashesArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntCrashesArgs


class ApiListHuntCrashesResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntCrashesResult


class ApiListHuntCrashesHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of client crashes for the given hunt."""

  category = CATEGORY
  args_type = ApiListHuntCrashesArgs
  result_type = ApiListHuntCrashesResult

  def Handle(self, args, token=None):
    try:
      aff4_crashes = aff4.FACTORY.Open(
          HUNTS_ROOT_PATH.Add(args.hunt_id).Add("crashes"),
          mode="r",
          aff4_type=collects.PackedVersionedCollection,
          token=token)

      total_count = len(aff4_crashes)
      result = api_call_handler_utils.FilterAff4Collection(aff4_crashes,
                                                           args.offset,
                                                           args.count,
                                                           args.filter)
    except aff4.InstantiationError:
      total_count = 0
      result = []

    return ApiListHuntCrashesResult(items=result, total_count=total_count)


class ApiGetHuntResultsExportCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetHuntResultsExportCommandArgs


class ApiGetHuntResultsExportCommandResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetHuntResultsExportCommandResult


class ApiGetHuntResultsExportCommandHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders GRR export tool command line that exports hunt results."""

  category = CATEGORY
  args_type = ApiGetHuntResultsExportCommandArgs
  result_type = ApiGetHuntResultsExportCommandResult

  def Handle(self, args, token=None):
    results_path = HUNTS_ROOT_PATH.Add(args.hunt_id).Add("Results")

    export_command_str = " ".join([
        config_lib.CONFIG["AdminUI.export_command"],
        "--username",
        utils.ShellQuote(token.username),
        # NOTE: passing reason is no longer necessary, as necessary
        # approval will be found and cached automatically.
        "collection_files",
        "--path",
        utils.ShellQuote(results_path),
        "--output",
        "."
    ])

    return ApiGetHuntResultsExportCommandResult(command=export_command_str)


class ApiListHuntOutputPluginsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntOutputPluginsArgs


class ApiListHuntOutputPluginsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntOutputPluginsResult


class ApiListHuntOutputPluginsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's output plugins states."""

  category = CATEGORY
  args_type = ApiListHuntOutputPluginsArgs
  result_type = ApiListHuntOutputPluginsResult

  def Handle(self, args, token=None):
    metadata = aff4.FACTORY.Create(
        HUNTS_ROOT_PATH.Add(args.hunt_id).Add("ResultsMetadata"),
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

  collection_name = None
  category = CATEGORY

  def Handle(self, args, token=None):
    if not self.collection_name:
      raise ValueError("collection_name can't be None")

    metadata = aff4.FACTORY.Create(
        HUNTS_ROOT_PATH.Add(args.hunt_id).Add("ResultsMetadata"),
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

    logs_collection = aff4.FACTORY.Open(
        HUNTS_ROOT_PATH.Add(args.hunt_id).Add(self.collection_name),
        mode="r",
        token=token)

    if len(plugins) == 1:
      total_count = len(logs_collection)
      logs = list(itertools.islice(
          logs_collection.GenerateItems(offset=args.offset),
          args.count or None))
    else:
      all_logs_for_plugin = [x for x in logs_collection
                             if x.plugin_descriptor == plugin_descriptor]
      total_count = len(all_logs_for_plugin)
      logs = all_logs_for_plugin[args.offset:]
      if args.count:
        logs = logs[:args.count]

    return self.result_type(total_count=total_count, items=logs)


class ApiListHuntOutputPluginLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntOutputPluginLogsArgs


class ApiListHuntOutputPluginLogsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntOutputPluginLogsResult


class ApiListHuntOutputPluginLogsHandler(
    ApiListHuntOutputPluginLogsHandlerBase):
  """Renders hunt's output plugin's log."""

  collection_name = "OutputPluginsStatus"
  args_type = ApiListHuntOutputPluginLogsArgs
  result_type = ApiListHuntOutputPluginLogsResult


class ApiListHuntOutputPluginErrorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntOutputPluginErrorsArgs


class ApiListHuntOutputPluginErrorsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntOutputPluginErrorsResult


class ApiListHuntOutputPluginErrorsHandler(
    ApiListHuntOutputPluginLogsHandlerBase):
  """Renders hunt's output plugin's errors."""

  collection_name = "OutputPluginsErrors"
  args_type = ApiListHuntOutputPluginErrorsArgs
  result_type = ApiListHuntOutputPluginErrorsResult


class ApiListHuntLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntLogsArgs


class ApiListHuntLogsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntLogsResult


class ApiListHuntLogsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of log elements for the given hunt."""

  category = CATEGORY
  args_type = ApiListHuntLogsArgs
  result_type = ApiListHuntLogsResult

  def Handle(self, args, token=None):
    # TODO(user): handle cases when hunt doesn't exists.
    # TODO(user): Use hunt's logs_collection_urn to open logs collection.
    try:
      logs_collection = aff4.FACTORY.Open(
          HUNTS_ROOT_PATH.Add(args.hunt_id).Add("Logs"),
          aff4_type=flow_runner.FlowLogCollection,
          mode="r",
          token=token)
    except IOError:
      logs_collection = aff4.FACTORY.Create(
          HUNTS_ROOT_PATH.Add(args.hunt_id).Add("Logs"),
          aff4_type=collects.RDFValueCollection,
          mode="r",
          token=token)

    result = api_call_handler_utils.FilterAff4Collection(logs_collection,
                                                         args.offset,
                                                         args.count,
                                                         args.filter)

    return ApiListHuntLogsResult(items=result, total_count=len(logs_collection))


class ApiListHuntErrorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntErrorsArgs


class ApiListHuntErrorsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntErrorsResult


class ApiListHuntErrorsHandler(api_call_handler_base.ApiCallHandler):
  """Returns a list of errors for the given hunt."""

  category = CATEGORY
  args_type = ApiListHuntErrorsArgs
  result_type = ApiListHuntErrorsResult

  def Handle(self, args, token=None):
    # TODO(user): handle cases when hunt doesn't exists.
    # TODO(user): Use hunt's logs_collection_urn to open errors collection.

    errors_collection = aff4.FACTORY.Open(
        HUNTS_ROOT_PATH.Add(args.hunt_id).Add("ErrorClients"),
        mode="r",
        token=token)

    result = api_call_handler_utils.FilterAff4Collection(errors_collection,
                                                         args.offset,
                                                         args.count,
                                                         args.filter)

    return ApiListHuntErrorsResult(items=result,
                                   total_count=len(errors_collection))


class ApiGetHuntClientCompletionStatsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetHuntClientCompletionStatsArgs


class ApiGetHuntClientCompletionStatsResult(rdf_structs.RDFProtoStruct):
  """Result for getting the client completions of a hunt."""
  protobuf = api_pb2.ApiGetHuntClientCompletionStatsResult

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
      data_point = stats_rdf.SampleFloat()
      data_point.x_value = stat[0]
      data_point.y_value = stat[1]
      result.append(data_point)
    return result


class ApiGetHuntClientCompletionStatsHandler(
    api_call_handler_base.ApiCallHandler):
  """Calculates hunt's client completion stats."""

  category = CATEGORY
  args_type = ApiGetHuntClientCompletionStatsArgs
  result_type = ApiGetHuntClientCompletionStatsResult

  def Handle(self, args, token=None):
    target_size = args.size
    if target_size <= 0:
      target_size = 1000

    hunt = aff4.FACTORY.Open(
        HUNTS_ROOT_PATH.Add(args.hunt_id),
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
  protobuf = api_pb2.ApiGetHuntFilesArchiveArgs


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
                  (args.hunt_id.Basename(), generator.archived_files,
                   generator.total_files, generator.output_size),
                  self.__class__.__name__)
    except Exception as e:
      user.Notify("Error", None, "Archive generation failed for hunt %s: %s" %
                  (args.hunt_id.Basename(), utils.SmartStr(e)),
                  self.__class__.__name__)
      raise
    finally:
      user.Close()

  def Handle(self, args, token=None):
    hunt_urn = rdfvalue.RDFURN("aff4:/hunts").Add(args.hunt_id.Basename())
    hunt = aff4.FACTORY.Open(hunt_urn, aff4_type=hunts.GRRHunt, token=token)

    hunt_api_object = ApiHunt().InitFromAff4Object(hunt)
    description = ("Files downloaded by hunt %s (%s, '%s') created by user %s "
                   "on %s" % (hunt_api_object.name,
                              hunt_api_object.urn.Basename(),
                              hunt_api_object.description,
                              hunt_api_object.creator, hunt_api_object.created))

    collection_urn = hunt.state.context.results_collection_urn
    collection = aff4.FACTORY.Open(collection_urn, token=token)

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
    content_generator = self._WrapContentGenerator(generator,
                                                   collection,
                                                   args,
                                                   token=token)
    return api_call_handler_base.ApiBinaryStream(
        target_file_prefix + file_extension,
        content_generator=content_generator)


class ApiGetHuntFileArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetHuntFileArgs


class ApiGetHuntFileHandler(api_call_handler_base.ApiCallHandler):
  """Downloads a file referenced in the hunt results."""

  category = CATEGORY
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

    hunt_results_urn = rdfvalue.RDFURN("aff4:/hunts").Add(args.hunt_id.Basename(
    )).Add("Results")
    results = aff4.FACTORY.Open(hunt_results_urn,
                                aff4_type=hunts_results.HuntResultCollection,
                                token=token)

    expected_aff4_path = args.client_id.Add("fs").Add(args.vfs_path.Path())
    # TODO(user): should after_tiestamp be strictly less than the desired
    # timestamp.
    timestamp = rdfvalue.RDFDatetime(int(args.timestamp) - 1)

    # If the entry corresponding to a given path is not found within
    # MAX_RECORDS_TO_CHECK from a given timestamp, we report a 404.
    for _, item in results.Scan(
        after_timestamp=timestamp.AsMicroSecondsFromEpoch(),
        max_records=self.MAX_RECORDS_TO_CHECK):
      try:
        aff4_path = export.CollectionItemToAff4Path(item)
      except export.ItemNotExportableError:
        continue

      if aff4_path != expected_aff4_path:
        continue

      try:
        aff4_stream = aff4.FACTORY.Open(aff4_path,
                                        aff4_type=aff4.AFF4Stream,
                                        token=token)
        if not aff4_stream.GetContentAge():
          break

        return api_call_handler_base.ApiBinaryStream(
            "%s_%s" % (args.client_id.Basename(),
                       utils.SmartStr(aff4_path.Basename())),
            content_generator=self._GenerateFile(aff4_stream),
            content_length=len(aff4_stream))
      except aff4.InstantiationError:
        break

    raise HuntFileNotFoundError("File %s with timestamp %s and client %s "
                                "wasn't found among the results of hunt %s" %
                                (utils.SmartStr(args.vfs_path),
                                 utils.SmartStr(args.timestamp),
                                 utils.SmartStr(args.client_id),
                                 utils.SmartStr(args.hunt_id)))


class ApiGetHuntStatsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetHuntStatsArgs


class ApiGetHuntStatsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetHuntStatsResult


class ApiGetHuntStatsHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt stats request."""

  category = CATEGORY
  args_type = ApiGetHuntStatsArgs
  result_type = ApiGetHuntStatsResult

  def Handle(self, args, token=None):
    """Retrieves the stats for a hunt."""
    hunt = aff4.FACTORY.Open(
        HUNTS_ROOT_PATH.Add(args.hunt_id),
        aff4_type=hunts.GRRHunt,
        token=token)

    stats = hunt.GetRunner().context.usage_stats

    return ApiGetHuntStatsResult(stats=stats)


class ApiListHuntClientsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntClientsArgs


class ApiListHuntClientsResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntClientsResult


class ApiHuntClient(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiHuntClient


class ApiListHuntClientsHandler(api_call_handler_base.ApiCallHandler):
  """Handles requests for hunt clients."""

  category = CATEGORY
  args_type = ApiListHuntClientsArgs
  result_type = ApiListHuntClientsResult

  def Handle(self, args, token=None):
    """Retrieves the clients for a hunt."""
    hunt_urn = HUNTS_ROOT_PATH.Add(args.hunt_id)
    hunt = aff4.FACTORY.Open(hunt_urn, aff4_type=hunts.GRRHunt, token=token)

    clients_by_status = hunt.GetClientsByStatus()
    hunt_clients = clients_by_status[args.client_status.name]
    total_count = len(hunt_clients)

    if args.count:
      hunt_clients = sorted(hunt_clients)[args.offset:args.offset + args.count]
    else:
      hunt_clients = sorted(hunt_clients)[args.offset:]

    all_flow_urns = hunts.GRRHunt.GetAllSubflowUrns(hunt_urn, hunt_clients,
                                                    token)
    flow_requests = flow.GRRFlow.GetFlowRequests(all_flow_urns, token)
    client_requests = aff4_grr.VFSGRRClient.GetClientRequests(hunt_clients,
                                                              token)

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
      response_urns.append(rdfvalue.RDFURN(request_base_urn).Add("request:%08X"
                                                                 % request.id))

    response_dict = dict(data_store.DB.MultiResolvePrefix(
        response_urns, "flow:", token=token))

    result_items = []
    for flow_urn in sorted(all_flow_urns):
      request_urn = flow_urn.Add("state")
      client_id = flow_urn.Split()[2]

      item = ApiHuntClient()
      item.client_id = client_id
      item.flow_urn = flow_urn
      try:
        request_obj = waitingfor[request_urn]
      except KeyError:
        request_obj = None

      if request_obj:
        response_urn = rdfvalue.RDFURN(request_urn).Add("request:%08X" %
                                                        request_obj.id)
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

        item.incomplete_request_id = str(request_obj.id)
        item.next_state = request_obj.next_state
        item.expected_args = request_obj.request.args_rdf_name
        item.available_responses_count = responses_available
        item.expected_responses = responses_expected
        item.is_status_available = status_available
        item.available_client_requests_count = client_requests_available

      result_items.append(item)

    return ApiListHuntClientsResult(items=result_items, total_count=total_count)


class ApiGetHuntContextArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetHuntContextArgs


class ApiGetHuntContextResult(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetHuntContextResult


class ApiGetHuntContextHandler(api_call_handler_base.ApiCallHandler):
  """Handles requests for hunt contexts."""

  category = CATEGORY
  args_type = ApiGetHuntContextArgs
  result_type = ApiGetHuntContextResult

  def Handle(self, args, token=None):
    """Retrieves the context for a hunt."""
    hunt = aff4.FACTORY.Open(
        HUNTS_ROOT_PATH.Add(args.hunt_id),
        aff4_type=hunts.GRRHunt,
        token=token)

    context = api_call_handler_utils.ApiDataObject().InitFromDataObject(
        hunt.state.context)

    return ApiGetHuntContextResult(context=context)


class ApiCreateHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiCreateHuntArgs


class ApiCreateHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt creation request."""

  category = CATEGORY
  args_type = ApiCreateHuntArgs
  result_type = ApiHunt
  strip_json_root_fields_types = False

  # Anyone should be able to create a hunt (permissions are required to
  # actually start it) so marking this handler as privileged to turn off
  # ACL checks.
  privileged = True

  def Handle(self, args, token=None):
    """Creates a new hunt."""

    # We only create generic hunts with /hunts/create requests.
    args.hunt_runner_args.hunt_name = "GenericHunt"

    # Anyone can create the hunt but it will be created in the paused
    # state. Permissions are required to actually start it.
    with implementation.GRRHunt.StartHunt(runner_args=args.hunt_runner_args,
                                          args=args.hunt_args,
                                          token=token) as hunt:

      # Nothing really to do here - hunts are always created in the paused
      # state.
      logging.info("User %s created a new %s hunt (%s)", token.username,
                   hunt.state.args.flow_runner_args.flow_name, hunt.urn)

      return ApiHunt().InitFromAff4Object(hunt, with_full_summary=True)
