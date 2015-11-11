#!/usr/bin/env python
"""API renderers for dealing with flows."""

import itertools
import urlparse

import logging

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_renderer_base
from grr.gui import api_value_renderers

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import client_index
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import throttle
from grr.lib import utils
from grr.lib.aff4_objects import security as aff4_security
from grr.lib.flows.general import file_finder
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


CATEGORY = "Flows"


class ApiFlow(rdf_structs.RDFProtoStruct):
  """ApiFlow is used when rendering responses.

  ApiFlow is meant to be more lightweight than automatically generated AFF4
  representation. It's also meant to contain only the information needed by
  the UI and and to not expose implementation defails.
  """
  protobuf = api_pb2.ApiFlow

  def GetArgsClass(self):
    if self.name:
      flow_cls = flow.GRRFlow.classes.get(self.name)
      if flow_cls is None:
        raise ValueError("Flow %s not known by this implementation." %
                         self.name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class ApiFlowStatusRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiFlowStatusRendererArgs


class ApiFlowStatusRenderer(api_call_renderer_base.ApiCallRenderer):
  """Renders summary of a given flow.

  Only top-level flows can be targeted. Times returned in the response are micro
  seconds since epoch.
  """

  category = CATEGORY
  args_type = ApiFlowStatusRendererArgs

  # Make this SetUID, see comment below. Authentication is still required.
  privileged = True

  # Require explicit ACL to use this API.
  enabled_by_default = False

  def Render(self, args, token=None):
    """Render flow status.

    This renderer needs to be setuid because it needs to access any top level
    flow on any client. The ACL model operates at the object level, and doesn't
    give us the ability to target specific attributes of the object. This
    renderer relies on ClientURN and SessionID type validation to check the
    input parameters to avoid allowing arbitrary reads into the client aff4
    space. This renderer filters out only the attributes that are appropriate to
    release without authorization (authentication is still required).

    Args:
      args: ApiFlowStatusRendererArgs object
      token: access token
    Returns:
      dict representing flow state
    Raises:
      ValueError: if there is no flow at the URN
    """
    # args.flow_id looks like aff4:/F:ABCDEF12, convert it into a flow urn for
    # the target client.
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    try:
      flow_obj = aff4.FACTORY.Open(flow_urn, aff4_type="GRRFlow",
                                   token=token)
    except aff4.InstantiationError:
      raise ValueError("No flow object at %s" % flow_urn)

    flow_state = flow_obj.Get(flow_obj.Schema.FLOW_STATE)

    # We expect there is a use case for exposing flow_state.args, but in the
    # interest of exposing the minimum information required, we'll leave it out
    # until there is demonstrated need.
    rdf_result_map = {
        # "args": flow_state.args,
        "backtrace": flow_state.context.backtrace,
        "client_resources": flow_state.context.client_resources,
        "create_time": flow_state.context.create_time,
        "creator": flow_state.context.creator,
        "flow_runner_args": flow_state.context.args,
        "last_update_time": flow_obj.Get(flow_obj.Schema.LAST),
        "network_bytes_sent": flow_state.context.network_bytes_sent,
        "output_urn": flow_state.context.output_urn,
        "session_id": flow_state.context.session_id,
        "state": flow_state.context.state,
        }

    result = {}
    for dest_key, src in rdf_result_map.iteritems():
      result[dest_key] = api_value_renderers.RenderValue(src)

    result["current_state"] = flow_state.context.current_state
    try:
      result_collection = aff4.FACTORY.Open(flow_state.context.output_urn,
                                            aff4_type="RDFValueCollection",
                                            token=token)
      result["result_count"] = len(result_collection)
    except aff4.InstantiationError:
      result["result_count"] = 0

    return result


class ApiFlowResultsRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiFlowResultsRendererArgs


class ApiFlowResultsRenderer(api_call_renderer_base.ApiCallRenderer):
  """Renders results of a given flow."""

  category = CATEGORY
  args_type = ApiFlowResultsRendererArgs

  def Render(self, args, token=None):
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    flow_obj = aff4.FACTORY.Open(flow_urn, aff4_type="GRRFlow", mode="r",
                                 token=token)

    output_urn = flow_obj.GetRunner().output_urn
    output_collection = aff4.FACTORY.Create(
        output_urn, aff4_type="RDFValueCollection", mode="r", token=token)
    return api_aff4_object_renderers.RenderAFF4Object(
        output_collection,
        [api_aff4_object_renderers.ApiRDFValueCollectionRendererArgs(
            offset=args.offset, count=args.count, filter=args.filter,
            with_total_count=True)])


class ApiFlowResultsExportCommandRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiFlowResultsExportCommandRendererArgs


class ApiFlowResultsExportCommandRenderer(
    api_call_renderer_base.ApiCallRenderer):
  """Renders GRR export tool command line that exports flow results."""

  category = CATEGORY
  args_type = ApiFlowResultsExportCommandRendererArgs

  def Render(self, args, token=None):
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    flow_obj = aff4.FACTORY.Open(flow_urn, aff4_type="GRRFlow", mode="r",
                                 token=token)
    output_urn = flow_obj.GetRunner().output_urn

    export_command_str = " ".join([
        config_lib.CONFIG["AdminUI.export_command"],
        "--username", utils.ShellQuote(token.username),
        "--reason", utils.ShellQuote(token.reason),
        "collection_files",
        "--path", utils.ShellQuote(output_urn),
        "--output", "."])

    return dict(command=export_command_str)


class ApiFlowArchiveFilesRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiFlowArchiveFilesRendererArgs


class ApiFlowArchiveFilesRenderer(api_call_renderer_base.ApiCallRenderer):
  """Generates archive with all files referenced in flow's results."""

  category = CATEGORY
  args_type = ApiFlowArchiveFilesRendererArgs

  def Render(self, args, token=None):
    """Starts archive generation flow."""

    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    try:
      token = aff4_security.Approval.GetApprovalForObject(
          args.client_id, token=token)
    except access_control.UnauthorizedAccess:
      pass

    flow_obj = aff4.FACTORY.Open(flow_urn, aff4_type="GRRFlow", mode="r",
                                 token=token)

    collection_urn = flow_obj.GetRunner().output_urn
    target_file_prefix = "flow_%s_%s" % (
        flow_obj.state.context.args.flow_name,
        flow_urn.Basename().replace(":", "_"))
    notification_message = "Flow results for %s (%s) ready for download" % (
        flow_obj.urn.Basename(), flow_obj.state.context.args.flow_name)

    urn = flow.GRRFlow.StartFlow(client_id=args.client_id,
                                 flow_name="ExportCollectionFilesAsArchive",
                                 collection_urn=collection_urn,
                                 target_file_prefix=target_file_prefix,
                                 notification_message=notification_message,
                                 format=args.archive_format,
                                 token=token)
    logging.info("Generating %s archive for %s with flow %s.", format,
                 flow_obj.urn, urn)

    return dict(status="OK", flow_urn=utils.SmartStr(urn))


class ApiFlowOutputPluginsRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiFlowOutputPluginsRendererArgs


class ApiFlowOutputPluginsRenderer(api_call_renderer_base.ApiCallRenderer):
  """Renders output plugins descriptors and states for a given flow."""

  category = CATEGORY
  args_type = ApiFlowOutputPluginsRendererArgs

  def Render(self, args, token=None):
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    flow_obj = aff4.FACTORY.Open(flow_urn, aff4_type="GRRFlow", mode="r",
                                 token=token)

    output_plugins_states = flow_obj.GetRunner().context.output_plugins_states

    result = {}
    for plugin_descriptor, plugin_state in output_plugins_states:
      result[plugin_descriptor.plugin_name] = (
          api_value_renderers.RenderValue(plugin_descriptor),
          api_value_renderers.RenderValue(plugin_state))

    return result


class ApiClientFlowsListRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiClientFlowsListRendererArgs


class ApiClientFlowsListRenderer(api_call_renderer_base.ApiCallRenderer):
  """Lists flows launched on a given client."""

  category = CATEGORY
  args_type = ApiClientFlowsListRendererArgs

  def _GetCreationTime(self, obj):
    try:
      return obj.state.context.get("create_time")
    except AttributeError:
      return obj.Get(obj.Schema.LAST, 0)

  def _BuildApiFlowRepresentation(self, flow_obj):
    result = ApiFlow(urn=flow_obj.urn,
                     name=flow_obj.state.context.args.flow_name,
                     started_at=flow_obj.state.context.create_time,
                     last_active_at=flow_obj.Get(flow_obj.Schema.LAST),
                     creator=flow_obj.state.context.creator)

    if flow_obj.Get(flow_obj.Schema.CLIENT_CRASH):
      result.state = "CLIENT_CRASHED"
    else:
      result.state = flow_obj.state.context.state

    try:
      result.args = flow_obj.args
    except ValueError:
      # If args class name has changed, ValueError will be raised. Handling
      # this gracefully - we should still try to display some useful info
      # about the flow.
      pass

    return result

  def Render(self, args, token=None):
    client_root_urn = args.client_id.Add("flows")

    if not args.count:
      stop = None
    else:
      stop = args.offset + args.count

    root_children_urns = aff4.FACTORY.Open(
        client_root_urn, token=token).ListChildren()
    root_children_urns = sorted(root_children_urns,
                                key=lambda x: x.age, reverse=True)
    root_children_urns = root_children_urns[args.offset:stop]

    root_children = aff4.FACTORY.MultiOpen(
        root_children_urns, aff4_type=flow.GRRFlow.__name__,
        token=token)
    root_children = sorted(root_children, key=self._GetCreationTime,
                           reverse=True)

    nested_children_urns = dict(aff4.FACTORY.RecursiveMultiListChildren(
        [fd.urn for fd in root_children], token=token))
    nested_children = aff4.FACTORY.MultiOpen(
        set(itertools.chain(*nested_children_urns.values())),
        aff4_type=flow.GRRFlow.__name__, token=token)
    nested_children_map = dict((x.urn, x) for x in nested_children)

    def BuildList(fds):
      """Builds list of flows recursively."""
      result = []
      for fd in fds:
        api_flow = self._BuildApiFlowRepresentation(fd)

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

    items = BuildList(root_children)
    result = dict(offset=args.offset,
                  count=len(items),
                  items=api_value_renderers.RenderValue(items))
    return result


class ApiRemoteGetFileRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiRemoteGetFileRendererArgs


class ApiRemoteGetFileRenderer(api_call_renderer_base.ApiCallRenderer):
  """Downloads files from specified machine without requiring approval."""

  category = CATEGORY
  args_type = ApiRemoteGetFileRendererArgs

  # Make this SetUID to be able to start it on any client without approval.
  privileged = True

  # Require explicit ACL to use this API. Since no approvals are required to
  # initiate the download, we expect use to be tightly constrained using API
  # ACLs.
  enabled_by_default = False

  def GetClientTarget(self, args, token=None):
    # Find the right client to target using a hostname search.
    index = aff4.FACTORY.Create(
        client_index.MAIN_INDEX,
        aff4_type="ClientIndex", mode="rw", token=token)

    client_list = index.LookupClients([args.hostname])
    if not client_list:
      raise ValueError("No client found matching %s" % args.hostname)

    # If we get more than one, take the one with the most recent poll.
    if len(client_list) > 1:
      return client_index.GetMostRecentClient(client_list, token=token)
    else:
      return client_list[0]

  def Render(self, args, token=None):
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
    throttler.EnforceLimits(client_urn, token.username,
                            "FileFinder", file_finder_args,
                            token=token)

    # Limit the whole flow to 200MB so if a glob matches lots of small files we
    # still don't have too much impact.
    runner_args = flow_runner.FlowRunnerArgs(client_id=client_urn,
                                             flow_name="FileFinder",
                                             network_bytes_limit=200*1000*1000)

    flow_id = flow.GRRFlow.StartFlow(runner_args=runner_args,
                                     token=token,
                                     args=file_finder_args)

    # Provide a url where the caller can check on the flow status.
    status_url = urlparse.urljoin(
        config_lib.CONFIG["AdminUI.url"],
        "/api/flows/%s/%s/status" % (client_urn.Basename(), flow_id.Basename()))
    return dict(
        flow_id=api_value_renderers.RenderValue(flow_id),
        flow_args=api_value_renderers.RenderValue(file_finder_args),
        runner_args=api_value_renderers.RenderValue(runner_args),
        status_url=status_url)


class ApiStartFlowRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiStartFlowRendererArgs

  def GetFlowArgsClass(self):
    if self.runner_args.flow_name:
      flow_cls = flow.GRRFlow.classes.get(self.runner_args.flow_name)
      if flow_cls is None:
        raise ValueError("Flow %s not known by this implementation." %
                         self.runner_args.flow_name)

      # The required protobuf for this class is in args_type.
      return flow_cls.args_type


class ApiStartFlowRenderer(api_call_renderer_base.ApiCallRenderer):
  """Starts a flow on a given client with given parameters."""

  category = CATEGORY
  args_type = ApiStartFlowRendererArgs

  def Render(self, args, token=None):
    flow_id = flow.GRRFlow.StartFlow(client_id=args.client_id,
                                     flow_name=args.runner_args.flow_name,
                                     token=token,
                                     args=args.flow_args,
                                     runner_args=args.runner_args)

    return dict(
        flow_id=api_value_renderers.RenderValue(flow_id),
        flow_args=api_value_renderers.RenderValue(args.flow_args),
        runner_args=api_value_renderers.RenderValue(args.runner_args))


class ApiCancelFlowRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiCancelFlowRendererArgs


class ApiCancelFlowRenderer(api_call_renderer_base.ApiCallRenderer):
  """Cancels given flow on a given client."""

  category = CATEGORY
  args_type = ApiCancelFlowRendererArgs
  privileged = True

  def Render(self, args, token=None):
    flow_urn = args.client_id.Add("flows").Add(args.flow_id.Basename())
    # If we can read the flow, we're allowed to terminate it.
    data_store.DB.security_manager.CheckDataStoreAccess(
        token.RealUID(), [flow_urn], "r")

    flow.GRRFlow.TerminateFlow(flow_urn, reason="Cancelled in GUI",
                               token=token, force=True)

    return dict(status="OK")


class ApiFlowDescriptorsListRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiFlowDescriptorsListRendererArgs


class ApiFlowDescriptorsListRenderer(api_call_renderer_base.ApiCallRenderer):
  """Renders all available flows descriptors."""

  category = CATEGORY
  args_type = ApiFlowDescriptorsListRendererArgs

  client_flow_behavior = flow.FlowBehaviour("Client Flow")
  global_flow_behavior = flow.FlowBehaviour("Global Flow")

  def _FlowTypeToBehavior(self, flow_type):
    if flow_type == self.args_type.FlowType.CLIENT:
      return self.client_flow_behavior
    elif flow_type == self.args_type.FlowType.GLOBAL:
      return self.global_flow_behavior
    else:
      raise ValueError("Unexpected flow type: " + str(flow_type))

  def Render(self, args, token=None):
    """Renders list of descriptors for all the flows."""

    result = {}

    for name in sorted(flow.GRRFlow.classes.keys()):
      cls = flow.GRRFlow.classes[name]

      # Flows without a category do not show up in the GUI.
      if not getattr(cls, "category", None):
        continue

      # If a flow is tagged as AUTHORIZED_LABELS, the user must have the correct
      # label to see it.
      if cls.AUTHORIZED_LABELS:
        try:
          data_store.DB.security_manager.CheckUserLabels(
              token.username, cls.AUTHORIZED_LABELS,
              token=token)
        except access_control.UnauthorizedAccess:
          continue

      if args.HasField("flow_type"):
        # Skip if there are behaviours that are not supported by the class.
        behavior = self._FlowTypeToBehavior(args.flow_type)
        if not behavior.IsSupported(cls.behaviours):
          continue

      states = []

      # Fill in information about each state
      for state_method in cls.__dict__.values():
        try:
          next_states = state_method.next_states

          # Only show the first line of the doc string.
          try:
            func_doc = state_method.func_doc.split("\n")[0].strip()
          except AttributeError:
            func_doc = ""
          states.append((state_method.func_name,
                         func_doc, ", ".join(next_states)))
        except AttributeError:
          pass

      states = sorted(states, key=lambda x: x[0])

      # Now fill in information about each arg to this flow.
      prototypes = []
      for type_descriptor in cls.args_type.type_infos:
        if not type_descriptor.hidden:
          prototypes.append("%s" % (type_descriptor.name))
      prototype = "%s(%s)" % (cls.__name__, ", ".join(prototypes))

      flow_descriptor = dict(name=name,
                             friendly_name=cls.friendly_name,
                             doc=cls.__doc__,
                             prototype=prototype,
                             states=states,
                             behaviours=sorted(cls.behaviours),
                             args_type=cls.args_type.__name__,
                             default_args=api_value_renderers.RenderValue(
                                 cls.GetDefaultArgs(token=token)))
      result.setdefault(cls.category.strip("/"), []).append(flow_descriptor)

    return result
