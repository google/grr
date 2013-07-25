#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""Inspect current state of in flight flows.

This module provides a UI for inspecting the messages outstanding for a client
and how they are progressing. This helps the user understand the status and
progress of existing flows.
"""




from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.lib import data_store
from grr.lib import flow_runner
from grr.lib import rdfvalue
from grr.lib import scheduler


class InspectView(renderers.Splitter2Way):
  """Inspect outstanding requests for the client."""
  description = "Debug Client Requests"
  behaviours = frozenset(["HostAdvanced"])

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
      var task_id = node.find("span[rdfvalue]").attr("rdfvalue");
      grr.publish("request_table_select", task_id);
    };
  }, '{{ unique|escapejs }}');
</script>
"""

  post_parameters = ["client_id"]

  def __init__(self, **kwargs):
    super(RequestTable, self).__init__(**kwargs)
    self.AddColumn(renderers.RDFValueColumn(
        "Status", renderer=renderers.IconRenderer, width="40px"))

    self.AddColumn(renderers.RDFValueColumn(
        "ID", renderer=renderers.ValueRenderer))
    self.AddColumn(renderers.RDFValueColumn("Due"))
    self.AddColumn(renderers.RDFValueColumn("Flow", width="70%"))
    self.AddColumn(renderers.RDFValueColumn("Client Action", width="30%"))

  def BuildTable(self, start_row, end_row, request):
    client_id = rdfvalue.ClientURN(request.REQ.get("client_id"))
    now = rdfvalue.RDFDatetime().Now()

    # Make a local scheduler.
    scheduler_obj = scheduler.TaskScheduler()

    for i, task in enumerate(scheduler_obj.Query(client_id, limit=end_row,
                                                 token=request.token)):
      if i < start_row:
        continue

      difference = now - task.eta
      if difference > 0:
        self.AddCell(i, "Status", dict(
            icon="stock_yes", description="Available for Lease"))
      else:
        self.AddCell(i, "Status", dict(
            icon="clock",
            description="Leased for %s Seconds" % (difference / 1e6)))

      self.AddCell(i, "ID", task.task_id)
      self.AddCell(i, "Flow", task.session_id)
      self.AddCell(i, "Due", rdfvalue.RDFDatetime(task.eta))
      self.AddCell(i, "Client Action", task.name)


class ResponsesTable(renderers.TableRenderer):
  """Show all outstanding requests for a client.

  Post Parameters:
    - client_id: The client to show the flows for.
    - task_id: The id of the request to display.
  """

  post_parameters = ["client_id", "task_id"]

  def __init__(self, **kwargs):
    super(ResponsesTable, self).__init__(**kwargs)
    self.AddColumn(renderers.RDFValueColumn("Task ID"))
    self.AddColumn(renderers.RDFValueColumn(
        "Response", renderer=fileview.GrrMessageRenderer, width="100%"))

  def BuildTable(self, start_row, end_row, request):
    """Builds the table."""
    client_id = rdfvalue.ClientURN(request.REQ.get("client_id"))

    task_id = "task:%s" % request.REQ.get("task_id", "")

    # This is the request.
    scheduler_obj = scheduler.TaskScheduler()

    request_messages = scheduler_obj.Query(
        client_id, task_id=task_id, token=request.token)

    if not request_messages: return

    request_message = request_messages[0]

    state_queue = (flow_runner.FlowManager.FLOW_STATE_TEMPLATE %
                   request_message.session_id)

    predicate_re = (flow_runner.FlowManager.FLOW_RESPONSE_PREFIX %
                    request_message.request_id) + ".*"

    # Get all the responses for this request.
    for i, (predicate, message, _) in enumerate(data_store.DB.ResolveRegex(
        state_queue, predicate_re, decoder=rdfvalue.GrrMessage, limit=end_row,
        token=request.token)):

      if i < start_row:
        continue
      if i > end_row:
        break

      # Tie up the request to each response to make it easier to render.
      rdf_response_message = rdfvalue.GrrMessage(message)
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
    $("#{{unique|escapejs}} li.active a").click();
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
{%if this.msg %}
<div id="{{unique|escape}}" class="{{this.css_class}}">
 <h3>Request {{this.msg.task_id|escape}}</h3>

<table id='{{ unique|escape }}' class="table table-condensed table-bordered">
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
    """Layout."""
    if request.REQ.get("task_id") is None:
      return

    client_id = rdfvalue.ClientURN(request.REQ.get("client_id"))
    task_id = "task:" + request.REQ.get("task_id")

    # Make a local scheduler.
    scheduler_obj = scheduler.TaskScheduler()
    msgs = scheduler_obj.Query(client_id, task_id=task_id, token=request.token)
    if msgs:
      self.msg = msgs[0]
      self.view = renderers.FindRendererForObject(
          self.msg).RawHTML(request)

    return super(RequestRenderer, self).Layout(request, response)
