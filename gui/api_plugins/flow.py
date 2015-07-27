#!/usr/bin/env python
"""API renderers for dealing with flows."""

from grr.gui import api_aff4_object_renderers
from grr.gui import api_call_renderers
from grr.gui import api_value_renderers

from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib.rdfvalues import structs as rdf_structs

from grr.proto import api_pb2


class ApiFlowStatusRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiFlowStatusRendererArgs


class ApiFlowStatusRenderer(api_call_renderers.ApiCallRenderer):
  """Renders summary of a given flow.

  Only top-level flows can be targeted. Times returned in the response are micro
  seconds since epoch.
  """

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


class ApiFlowResultsRenderer(api_call_renderers.ApiCallRenderer):
  """Renders results of a given flow."""

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
            offset=args.offset, count=args.count, with_total_count=True)])


class ApiFlowOutputPluginsRendererArgs(rdf_structs.RDFProtoStruct):
  protobuf = api_pb2.ApiFlowOutputPluginsRendererArgs


class ApiFlowOutputPluginsRenderer(api_call_renderers.ApiCallRenderer):
  """Renders output plugins descriptors and states for a given flow."""

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


class ApiStartFlowRenderer(api_call_renderers.ApiCallRenderer):
  """Starts a flow on a given client with given parameters."""

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


class ApiFlowDescriptorsListRenderer(api_call_renderers.ApiCallRenderer):
  """Renders all available flows descriptors."""

  # Only show flows in the tree that specify all of these behaviours in their
  # behaviours attribute.
  flow_behaviors_to_render = flow.FlowBehaviour("Client Flow")

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

      # Skip if there are behaviours that are not supported by the class.
      if not self.flow_behaviors_to_render.IsSupported(cls.behaviours):
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
