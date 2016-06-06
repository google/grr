#!/usr/bin/env python
"""GUI elements allowing launching and management of flows."""

import os


from grr.gui import renderers
from grr.gui.plugins import crash_view
from grr.gui.plugins import fileview
from grr.gui.plugins import forms
from grr.gui.plugins import semantic
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.aff4_objects import users as aff4_users
from grr.lib.flows.general import file_finder as flows_file_finder
from grr.lib.flows.general import registry as flows_registry
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import standard as rdf_standard


class LaunchFlows(renderers.AngularDirectiveRenderer):
  """Launches a new flow."""

  description = "Start new flows"
  behaviours = frozenset(["Host"])
  order = 10

  directive = "grr-start-flow-view"

  def Layout(self, request, response):
    self.directive_args = {"flow-type": "CLIENT"}
    self.directive_args["client-id"] = request.REQ.get("client_id")
    return super(LaunchFlows, self).Layout(request, response)


class FlowTree(renderers.TreeRenderer):
  """Show all flows in a tree.

  Generated Javascript Events:
    - flow_select(flow_path) - The full path for the flow name (category +
      name).
  """

  publish_select_queue = "flow_select"

  # Only show flows in the tree that specify all of these behaviours in their
  # behaviours attribute.
  flow_behaviors_to_render = flow.FlowBehaviour("Client Flow")

  def EnumerateCategories(self, path, request, flow_behaviors_to_render):
    """Search through all flows for categories starting with path."""
    categories = set()
    flows = set()
    # Use an object for path manipulations.
    path = rdfvalue.RDFURN(path)

    for name, cls in flow.GRRFlow.classes.items():
      # Flows without a category do not show up in the GUI.
      if not getattr(cls, "category", None):
        continue

      # Skip the flow if the user is not allowed to start it.
      try:
        data_store.DB.security_manager.CheckIfCanStartFlow(request.token,
                                                           name,
                                                           with_client_id=True)
      except access_control.UnauthorizedAccess:
        continue

      # Skip if there are behaviours that are not supported by the class.
      if not flow_behaviors_to_render.IsSupported(cls.behaviours):
        continue

      category = rdfvalue.RDFURN(cls.category)
      if category == path:
        flows.add((name, cls.friendly_name))
      else:
        relative_path = category.RelativeName(path)
        # This category starts with this path
        if relative_path is not None:
          categories.add(relative_path.split("/")[0])

    return categories, flows

  def RenderBranch(self, path, request):
    """Renders tree leafs for flows."""
    # Retrieve the user's GUI mode preferences.
    self.user = request.user
    try:
      user_record = aff4.FACTORY.Open(
          aff4.ROOT_URN.Add("users").Add(self.user),
          aff4_users.GRRUser,
          token=request.token)

      user_preferences = user_record.Get(user_record.Schema.GUI_SETTINGS)
    except IOError:
      user_preferences = aff4_users.GRRUser.SchemaCls.GUI_SETTINGS()

    flow_behaviors_to_render = (
        self.flow_behaviors_to_render + user_preferences.mode)
    categories, flows = self.EnumerateCategories(path, request,
                                                 flow_behaviors_to_render)
    for category in sorted(categories):
      self.AddElement(category)

    for name, friendly_name in sorted(flows):
      self.AddElement(name, behaviour="leaf", friendly_name=friendly_name)


class FlowManagementTabs(renderers.TabLayout):
  """Show information about the flows.

  Listening Javascript Events:
    - flow_select(flow_path) - A selection event on the tree informing us of the
      flow path. The basename of flow_path is the name of the flow.

  Internal State:
    - flow_path - The category and name of the flow we display.
  """
  names = ["Flow Information", "Current Running Flows"]
  delegated_renderers = ["FlowInformation", "ListFlowsTable"]

  tab_hash = "ft"

  def Layout(self, request, response):
    self.state = dict(flow_path=request.REQ.get("flow_path"),
                      client_id=request.REQ.get("client_id"))

    response = super(FlowManagementTabs, self).Layout(request, response)
    return self.CallJavascript(response, "FlowManagementTabs.Layout")


class FlowInformation(renderers.TemplateRenderer):
  """Displays information about the flow.

  Post Parameters:
    - flow_path: The category + flow name for use to display.
  """

  layout_template = renderers.Template("""
<h3>{{ this.flow_name|escape }}</h3>
<p>{{ this.flow_doc|linebreaks }}</p>

<pre>
Prototype: {{ this.prototype|escape }}
{{ this.prototype_doc|escape }}
</pre>
<table class="table table-condensed table-bordered full-width fixed-columns">
<colgroup>
<col style="width: 20%" />
<col style="width: 60%" />
<col style="width: 20%" />
</colgroup>
<thead>
<tr>
<th class="ui-state-default">State</th>
<th class="ui-state-default">Description</th>
<th class="ui-state-default">Next States</th></tr>
</thead>
<tbody>
{% for state, doc, next in this.states %}
   <tr><td class='state'>{{ state|escape }}</td>
   <td class='description'>{{ doc|escape }}</td>
   <td class='text'>{{ next|escape }}</td></tr>
{% endfor %}
</tbody>
</table>
""")

  # This is prepended to flow args to eliminate clashes with other parameters.
  arg_prefix = "v_"

  def Layout(self, request, response):
    """Update the progress bar based on the progress reported."""
    self.flow_name = request.REQ.get("flow_path", "").split("/")[-1]

    try:
      flow_class = flow.GRRFlow.classes[self.flow_name]
      if not aff4.issubclass(flow_class, flow.GRRFlow):
        return response
    except KeyError:
      return response

    self.states = []

    # Fill in information about each state
    for state_method in flow_class.__dict__.values():
      try:
        next_states = state_method.next_states

        # Only show the first line of the doc string.
        try:
          func_doc = state_method.func_doc.split("\n")[0].strip()
        except AttributeError:
          func_doc = ""
        self.states.append((state_method.func_name, func_doc,
                            ", ".join(next_states)))
      except AttributeError:
        pass

    # Now fill in information about each arg to this flow.
    prototypes = []
    for type_descriptor in flow_class.args_type.type_infos:
      if not type_descriptor.hidden:
        prototypes.append("%s" % (type_descriptor.name))

    self.prototype = "%s(%s)" % (flow_class.__name__, ", ".join(prototypes))

    self.flow_doc = flow_class.__doc__

    return super(FlowInformation, self).Layout(request, response)


class SemanticProtoFlowForm(renderers.TemplateRenderer):
  """Render a flow based on its semantic information."""

  layout_template = renderers.Template("""
<div class="FormBody" id="{{unique|escape}}">
{% if this.flow_found %}
  <form id='form_{{unique|escape}}' class="form-horizontal FormData"
    data-flow_path='{{this.flow_name|escape}}'
    data-dom_node='{{id|escape}}'
    >

    {{this.form|safe}}
    <hr/>
    {{this.runner_form|safe}}

    <div class="form-group">
      <div class="col-sm-offset-2 col-sm-3" style="padding-top: 1em">
      <button id='submit_{{unique|escape}}' class="btn btn-success Launch" >
        Launch
      </button>
      </div>
    </div>
  </form>
{% else %}
Please Select a flow to launch from the tree on the left.
{% endif %}
</div>

<div id="contents_{{unique}}"></div>
""") + renderers.TemplateRenderer.help_template

  ajax_template = renderers.Template("""
Launched Flow {{this.flow_name}} with the following args:<br>
<div>
  {{this.args_html|safe}}
  {{this.runner_args_html|safe}}
</div>
""")

  context_help_url = "user_manual.html#_flows"

  def _GetFlowName(self, request):
    return os.path.basename(request.REQ.get("flow_path", ""))

  def Layout(self, request, response):
    """Render the form for creating the flow args."""
    self.flow_name = self._GetFlowName(request)
    self.flow_cls = flow.GRRFlow.classes.get(self.flow_name)

    if aff4.issubclass(self.flow_cls, flow.GRRFlow):
      self.flow_found = True

      self.form = forms.SemanticProtoFormRenderer(
          self.flow_cls.GetDefaultArgs(token=request.token),
          prefix="args").RawHTML(request)

      self.runner_form = forms.SemanticProtoFormRenderer(
          flow_runner.FlowRunnerArgs(flow_name=self.flow_name),
          prefix="runner").RawHTML(request)

    response = super(SemanticProtoFlowForm, self).Layout(request, response)
    return self.CallJavascript(response,
                               "SemanticProtoFlowForm.Layout",
                               renderer=self.__class__.__name__)

  def RenderAjax(self, request, response):
    """Parse the flow args from the form and launch the flow."""
    self.flow_name = self._GetFlowName(request)
    self.client_id = request.REQ.get("client_id", None)
    self.dom_node = request.REQ.get("dom_node")

    flow_cls = flow.GRRFlow.classes.get(self.flow_name)
    if flow_cls is not None:

      self.args = forms.SemanticProtoFormRenderer(
          flow_cls.args_type(), prefix="args").ParseArgs(request)

      try:
        self.args.Validate()
      except ValueError as e:
        return self.CallJavascript(response,
                                   "SemanticProtoFlowForm.RenderAjaxError",
                                   error=str(e))

      self.runner_args = forms.SemanticProtoFormRenderer(
          flow_runner.FlowRunnerArgs(),
          prefix="runner_").ParseArgs(request)

      self.runner_args.Validate()

      self.flow_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                            flow_name=self.flow_name,
                                            token=request.token,
                                            args=self.args,
                                            runner_args=self.runner_args)

    self.args_html = semantic.FindRendererForObject(self.args).RawHTML(request)
    self.runner_args_html = semantic.FindRendererForObject(
        self.runner_args).RawHTML(request)
    response = renderers.TemplateRenderer.Layout(
        self, request,
        response, apply_template=self.ajax_template)
    return self.CallJavascript(response,
                               "SemanticProtoFlowForm.RenderAjax",
                               renderer=self.__class__.__name__,
                               dom_node=self.dom_node)


class FlowFormCancelAction(renderers.TemplateRenderer):
  """Handle submission of a Cancel Flow button press.

  Post Parameters:
    - flow_id: The flow to cancel.
  """
  layout_template = renderers.Template("")

  def Layout(self, request, response):
    # We can't terminate flow directly through flow.GRRFlow.TerminateFlow as
    # it requires writing to the datastore. We're not allowed to do it from
    # the GUI. Therefore we use dedicated TerminateFlow flow.
    flow.GRRFlow.StartFlow(flow_name="TerminateFlow",
                           flow_urn=rdfvalue.RDFURN(request.REQ.get("flow_id")),
                           reason="Cancelled in GUI",
                           token=request.token)

    return super(FlowFormCancelAction, self).Layout(request, response)


class FlowStateIcon(semantic.RDFValueRenderer):
  """Render the flow state by using an icon."""

  layout_template = renderers.Template("""
<div class="centered">
  <img class='grr-icon grr-flow-icon'
    src='/static/images/{{this.icon|escape}}'
    title='{{this.title|escape}}'
/>
</div>""")

  # Maps the flow states to icons we can show
  state_map = {"TERMINATED": ("stock_yes.png", "Flow finished normally."),
               "RUNNING": ("clock.png", "Flow is still running."),
               "ERROR": ("nuke.png", "Flow terminated with an error."),
               "CLIENT_CRASHED": (
                   "skull-icon.png",
                   "The client crashed while executing this flow.")}

  icon = "question-red.png"

  def Layout(self, request, response):
    try:
      self.icon, self.title = self.state_map[str(self.proxy)]
    except (KeyError, ValueError):
      pass

    super(FlowStateIcon, self).Layout(request, response)


class ManageFlows(renderers.AngularDirectiveRenderer):
  """View client's launched flows."""

  post_parameters = ["client_id"]
  directive = "grr-client-flows-view"

  description = "Manage launched flows"
  behaviours = frozenset(["Host"])
  order = 20

  def Layout(self, request, response):
    self.directive_args = {}
    self.directive_args["client-id"] = request.REQ.get("client_id")
    return super(ManageFlows, self).Layout(request, response)


class FlowLogView(renderers.AngularDirectiveRenderer):
  post_parameters = ["flow"]

  directive = "grr-flow-log"

  def Layout(self, request, response):
    self.directive_args = {}
    self.directive_args["flow-urn"] = request.REQ.get("flow")
    return super(FlowLogView, self).Layout(request, response)


class FlowTabView(renderers.TabLayout):
  """Show various flow information in a Tab view.

  Listening Javascript Events:
    - flow_table_select(flow_aff4_path) - A selection event on the tree
      informing us of the flow aff4 path. The basename of flow_path is the name
      of the flow.

  Internal State:
    - flow_path - The category and name of the flow we display.
  """
  names = ["Flow Information", "Requests", "Results", "Log", "Export"]
  delegated_renderers = ["ShowFlowInformation", "FlowRequestView",
                         "FlowResultsView", "FlowLogView",
                         "FlowResultsExportView"]

  tab_hash = "ftv"

  def IsOutputExportable(self, flow_urn, token=None):
    flow_obj = aff4.FACTORY.Open(flow_urn, token=token)
    runner = flow_obj.GetRunner()
    if getattr(runner, "output_urn", None):
      return fileview.CollectionExportView.IsCollectionExportable(
          runner.output_urn, token=token)

    return False

  def Layout(self, request, response):
    req_flow = request.REQ.get("flow")
    if req_flow:
      self.state["flow"] = req_flow

    client_id = request.REQ.get("client_id")
    if client_id:
      self.state["client_id"] = client_id

    if req_flow and not self.IsOutputExportable(req_flow, token=request.token):
      self.disabled = ["FlowResultsExportView"]

    response = super(FlowTabView, self).Layout(request, response)
    return self.CallJavascript(response,
                               "FlowTabView.Layout",
                               renderer=self.__class__.__name__)


class FlowRequestView(renderers.TableRenderer):
  """View outstanding requests for a flow.

  Post Parameters:
    - client_id: The client to show the flows for.
    - flow: The flow to show.
  """

  post_parameters = ["flow", "client_id"]

  def __init__(self, **kwargs):
    super(FlowRequestView, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn("ID"))
    self.AddColumn(semantic.RDFValueColumn("Request", width="100%"))
    self.AddColumn(semantic.RDFValueColumn("Last Response", width="100%"))

  def BuildTable(self, start_row, end_row, request):
    session_id = request.REQ.get("flow", "")

    if not session_id:
      return

    manager = queue_manager.QueueManager(token=request.token)
    for i, (request, responses) in enumerate(manager.FetchRequestsAndResponses(
        rdfvalue.RDFURN(session_id))):
      if request.id == 0:
        continue

      if i < start_row:
        continue
      if i > end_row:
        break

      # Tie up the request to each response to make it easier to render.
      self.AddCell(i, "ID", manager.FLOW_REQUEST_TEMPLATE % request.id)
      self.AddCell(i, "Request", request)
      if responses:
        self.AddCell(i, "Last Response", responses[-1])


class FlowResultsView(renderers.AngularDirectiveRenderer):
  """Shows flow results."""

  directive = "grr-flow-results"

  def Layout(self, request, response):
    self.directive_args = {}
    self.directive_args["flow-urn"] = request.REQ.get("flow")
    return super(FlowResultsView, self).Layout(request, response)


class FlowResultsExportView(fileview.CollectionExportView):
  """Displays export command to export flow's results."""

  def Layout(self, request, response):
    session_id = request.REQ.get("flow", "")

    if not session_id:
      return

    flow_obj = aff4.FACTORY.Open(session_id, token=request.token)
    runner = flow_obj.GetRunner()
    if runner.output_urn is not None:
      return super(FlowResultsExportView, self).Layout(
          request, response, aff4_path=runner.output_urn)


class TreeColumn(semantic.RDFValueColumn, renderers.TemplateRenderer):
  """A specialized column which adds tree controls."""

  template = renderers.Template("""
{% if this.branch %}
<span depth='{{this.depth|escape}}'
  onclick='grr.table.toggleChildRows(this, "{{this.value|escapejs}}");'
  style='margin-left: {{this.depth|escape}}em;'
  class='tree_closed tree_branch'/>
{% else %}
<span depth='{{this.depth|escape}}' class='tree_leaf'
   style='margin-left: {{this.depth|escape}}em;' />
{% endif %}
""")

  def AddElement(self, index, element, depth, row_type):
    self.rows[index] = (element, depth, row_type == "branch")

  def RenderRow(self, index, request, row_options):
    """Renders the cell with additional tree controls."""
    self.value, self.depth, self.branch = self.rows.get(index, ("", 0, "leaf"))
    self.index = index

    row_options["row_id"] = index

    renderer = self.renderer
    if renderer is None:
      # What is the RDFValueRenderer for this attribute?
      renderer = semantic.RDFValueRenderer.RendererForRDFValue(
          self.value.__class__.__name__)

    # Intantiate the renderer and return the HTML
    if renderer:
      result = renderer(self.value).RawHTML(request)
    else:
      result = utils.SmartStr(self.value)

    return self.FormatFromTemplate(self.template,
                                   value=result,
                                   index=index,
                                   this=self)


class FlowColumn(TreeColumn):
  """A specialized tree/column for sessions."""

  template = """
<div id='cancel_{{this.index|escape}}' flow_id="{{this.value|escape}}"
  style='float: left'>
</div>""" + TreeColumn.template + """
{{this.row_name|safe}}
"""

  def __init__(self, *args, **kwargs):
    super(FlowColumn, self).__init__(*args, **kwargs)
    self.rows_names = {}

  def AddElement(self, index, element, depth, row_type, row_name):
    self.rows_names[index] = row_name
    super(FlowColumn, self).AddElement(index, element, depth, row_type)

  def RenderRow(self, index, request, row_options):
    self.row_name = self.rows_names.get(index, "")
    return super(FlowColumn, self).RenderRow(index, request, row_options)


class ListFlowsTable(renderers.TableRenderer):
  """List all flows for a client in a table.

  Generated Javascript Events:
    - flow_table_select(flow): The flow id that the user has selected.

  Post Parameters:
    - client_id: The client to show the flows for.
  """
  selection_publish_queue = "flow_table_select"

  with_toolbar = True

  layout_template = """
{% if this.with_toolbar %}
<div id="toolbar_{{unique|escape}}" class="breadcrumb">
  <li>
    <button id="cancel_flow_{{unique|escape}}" title="Cancel Selected Flows"
      class="btn btn-default" name="cancel_flow">
      <img src="/static/images/editdelete.png" class="toolbar_icon">
    </button>
  </li>
</div>
{% endif %}
""" + renderers.TableRenderer.layout_template

  def _GetCreationTime(self, obj):
    try:
      return obj.state.context.get("create_time")
    except AttributeError:
      return obj.Get(obj.Schema.LAST, 0)

  def __init__(self, **kwargs):
    super(ListFlowsTable, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn("State",
                                           renderer=FlowStateIcon,
                                           width="40px"))
    self.AddColumn(FlowColumn("Path",
                              renderer=semantic.SubjectRenderer,
                              width="20%"))
    self.AddColumn(semantic.RDFValueColumn("Flow Name", width="20%"))
    self.AddColumn(semantic.RDFValueColumn("Creation Time", width="20%"))
    self.AddColumn(semantic.RDFValueColumn("Last Active", width="20%"))
    self.AddColumn(semantic.RDFValueColumn("Creator", width="20%"))

  def BuildTable(self, start_row, end_row, request):
    """Renders the table."""
    depth = request.REQ.get("depth", 0)

    flow_urn = self.state.get("value", request.REQ.get("value"))
    if flow_urn is None:
      client_id = request.REQ.get("client_id")
      if not client_id:
        return

      flow_urn = rdf_client.ClientURN(client_id).Add("flows")

    flow_root = aff4.FACTORY.Open(flow_urn, mode="r", token=request.token)
    root_children_paths = sorted(flow_root.ListChildren(),
                                 key=lambda x: x.age,
                                 reverse=True)
    additional_rows = (depth == 0 and len(root_children_paths) > end_row)

    if not depth:
      root_children_paths = root_children_paths[start_row:end_row]

    # TODO(user): should be able to specify aff4_type="GRRFlow" here.
    # Currently this doesn't work because symlinks get filtered out.
    # This is an aff4.FACTORY.MultiOpen's bug.
    root_children = aff4.FACTORY.MultiOpen(root_children_paths,
                                           token=request.token)
    root_children = sorted(root_children,
                           key=self._GetCreationTime,
                           reverse=True)
    level2_children = dict(aff4.FACTORY.MultiListChildren(
        [f.urn for f in root_children],
        token=request.token))

    self.size = len(root_children)

    row_index = start_row
    for flow_obj in root_children:
      if level2_children.get(flow_obj.urn, None):
        row_type = "branch"
      else:
        row_type = "leaf"

      row = {}
      last = flow_obj.Get(flow_obj.Schema.LAST)
      if last:
        row["Last Active"] = last

      if isinstance(flow_obj, aff4.AFF4Object.GRRFlow):
        row_name = (flow_obj.symlink_urn or flow_obj.urn).Basename()
        try:
          if flow_obj.Get(flow_obj.Schema.CLIENT_CRASH):
            row["State"] = "CLIENT_CRASHED"
          else:
            row["State"] = flow_obj.state.context.state

          row["Flow Name"] = flow_obj.state.context.args.flow_name
          row["Creation Time"] = flow_obj.state.context.create_time
          row["Creator"] = flow_obj.state.context.creator
        except AttributeError:
          row["Flow Name"] = "Failed to open flow."

      elif isinstance(flow_obj, aff4.AFF4Object.GRRHunt):
        row_name = flow_obj.urn.Dirname()
        row["Flow Name"] = "Hunt"

      else:
        # A logs collection, skip, it will be rendered separately
        continue

      self.columns[1].AddElement(
          # If flow object is symlinked, we want to use symlink path in the
          # table. This way UI logic can make reasonable assumptions about
          # client's flows URNs.
          row_index,
          flow_obj.symlink_urn or flow_obj.urn,
          depth,
          row_type,
          row_name)

      self.AddRow(row, row_index)
      row_index += 1

    return additional_rows

  def Layout(self, request, response):
    response = super(ListFlowsTable, self).Layout(request, response)
    return self.CallJavascript(
        response,
        "ListFlowsTable.Layout",
        selection_publish_queue=self.selection_publish_queue)


class ShowFlowInformation(fileview.AFF4Stats):
  """Display information about the flow.

  Post Parameters:
    - flow: The flow id we will display.

  Internal State:
    - client_id, flow
  """

  selection_publish_queue = "flow_table_select"
  historical_renderer = "HistoricalFlowView"

  # Embed the regular AFF4Stats inside a container to allow scrolling
  layout_template = renderers.Template("""
<div id="container_{{unique|escapejs}}">
{% if this.path %}
""" + str(fileview.AFF4Stats.layout_template) + """
<br/>
{% else %}
Please select a flow to manage from the above table.
{% endif %}
</div>
""")

  def Layout(self, request, response):
    """Introspect the Schema for flow objects."""
    try:
      self.state["flow"] = session_id = request.REQ["flow"]
      self.fd = aff4.FACTORY.Open(session_id,
                                  token=request.token,
                                  age=aff4.ALL_TIMES)
      self.classes = self.RenderAFF4Attributes(self.fd, request)
      self.path = self.fd.urn
    except (KeyError, IOError):
      self.path = None

    # Skip our parent's Layout method and install parent's javascript code.
    response = super(fileview.AFF4Stats, self).Layout(request, response)
    return self.CallJavascript(response,
                               "AFF4Stats.Layout",
                               historical_renderer=self.historical_renderer,
                               historical_renderer_state=self.state)


class HistoricalFlowView(fileview.HistoricalView):
  """View historical attributes for the flow."""

  def Layout(self, request, response):
    self.state = dict(flow=request.REQ.get("flow"),
                      attribute=request.REQ.get("attribute"))

    self.AddColumn(semantic.RDFValueColumn(self.state["attribute"]))

    return renderers.TableRenderer.Layout(self, request, response)

  def BuildTable(self, start_row, end_row, request):
    """Populate the table with attribute values."""
    flow_name = request.REQ.get("flow")
    attribute_name = request.REQ.get("attribute")

    if attribute_name is None:
      return

    self.AddColumn(semantic.RDFValueColumn(attribute_name))
    fd = aff4.FACTORY.Open(flow_name, token=request.token, age=aff4.ALL_TIMES)

    return self.BuildTableFromAttribute(attribute_name, fd, start_row, end_row)


class FlowPBRenderer(semantic.RDFProtoRenderer):
  """Format the FlowPB protobuf."""
  classname = "Flow"
  name = "Flow Protobuf"

  backtrace_template = renderers.Template("""
<div id='hidden_pre_{{name|escape}}'>
  <ins class='fg-button ui-icon ui-icon-minus'/>
  {{error_msg|escape}}
  <div class='contents'>
    <pre>{{value|escape}}</pre>
  </div>
</div>
""")

  def RenderBacktrace(self, descriptor, value):
    error_msg = value.rstrip().split("\n")[-1]
    response = self.FormatFromTemplate(self.backtrace_template,
                                       value=value,
                                       name=descriptor.name,
                                       error_msg=error_msg)
    return self.CallJavascript(response,
                               "FlowPBRenderer.RenderBacktrace",
                               name=descriptor.name)

  # Pretty print these special fields.
  translator = dict(
      backtrace=RenderBacktrace,
      pickle=semantic.RDFProtoRenderer.Ignore,
      children=semantic.RDFProtoRenderer.Ignore,
      network_bytes_sent=semantic.RDFProtoRenderer.HumanReadableBytes)


class FlowNotificationRenderer(semantic.RDFValueRenderer):
  """Renders notifications inside the FlowRenderer."""
  classname = "Notification"

  # Note here that following href e.g. right click new tab will give a fresh URL
  # but clicking will maintain state of other tabs.
  layout_template = renderers.Template("""
{% if this.proxy.type == "ViewObject" %}
<a id="{{unique}}" href="/#{{this.BuildHash|escape}}"
target_hash="{{this.BuildHash|escape}}">
{{this.proxy.subject|escape}}</a>
{% endif %}
{{this.proxy.message|escape}}
""")

  def BuildHash(self):
    """Build hash string to navigate to the appropriate location."""
    return renderers.ViewNotifications.BuildHashFromNotification(self.proxy)

  def Layout(self, request, response):
    response = super(FlowNotificationRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "FlowNotificationRenderer.Layout")


class ClientCrashesRenderer(crash_view.ClientCrashCollectionRenderer):
  """View launched flows in a tree."""
  description = "Crashes"
  behaviours = frozenset(["HostAdvanced"])
  order = 50

  def Layout(self, request, response):
    client_id = request.REQ.get("client_id")
    self.crashes_urn = rdf_client.ClientURN(client_id).Add("crashes")
    super(ClientCrashesRenderer, self).Layout(request, response)


class GlobalLaunchFlows(renderers.AngularDirectiveRenderer):
  """Launches flows that apply across clients."""
  description = "Start Global Flows"
  behaviours = frozenset(["General"])
  order = 10

  directive = "grr-start-flow-view"

  def Layout(self, request, response):
    self.directive_args = {"flow-type": "GLOBAL"}
    self.directive_args["client-id"] = request.REQ.get("client_id")
    return super(GlobalLaunchFlows, self).Layout(request, response)


class GlobExpressionListFormRenderer(forms.RepeatedFieldFormRenderer):
  type = rdf_paths.GlobExpression
  context_help_url = "user_manual.html#_specifying_file_paths"


class GlobExpressionFormRenderer(forms.ProtoRDFValueFormRenderer):
  """A renderer for glob expressions with autocomplete."""
  type = rdf_paths.GlobExpression

  layout_template = ("""<div class="form-group">
""" + forms.TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
    <input id='{{this.prefix}}'
      type=text
{% if this.default %}
  value='{{ this.default|escape }}'
{% endif %}
      onchange="grr.forms.inputOnChange(this)"
      class="form-control unset input-xxlarge"/>
  </div>
</div>
""")

  def Layout(self, request, response):
    self.completions = rdf_client.KnowledgeBase().GetKbFieldNames()

    response = super(GlobExpressionFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response,
                               "GlobExpressionFormRenderer.Layout",
                               prefix=self.prefix,
                               completions=self.completions)


class FileFinderConditionFormRenderer(forms.UnionMultiFormRenderer):
  """Renders a single option in a list of conditions."""
  type = flows_file_finder.FileFinderCondition
  union_by_field = "condition_type"


class FileFinderConditionListFormRenderer(forms.RepeatedFieldFormRenderer):
  """Renders multiple conditions. Doesn't display a "default" condition."""
  type = flows_file_finder.FileFinderCondition

  # We want list of conditions to be empty by default.
  add_element_on_first_show = False


class FileFinderActionFormRenderer(forms.UnionMultiFormRenderer):
  """Renders a file finder action selector."""
  type = flows_file_finder.FileFinderAction
  union_by_field = "action_type"


class RegistryFinderConditionFormRenderer(forms.UnionMultiFormRenderer):
  """Renders a single option in a list of conditions."""
  type = flows_registry.RegistryFinderCondition
  union_by_field = "condition_type"


class RegistryFinderConditionListFormRenderer(forms.RepeatedFieldFormRenderer):
  """Renders multiple conditions. Doesn't display a "default" condition."""
  type = flows_registry.RegistryFinderCondition

  # We want list of conditions to be empty by default.
  add_element_on_first_show = False


class RegularExpressionFormRenderer(forms.ProtoRDFValueFormRenderer):
  type = rdf_standard.RegularExpression
  context_help_url = "user_manual.html#_regex_matches"


class LiteralExpressionFormRenderer(forms.BinaryStringTypeFormRenderer):
  type = rdf_standard.LiteralExpression
  context_help_url = "user_manual.html#_literal_matches"
