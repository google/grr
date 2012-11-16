#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""GUI elements allowing launching and management of flows."""


import functools
import urllib


import logging
from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_context
from grr.lib import type_info
from grr.lib import utils
from grr.proto import jobs_pb2


class LaunchFlows(renderers.Splitter):
  """Launches a new flow."""
  description = "Start new flows"
  behaviours = frozenset(["Host"])

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
    userlabels = None
    flows = set()
    # Use an object for path manipulations.
    path = aff4.RDFURN(path)

    for name, cls in flow.GRRFlow.classes.items():
      if not cls.category:
        continue
      if cls.AUTHORIZED_LABELS:
        if userlabels is None:
          userlabels = set()
          user_fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users")
                                      .Add(request.token.username)
                                      .Add("labels"), token=request.token)
          for label in user_fd.Get(user_fd.Schema.LABEL).data.label:
            userlabels.add(label)

        intersection = userlabels & set(cls.AUTHORIZED_LABELS)
        if not intersection:
          continue

      category = aff4.RDFURN(cls.category)
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
    $("#{{unique|escapejs}} li.ui-state-active a").click();
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
<h2>{{ this.flow_name|escape }}</h2>
<h3>{{ this.flow_doc|linebreaks }}</h3>
<p>
Prototype: {{ this.prototype|escape }}
<br>
{{ this.prototype_doc|linebreaks }}
</p>
<table class="display">
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

  def GetArgs(self, flow_class, request, arg_template=None):
    """Return all the required args for the flow."""

    if arg_template is None:
      arg_template = self.arg_prefix + "%s"
    multi_arg_template = arg_template + "[]"

    result = []
    for arg_name, arg_type, arg_default in flow_class.GetFlowArgTypeInfo():

      # Note this is a hack that requires refactoring of the typeinfo/renderer
      # binding. The correct solution is that the get_var is handled in the
      # renderer, and the DecodeString intelligence is moved there as well.
      if not isinstance(arg_type, type_info.MultiSelectList):
        # Retrieve the value from the request, use arg default if not present.
        get_var = request.REQ.get(arg_template % utils.SmartStr(arg_name))
        if get_var is None:
          get_var = arg_default
        else:
          get_var = arg_type.DecodeString(get_var)
      else:
        # This is from a multiselect option box, variables are called v_var[]
        get_var = request.REQ.getlist(multi_arg_template %
                                      utils.SmartStr(arg_name))
        if get_var is None:
          get_var = arg_default

      # We append a special prefix to prevent name collisions.
      result.append((arg_name, arg_template % utils.SmartStr(arg_name),
                     arg_type, get_var, arg_default))

    return result

  def Layout(self, request, response):
    """Update the progress bar based on the progress reported."""
    self.flow_name = request.REQ.get("flow_path", "").split("/")[-1]

    try:
      flow_class = flow.GRRFlow.classes[self.flow_name]
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

    args = self.GetArgs(flow_class, request)
    self.prototype = "%s(%s)" % (flow_class.__name__,
                                 ", ".join([x[0] for x in args]))

    self.prototype_doc = ""
    self.flow_doc = flow_class.__doc__

    if flow_class.__init__.__doc__ != flow.GRRFlow.__init__.__doc__:
      self.prototype_doc = flow_class.__init__.__doc__

    return super(FlowInformation, self).Layout(request, response)


class FlowForm(FlowInformation):
  """Construct a form to launch the Flow.

  Listening Javascript Events:
    - flow_select(flow_path) - A new path was selected in the tree and we
      rerender ourselves to make a new form.
  """

  layout_template = renderers.Template("""
<div class="FormBody" id="FormBody_{{unique|escape}}">
<form id='form_{{unique|escape}}' method='POST'>
{% if this.form_elements %}
  <input type=hidden name='FlowName' value='{{ this.flow_name|escape }}'/>
  <table><tbody><tr>
  <td class='proto_key'>Client ID</td><td>
  <div class="proto_value" id="client_id_{{unique|escape}}">
    {{this.client_id|escape}}</div></td>

  {% for form_element in this.form_elements %}
    <tr>{{form_element|escape}}</tr>
  {% endfor %}
  </tbody></table>
  <input id='submit_{{unique|escape}}' type="submit" value="Launch"/>
{% endif %}
</form>
</div>
<script>
  $("#submit_{{unique|escapejs}}").button()
    .click(function () {
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

    # Fill in the form elements
    try:
      flow_class = flow.GRRFlow.classes[self.flow_name]
      self.form_elements = self.RenderFormElements(
          self.GetArgs(flow_class, request))
    except KeyError:
      pass

    return renderers.TemplateRenderer.Layout(self, request, response)

  def RenderFormElements(self, args):
    """Produce html for each arg so a form can be build."""
    for desc, field, arg_type, value, default in args:
      if not isinstance(arg_type, type_info.TypeInfoObject):
        raise RuntimeError("%s is not a valid TypeInfoObject" % arg_type)
      else:
        form_renderer = renderers.Renderer.classes[arg_type.renderer]()
        yield form_renderer.Format(arg_type=arg_type, field=field, desc=desc,
                                   value=value, default=default,
                                   client=self.client, unique=self.unique)

    arg_type = type_info.ProtoEnum(jobs_pb2.GrrMessage, "Priority")
    form_renderer = renderers.Renderer.classes[arg_type.renderer]()

    yield form_renderer.Format(desc="Priority", field="priority",
                               arg_type=arg_type, default=1, value=1,
                               unique=self.unique)


class FlowFormAction(FlowInformation):
  """Execute a flow and show status."""

  back_button = """
<form id='form_{{unique|escape}}'>
  <input type=hidden name='flow_name' value='{{this.flow_name|escape}}' />
{% for desc, value in args_sent %}
  <input type=hidden name='{{arg_prefix|escape}}{{ desc|escape }}'
   value='{{ value|escape }}'/>
{% endfor %}

<input id='submit' type="submit" value="Back"/>
</form>
<script>
  $("#submit").button()
    .click(function () {
      return grr.submit('FlowForm', 'form_{{unique|escapejs}}',
                        '{{id|escapejs}}', false);
    });

  // Still respond if the tree is selected.
  grr.subscribe('tree_select', function() {
         grr.layout("FlowForm", "{{id|escapejs}}");
  }, 'form_{{unique|escapejs}}');
</script>
"""

  view_button = """
<form id='form2_{{unique|escape}}'>
  <input id='gotoflow' type='submit' value='View'>
</form>
<script>
  $('#gotoflow').button().click(function () {
      grr.publish('hash_state', 'flow', '{{this.flow_id|escapejs}}');
      grr.publish('hash_state', 'main', 'ManageFlows');
      grr.loadFromHash();
  });
</script>
"""

  layout_template = renderers.Template("""
Launched flow <b>{{this.flow_name|escape}}</b><br/>
{{this.flow_id|escape}}<br/>
parameters: <p>
client_id = {{ this.client_id|escape }}
{% for desc, arg in this.args_sent %}
<br>  {{ desc|escape }} = '{{ arg|escape }}'
{% endfor %}
<div class='button_row'>
""" + back_button + view_button + "</div>")

  error_template = renderers.Template("""
<h2>Error: Flow '{{ name|escape }}' : </h2> {{ error|escape }}
""" + back_button)

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

      # We need to be careful here as an attacker controls flow name and
      # arguments. Make sure to append the token and event_id as keyword
      # arguments to the constructor - this will raise if a non-flow reference
      # happened to make its way here, and is thus more defensive.
      self.args = {}
      self.args["event_id"] = request.event_id

      for name, _, _, value, _ in self.GetArgs(flow_class, request):
        self.args[name] = value

      priority = request.REQ.get("priority")
      if priority:
        self.args["priority"] = int(priority)

      self.flow_id = flow.FACTORY.StartFlow(self.client_id, self.flow_name,
                                            token=request.token, **self.args)
      self.args_sent = self.args.items()

      return renderers.TemplateRenderer.Layout(self, request, response)

    # Here we catch all exceptions in order to relay potential errors to users
    # (Otherwise they are just hidden by django error page).
    except Exception as e:  # pylint: disable=W0703
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
    self.flow_id = request.REQ.get("flow_id", "")
    flow.FACTORY.TerminateFlow(self.flow_id, reason="Cancelled in GUI",
                               token=request.token, force=True)
    super(FlowFormCancelAction, self).Layout(request, response)


class FlowStateIcon(renderers.RDFValueRenderer):
  """Render the flow state by using an icon."""

  layout_template = renderers.Template("""
<img class='grr-icon grr-flow-icon'
  src='/static/images/{{this.icon|escape}}' />""")

  # Maps the flow states to icons we can show
  state_map = {jobs_pb2.FlowPB.TERMINATED: "stock_yes.png",
               jobs_pb2.FlowPB.RUNNING: "clock.png",
               jobs_pb2.FlowPB.ERROR: "nuke.png"}

  icon = "question-red.png"

  def Layout(self, request, response):
    try:
      self.icon = self.state_map[int(self.proxy)]
    except (KeyError, ValueError):
      pass

    super(FlowStateIcon, self).Layout(request, response)


class FlowArgsRenderer(renderers.RDFProtoRenderer):
  """Render the flow args."""

  def Layout(self, _, response):
    response.write(self.ProtoDict(_, self.proxy.data))

    return response


# Here we want the same behaviour as VirtualFileSystemView (i.e. present a
# select client form initially), but then we want a 2 way splitter instead.
class ManageFlows(renderers.Splitter2Way):
  """Managed launched flows."""
  description = "Manage launched flows"
  behaviours = frozenset(["Host"])

  top_renderer = "ListFlowsTable"
  bottom_renderer = "FlowTabView"


class FlowTabView(renderers.TabLayout):
  """Show various flow information in a Tab view.

  Listening Javascript Events:
    - flow_table_select(flow_path) - A selection event on the tree informing us
      of the flow path. The basename of flow_path is the name of the flow.

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
    self.state = dict(flow=request.REQ.get("flow"),
                      client_id=request.REQ.get("client_id"))
    return super(FlowTabView, self).Layout(request, response)


class RequestStateRenderer(renderers.RDFProtoRenderer):
  """Render the RequestState proto."""

  translator = dict(
      request=functools.partial(renderers.RDFProtoRenderer.RDFProtoRenderer,
                                proto_renderer_name="GrrRequestRenderer"))


class FlowRequestView(renderers.TableRenderer):
  """View outstanding requests for a flow.

  Post Parameters:
    - client_id: The client to show the flows for.
    - flow: The flow to show.
  """

  post_parameters = ["flow", "client_id"]

  def __init__(self):
    super(FlowRequestView, self).__init__()
    self.AddColumn(renderers.RDFValueColumn("ID", width=10))
    self.AddColumn(renderers.RDFValueColumn("Request",
                                            renderer=RequestStateRenderer))

  def BuildTable(self, start_row, end_row, request):
    session_id = request.REQ.get("flow", "")

    state_queue = flow_context.FlowManager.FLOW_STATE_TEMPLATE % session_id
    predicate_re = flow_context.FlowManager.FLOW_REQUEST_PREFIX + ".*"

    # Get all the responses for this request.
    for i, (predicate, req_state, _) in enumerate(data_store.DB.ResolveRegex(
        state_queue, predicate_re, decoder=jobs_pb2.RequestState,
        limit=end_row, token=request.token)):

      if i < start_row:
        continue
      if i > end_row:
        break

      # Tie up the request to each response to make it easier to render.
      rdf_req_state = aff4.RDFProto(req_state)

      self.AddCell(i, "ID", predicate)
      self.AddCell(i, "Request", rdf_req_state)


class TreeColumn(renderers.RDFValueColumn, renderers.TemplateRenderer):
  """A specialized column which adds tree controls."""

  template = renderers.Template("""
{% if this.branch %}
<span depth='{{this.depth|escape}}' onclick='grr.table.hideChildRows(this);'
  style='margin-left: {{this.depth|escape}}em;' class='tree_closed tree_branch
  {% if this.depth %}
    tree_hidden
  {% endif %}
  '/>
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
    if self.depth:
      row_options["class"] = "tree_hidden"

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
{{this.value|safe}}
"""


class ListFlowsTable(renderers.TableRenderer):
  """List all flows for a client in a table.

  Generated Javascript Events:
    - flow_table_select(flow): The flow id that the user has selected.

  Post Parameters:
    - client_id: The client to show the flows for.
  """
  selection_publish_queue = "flow_table_select"

  layout_template = """
<div id="toolbar_{{unique|escape}}" class="toolbar">
  <button id='cancel_flow_{{unique|escape}}' title='Cancel Selected Flows'>
    <img src='/static/images/editdelete.png' class='toolbar_icon'>
  </button> <div id="cancel" />
</div>
""" + renderers.TableRenderer.layout_template + """
<script>
  $("#cancel_flow_{{unique|escape}}").click(function () {

    /* Find all selected rows and cancel them. */
    $("#table_{{id|escape}}")
      .find("tr.row_selected div[flow_id]")
      .each(function () {
         var flow_id = $(this).attr('flow_id');
         var id = $(this).attr('id');

         /* Cancel the flow, and then reset the icon. */
         grr.layout("FlowFormCancelAction", id,
             {flow_id: flow_id}, function () {
           $('div[flow_id=' + flow_id +']').parents('tr').find(
             '.grr-flow-icon').attr('src', '/static/images/nuke.png')
             .click();
         });
    });
  });

  //Receive the selection event and emit a session_id
  grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
    if (node) {
      flow = node.find("div[flow_id]").attr('flow_id');
      grr.publish("{{ this.selection_publish_queue|escapejs }}",
                  flow);
    };
  }, '{{ unique|escapejs }}');

  /* Update the flow view from the hash. */
  if(grr.hash.flow) {
    grr.publish("{{ this.selection_publish_queue|escapejs }}",
                grr.hash.flow);
  };
</script>
"""

  def __init__(self):
    super(ListFlowsTable, self).__init__()
    self.AddColumn(renderers.AttributeColumn(
        "Flow.state", renderer=FlowStateIcon, width=0))
    self.AddColumn(FlowColumn("Path", renderer=renderers.SubjectRenderer))
    self.AddColumn(renderers.AttributeColumn("Flow.name"))
    self.AddColumn(renderers.AttributeColumn("Flow.create_time"))
    self.AddColumn(renderers.RDFValueColumn("Last Active"))
    self.AddColumn(renderers.AttributeColumn("Flow.creator"))

  def _BuildParentTree(self, flows):
    """Given a list of flows, builds an index of the flows.

    We also add a children list to each flow.

    Args:
       flows: A list of GRRFlow objects.

    Returns:
       A dict of all flow objects, keyed by session_id. Each flow object will
       also have a children list of its children. In addition, the "root" object
       will contain all the flows without parents.
    """
    # Make a root node to hold all unparented flows.
    root = aff4.RDFValue.classes["Flow"]()
    root.children = []

    index = {"root": root}

    # We use the precondition that later flows are always parented by earlier
    # flows. So we can not have a situation where a parent flow can not be
    # found.
    for flow_obj in sorted(flows, key=lambda x: x.flow_pb.data.create_time):
      # Assume that session_ids are unique.
      index[flow_obj.session_id] = flow_obj
      flow_obj.children = []

      # If there are parents, add them here.
      parent = flow_obj.flow_pb.data.request_state.session_id

      # Reparent orphans to the root. This happens when we fetch more of flows
      # for the incremental table, and the new flows really belong to a flow
      # fetched by previous refresh. By re-parenting these orphans at least we
      # can show them in the table.
      if parent not in index:
        parent = "root"

      index[parent].children.append(flow_obj)

    return index

  def BuildTable(self, start, end, request):
    """Renders the table."""
    client_id = request.REQ.get("client_id")
    if not client_id: return
    self.row_index = start

    # Flows are stored as versions of the FLOW attribute, so here we need all
    # the versions so we can list them in the table.
    client = aff4.FACTORY.Create(client_id, "VFSGRRClient", mode="r",
                                 token=request.token, age=aff4.ALL_TIMES)

    # This is how many flows we have.
    flows = client.GetValuesForAttribute(client.Schema.FLOW)

    self.size = len(flows)

    flows = flows[start:end]

    # Sort the flows so the most recent ones are at the top.
    index = self._BuildParentTree(client.GetFlows(start=start, length=end-start,
                                                  age_policy=aff4.NEWEST_TIME))

    def RenderBranch(session_id, depth):
      """Render a single branch of the tree."""
      children = index[session_id].children
      children.sort(key=lambda x: x.flow_pb.data.create_time, reverse=True)
      nodes = 0

      for child in children:
        if child.children:
          row_type = "branch"
        else:
          row_type = "leaf"

        self.columns[1].AddElement(self.row_index, child.session_id,
                                   depth, row_type)
        self.columns[4].AddElement(self.row_index, child.flow_pb.age)
        self.AddRowFromFd(self.row_index, child)

        self.row_index += 1
        nodes += 1

        # Now do the children
        if row_type == "branch":
          RenderBranch(child.session_id, depth + 1)

      return nodes

    # Recursively render all the branches.
    RenderBranch("root", 0)

    for f in flows:
      session_id = f.Split()[-1]
      if session_id not in index:
        self.columns[1].AddElement(self.row_index, session_id, 0, "leaf")
        self.columns[2].AddElement(self.row_index,
                                   "Flow too old, no information")
        self.columns[4].AddElement(self.row_index, f.age)
        self.row_index += 1

    # The last row we wrote.
    return self.row_index


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
      switch = aff4.FACTORY.Open(aff4.FLOW_SWITCH_URN, token=request.token,
                                 age=aff4.ALL_TIMES)
      self.fd = switch.OpenMember(session_id)
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
    fd = aff4.FACTORY.Open(aff4.FLOW_SWITCH_URN, token=request.token,
                           age=aff4.ALL_TIMES)

    self.BuildTableFromAttribute(attribute_name, fd.OpenMember(flow_name),
                                 start_row, end_row)


class FlowPBRenderer(renderers.RDFProtoRenderer):
  """Format the FlowPB protobuf."""
  classname = "Flow"
  name = "Flow Protobuf"

  # {{value}} comes from the translator so its assumed to be safe.
  proto_template = renderers.Template("""
<table class='proto_table'>
<tbody>
{% for key, value in data %}
<tr>
<td class="proto_key">{{key|escape}}</td><td class="proto_value">
{{value|safe}}
</td>
</tr>
{% endfor %}
</tbody>
</table>
""")

  def RenderProtoDict(self, _, protodict):
    protodict = utils.ProtoDict(protodict)

    return self.FormatFromTemplate(self.proto_template,
                                   data=protodict.ToDict().items())

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
      create_time=renderers.RDFProtoRenderer.Time,
      pickle=renderers.RDFProtoRenderer.Ignore,
      backtrace=RenderBacktrace,
      state=renderers.RDFProtoRenderer.Enum,
      ts_id=renderers.RDFProtoRenderer.Ignore,
      args=renderers.RDFProtoRenderer.ProtoDict,
      network_bytes_sent=renderers.RDFProtoRenderer.HumanReadableBytes)


class FlowNotificationRenderer(renderers.RDFValueRenderer):
  """Renders notifications inside the FlowRenderer."""
  classname = "Notification"

  # Note here that following href e.g. right click new tab will give a fresh URL
  # but clicking will maintain state of other tabs.
  layout_template = renderers.Template("""
{% if this.proxy.data.type == "ViewObject" %}
<a id="{{unique}}" href="/#{{this.BuildHash|escape}}"
target_hash="{{this.BuildHash|escape}}">
{{this.proxy.data.subject|escape}}</a>
{% endif %}
{{this.proxy.data.message|escape}}

<script>
$("#{{unique|escape}}").click(function(){
  grr.loadFromHash($(this).attr("target_hash"));
});
</script>
""")

  def BuildHash(self):
    """Build hash string to navigate to the appropriate location."""
    h = {}
    path = aff4.RDFURN(self.proxy.data.subject)
    components = path.Path().split("/")[1:]
    h["c"] = components[0]
    h["path"] = "/".join(components[1:])
    h["t"] = renderers.DeriveIDFromPath("/".join(components[1:-1]))
    h["main"] = "VirtualFileSystemView"
    return urllib.urlencode(
        sorted([(x, utils.SmartStr(y)) for x, y in h.items()]))
