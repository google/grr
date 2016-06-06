#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Inspect current state of in flight flows.

This module provides a UI for inspecting the messages outstanding for a client
and how they are progressing. This helps the user understand the status and
progress of existing flows.
"""




from grr.gui import renderers
from grr.gui.plugins import fileview
from grr.gui.plugins import semantic
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib.aff4_objects import stats as aff4_stats
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows


class ClientLoadView(renderers.TemplateRenderer):
  """Show client load information."""
  description = "Current Client Load"
  behaviours = frozenset(["HostAdvanced"])

  layout_template = renderers.Template("""
<div id="{{unique|escape}}" class="padded">

<h3>Client load information for: {{this.client_id|escape}}</h3>
<br/>

<h4>Actions in progress</h4>
{% if this.client_actions %}

  <table class="table table-condensed table-striped">
  <thead>
    <th>Action</th>
    <th>Priority</th>
    <th>Lease time left</th>
    <th>Parent flow</th>
  </thead>
  <tbody>
  {% for action in this.client_actions %}
  <tr>
    <td>{{action.name|escape}}</td>
    <td>{{action.priority|escape}}</td>
    <td>{{action.lease_time_left|escape}}</td>
    <td>
      <a class="flow_details_link" flow_urn="{{action.parent_flow.urn|escape}}">
        {{action.parent_flow.name|escape}}
      </a>
    </td>
  </tr>
  {% endfor %}
  </tbody>
  </table>
{% else %}
No actions currently in progress.
{% endif %}

<br/>

<h4>Client CPU load
{% if this.stats_timestamp %} (as of {{this.stats_timestamp|escape}})
{% endif %}</h4>
<div id="client_cpu_{{unique|escape}}"
  style="width: 100%; height: 300px"></div>
<br/>

<br/>

<h4>Client IO load
{% if this.stats_timestamp %} (as of {{this.stats_timestamp|escape}})
{% endif %}</h4>
<h5>Bytes</h5>
<div id="client_io_bytes_{{unique|escape}}"
  style="width: 100%; height: 300px">
</div>

<h5>Number of operations</h5>
<div id="client_io_count_{{unique|escape}}"
  style="width: 100%; height: 300px"></div>

<div id="FlowDetails_{{unique|escape}}" class="panel details-right-panel hide">
  <div class="padded">
    <button id="FlowDetailsClose_{{unique|escape}}" class="close">
      &times;
    </button>
  </div>
  <div id="FlowDetailsContent_{{unique|escape}}"></div>
</div>

</div>
""")

  def Layout(self, request, response):
    self.client_id = rdf_client.ClientURN(request.REQ.get("client_id"))
    self.client_actions = []

    current_time = rdfvalue.RDFDatetime().Now()
    leased_tasks = []
    with queue_manager.QueueManager(token=request.token) as manager:
      tasks = manager.Query(self.client_id.Queue(), limit=1000)
      for task in tasks:
        if task.eta > current_time:
          leased_tasks.append(task)

    flows_map = {}
    for flow_obj in aff4.FACTORY.MultiOpen(
        set(task.session_id for task in leased_tasks),
        mode="r",
        token=request.token):
      flows_map[flow_obj.urn] = flow_obj

    for task in leased_tasks:
      flow_obj = flows_map.get(task.session_id, None)
      if flow_obj:
        self.client_actions.append(dict(name=task.name,
                                        priority=str(task.priority),
                                        lease_time_left=str(task.eta -
                                                            current_time),
                                        parent_flow=dict(name=flow_obj.Name(),
                                                         urn=flow_obj.urn)))

    now = rdfvalue.RDFDatetime().Now()
    hour_before_now = now - rdfvalue.Duration("1h")

    stats_urn = self.client_id.Add("stats")
    stats_obj = aff4.FACTORY.Create(
        stats_urn,
        aff4_stats.ClientStats,
        mode="r",
        age=(hour_before_now.AsMicroSecondsFromEpoch(),
             now.AsMicroSecondsFromEpoch()),
        token=request.token)
    client_stats_list = list(stats_obj.GetValuesForAttribute(
        stats_obj.Schema.STATS))

    cpu_samples = []
    io_samples = []
    for client_stats in client_stats_list:
      cpu_samples.extend(client_stats.cpu_samples)
      io_samples.extend(client_stats.io_samples)

    cpu_samples = sorted(cpu_samples, key=lambda x: x.timestamp)
    io_samples = sorted(io_samples, key=lambda x: x.timestamp)

    if client_stats_list:
      client_stats = client_stats_list[-1].Copy()
    else:
      client_stats = rdf_client.ClientStats()

    client_stats.cpu_samples = cpu_samples
    client_stats.io_samples = io_samples

    if client_stats.cpu_samples:
      self.stats_timestamp = client_stats.cpu_samples[-1].timestamp
    elif client_stats.io_samples:
      self.stats_timestamp = client_stats.io_samples[-1].timestamp
    else:
      self.stats_timestamp = None

    user_cpu_data = []
    system_cpu_data = []
    for sample in client_stats.cpu_samples:
      if sample.timestamp > hour_before_now and sample.timestamp < now:
        user_cpu_data.append((sample.timestamp.AsSecondsFromEpoch() * 1000,
                              sample.user_cpu_time))
        system_cpu_data.append((sample.timestamp.AsSecondsFromEpoch() * 1000,
                                sample.system_cpu_time))

    read_bytes_data = []
    write_bytes_data = []
    read_count_data = []
    write_count_data = []
    for sample in client_stats.io_samples:
      if sample.timestamp > hour_before_now and sample.timestamp < now:
        read_bytes_data.append((sample.timestamp.AsSecondsFromEpoch() * 1000,
                                sample.read_bytes))
        write_bytes_data.append((sample.timestamp.AsSecondsFromEpoch() * 1000,
                                 sample.write_bytes))
        read_count_data.append((sample.timestamp.AsSecondsFromEpoch() * 1000,
                                sample.read_count))
        write_count_data.append((sample.timestamp.AsSecondsFromEpoch() * 1000,
                                 sample.write_count))

    response = super(ClientLoadView, self).Layout(request, response)
    return self.CallJavascript(response,
                               "ClientLoadView.Layout",
                               user_cpu_data=user_cpu_data,
                               system_cpu_data=system_cpu_data,
                               read_bytes_data=read_bytes_data,
                               write_bytes_data=write_bytes_data,
                               read_count_data=read_count_data,
                               write_count_data=write_count_data)


class DebugClientRequestsView(renderers.Splitter2Way):
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

  post_parameters = ["client_id"]

  def __init__(self, **kwargs):
    super(RequestTable, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn("Status",
                                           renderer=semantic.IconRenderer,
                                           width="40px"))

    self.AddColumn(semantic.RDFValueColumn("ID",
                                           renderer=renderers.ValueRenderer))
    self.AddColumn(semantic.RDFValueColumn("Due"))
    self.AddColumn(semantic.RDFValueColumn("Flow", width="70%"))
    self.AddColumn(semantic.RDFValueColumn("Client Action", width="30%"))

  def BuildTable(self, start_row, end_row, request):
    client_id = rdf_client.ClientURN(request.REQ.get("client_id"))
    now = rdfvalue.RDFDatetime().Now()

    # Make a local QueueManager.
    manager = queue_manager.QueueManager(token=request.token)

    for i, task in enumerate(manager.Query(client_id, limit=end_row)):
      if i < start_row:
        continue

      difference = now - task.eta
      if difference > 0:
        self.AddCell(i,
                     "Status",
                     dict(icon="stock_yes",
                          description="Available for Lease"))
      else:
        self.AddCell(i,
                     "Status",
                     dict(icon="clock",
                          description="Leased for %s Seconds" %
                          (difference / 1e6)))

      self.AddCell(i, "ID", task.task_id)
      self.AddCell(i, "Flow", task.session_id)
      self.AddCell(i, "Due", rdfvalue.RDFDatetime(task.eta))
      self.AddCell(i, "Client Action", task.name)

  def Layout(self, request, response):
    response = super(RequestTable, self).Layout(request, response)
    return self.CallJavascript(response, "RequestTable.Layout")


class ResponsesTable(renderers.TableRenderer):
  """Show all outstanding requests for a client.

  Post Parameters:
    - client_id: The client to show the flows for.
    - task_id: The id of the request to display.
  """

  post_parameters = ["client_id", "task_id"]

  def __init__(self, **kwargs):
    super(ResponsesTable, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn("Task ID"))
    self.AddColumn(semantic.RDFValueColumn("Response",
                                           renderer=fileview.GrrMessageRenderer,
                                           width="100%"))

  def BuildTable(self, start_row, end_row, request):
    """Builds the table."""
    client_id = rdf_client.ClientURN(request.REQ.get("client_id"))

    task_id = "task:%s" % request.REQ.get("task_id", "")

    # Make a local QueueManager.
    manager = queue_manager.QueueManager(token=request.token)

    # This is the request.
    request_messages = manager.Query(client_id, task_id=task_id)

    if not request_messages:
      return

    request_message = request_messages[0]

    state_queue = request_message.session_id.Add("state/request:%08X" %
                                                 request_message.request_id)

    predicate_pre = (
        manager.FLOW_RESPONSE_PREFIX + "%08X" % request_message.request_id)
    # Get all the responses for this request.
    for i, (predicate, serialized_message,
            _) in enumerate(data_store.DB.ResolvePrefix(state_queue,
                                                        predicate_pre,
                                                        limit=end_row,
                                                        token=request.token)):

      message = rdf_flows.GrrMessage(serialized_message)

      if i < start_row:
        continue
      if i > end_row:
        break

      # Tie up the request to each response to make it easier to render.
      rdf_response_message = rdf_flows.GrrMessage(message)
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

  def Layout(self, request, response):
    response = super(RequestTabs, self).Layout(request, response)
    return self.CallJavascript(response, "RequestTabs.Layout")


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

    client_id = rdf_client.ClientURN(request.REQ.get("client_id"))
    task_id = "task:" + request.REQ.get("task_id")

    # Make a local QueueManager.
    manager = queue_manager.QueueManager(token=request.token)
    msgs = manager.Query(client_id, task_id=task_id)
    if msgs:
      self.msg = msgs[0]
      self.view = semantic.FindRendererForObject(self.msg).RawHTML(request)

    return super(RequestRenderer, self).Layout(request, response)
