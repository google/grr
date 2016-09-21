#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""Inspect current state of in flight flows.

This module provides a UI for inspecting the messages outstanding for a client
and how they are progressing. This helps the user understand the status and
progress of existing flows.
"""




from grr.gui import renderers
from grr.lib import aff4
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib.aff4_objects import stats as aff4_stats
from grr.lib.rdfvalues import client as rdf_client


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

    current_time = rdfvalue.RDFDatetime.Now()
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
        self.client_actions.append(
            dict(
                name=task.name,
                priority=str(task.priority),
                lease_time_left=str(task.eta - current_time),
                parent_flow=dict(
                    name=flow_obj.Name(), urn=flow_obj.urn)))

    now = rdfvalue.RDFDatetime.Now()
    hour_before_now = now - rdfvalue.Duration("1h")

    stats_urn = self.client_id.Add("stats")
    stats_obj = aff4.FACTORY.Create(
        stats_urn,
        aff4_stats.ClientStats,
        mode="r",
        age=(hour_before_now.AsMicroSecondsFromEpoch(),
             now.AsMicroSecondsFromEpoch()),
        token=request.token)
    client_stats_list = list(
        stats_obj.GetValuesForAttribute(stats_obj.Schema.STATS))

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
    return self.CallJavascript(
        response,
        "ClientLoadView.Layout",
        user_cpu_data=user_cpu_data,
        system_cpu_data=system_cpu_data,
        read_bytes_data=read_bytes_data,
        write_bytes_data=write_bytes_data,
        read_count_data=read_count_data,
        write_count_data=write_count_data)
