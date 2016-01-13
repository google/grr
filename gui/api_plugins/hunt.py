#!/usr/bin/env python
"""API handlers for accessing hunts."""

import functools
import itertools
import operator

import logging

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_handler_base
from grr.gui import api_value_renderers
from grr.gui.api_plugins import output_plugin as api_output_plugin

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import security as aff4_security

from grr.lib.hunts import implementation

from grr.lib.rdfvalues import structs as rdf_structs


from grr.proto import api_pb2


CATEGORY = "Hunts"

HUNTS_ROOT_PATH = rdfvalue.RDFURN("aff4:/hunts")


class ApiGRRHuntRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGRRHuntRendererArgs


class ApiGRRHuntRenderer(
    api_aff4_object_renderers.ApiAFF4ObjectRendererBase):
  """Renderer for GRRHunt objects."""

  aff4_type = "GRRHunt"
  args_type = ApiGRRHuntRendererArgs

  def RenderObject(self, hunt, args):
    runner = hunt.GetRunner()
    context = runner.context

    untyped_summary_part = dict(
        state=hunt.Get(hunt.Schema.STATE),
        hunt_name=context.args.hunt_name,
        create_time=context.create_time,
        expires=context.expires,
        client_limit=context.args.client_limit,
        client_rate=context.args.client_rate,
        creator=context.creator,
        description=context.args.description)
    typed_summary_part = {}

    if args.with_full_summary:
      all_clients_count, completed_clients_count, _ = hunt.GetClientsCounts()

      untyped_summary_part.update(dict(
          stats=context.usage_stats,
          all_clients_count=all_clients_count,
          completed_clients_count=completed_clients_count,
          outstanding_clients_count=(
              all_clients_count - completed_clients_count)))

      typed_summary_part = dict(
          regex_rules=runner.args.regex_rules or [],
          integer_rules=runner.args.integer_rules or [],
          args=hunt.state.args)

      try:
        typed_summary_part["rules"] = runner.args.rules
      except AttributeError:
        typed_summary_part["rules"] = []

    for k, v in untyped_summary_part.items():
      untyped_summary_part[k] = api_value_renderers.RenderValue(v)

    for k, v in typed_summary_part.items():
      typed_summary_part[k] = api_value_renderers.RenderValue(v)

    rendered_object = {
        "summary": dict(untyped_summary_part.items() +
                        typed_summary_part.items())
    }
    return rendered_object


class ApiListHuntsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntsArgs


class ApiListHuntsHandler(api_call_handler_base.ApiCallHandler):
  """Renders list of available hunts."""

  category = CATEGORY
  args_type = ApiListHuntsArgs

  def _RenderHuntList(self, hunt_list):
    hunts_list = sorted(hunt_list, reverse=True,
                        key=lambda hunt: hunt.GetRunner().context.create_time)

    encoded_hunt_list = []
    for hunt in hunts_list:
      encoded_hunt = api_aff4_object_renderers.RenderAFF4Object(
          hunt,
          [api_aff4_object_renderers.ApiAFF4ObjectRendererArgs(limit_lists=0)])
      encoded_hunt_list.append(encoded_hunt)

    return encoded_hunt_list

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

    if ((args.created_by or args.description_contains)
        and not args.active_within):
      raise ValueError("created_by/description_contains filters have to be "
                       "used together with active_within filter (to prevent "
                       "queries of death)")

    if args.created_by:
      filters.append(functools.partial(self._CreatedByFilter,
                                       self._Username(args.created_by, token)))

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

  def RenderNonFiltered(self, args, token):
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

    return dict(total_count=total_count,
                offset=args.offset,
                count=len(hunt_list),
                items=self._RenderHuntList(hunt_list))

  def RenderFiltered(self, filter_func, args, token):
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
      if (not isinstance(hunt, hunts.GRRHunt) or not hunt.state
          or not filter_func(hunt)):
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

    return dict(offset=args.offset,
                count=len(hunt_list),
                items=self._RenderHuntList(hunt_list))

  def Render(self, args, token=None):
    filter_func = self._BuildFilter(args, token)
    if not filter_func and args.active_within:
      # If no filters except for "active_within" were specified, just use
      # a stub filter function that always returns True. Filtering by
      # active_within is done by RenderFiltered code before other filters
      # are applied.
      filter_func = lambda x: True

    if filter_func:
      return self.RenderFiltered(filter_func, args, token)
    else:
      return self.RenderNonFiltered(args, token)


class ApiGetHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetHuntArgs


class ApiGetHuntHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's summary."""

  category = CATEGORY
  args_type = ApiGetHuntArgs

  def Render(self, args, token=None):
    hunt = aff4.FACTORY.Open(HUNTS_ROOT_PATH.Add(args.hunt_id),
                             aff4_type="GRRHunt", token=token)

    return api_aff4_object_renderers.RenderAFF4Object(
        hunt,
        [ApiGRRHuntRendererArgs(with_full_summary=True)])


class ApiListHuntResultsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntResultsArgs


class ApiListHuntResultsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt results."""

  category = CATEGORY
  args_type = ApiListHuntResultsArgs

  def Render(self, args, token=None):
    results = aff4.FACTORY.Create(
        HUNTS_ROOT_PATH.Add(args.hunt_id).Add("Results"), mode="r",
        aff4_type="RDFValueCollection", token=token)

    return api_aff4_object_renderers.RenderAFF4Object(
        results,
        [api_aff4_object_renderers.ApiRDFValueCollectionRendererArgs(
            offset=args.offset, count=args.count, filter=args.filter,
            with_total_count=True)])


class ApiGetHuntResultsExportCommandArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiGetHuntResultsExportCommandArgs


class ApiGetHuntResultsExportCommandHandler(
    api_call_handler_base.ApiCallHandler):
  """Renders GRR export tool command line that exports hunt results."""

  category = CATEGORY
  args_type = ApiGetHuntResultsExportCommandArgs

  def Render(self, args, token=None):
    results_path = HUNTS_ROOT_PATH.Add(args.hunt_id).Add("Results")

    export_command_str = " ".join([
        config_lib.CONFIG["AdminUI.export_command"],
        "--username", utils.ShellQuote(token.username),
        # NOTE: passing reason is no longer necessary, as necessary
        # approval will be found and cached automatically.
        "collection_files",
        "--path", utils.ShellQuote(results_path),
        "--output", "."])

    return dict(command=export_command_str)


class ApiListHuntOutputPluginsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntOutputPluginsArgs


class ApiListHuntOutputPluginsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's output plugins states."""

  category = CATEGORY
  args_type = ApiListHuntOutputPluginsArgs

  def Render(self, args, token=None):
    metadata = aff4.FACTORY.Create(
        HUNTS_ROOT_PATH.Add(args.hunt_id).Add("ResultsMetadata"), mode="r",
        aff4_type="HuntResultsMetadata", token=token)

    plugins = metadata.Get(metadata.Schema.OUTPUT_PLUGINS, {})

    result = []
    for plugin_name, (plugin_descriptor, plugin_state) in plugins.items():
      api_plugin = api_output_plugin.ApiOutputPlugin(
          id=plugin_name, plugin_descriptor=plugin_descriptor,
          state=plugin_state)
      result.append(api_plugin)

    return dict(offset=0, count=len(result), total_count=len(result),
                items=api_value_renderers.RenderValue(result))


class ApiListHuntOutputPluginLogsHandlerBase(
    api_call_handler_base.ApiCallHandler):
  """Base class used to define log and status messages handlerers."""

  __abstract = True  # pylint: disable=g-bad-name

  collection_name = None
  category = CATEGORY

  def Render(self, args, token=None):
    if not self.collection_name:
      raise ValueError("collection_name can't be None")

    metadata = aff4.FACTORY.Create(
        HUNTS_ROOT_PATH.Add(args.hunt_id).Add("ResultsMetadata"), mode="r",
        aff4_type="HuntResultsMetadata", token=token)
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
        mode="r", token=token)

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

    return dict(offset=args.offset,
                count=len(logs),
                total_count=total_count,
                items=api_value_renderers.RenderValue(logs))


class ApiListHuntOutputPluginLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntOutputPluginLogsArgs


class ApiListHuntOutputPluginLogsHandler(
    ApiListHuntOutputPluginLogsHandlerBase):
  """Renders hunt's output plugin's log."""

  collection_name = "OutputPluginsStatus"
  args_type = ApiListHuntOutputPluginLogsArgs


class ApiListHuntOutputPluginErrorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntOutputPluginErrorsArgs


class ApiListHuntOutputPluginErrorsHandler(
    ApiListHuntOutputPluginLogsHandlerBase):
  """Renders hunt's output plugin's errors."""

  collection_name = "OutputPluginsErrors"
  args_type = ApiListHuntOutputPluginErrorsArgs


class ApiListHuntLogsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntLogsArgs


class ApiListHuntLogsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's log."""

  category = CATEGORY
  args_type = ApiListHuntLogsArgs

  def Render(self, args, token=None):
    # TODO(user): handle cases when hunt doesn't exists.
    # TODO(user): Use hunt's logs_collection_urn to open logs collection.
    try:
      logs_collection = aff4.FACTORY.Open(
          HUNTS_ROOT_PATH.Add(args.hunt_id).Add("Logs"),
          aff4_type=flow_runner.FlowLogCollection.__name__, mode="r",
          token=token)
    except IOError:
      logs_collection = aff4.FACTORY.Create(
          HUNTS_ROOT_PATH.Add(args.hunt_id).Add("Logs"),
          aff4_type="RDFValueCollection", mode="r", token=token)

    return api_aff4_object_renderers.RenderAFF4Object(
        logs_collection,
        [api_aff4_object_renderers.ApiRDFValueCollectionRendererArgs(
            offset=args.offset, count=args.count, with_total_count=True)])


class ApiListHuntErrorsArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiListHuntErrorsArgs


class ApiListHuntErrorsHandler(api_call_handler_base.ApiCallHandler):
  """Renders hunt's errors."""

  category = CATEGORY
  args_type = ApiListHuntErrorsArgs

  def Render(self, args, token=None):
    # TODO(user): handle cases when hunt doesn't exists.
    # TODO(user): Use hunt's logs_collection_urn to open errors collection.

    errors_collection = aff4.FACTORY.Open(
        HUNTS_ROOT_PATH.Add(args.hunt_id).Add("ErrorClients"),
        mode="r",
        token=token)

    return api_aff4_object_renderers.RenderAFF4Object(
        errors_collection,
        [api_aff4_object_renderers.ApiRDFValueCollectionRendererArgs(
            offset=args.offset, count=args.count, with_total_count=True)])


class ApiArchiveHuntFilesArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiArchiveHuntFilesArgs


class ApiArchiveHuntFilesHandler(api_call_handler_base.ApiCallHandler):
  """Generates archive with all files referenced in hunt's results."""

  category = CATEGORY
  args_type = ApiArchiveHuntFilesArgs
  privileged = True

  def Render(self, args, token=None):
    """Check if the user has access to the hunt and start archiving."""
    hunt_urn = rdfvalue.RDFURN("aff4:/hunts").Add(args.hunt_id.Basename())

    # TODO(user): This should be abstracted away into AccessControlManager
    # API.
    try:
      token = aff4_security.Approval.GetApprovalForObject(
          hunt_urn, token=token.RealUID())
    except access_control.UnauthorizedAccess:
      token = token.RealUID()

    # This check is needed for cases when security manager has custom
    # non-approval-based ACL checking logic.
    data_store.DB.security_manager.CheckHuntAccess(token, hunt_urn)

    hunt = aff4.FACTORY.Open(aff4.ROOT_URN.Add("hunts").Add(
        args.hunt_id.Basename()), aff4_type="GRRHunt", token=token)

    collection_urn = hunt.state.context.results_collection_urn
    target_file_prefix = "hunt_" + hunt.urn.Basename().replace(":", "_")
    notification_message = ("Hunt results for %s ready for download" %
                            hunt.urn.Basename())

    urn = flow.GRRFlow.StartFlow(flow_name="ExportCollectionFilesAsArchive",
                                 collection_urn=collection_urn,
                                 target_file_prefix=target_file_prefix,
                                 notification_message=notification_message,
                                 format=args.archive_format,
                                 # We have to run the flow with SetUID token,
                                 # as it will have to read files from
                                 # multiple clients.
                                 token=token.SetUID())
    logging.info("Generating %s archive for %s with flow %s.", format,
                 hunt.urn, urn)

    return dict(status="OK", flow_urn=utils.SmartStr(urn))


class ApiCreateHuntArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiCreateHuntArgs


class ApiCreateHuntHandler(api_call_handler_base.ApiCallHandler):
  """Handles hunt creation request."""

  category = CATEGORY
  args_type = ApiCreateHuntArgs

  # Anyone should be able to create a hunt (permissions are required to
  # actually start it) so marking this handler as privileged to turn off
  # ACL checks.
  privileged = True

  def Render(self, args, token=None):
    """Creates a new hunt."""

    # We only create generic hunts with /hunts/create requests.
    args.hunt_runner_args.hunt_name = "GenericHunt"

    # Anyone can create the hunt but it will be created in the paused
    # state. Permissions are required to actually start it.
    with implementation.GRRHunt.StartHunt(
        runner_args=args.hunt_runner_args,
        args=args.hunt_args,
        token=token) as hunt:

      # Nothing really to do here - hunts are always created in the paused
      # state.
      logging.info("User %s created a new %s hunt (%s)",
                   token.username, hunt.state.args.flow_runner_args.flow_name,
                   hunt.urn)

      return dict(
          status="OK",
          hunt_id=api_value_renderers.RenderValue(hunt.urn),
          hunt_args=api_value_renderers.RenderValue(hunt.state.args),
          hunt_runner_args=api_value_renderers.RenderValue(hunt.runner.args))
