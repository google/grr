#!/usr/bin/env python
# Copyright 2012 Google Inc.
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


"""Inspect current state of in flight flows.

This module provides a UI for inspecting the messages outstanding for a client
and how they are progressing. This helps the user understand the status and
progress of existing flows.
"""




from grr.client import actions
from grr.gui import renderers
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flow_context
from grr.lib import scheduler
from grr.lib.aff4_objects import aff4_grr
from grr.proto import jobs_pb2


class TaskRenderer(renderers.RDFProtoRenderer):
  """Render a Task Scheduler Task."""
  ClassName = "TaskSchedulerTask"
  name = "Task Scheduler Task"

  def RenderAsRequest(self, *args):
    return self.RDFProtoRenderer(
        *args, proto_renderer_name="GrrRequestRenderer")

  translator = dict(value=RenderAsRequest, eta=renderers.RDFProtoRenderer.Time)


class InspectView(renderers.Splitter2Way):
  """Inspect outstanding requests for the client."""
  description = "Debug Client Requests"
  behaviours = frozenset(["Host"])

  order = 100

  top_renderer = "RequestTable"
  bottom_renderer = "RequestTabs"


class RequestTable(renderers.TableRenderer):
  """Show all outstanding requests for a client.

  Generated Javascript Events:
    - request_table_select(request_id): The task id that the user has selected.

  Post Parameters:
    - client_id: The client to show the flows for.
  """
  layout_template = renderers.TableRenderer.layout_template + """
<script>
  //Receive the selection event and emit a path
  grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
    if (node) {
      var task_id = node.find("td:contains(task)").text();

      grr.publish("request_table_select", task_id);
    };
  }, '{{ unique|escapejs }}');
</script>
"""

  post_parameters = ["client_id"]

  def __init__(self):
    super(RequestTable, self).__init__()
    self.AddColumn(renderers.RDFValueColumn(
        "Status", renderer=renderers.IconRenderer, width=0))

    self.AddColumn(renderers.RDFValueColumn("ID"))
    self.AddColumn(renderers.RDFValueColumn("Due"))
    self.AddColumn(renderers.RDFValueColumn("Flow", width=20))
    self.AddColumn(renderers.RDFValueColumn("Client Action"))

  def BuildTable(self, start_row, end_row, request):
    client_id = request.REQ.get("client_id")
    now = aff4.RDFDatetime()

    # Make a local scheduler.
    scheduler_obj = scheduler.TaskScheduler()

    for i, task in enumerate(scheduler_obj.Query(client_id, limit=end_row,
                                                 token=request.token)):
      if i < start_row:
        continue

      request = jobs_pb2.GrrMessage()
      request.ParseFromString(task.value)

      difference = now - task.eta
      if difference > 0:
        self.AddCell(i, "Status", dict(
            icon="stock_yes", description="Available for Lease"))
      else:
        self.AddCell(i, "Status", dict(
            icon="clock",
            description="Leased for %s Seconds" % (difference / 1e6)))

      self.AddCell(i, "ID", task.task_id)
      self.AddCell(i, "Flow", request.session_id)
      self.AddCell(i, "Due", aff4.RDFDatetime(task.eta))
      self.AddCell(i, "Client Action", request.name)


class ResponsesTable(renderers.TableRenderer):
  """Show all outstanding requests for a client.

  Post Parameters:
    - client_id: The client to show the flows for.
    - task_id: The id of the request to display.
  """

  post_parameters = ["client_id", "task_id"]

  def __init__(self):
    super(ResponsesTable, self).__init__()
    self.AddColumn(renderers.RDFValueColumn("Task ID", width=10))
    self.AddColumn(renderers.RDFValueColumn(
        "Response", renderer=GrrResponseRenderer))

  def BuildTable(self, start_row, end_row, request):
    client_id = request.REQ.get("client_id")
    task_id = request.REQ.get("task_id")

    # This is the request.
    scheduler_obj = scheduler.TaskScheduler()
    request_message = scheduler_obj.Query(
        client_id, task_id=task_id, token=request.token,
        decoder=jobs_pb2.GrrMessage)[0].value

    state_queue = (flow_context.FlowManager.FLOW_STATE_TEMPLATE %
                   request_message.session_id)

    predicate_re = (flow_context.FlowManager.FLOW_RESPONSE_PREFIX %
                    request_message.request_id) + ".*"

    # Get all the responses for this request.
    for i, (predicate, message, _) in enumerate(data_store.DB.ResolveRegex(
        state_queue, predicate_re, decoder=jobs_pb2.GrrMessage, limit=end_row,
        token=request.token)):

      if i < start_row:
        continue
      if i > end_row:
        break

      # Tie up the request to each response to make it easier to render.
      rdf_response_message = aff4_grr.GRRMessage(message)
      rdf_response_message.request = request_message

      self.AddCell(i, "Task ID", predicate)
      self.AddCell(i, "Response", rdf_response_message)


class RequestTabs(renderers.TabLayout):
  """Show a tabset to inspect the requests.

    Events:
    - Listen for the request_table_select event. Update the task_id in our state
      and reload the current tab.
  """

  names = ["Request", "Responses"]
  delegated_renderers = ["RequestRenderer", "ResponsesTable"]

  tab_hash = "rt"

  # When a new request is selected we redraw the current tab.
  layout_template = renderers.TabLayout.layout_template + """
<script>
grr.subscribe('request_table_select', function (task_id) {
    $("#{{unique|escapejs}}").data().state.task_id = task_id;
    $("#{{unique|escapejs}} li.ui-state-active a").click();
}, '{{unique|escapejs}}');
</script>
"""


class RequestRenderer(renderers.TemplateRenderer):
  """Display details of the request packet.

  Post Parameters:
    - task_id: The id of the request to display.
    - client_id: The client to show requests for.
  """

  layout_template = renderers.Template("""
{%if this.task %}
<div id="{{unique|escape}}" class="{{this.css_class}}">
 <h3>Request {{this.task.task_id|escape}}</h3>

<table id='{{ unique|escape }}' class="display">
<thead>
<tr>
  <th class="ui-state-default">Task</th>
</tr>
</thead>
<tbody>
 <tr>
   <td>
     <div class="default_view">{{ this.view|safe }}</div>
   </td>
 </tr>
</tbody>
</table>

</div>
{% endif %}
""")

  def Layout(self, request, response):
    client_id = request.REQ.get("client_id")
    task_id = request.REQ.get("task_id")

    # Make a local scheduler.
    scheduler_obj = scheduler.TaskScheduler()
    tasks = scheduler_obj.Query(client_id, task_id=task_id, token=request.token)

    if tasks:
      self.task = tasks[0]

      # Make an RDFValue from the task.
      rdf_task = aff4_grr.TaskSchedulerTask(self.task.SerializeToString())
      self.view = renderers.FindRendererForObject(rdf_task).RawHTML(request)

    return super(RequestRenderer, self).Layout(request, response)


class GrrRequestRenderer(renderers.RDFProtoRenderer):
  """Render a GRR Message."""
  ClassName = "GRRMessage"
  name = "GRR Request"

  # A map between the protobuf and the renderer for it.
  RENDERER_LOOKUP = {"GrrStatus": ("StatusProtoRenderer", "RDFProto")}

  def _GetProtoFromAction(self, client_action):
    return client_action.in_protobuf()

  def ArgRenderer(self, description, value):
    """Render the args field intelligently."""
    # The args field is a serialized protobuf destined for a client action. We
    # need to come up with a way to sensibly render this field:
    #
    # 1) Use the name of the field to find the client action this request is
    # going to.
    #
    # 2) Find the protobuf which can be used to decode it from the action's
    # in_protobuf.
    #
    # 3) Find the best renderer and RDFValue for this protobuf through a lookup
    # mapping.
    client_action = actions.ActionPlugin.classes.get(self.proxy.data.name)
    if client_action is None or client_action.in_protobuf is None:
      return self.Pre(description, value)

    # The args member is a serialized proto of this type:
    proto = self._GetProtoFromAction(client_action)
    proto.ParseFromString(value)

    proto_renderer, rdf_value_cls = self.RENDERER_LOOKUP.get(
        proto.__class__.__name__,
        ("RDFProtoRenderer", "RDFProto"))

    # Make an RDFValue to represent this protobuf.
    rdf_value = aff4.RDFValue.classes[rdf_value_cls](proto)

    # Now render this RDFValue using the specified renderer.
    renderer = self.classes[proto_renderer](rdf_value)

    return renderer.RawHTML()

  translator = dict(args=ArgRenderer,
                    auth_state=renderers.RDFProtoRenderer.Enum,
                    type=renderers.RDFProtoRenderer.Enum,
                    priority=renderers.RDFProtoRenderer.Enum)


class GrrResponseRenderer(GrrRequestRenderer):
  """A renderer for responses."""

  def ArgRenderer(self, description, value):
    """Render the args field intelligently."""
    # Status messages are special.
    if self.proxy.data.type == jobs_pb2.GrrMessage.STATUS:
      proto_cls = jobs_pb2.GrrStatus
    else:
      # Find the protobuf type by consulting the original request's
      # client_action.
      client_action = actions.ActionPlugin.classes.get(self.proxy.request.name)
      if client_action is None or client_action.out_protobuf is None:
        return self.Pre(description, value)

      proto_cls = client_action.out_protobuf

    # The args member is a serialized proto of this type:
    proto = proto_cls()
    proto.ParseFromString(value)

    proto_renderer, rdf_value_cls = self.RENDERER_LOOKUP.get(
        proto.__class__.__name__,
        ("RDFProtoRenderer", "RDFProto"))

    # Make an RDFValue to represent this protobuf.
    rdf_value = aff4.RDFValue.classes[rdf_value_cls](proto)

    # Now render this RDFValue using the specified renderer.
    renderer = self.classes[proto_renderer](rdf_value)

    return renderer.RawHTML()

  translator = GrrRequestRenderer.translator.copy()
  translator.update(args=ArgRenderer)


class StatusProtoRenderer(renderers.RDFProtoRenderer):
  """Render the status Proto."""

  translator = dict(status=renderers.RDFProtoRenderer.Enum)
