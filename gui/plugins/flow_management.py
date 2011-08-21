#!/usr/bin/env python
#
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


import json

from django import http
from django import template
from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.lib import aff4
from grr.lib import flow
from grr.lib import utils
from grr.proto import jobs_pb2


class LaunchFlows(renderers.Splitter):
  """Launches a new flow."""
  category = "Flow Management"
  description = "Start new flows"

  left_renderer = "FlowTree"
  top_right_renderer = "FlowForm"
  bottom_right_renderer = "FlowInformation"


class FlowTree(renderers.TreeRenderer):
  """Show all flows in a tree."""

  def EnumerateCategories(self, path):
    """Search through all flows for categories starting with path."""
    categories = set()
    flows = set()
    # Use an object for path manipulations.
    path = aff4.RDFURN(path)

    for name, cls in flow.GRRFlow.classes.items():
      if not cls.category:
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

  def RenderAjax(self, request, _):
    """Renders tree leafs for flows."""
    path = request.REQ.get("path", "/")

    result = []
    categories, flows = self.EnumerateCategories(path)
    for category in categories:
      full_path = path + category + "/"
      result.append(dict(data=category,
                         attr=dict(id=renderers.DeriveIDFromPath(full_path)),
                         children=[],
                         state="closed"))

    for f in flows:
      full_path = path + "/" + f
      result.append(dict(data=f,
                         attr=dict(path=full_path,
                                   id=renderers.DeriveIDFromPath(full_path))))

    encoder = json.JSONEncoder()
    return http.HttpResponse(encoder.encode(result),
                             mimetype="application/json")


class FlowInformation(renderers.Renderer):
  """Displays information about the flow."""

  event_queue = "tree_select"

  layout_template = template.Template("""
<div id='{{ renderer }}_{{ unique }}' class="FormBody"></div>
<script>
  grr.subscribe('{{ event_queue }}', function (path) {
     grr.state.path = path;
     grr.update('{{ renderer }}', '{{ renderer }}_{{ unique }}');
 }, '{{ renderer }}_{{ unique }}');
</script>
""")

  def Layout(self, request, response):
    """Just connect to the tree select signal."""
    response = super(FlowInformation, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.layout_template, response, unique=self.unique,
        id=self.id, event_queue=self.event_queue,
        renderer=self.__class__.__name__)

  ajax_template = template.Template("""
<h2>{{ name }}</h2>
<h3>{{ doc|linebreaks }}</h3>
<p>
Prototype: {{ prototype }}
<br>
{{ prototype_doc|linebreaks }}
</p>
<table class="display">
<thead>
<tr>
<th class="ui-state-default">State</th>
<th class="ui-state-default">Description</th>
<th class="ui-state-default">Next States</th></tr>
</thead>
<tbody>
{% for state, doc, next in states %}
   <tr><td class='state'>{{ state }}</td>
   <td class='description'>{{ doc }}</td>
   <td class='text'>{{ next }}</td></tr>
{% endfor %}
</tbody>
</table>
""")

  # This is prepended to flow args to eliminate clashes with other parameters.
  arg_prefix = "v_"

  def GetArgs(self, flow_class, request):
    """Return all the required args for the flow."""

    # Calculate the prototype
    omit_args = ("self kwargs kw client_id _request_state "
                 "flow_factory queue_name user event_id").split()

    args = [x for x in flow_class.__init__.im_func.func_code.co_varnames
            if x not in omit_args]

    defaults = flow_class.__init__.im_func.func_defaults

    # Map the default values on the args
    result = []
    for i in range(len(args)):
      try:
        default = defaults[i - len(args)]
      except IndexError:
        default = ""

      # Parse the get value based on the type of the default
      get_var = request.REQ.get(self.arg_prefix + utils.SmartStr(args[i]))

      # We append a special prefix to prevent name collisions
      result.append((args[i], self.arg_prefix + utils.SmartStr(args[i]),
                     get_var, default))

    return result

  def RenderAjax(self, request, response):
    """Update the progress bar based on the progress reported."""
    response = super(FlowInformation, self).RenderAjax(request, response)

    flow_name = request.REQ.get("path", "").split("/")[-1]

    try:
      flow_class = flow.GRRFlow.classes[flow_name]
    except KeyError:
      return response

    states = []
    # Fill in information about each state
    for state_method in flow_class.__dict__.values():
      try:
        next_states = state_method.next_states

        # Only show the first line of the doc string.
        try:
          func_doc = state_method.func_doc.split("\n")[0].strip()
        except AttributeError:
          func_doc = ""
        states.append((state_method.func_name,
                       func_doc, ", ".join(next_states)))
      except AttributeError: pass

    args = self.GetArgs(flow_class, request)
    prototype = "%s(%s)" % (flow_class.__name__,
                            ", ".join([x[0] for x in args]))

    prototype_doc = ""
    if flow_class.__init__.__doc__ != flow.GRRFlow.__init__.__doc__:
      prototype_doc = flow_class.__init__.__doc__

    return self.RenderFromTemplate(
        self.ajax_template, response,
        name=flow_name, prototype=prototype,
        states=states, prototype_doc=prototype_doc,
        doc=flow_class.__doc__, unique=self.unique,
        id=self.id
        )


class FlowForm(FlowInformation):
  """Construct a form to launch the Flow."""

  ajax_template = template.Template("""
<div class="FormBody">
<form id='form_{{unique}}' method='POST'>
<input type=hidden name='FlowName' value='{{ name }}'/>
<table><tbody><tr>
<td class='proto_key'>Client ID</td><td>
<div class="proto_value" id="client_id_{{unique}}">
{{client_id}}</div></td>

{% for desc, field, value, default in fields %}
  <tr><td>{{ desc }}</td>
{% if value %}
 <td><input name='{{ field }}' type=text value='{{ value }}'/></td>
{% else %}
 <td><input name='{{ field }}' type=text value='{{ default }}'/></td>
{% endif %}
</tr>
{% endfor %}
</tbody></table>
<input id='submit' type="submit" value="Launch"/>
</form>
</div>
<script>
  $("#submit").button()
    .click(function () {
      return grr.submit('FlowFormAction', 'form_{{unique}}',
                        '{{ id }}', false, grr.layout);
    });

  grr.subscribe('client_selection', function (cn) {
    $("#client_id_{{unique}}").text(cn);
  }, "form_{{unique}}");
</script>
""")

  def RenderAjax(self, request, response):
    """Update the form from the tree selection."""
    super(FlowInformation, self).RenderAjax(request, response)

    flow_name = request.REQ.get("path", "").split("/")[-1]

    try:
      flow_class = flow.GRRFlow.classes[flow_name]
    except KeyError:
      return response

    args = self.GetArgs(flow_class, request)

    return self.RenderFromTemplate(
        self.ajax_template, response,
        name=flow_name, client_id=request.REQ.get("client_id", ""),
        fields=args, doc=flow_class.__doc__,
        renderer=self.__class__.__name__, id=self.id, unique=self.unique
        )


class FlowFormAction(FlowInformation):
  """Execute a flow and show status."""

  back_button = """
<form id='form'>

{% for desc, value in args_sent %}
  <input type=hidden name='{{arg_prefix}}{{ desc }}' value='{{ value }}'/>
{% endfor %}

<input id='submit' type="submit" value="Back"/>
</form>
<script>
  $("#submit").button()
    .click(function () {
      return grr.submit('FlowForm', 'form', $('#form').parent().attr("id"),
                        false, grr.update);
    });
</script>
"""

  layout_template = template.Template("""
Launched flow <b>{{name}}</b> with parameters: <p>
client_id = {{ client_id }}
{% for desc, arg in args_sent %}
<br>  {{ desc }} = '{{ arg }}'
{% endfor %}
""" + back_button)

  error_template = template.Template("""
<h2>Error: Flow '{{ name }}' : </h2> {{ error }}
""" + back_button)

  def BuildArgs(self, arg_list):
    """Convert the arg_list into a dict substituting default values."""
    args = {}
    for name, _, get_var, default in arg_list:
      if get_var is not None:
        # Here we try to guess the real type of the encoded get_var by examining
        # the type of the default parameter. If the default is a bool we try to
        # interpret the value as a true/value.
        if type(default) == bool:
          if get_var.lower() == "true":
            default = True
          elif get_var.lower() == "false":
            default = False
          else:
            raise RuntimeError("Error parsing parameter '%s': "
                               "Value '%s' invalid" % (name, get_var))
        elif default is None and get_var == "None":
          # If the default is None we have no idea what the arg type really is,
          # we just need to preserve the None or else convert to string.
          default = None
        elif type(default) == int or type(default) == long:
          default = long(get_var)
        else:
          # String parameter
          default = utils.SmartUnicode(get_var)

      args[name] = default

    return args

  def Layout(self, request, response):
    """Launch the flow."""
    response = super(FlowInformation, self).Layout(request, response)
    req = request.REQ
    flow_name = req.get("FlowName")

    try:
      flow_class = flow.GRRFlow.classes[flow_name]
    except KeyError:
      return self.RenderFromTemplate(self.error_template, response,
                                     error="Client not found", name=flow_name)

    try:
      arg_list = self.GetArgs(flow_class, request)

      client_id = req.get("client_id")
      if not client_id:
        raise RuntimeError("Client Id Not provided.")

      # We need to be careful here as an attacker controls flow name and
      # arguments. Make sure to append the username and event_id as keyword
      # arguments to the constructor - this will raise if a non-flow reference
      # happened to make its way here, and is thus more defensive.
      args = self.BuildArgs(arg_list)
      args["event_id"] = request.event_id

      user = request.META.get("REMOTE_USER")
      flow.FACTORY.StartFlow(client_id, flow_name, user=user, **args)

      return self.RenderFromTemplate(
          self.layout_template, response, arg_prefix=self.arg_prefix,
          id=self.id, event_queue=self.event_queue, name=flow_name,
          client_id=client_id, args=arg_list, unique=self.unique,
          args_sent=args.items(), renderer=self.__class__.__name__)

    # Here we catch all exceptions in order to relay potential errors to users
    # (Otherwise they are just hidden by django error page).
    except Exception, e:
      return self.RenderFromTemplate(
          self.error_template, response, args=arg_list,
          error=str(e), id=self.id,
          name=flow_name)


# The following is an interface for managing launched flows for a client


class FlowStateIcon(renderers.RDFValueRenderer):
  """Render the flow state by using an icon."""

  layout_template = template.Template("""
<img class='grr-icon' src='/static/images/{{icon}}' />""")

  # Maps the flow states to icons we can show
  state_map = {jobs_pb2.FlowPB.TERMINATED: "stock_yes.png",
               jobs_pb2.FlowPB.RUNNING: "clock.png",
               jobs_pb2.FlowPB.ERROR: "nuke.jpg"}

  def Layout(self, _, response):
    return self.RenderFromTemplate(
        self.layout_template, response,
        icon=self.state_map.get(self.proxy, "question"))


# Here we want the same behaviour as VirtualFileSystemView (i.e. present a
# select client form initially), but then we want a 2 way splitter instead.
class ManageFlows(fileview.VirtualFileSystemView, renderers.Splitter2Way):
  """Managed launched flows."""
  category = "Flow Management"
  description = "Manage launched flows"

  top_renderer = "ListFlowsTable"
  bottom_renderer = "ShowFlowInformation"


class ListFlowsTable(renderers.TableRenderer):
  """List all flows for a client in a table."""
  selection_publish_queue = "flow_select"
  table_options = {
      "table_hash": "ft",
      }

  flow_table_template = template.Template("""
<script>
  //Receive the selection event and emit a session_id
  grr.subscribe("table_selection_{{ id|escapejs }}", function(node) {
    if (node) {
      var element = node.find("span")[0];
      if (element) {
        grr.state.flow = element.innerHTML;
        grr.publish("{{ selection_publish_queue|escapejs }}",
                    grr.state.flow);
      };
    };
  }, 'table_{{ unique }}');

  grr.subscribe('client_selection', function(message) {
    grr.layout("{{renderer}}", "{{id}}");
  },  'table_{{ unique }}');

</script>
""")

  def __init__(self):
    super(ListFlowsTable, self).__init__()
    self.AddColumn(renderers.AttributeColumn(
        "Flow.state", renderer=FlowStateIcon))
    self.AddColumn(renderers.AttributeColumn(
        "Flow.session_id", renderer=renderers.SubjectRenderer))
    self.AddColumn(renderers.AttributeColumn("Flow.create_time"))
    self.AddColumn(renderers.AttributeColumn("Flow.name"))
    self.AddColumn(renderers.AttributeColumn("Flow.creator"))

  def Layout(self, request, response):
    """The table lists files in the directory and allow file selection."""
    response = super(ListFlowsTable, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.flow_table_template, response,
        id=self.id, unique=self.unique, renderer=self.__class__.__name__,
        selection_publish_queue=self.selection_publish_queue,
        )

  def RenderAjax(self, request, response):
    """Renders the table."""
    client_id = request.REQ.get("client_id")
    row_index = start = int(request.REQ.get("iDisplayStart", 0))
    length = int(request.REQ.get("iDisplayLength", 50))

    client = aff4.FACTORY.Open(client_id)
    # How many flows do we have? Set the size so we can page the table.
    flows = client.GetValuesForAttribute(client.Schema.FLOW)
    self.size = len(flows)

    for flow_obj in client.GetFlows(start, length):
      # Add the fd to all the columns
      for column in self.columns:
        # This sets AttributeColumns directly from their fd.
        if isinstance(column, renderers.AttributeColumn):
          column.AddRowFromFd(row_index, flow_obj)

      row_index += 1
      if row_index > start + length:
        break

    # Call our baseclass to actually do the rendering
    return super(ListFlowsTable, self).RenderAjax(request, response)


class ShowFlowInformation(fileview.AFF4Stats):
  """Display information about the flow."""

  selection_publish_queue = "flow_select"

  flow_view_template = template.Template("""
<div id="container_{{unique}}" class="FormBody">
{% autoescape off %}
{{stat_content}}
{% endautoescape %}
<script>
  grr.subscribe("{{ selection_publish_queue }}", function (session_id) {
     grr.state.flow = session_id;

     grr.layout("{{renderer}}", "{{id}}");
  }, "container_{{unique}}");
</script>
</div>
""")

  def Layout(self, request, response):
    """Introspect the Schema for flow objects."""
    response = renderers.Renderer.Layout(self, request, response)
    flow_urn = request.REQ.get("flow")

    stat_content = "Please Select a flow to manage from the above table."
    if flow_urn:
      fd = aff4.FACTORY.Open(aff4.RDFURN("aff4:/flows").Add(flow_urn))
      classes = self.RenderAFF4Attributes(fd)
      stat_content = self.FormatFromTemplate(
          self.layout_template,
          classes=classes, id=self.id, unique=self.unique, path=fd.urn)

    return self.RenderFromTemplate(
        self.flow_view_template, response,
        selection_publish_queue=self.selection_publish_queue,
        renderer=self.__class__.__name__, id=self.id, unique=self.unique,
        stat_content=stat_content)


class FlowPBRenderer(renderers.RDFProtoRenderer):
  """Format the FlowPB protobuf."""
  ClassName = "Flow"
  name = "Flow Protobuf"

  # Pretty print these special fields.
  translator = dict(create_time=renderers.RDFProtoRenderer.Time,
                    pickle=renderers.RDFProtoRenderer.Ignore,
                    backtrace=renderers.RDFProtoRenderer.Pre,
                    state=renderers.RDFProtoRenderer.Enum,
                    ts_id=renderers.RDFProtoRenderer.Ignore,
                    args=renderers.RDFProtoRenderer.ProtoDict)
