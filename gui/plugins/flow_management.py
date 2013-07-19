#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.

"""GUI elements allowing launching and management of flows."""


import urllib


import logging
from grr.gui import renderers
from grr.gui.plugins import crash_view
from grr.gui.plugins import fileview
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


class LaunchFlows(renderers.Splitter):
  """Launches a new flow."""
  description = "Start new flows"
  behaviours = frozenset(["Host"])
  order = 10

  left_renderer = "FlowTree"
  top_right_renderer = "FlowForm"
  bottom_right_renderer = "FlowManagementTabs"


class FlowTree(renderers.TreeRenderer):
  """Show all flows in a tree.

  Generated Javascript Events:
    - flow_select(flow_name) - The full path for the flow name (category +
      name).
  """

  publish_select_queue = "flow_select"

  def EnumerateCategories(self, path, request):
    """Search through all flows for categories starting with path."""
    categories = set()
    flows = set()
    # Use an object for path manipulations.
    path = rdfvalue.RDFURN(path)

    for name, cls in flow.GRRFlow.classes.items():
      if not hasattr(cls, "category") or not cls.category:
        continue
      if cls.AUTHORIZED_LABELS:
        if not data_store.DB.security_manager.CheckUserLabels(
            request.token.username, cls.AUTHORIZED_LABELS):
          continue

      category = rdfvalue.RDFURN(cls.category)
      if category == path:
        flows.add(name)
      else:
        relative_path = category.RelativeName(path)
        # This category starts with this path
        if relative_path is not None:
          categories.add(relative_path.split("/")[0])

    return categories, flows

  def RenderBranch(self, path, request):
    """Renders tree leafs for flows."""
    categories, flows = self.EnumerateCategories(path, request)
    for category in sorted(categories):
      self.AddElement(category)

    for f in sorted(flows):
      self.AddElement(f, "leaf")


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
    for type_descriptor in flow_class.flow_typeinfo:
      if not type_descriptor.hidden:
        prototypes.append("%s %s" % (type_descriptor.__class__.__name__,
                                     type_descriptor.name))

    self.prototype = "%s(%s)" % (flow_class.__name__, ", ".join(prototypes))

    self.flow_doc = flow_class.__doc__

    return super(FlowInformation, self).Layout(request, response)


class FlowForm(FlowInformation):
  """Construct a form to launch the Flow.

  Listening Javascript Events:
    - flow_select(flow_path) - A new path was selected in the tree and we
      rerender ourselves to make a new form.
  """

  # Prefix to use in form elements' names
  prefix = "v_"

  # Ignore flow argumentes with given names
  ignore_flow_args = []

  layout_template = renderers.Template("""
<div class="FormBody" id="FormBody_{{unique|escape}}">
<form id='form_{{unique|escape}}' method='POST' class="form-horizontal">
{% if this.flow_name %}
  <input type=hidden name='FlowName' value='{{ this.flow_name|escape }}'/>
  <div class="control-group">
    <label class="control-label">Client ID</label>
    <div class="controls">
      <span class="uneditable-input" id="client_id_{{unique|escape}}">
        {{this.client_id|escape}}
      </span>
    </div>
  </div>

  {{this.flow_args|safe}}

  <div class="control-group">
    <div class="controls">
      <input id='submit_{{unique|escape}}' type="submit" class="btn btn-success"
        value="Launch"/>
    </div>
  </div>
{% endif %}
</form>
</div>
<script>
  $("#submit_{{unique|escapejs}}").click(function () {
      return grr.submit('FlowFormAction', 'form_{{unique|escapejs}}',
                        '{{id|escapejs}}', false);
    });

  grr.subscribe('flow_select', function(path) {
     grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}", {
       flow_name: path,
       client_id: grr.state.client_id,
       reason: grr.state.reason
     });
  }, 'form_{{unique|escapejs}}');

  $("input.form_field_or_none").each(function(index) {
    grr.formNoneHandler($(this));
  });

  // Fixup checkboxes so they return values even if unchecked.
  $(".FormBody").find("input[type=checkbox]").change(function() {
    $(this).attr("value", $(this).attr("checked") ? "True" : "False");
  });

</script>
""")

  def Layout(self, request, response):
    """Update the form from the tree selection."""
    self.flow_name = request.REQ.get("flow_name", "").split("/")[-1]
    self.client_id = request.REQ.get("client_id", "")
    self.client = aff4.FACTORY.Open(self.client_id, token=request.token)

    type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()

    # Fill in the form elements
    if self.flow_name in flow.GRRFlow.classes:
      flow_class = flow.GRRFlow.classes[self.flow_name]
      if aff4.issubclass(flow_class, flow.GRRFlow):
        flow_typeinfo = flow_class.flow_typeinfo

        # Merge standard flow args if needed
        if flow_typeinfo is not flow.GRRFlow.flow_typeinfo:
          flow_typeinfo = flow_typeinfo.Add(flow.GRRFlow.flow_typeinfo)

        # Filter out ignored args so that they do not get rendered
        flow_typeinfo = flow_typeinfo.Remove(
            *[arg for arg in self.ignore_flow_args
              if flow_typeinfo.HasDescriptor(arg)])

        self.flow_args = type_descriptor_renderer.Form(
            flow_typeinfo, request, prefix=self.prefix)

    return renderers.TemplateRenderer.Layout(self, request, response)


class FlowFormAction(FlowInformation):
  """Execute a flow and show status."""

  buttons = """
<form id='form_{{unique|escape}}'>
  <input type=hidden name='flow_name' value='{{this.flow_name|escape}}' />
{% for desc, value in args_sent %}
  <input type=hidden name='{{arg_prefix|escape}}{{ desc|escape }}'
   value='{{ value|escape }}'/>
{% endfor %}

<input id='submit' type="submit" value="Back" class="btn" />
<input id='gotoflow' type='submit' value='View' class="btn" />
</form>
<script>
  $("#submit").button()
    .click(function () {
      return grr.submit('FlowForm', 'form_{{unique|escapejs}}',
                        '{{id|escapejs}}', false);
    });

  $('#gotoflow').button().click(function () {
      grr.publish('hash_state', 'flow', '{{this.flow_id|escapejs}}');
      grr.publish('hash_state', 'main', 'ManageFlows');
      grr.loadFromHash();
  });

  grr.subscribe('flow_select', function(path) {
     grr.layout("FlowForm", "{{id|escapejs}}", {
       flow_name: path,
       client_id: grr.state.client_id,
       reason: grr.state.reason
     });
  }, 'form_{{unique|escapejs}}');
</script>
"""

  hide_view_button = """
<script>
$('#gotoflow').hide();
</script>
"""

  layout_template = renderers.Template("""
<div class="fill-parent no-top-margin">
<h3>Launched flow {{this.flow_name|escape}}</h3>
<p><small>{{this.flow_id|escape}}</small></p>
<dl class="dl-horizontal">
  <dt>client_id</dt>
  <dd>'{{ this.client_id|escape }}'</dd>
{% for desc, arg in this.args_sent %}
  <dt>{{ desc|escape }}</dt>
  <dd>{{ arg|escape }}</dd>
{% endfor %}
</dl>
<div class='button_row'>
""" + buttons + "</div>")

  error_template = renderers.Template("""
<h2>Error: Flow '{{ name|escape }}' : </h2> {{ error|escape }}
""" + buttons + hide_view_button)

  def Layout(self, request, response):
    """Launch the flow."""
    req = request.REQ
    self.flow_name = req.get("FlowName")

    try:
      flow_class = flow.GRRFlow.classes[self.flow_name]
    except KeyError:
      return self.RenderFromTemplate(self.error_template, response,
                                     error="Flow not found",
                                     name=self.flow_name,
                                     this=self)

    try:
      self.client_id = req.get("client_id")
      if not self.client_id:
        raise RuntimeError("Client Id Not provided.")

      type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()

      # We need to be careful here as an attacker controls flow name and
      # arguments. Make sure to append the token and event_id as keyword
      # arguments to the constructor - this will raise if a non-flow reference
      # happened to make its way here, and is thus more defensive.
      self.args = dict(type_descriptor_renderer.ParseArgs(
          flow_class.flow_typeinfo, request))

      self.args["event_id"] = request.event_id

      priority = request.REQ.get("priority")
      if priority:
        self.args["priority"] = int(priority)

      self.args_sent = []
      for (k, v) in self.args.items():
        value = utils.SmartUnicode(v)
        if v:
          value = "'" + value + "'"
        self.args_sent.append((utils.SmartUnicode(k), value))

      self.flow_id = flow.GRRFlow.StartFlow(self.client_id, self.flow_name,
                                            token=request.token, **self.args)

      return renderers.TemplateRenderer.Layout(self, request, response)

    # Here we catch all exceptions in order to relay potential errors to users
    # (Otherwise they are just hidden by django error page).
    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Error: %s", e)
      renderers.Renderer.Layout(self, request, response)
      return self.RenderFromTemplate(
          self.error_template, response, this=self,
          error=str(e), id=self.id, name=self.flow_name)


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
        None, "TerminateFlow",
        flow_urn=rdfvalue.RDFURN(request.REQ.get("flow_id")),
        reason="Cancelled in GUI", token=request.token)

    super(FlowFormCancelAction, self).Layout(request, response)


class FlowStateIcon(renderers.RDFValueRenderer):
  """Render the flow state by using an icon."""

  layout_template = renderers.Template("""
<div class="centered">
  <img class='grr-icon grr-flow-icon'
    src='/static/images/{{this.icon|escape}}' />
</div>""")

  # Maps the flow states to icons we can show
  state_map = {"TERMINATED": "stock_yes.png",
               "RUNNING": "clock.png",
               "ERROR": "nuke.png",
               "CLIENT_CRASHED": "skull-icon.png"}

  icon = "question-red.png"

  def Layout(self, request, response):
    try:
      self.icon = self.state_map[str(self.proxy)]
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
    self.AddColumn(renderers.RDFValueColumn("ID"))
    self.AddColumn(renderers.RDFValueColumn("Request", width="100%"))

  def BuildTable(self, start_row, end_row, request):
    session_id = request.REQ.get("flow", "")

    state_queue = flow_runner.FlowManager.FLOW_STATE_TEMPLATE % session_id
    predicate_re = flow_runner.FlowManager.FLOW_REQUEST_PREFIX + ".*"

    # Get all the responses for this request.
    for i, (predicate, req_state, _) in enumerate(data_store.DB.ResolveRegex(
        state_queue, predicate_re, decoder=rdfvalue.RequestState,
        limit=end_row, token=request.token)):

      if i < start_row:
        continue
      if i > end_row:
        break

      # Tie up the request to each response to make it easier to render.
      self.AddCell(i, "ID", predicate)
      self.AddCell(i, "Request", rdfvalue.RequestState(req_state))


class TreeColumn(renderers.RDFValueColumn, renderers.TemplateRenderer):
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
      renderer = renderers.RDFValueRenderer.RendererForRDFValue(
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
    if isinstance(obj, aff4.AFF4Object.GRRFlow):
      return obj.state.context.get("create_time") or obj.Get(obj.Schema.LAST)
    else:
      return 0

  def __init__(self, **kwargs):
    super(ListFlowsTable, self).__init__(**kwargs)
    self.AddColumn(renderers.RDFValueColumn(
        "State", renderer=FlowStateIcon, width="40px"))
    self.AddColumn(FlowColumn("Path", renderer=renderers.SubjectRenderer,
                              width="20%"))
    self.AddColumn(renderers.RDFValueColumn("Flow Name", width="20%"))
    self.AddColumn(renderers.RDFValueColumn("Creation Time", width="20%"))
    self.AddColumn(renderers.RDFValueColumn("Last Active", width="20%"))
    self.AddColumn(renderers.RDFValueColumn("Creator", width="20%"))

  def BuildTable(self, start, _, request):
    """Renders the table."""
    depth = request.REQ.get("depth", 0)

    flow_urn = self.state.get("value", request.REQ.get("value"))

    if flow_urn is None:
      client_id = request.REQ.get("client_id")
      if not client_id: return

      flow_urn = rdfvalue.RDFURN(client_id).Add("flows")

    flow_root = aff4.FACTORY.Open(flow_urn, mode="r", token=request.token)
    root_children = list(flow_root.OpenChildren())
    self.size = len(root_children)

    level2_children = aff4.FACTORY.MultiListChildren(
        [f.urn for f in root_children], token=request.token)

    row_index = start
    for flow_obj in sorted(root_children,
                           key=self._GetCreationTime,
                           reverse=True):
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

          row["Flow Name"] = flow_obj.state.context.flow_name
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

    # The last row we wrote.
    return row_index


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

    self.AddColumn(renderers.RDFValueColumn(self.state["attribute"]))

    return renderers.TableRenderer.Layout(self, request, response)

  def BuildTable(self, start_row, end_row, request):
    """Populate the table with attribute values."""
    flow_name = request.REQ.get("flow")
    attribute_name = request.REQ.get("attribute")

    if attribute_name is None:
      return

    self.AddColumn(renderers.RDFValueColumn(attribute_name))
    fd = aff4.FACTORY.Open(flow_name, token=request.token, age=aff4.ALL_TIMES)

    self.BuildTableFromAttribute(attribute_name, fd, start_row, end_row)


class FlowPBRenderer(renderers.RDFProtoRenderer):
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
      pickle=renderers.RDFProtoRenderer.Ignore,
      children=renderers.RDFProtoRenderer.Ignore,
      network_bytes_sent=renderers.RDFProtoRenderer.HumanReadableBytes)


class FlowNotificationRenderer(renderers.RDFValueRenderer):
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


class PathspecFormRenderer(renderers.DelegatedTypeInfoRenderer):
  """Render a form for a pathspec."""
  type_info_cls = type_info.PathspecType


class GrepspecFormRenderer(renderers.DelegatedTypeInfoRenderer):
  type_info_cls = type_info.GrepspecType


class FindspecFormRenderer(renderers.DelegatedTypeInfoRenderer):
  type_info_cls = type_info.FindSpecType


class ClientCrashesRenderer(crash_view.ClientCrashCollectionRenderer):
  """View launched flows in a tree."""
  description = "Crashes"
  behaviours = frozenset(["HostAdvanced"])
  order = 50

  def Layout(self, request, response):
    client_id = request.REQ.get("client_id")
    self.crashes_urn = aff4.ROOT_URN.Add(client_id).Add("crashes")
    super(ClientCrashesRenderer, self).Layout(request, response)


class FlowStateRenderer(renderers.DictRenderer):
  """A Flow state is similar to a dict."""
  classname = "FlowState"


class DataObjectRenderer(renderers.DictRenderer):
  """A flow data object is also similar to a dict."""
  classname = "DataObject"
