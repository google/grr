#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""GUI elements allowing launching and management of flows."""

import os
import StringIO
import urllib


import matplotlib.pyplot as plt

from grr.gui import renderers
from grr.gui.plugins import crash_view
from grr.gui.plugins import fileview
from grr.gui.plugins import forms
from grr.gui.plugins import semantic
from grr.lib import access_control
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import utils


class LaunchFlows(renderers.Splitter):
  """Launches a new flow."""
  description = "Start new flows"
  behaviours = frozenset(["Host"])
  order = 10

  left_renderer = "FlowTree"
  top_right_renderer = "SemanticProtoFlowForm"
  bottom_right_renderer = "FlowManagementTabs"


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

      # If a flow is tagged as AUTHORIZED_LABELS, the user must have the correct
      # label to see it.
      if cls.AUTHORIZED_LABELS:
        try:
          data_store.DB.security_manager.CheckUserLabels(
              request.token.username, cls.AUTHORIZED_LABELS,
              token=request.token)
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
          aff4.ROOT_URN.Add("users").Add(self.user), "GRRUser",
          token=request.token)

      user_preferences = user_record.Get(user_record.Schema.GUI_SETTINGS)
    except IOError:
      user_preferences = aff4.GRRUser.SchemaCls.GUI_SETTINGS()

    flow_behaviors_to_render = (self.flow_behaviors_to_render +
                                user_preferences.mode)
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
  layout_template = renderers.TabLayout.layout_template + """
<script>
grr.subscribe('flow_select', function (path) {
    $("#{{unique|escapejs}}").data().state.flow_path = path;
    $("#{{unique|escapejs}} li.active a").click();
}, "{{unique|escapejs}}");
</script>"""

  def Layout(self, request, response):
    self.state = dict(flow_path=request.REQ.get("flow_path"),
                      client_id=request.REQ.get("client_id"))
    return super(FlowManagementTabs, self).Layout(request, response)


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
        self.states.append((state_method.func_name,
                            func_doc, ", ".join(next_states)))
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

    <div class="control-group">
      <div class="controls">
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
<script>
  $("#submit_{{unique|escapejs}}").click(function () {
      var state = {};
      $.extend(state, $('#form_{{unique|escapejs}}').data(), grr.state);

      grr.update('{{renderer}}', 'contents_{{unique|escapejs}}',
                 state);

      return false;
    });

  grr.subscribe('flow_select', function(path) {
     grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}", {
       flow_path: path,
       client_id: grr.state.client_id,
       reason: grr.state.reason
     });
  }, '{{unique|escapejs}}');
</script>
""") + renderers.TemplateRenderer.help_template

  ajax_template = renderers.Template("""
<pre>
{{this.args}}
</pre>
<pre>
{{this.runner_args}}
</pre>

Launched Flow {{this.flow_name}}.

<script>
  $("#{{this.dom_node|escapejs}} .FormBody").html("");

  grr.subscribe('flow_select', function(path) {
     grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}", {
       flow_path: path,
       client_id: grr.state.client_id,
       reason: grr.state.reason
     });
  }, '{{unique|escapejs}}');
</script>
""")

  ajax_error_template = renderers.Template("""
<script>
grr.publish("grr_messages", "{{error|escapejs}}");
grr.publish("grr_traceback", "{{error|escapejs}}");
</script>
""")

  context_help_url = "user_manual.html#_flows"

  def Layout(self, request, response):
    """Render the form for creating the flow args."""
    self.flow_name = os.path.basename(request.REQ.get("flow_path", ""))
    self.flow_cls = flow.GRRFlow.classes.get(self.flow_name)
    if aff4.issubclass(self.flow_cls, flow.GRRFlow):
      self.flow_found = True

      self.form = forms.SemanticProtoFormRenderer(
          self.flow_cls.GetDefaultArgs(token=request.token),
          prefix="args").RawHTML(request)

      self.runner_form = forms.SemanticProtoFormRenderer(
          flow.FlowRunnerArgs(flow_name=self.flow_name),
          prefix="runner").RawHTML(request)

    return super(SemanticProtoFlowForm, self).Layout(request, response)

  def RenderAjax(self, request, response):
    """Parse the flow args from the form and launch the flow."""
    self.flow_name = request.REQ.get("flow_path", "").split("/")[-1]
    self.client_id = request.REQ.get("client_id", None)
    self.dom_node = request.REQ.get("dom_node")

    flow_cls = flow.GRRFlow.classes.get(self.flow_name)
    if flow_cls is not None:

      self.args = forms.SemanticProtoFormRenderer(
          flow_cls.args_type(), prefix="args").ParseArgs(request)

      try:
        self.args.Validate()
      except ValueError as e:
        return self.RenderFromTemplate(self.ajax_error_template,
                                       response, error=e)

      self.runner_args = forms.SemanticProtoFormRenderer(
          flow.FlowRunnerArgs(), prefix="runner_").ParseArgs(request)

      self.runner_args.Validate()

      self.flow_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                            flow_name=self.flow_name,
                                            token=request.token,
                                            args=self.args,
                                            runner_args=self.runner_args)

    return renderers.TemplateRenderer.Layout(
        self, request, response, apply_template=self.ajax_template)


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
    flow.GRRFlow.StartFlow(
        flow_name="TerminateFlow",
        flow_urn=rdfvalue.RDFURN(request.REQ.get("flow_id")),
        reason="Cancelled in GUI", token=request.token)

    super(FlowFormCancelAction, self).Layout(request, response)


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


class ManageFlows(renderers.Splitter2Way):
  """View launched flows in a tree."""
  description = "Manage launched flows"
  behaviours = frozenset(["Host"])
  order = 20

  top_renderer = "ListFlowsTable"
  bottom_renderer = "FlowTabView"


class FlowTabView(renderers.TabLayout):
  """Show various flow information in a Tab view.

  Listening Javascript Events:
    - flow_table_select(flow_aff4_path) - A selection event on the tree
      informing us of the flow aff4 path. The basename of flow_path is the name
      of the flow.

  Internal State:
    - flow_path - The category and name of the flow we display.
  """
  names = ["Flow Information", "Requests"]
  delegated_renderers = ["ShowFlowInformation", "FlowRequestView"]

  tab_hash = "ftv"

  layout_template = renderers.TabLayout.layout_template + """
<script>
grr.subscribe('flow_table_select', function (path) {
  grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}",
    {flow: path, client_id: grr.state.client_id});
}, "tab_contents_{{unique|escapejs}}");
</script>"""

  def Layout(self, request, response):
    req_flow = request.REQ.get("flow")
    if req_flow:
      self.state["flow"] = req_flow

    client_id = request.REQ.get("client_id")
    if client_id:
      self.state["client_id"] = client_id

    return super(FlowTabView, self).Layout(request, response)


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
    for i, (request, responses) in enumerate(
        manager.FetchRequestsAndResponses(
            rdfvalue.RDFURN(session_id))):
      if request.id == 0:
        continue

      if i < start_row:
        continue
      if i > end_row:
        break

      # Tie up the request to each response to make it easier to render.
      self.AddCell(i, "ID",
                   manager.FLOW_REQUEST_TEMPLATE % request.id)
      self.AddCell(i, "Request", request)
      if responses:
        self.AddCell(i, "Last Response", responses[-1])


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

    return self.FormatFromTemplate(self.template, value=result,
                                   index=index, this=self)


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
      class="btn" name="cancel_flow">
      <img src="/static/images/editdelete.png" class="toolbar_icon">
    </button>
  </li>
</div>
{% endif %}
""" + renderers.TableRenderer.layout_template + """
<script>
  $("#cancel_flow_{{unique|escapejs}}").click(function () {

    /* Find all selected rows and cancel them. */
    $("#table_{{id|escape}}")
      .find("tr.row_selected div[flow_id]")
      .each(function () {
         var flow_id = $(this).attr('flow_id');
         var id = $(this).attr('id');

         /* Cancel the flow, and then reset the icon. */
         grr.layout("FlowFormCancelAction", id,
             {flow_id: flow_id}, function () {

           $('#table_{{id|escapejs}}').trigger('refresh');
         });
    });
  });

  //Receive the selection event and emit a session_id
  grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
    if (node) {
      flow = node.find("div[flow_id]").attr('flow_id');
      if (flow) {
        grr.publish("{{ this.selection_publish_queue|escapejs }}",
                    flow);
      };
    };
  }, '{{ unique|escapejs }}');

  /* Update the flow view from the hash. */
  if(grr.hash.flow) {
    // NOTE(mbushkov): delay is needed for cases when flow list and flow
    // information are rendered as parts of the same renderer. In that
    // case the ShowFlowInformation renderer won't be able to react on the
    // click because it subscribes for the flow_table_select event after
    // the code below is executed.
    window.setTimeout(function () {
      $('div[flow_id="' + grr.hash.flow +'"]').parents('tr').click();
    }, 1);
  }
</script>
"""

  def _GetCreationTime(self, obj):
    try:
      return obj.state.context.get("create_time")
    except AttributeError:
      return obj.Get(obj.Schema.LAST, 0)

  def __init__(self, **kwargs):
    super(ListFlowsTable, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn(
        "State", renderer=FlowStateIcon, width="40px"))
    self.AddColumn(FlowColumn("Path", renderer=semantic.SubjectRenderer,
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
      if not client_id: return

      flow_urn = rdfvalue.RDFURN(client_id).Add("flows")

    flow_root = aff4.FACTORY.Open(flow_urn, mode="r", token=request.token)
    root_children_paths = sorted(flow_root.ListChildren(),
                                 key=lambda x: x.age, reverse=True)

    if not depth:
      root_children_paths = root_children_paths[start_row:end_row]

    root_children = aff4.FACTORY.MultiOpen(
        root_children_paths, token=request.token)
    root_children = sorted(root_children, key=self._GetCreationTime,
                           reverse=True)
    level2_children = dict(aff4.FACTORY.MultiListChildren(
        [f.urn for f in root_children], token=request.token))

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
        row_name = flow_obj.urn.Basename()
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

      else:
        # We're dealing with a hunt here.
        row_name = flow_obj.urn.Dirname()
        row["Flow Name"] = "Hunt"

      self.columns[1].AddElement(row_index, flow_obj.urn, depth, row_type,
                                 row_name)

      self.AddRow(row, row_index)
      row_index += 1


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
<div id="container_{{unique|escapejs}}" class="FormBody">
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
      self.fd = aff4.FACTORY.Open(session_id, token=request.token,
                                  age=aff4.ALL_TIMES)
      self.classes = self.RenderAFF4Attributes(self.fd, request)
      self.path = self.fd.urn
    except (KeyError, IOError):
      self.path = None

    # Skip our parent's Layout method.
    return super(fileview.AFF4Stats, self).Layout(request, response)


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

    self.BuildTableFromAttribute(attribute_name, fd, start_row, end_row)


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
<script>
$('#hidden_pre_{{name|escape}}').click(function () {
  $(this).find('ins').toggleClass('ui-icon-plus ui-icon-minus');
  $(this).find('.contents').toggle();
}).click();
</script>
""")

  def RenderBacktrace(self, descriptor, value):
    error_msg = value.rstrip().split("\n")[-1]
    return self.FormatFromTemplate(self.backtrace_template, value=value,
                                   name=descriptor.name, error_msg=error_msg)

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

<script>
$("#{{unique|escape}}").click(function(){
  grr.loadFromHash($(this).attr("target_hash"));
});
</script>
""")

  def BuildHash(self):
    """Build hash string to navigate to the appropriate location."""
    h = {}
    path = rdfvalue.RDFURN(self.proxy.subject)
    components = path.Path().split("/")[1:]
    h["c"] = components[0]
    h["path"] = "/".join(components[1:])
    h["t"] = renderers.DeriveIDFromPath("/".join(components[1:-1]))
    h["main"] = "VirtualFileSystemView"
    return urllib.urlencode(
        sorted([(x, utils.SmartStr(y)) for x, y in h.items()]))


class ClientCrashesRenderer(crash_view.ClientCrashCollectionRenderer):
  """View launched flows in a tree."""
  description = "Crashes"
  behaviours = frozenset(["HostAdvanced"])
  order = 50

  def Layout(self, request, response):
    client_id = request.REQ.get("client_id")
    self.crashes_urn = rdfvalue.ClientURN(client_id).Add("crashes")
    super(ClientCrashesRenderer, self).Layout(request, response)


class ProgressGraphRenderer(renderers.ImageDownloadRenderer):

  def Content(self, request, _):
    """Generates the actual image to display."""
    flow_id = request.REQ.get("flow_id")
    flow_obj = aff4.FACTORY.Open(flow_id, age=aff4.ALL_TIMES)

    log = list(flow_obj.GetValuesForAttribute(flow_obj.Schema.LOG))

    create_time = flow_obj.state.context.create_time / 1000000

    plot_data = [(int(x.age) / 1000000, int(str(x).split(" ")[1]))
                 for x in log if "bytes" in str(x)]
    plot_data.append((create_time, 0))

    plot_data = sorted([(x - create_time, y) for (x, y) in plot_data])

    x = [a for (a, b) in plot_data]
    y = [b for (a, b) in plot_data]

    params = {"backend": "png"}

    plt.rcParams.update(params)
    plt.figure(1)
    plt.clf()

    plt.plot(x, y)
    plt.title("Progress for flow %s" % flow_id)
    plt.xlabel("Time (s)")
    plt.ylabel("Bytes downloaded")
    plt.grid(True)

    buf = StringIO.StringIO()
    plt.savefig(buf)
    buf.seek(0)

    return buf.read()


class GlobalLaunchFlows(renderers.Splitter):
  """Launches flows that apply across clients."""
  description = "Start Global Flows"
  behaviours = frozenset(["General"])
  order = 10

  left_renderer = "GlobalFlowTree"
  top_right_renderer = "SemanticProtoFlowForm"
  bottom_right_renderer = "FlowManagementTabs"


class GlobalFlowTree(FlowTree):
  """Show flows that work across clients."""
  publish_select_queue = "flow_select"
  flow_behaviors_to_render = flow.FlowBehaviour("Global Flow")


class GlobExpressionFormRenderer(forms.StringTypeFormRenderer):
  """A renderer for glob expressions with autocomplete."""
  type = rdfvalue.GlobExpression

  layout_template = ("""<div class="control-group">
""" + forms.TypeDescriptorFormRenderer.default_description_view + """
  <div class="controls">
    <input id='{{this.prefix}}'
      type=text
{% if this.default %}
  value='{{ this.default|escape }}'
{% endif %}
      onchange="grr.forms.inputOnChange(this)"
      class="unset input-xxlarge"/>
  </div>
</div>
<script>
grr.glob_completer.Completer("{{this.prefix}}", {{this.completions|safe}});
</script>
""")

  def AddProtoFields(self, name, attribute_type):
    for type_info in attribute_type.type_infos:
      self.completions.append("%s.%s" % (name, type_info.name))

  def _HandleType(self, name, attribute_type):
    # Skip these types.
    if attribute_type in (rdfvalue.Dict,):
      return

    # RDFValueArray contain a specific type.
    elif issubclass(attribute_type, rdfvalue.RDFValueArray):
      self._HandleType(name, attribute_type.rdf_type)

    # Semantic Protobufs just contain their own fields.
    elif issubclass(attribute_type, rdfvalue.RDFProtoStruct):
      self.AddProtoFields(name, attribute_type)

    else:
      self.completions.append(name)

  def Layout(self, request, response):
    self.completions = []
    for attribute in aff4.AFF4Object.VFSGRRClient.SchemaCls.ListAttributes():
      if attribute.name:
        self._HandleType(attribute.name, attribute.attribute_type)

    response = super(GlobExpressionFormRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "Layout", prefix=self.prefix,
                               completions=self.completions)


class FileFinderFilterFormRenderer(forms.UnionMultiFormRenderer):
  """Renders a single option in a list of filters."""
  type = rdfvalue.FileFinderFilter
  union_by_field = "filter_type"


class FileFinderFilterListFormRenderer(forms.RepeatedFieldFormRenderer):
  """Renders multiple filters. Doesn't display a "default" filter."""
  type = rdfvalue.FileFinderFilter

  # We want list of filters to be empty by default.
  add_element_on_first_show = False


class FileFinderActionFormRenderer(forms.UnionMultiFormRenderer):
  """Renders a file finder action selector."""
  type = rdfvalue.FileFinderAction
  union_by_field = "action_type"


class MemoryScannerFilterFormRenderer(forms.UnionMultiFormRenderer):
  """Renders a single option in a list of filters."""
  type = rdfvalue.MemoryScannerFilter
  union_by_field = "filter_type"


class MemoryScannerFilterListFormRenderer(forms.RepeatedFieldFormRenderer):
  """Renders multiple filters. Doesn't display a "default" filter."""
  type = rdfvalue.MemoryScannerFilter

  # We want list of filters to be empty by default.
  add_element_on_first_show = False


class MemoryScannerDumpOptionFormRenderer(forms.UnionMultiFormRenderer):
  """Renders a memory scanner dump option selector."""
  type = rdfvalue.MemoryScannerDumpOption
  union_by_field = "option_type"


class MemoryScannerActionFormRenderer(forms.UnionMultiFormRenderer):
  """Renders a memory scanner action selector."""
  type = rdfvalue.MemoryScannerAction
  union_by_field = "action_type"
