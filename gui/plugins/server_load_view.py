#!/usr/bin/env python
"""Show server load information.

This module provides a monitoring UI for inspecting current state of a server
part of GRR deployment.
"""



import re


from grr.gui import renderers
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib.aff4_objects import stats_store as stats_store_lib


class ScalarGraphRenderer(renderers.TemplateRenderer):
  """Renderer for graphs of 1 or more scalar values."""

  layout_template = renderers.Template("""
<h4>{{this.graph.title|escape}}</h4>

<div id="{{this.graph.name|escape}}_{{unique|escape}}" style="width:100%; height: 300px">
</div>
""")

  def __init__(self, name=None, title=None, y_axis_label=None, **kwargs):
    self.graph = dict(title=title,
                      name=name,
                      y_axis_label=y_axis_label,
                      series=[])
    super(ScalarGraphRenderer, self).__init__(**kwargs)

  def TimeSeriesToPlainObject(self, series):
    if series is None:
      return []

    result = []
    for timestamp, value in series.iteritems():
      result.append((timestamp.value / 1e6, value))

    return result

  def AddTimeSeries(self, time_series, title=None):
    self.graph["series"].append(
        dict(title=title,
             data=self.TimeSeriesToPlainObject(time_series)))

  def Layout(self, request, response):
    response = super(ScalarGraphRenderer, self).Layout(request, response)
    return self.CallJavascript(response, "ScalarGraphRenderer.Layout",
                               graph=self.graph)


class SystemHealthIndicatorRenderer(renderers.TemplateRenderer):
  """Renderer for a system health indicator."""

  layout_template = renderers.Template("""
<tr>
<td class="span1">
  {% if this.status != this.NO_DATA %}
  <img class="grr-icon-small" src="/static/images/{{this.status|escape}}" />
  {% else %}
  <nobr>(no data)</nobr>
  {% endif %}
</td>

<td>
{{this.title|escape}}
</td>
</tr>
""")

  NORMAL = "online.png"
  WARNING = "online-1d.png"
  DANGER = "offline.png"
  NO_DATA = None

  def __init__(self, title=None, status=None, **kwargs):
    if not title:
      raise ValueError("title has to be specified")

    self.title = title
    self.status = status

    super(SystemHealthIndicatorRenderer, self).__init__(**kwargs)


class ServerLoadView(renderers.TemplateRenderer):
  """Show server load information."""
  description = "Server Load"
  behaviours = frozenset(["GeneralAdvanced"])

  layout_template = renderers.Template("""

<div class="padded">
<div class="well">

<table class="table table-condensed no-bottom-margin">
<thead>
  <th colspan="2">System Health</th>
</thead>
<tbody>
{% for indicator in this.indicators %}
{{indicator|safe}}
{% endfor %}
</tbody>
</table>

</div>
</div>

<div class="pull-right" style="padding-right: 1em">

<div class="btn-toolbar" id="durations_{{unique|escape}}">
  <div class="btn-group">
  {% for duration in this.DURATION_CHOICES %}
    <button name="{{duration|escape}}" class="btn {% if this.duration == duration %}btn-primary disabled{% endif %}">{{duration|escape}}</button>
  {% endfor %}
  </div>
</div>

</div>  <!-- pull-right -->

<div id="{{unique|escape}}" class="padded">

{% for graph in this.graphs %}

{{graph|safe}}

{% endfor %}

</div>
""")

  DURATION_CHOICES = [rdfvalue.Duration("1h"),
                      rdfvalue.Duration("3h"),
                      rdfvalue.Duration("6h"),
                      rdfvalue.Duration("12h"),
                      rdfvalue.Duration("1d")]

  RATE_WINDOW = rdfvalue.Duration("10m")

  def ReadStatsStoreData(self, regex, time_range, token=None):
    stats_store = aff4.FACTORY.Create(
        stats_store_lib.StatsStore.DATA_STORE_ROOT,
        aff4_type="StatsStore", mode="rw", token=token)

    process_ids = stats_store.ListUsedProcessIds()
    filtered_ids = [pid for pid in process_ids
                    if re.match(regex, pid)]
    return stats_store.MultiReadStats(
        process_ids=filtered_ids, timestamp=time_range)

  def _ApplyPathToQuery(self, query, path):
    for path_item in path:
      if path_item == ":all":
        query = query.InAll()
      else:
        query = query.In(path_item)

    return query

  def QueryValue(self, data, path):
    query = stats_store_lib.StatsStoreDataQuery(data)
    query = self._ApplyPathToQuery(query, path)
    return query.TakeValue().Resample(
        rdfvalue.Duration("30s")).FillMissing(rdfvalue.Duration("10m"))

  def QueryDistributionSum(self, data, path):
    query = stats_store_lib.StatsStoreDataQuery(data)
    query = self._ApplyPathToQuery(query, path)
    return query.TakeDistributionSum().Resample(
        rdfvalue.Duration("30s")).FillMissing(rdfvalue.Duration("10m"))

  def QueryDistributionCount(self, data, path):
    query = stats_store_lib.StatsStoreDataQuery(data)
    query = self._ApplyPathToQuery(query, path)
    return query.TakeDistributionCount().Resample(
        rdfvalue.Duration("30s")).FillMissing(rdfvalue.Duration("10m"))

  def Layout(self, request, response):
    self.duration = rdfvalue.Duration(request.REQ.get("duration", "1h"))

    now = rdfvalue.RDFDatetime().Now()
    time_range = ((now - self.duration).AsMicroSecondsFromEpoch(),
                  now.AsMicroSecondsFromEpoch())

    frontend_stats = self.ReadStatsStoreData("frontend.*", time_range,
                                             token=request.token)
    enroller_stats = self.ReadStatsStoreData("enroller.*", time_range,
                                             token=request.token)
    worker_stats = self.ReadStatsStoreData("worker.*", time_range,
                                           token=request.token)

    # System health indicators
    ten_mins_before = now - rdfvalue.Duration("10m", now)
    self.indicators = []

    active_count = self.QueryValue(
        frontend_stats,
        ["frontend.*", "frontend_active_count", ":all"]).InTimeRange(
            ten_mins_before, now).AggregateViaSum().Mean()
    max_active_count = self.QueryValue(
        frontend_stats,
        ["frontend.*", "frontend_max_active_count"]).InTimeRange(
            ten_mins_before, now).AggregateViaSum().Mean()

    if max_active_count > 0:
      ratio = float(active_count) / max_active_count
      if ratio > 0.7:
        frontend_status = SystemHealthIndicatorRenderer.DANGER
      elif ratio > 0.35:
        frontend_status = SystemHealthIndicatorRenderer.WARNING
      else:
        frontend_status = SystemHealthIndicatorRenderer.NORMAL
    else:
      frontend_status = SystemHealthIndicatorRenderer.NO_DATA

    indicator = SystemHealthIndicatorRenderer(
        title="Frontends load",
        status=frontend_status)
    self.indicators.append(indicator.RawHTML(request))

    # Detailed graphs
    self.graphs = []

    #
    # Fronted graphs
    # --------------
    #
    self.graphs.append("<br/><br/><hr/><p class=lead>Frontend "
                       "(%d instances)</p>" % len(frontend_stats.keys()))

    # Frontend handled vs throttled graph
    graph = ScalarGraphRenderer(name="frontend_handled_vs_throttled",
                                title="Frontend handled vs throttled rate",
                                y_axis_label="Count")
    graph.AddTimeSeries(
        self.QueryDistributionCount(frontend_stats,
                                    ["frontend.*",
                                     "frontend_request_latency", ":all"]).
        AggregateViaSum().Rate(self.RATE_WINDOW).ts,
        title="Request Count")
    graph.AddTimeSeries(
        self.QueryValue(frontend_stats,
                        ["frontend.*",
                         "grr_frontendserver_handle_throttled_num"])
        .AggregateViaSum().Rate(self.RATE_WINDOW).ts,
        title="Throttled")
    self.graphs.append(graph.RawHTML(request))

    # Frontend request latency
    graph = ScalarGraphRenderer(name="frontend_request_latency",
                                title="Frontend request latency rate",
                                y_axis_label="Count")
    graph.AddTimeSeries(
        self.QueryDistributionSum(frontend_stats,
                                  ["frontend.*",
                                   "frontend_request_latency",
                                   ":all"]).
        AggregateViaSum().Rate(self.RATE_WINDOW).ts,
        title="Latency")
    self.graphs.append(graph.RawHTML(request))

    # Frontend active tasks count
    graph = ScalarGraphRenderer(name="frontend_active_count",
                                title="Frontend active tasks count",
                                y_axis_label="Count")
    graph.AddTimeSeries(
        self.QueryValue(frontend_stats,
                        ["frontend.*", "frontend_active_count", ":all"]).
        AggregateViaSum().ts,
        title="Count")
    self.graphs.append(graph.RawHTML(request))

    #
    # Worker graphs
    # -------------
    #
    self.graphs.append("<br/><br/><hr/><p class=lead>Workers "
                       "(%d instances)</p>" % len(worker_stats.keys()))

    # Worker successful vs failed flows
    graph = ScalarGraphRenderer(name="worker_flow_success_vs_failures",
                                title="Worker successful vs failed flows rate",
                                y_axis_label="Count")
    graph.AddTimeSeries(
        self.QueryValue(worker_stats,
                        ["worker.*", "grr_flow_completed_count"]).
        AggregateViaSum().Rate(self.RATE_WINDOW).ts,
        title="Successes")
    graph.AddTimeSeries(
        self.QueryValue(worker_stats,
                        ["worker.*", "grr_flow_errors"]).
        AggregateViaSum().Rate(self.RATE_WINDOW).ts,
        title="Failures")
    self.graphs.append(graph.RawHTML(request))

    # Worker latency
    graph = ScalarGraphRenderer(name="worker_latency",
                                title="Worker latency rate",
                                y_axis_label="Latency")
    graph.AddTimeSeries(
        self.QueryDistributionSum(worker_stats,
                                  ["worker.*", "grr_threadpool_working_time"]).
        AggregateViaSum().Rate(self.RATE_WINDOW).ts,
        title="Latency")
    self.graphs.append(graph.RawHTML(request))

    # Worker threadpool queueing time
    graph = ScalarGraphRenderer(name="worker_threadpool_queueing_time",
                                title="Worker threadpool queueing time rate",
                                y_axis_label="Time")
    graph.AddTimeSeries(
        self.QueryDistributionSum(worker_stats,
                                  ["worker.*", "grr_threadpool_queueing_time"]).
        AggregateViaSum().Rate(self.RATE_WINDOW).ts,
        title="Time")
    self.graphs.append(graph.RawHTML(request))

    # Client crashes
    graph = ScalarGraphRenderer(name="worker_client_crashes",
                                title="Worker client crashes rate",
                                y_axis_label="Count")
    graph.AddTimeSeries(
        self.QueryValue(worker_stats,
                        ["worker.*", "grr_client_crashes"]).
        AggregateViaSum().Rate(self.RATE_WINDOW).ts,
        title="Time")
    self.graphs.append(graph.RawHTML(request))

    #
    # Enrollers graphs
    # -------------
    #
    self.graphs.append("<br/><br/><hr/><p class=lead>Enrollers "
                       "(%d instances)</p>" % len(enroller_stats.keys()))

    # Successful vs failed enrollments
    graph = ScalarGraphRenderer(name="enroller_success_vs_failures",
                                title="Successful vs failed enrollments rate",
                                y_axis_label="Count")
    graph.AddTimeSeries(
        self.QueryValue(enroller_stats,
                        ["enroller.*", "grr_flow_completed_count"]).
        AggregateViaSum().Rate(self.RATE_WINDOW).ts,
        title="Successes")
    graph.AddTimeSeries(
        self.QueryValue(enroller_stats,
                        ["enroller.*", "grr_flow_errors"]).
        AggregateViaSum().Rate(self.RATE_WINDOW).ts,
        title="Failures")
    self.graphs.append(graph.RawHTML(request))

    # Enrollments latency
    graph = ScalarGraphRenderer(name="enroller_enrollment_latency",
                                title="Enroller enrollment latency rate",
                                y_axis_label="Latency")
    graph.AddTimeSeries(
        self.QueryDistributionSum(enroller_stats,
                                  ["enroller.*",
                                   "frontend_request_latency",
                                   ":all"]).
        AggregateViaSum().Rate(self.RATE_WINDOW).ts,
        title="Latency")
    self.graphs.append(graph.RawHTML(request))

    response = super(ServerLoadView, self).Layout(request, response)
    return self.CallJavascript(response, "ServerLoadView.Layout",
                               renderer=self.__class__.__name__)
