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


"""GUI elements to display general statistics."""


from grr.gui import renderers
from grr.lib import aff4
from grr.proto import analysis_pb2


class ShowStatistics(renderers.Splitter2WayVertical):
  """View various statistics."""

  description = "Show Statistics"
  behaviours = frozenset(["General"])

  left_renderer = "StatsTree"
  right_renderer = "ReportRenderer"


class ReportRenderer(renderers.TemplateRenderer):
  """A renderer for Statistic Reports."""

  layout_template = renderers.Template("""
{% if not this.delegated_renderer %}
<h1> Select a statistic to view.</h1>
{% endif %}
<div id="{{unique|escape}}"></div>
<script>
  grr.subscribe("tree_select", function(path) {
    grr.state.path = path
    grr.layout("{{renderer|escapejs}}", "{{id|escapejs}}");
  }, "{{unique|escapejs}}");
</script>
""")

  def Layout(self, request, response):
    """Delegate to a stats renderer if needed."""
    path = request.REQ.get("path", "")

    # Try and find the correct renderer to use.
    for cls in self.classes.values():
      try:
        if cls.category and cls.category == path:
          self.delegated_renderer = cls()

          # Render the renderer directly here
          self.delegated_renderer.Layout(request, response)
          break
      except AttributeError:
        pass

    return super(ReportRenderer, self).Layout(request, response)


class StatsTree(renderers.TreeRenderer):
  """Show all the available reports."""

  def GetStatsClasses(self):
    classes = []

    for cls in self.classes.values():
      if issubclass(cls, Report) and cls.category:
        classes.append(cls.category)

    classes.sort()
    return classes

  def RenderBranch(self, path, _):
    """Show all the stats available."""
    for category_name in self.GetStatsClasses():
      if category_name.startswith(path):
        elements = filter(None, category_name[len(path):].split("/"))

        # Do not allow duplicates
        if elements[0] in self: continue

        if len(elements) > 1:
          self.AddElement(elements[0], "branch")
        elif elements:
          self.AddElement(elements[0], "leaf")


class Report(renderers.TemplateRenderer):
  """This is the base of all Statistic Reports."""
  category = None


class PieChart(Report):
  """Display a pie chart."""

  layout_template = renderers.Template("""
{% if this.graph.data %}
  <h1>{{this.title|escape}}</h1>
  <div>
  {{this.description|escape}}
  </div>
  <div id="hover">Hover to show exact numbers.</div>
  <div id="{{unique|escape}}" class="grr_graph"></div>
  <script>

  var specs = [
    {% for data in this.graph.data %}
    {label: "{{data.label|escapejs}}", data: {{data.y_value|escapejs}} },
    {% endfor %}
  ];

  grr.subscribe("GeometryChange", function(id) {
    if(id != "{{id|escapejs}}") return;

    grr.fixHeight($("#{{unique|escapejs}}"));

    $.plot($("#{{unique|escapejs}}"), specs, {
      series: {
        pie: {
          show: true,
          label: {
            show: true,
            radius: 0.5,
            formatter: function(label, series){
              return ('<div style="font-size:8pt;' +
                      'text-align:center;padding:2px;color:white;">' +
                      label+'<br/>'+Math.round(series.percent)+'%</div>');
            },
            background: { opacity: 0.8 }
          }
        }
      },
      grid: {
        hoverable: true,
        clickable: true
      }
    });
    }, "{{unique|escapejs}}");

    $("#{{unique|escapejs}}").bind("plothover", function(event, pos, obj) {
      if (obj) {
        percent = parseFloat(obj.series.percent).toFixed(2);
        $("#hover").html('<span style="font-weight: bold; color: ' +
                         obj.series.color + '">' + obj.series.label + " " +
                         obj.series.data[0][1] + ' (' + percent + '%)</span>');
    }
  });

  grr.publish("GeometryChange", "{{id|escapejs}}");
  </script>
{% else %}
  <h1>No data Available</h1>
{% endif %}
""")


class OSBreakdown(PieChart):
  category = "/Clients/OS Breakdown/ 1 Day Active"
  title = "Operating system break down."
  description = "This plot shows what OS clients active within the last day."
  active_day = 1
  attribute_name = "OS_HISTOGRAM"

  def Layout(self, request, response):
    """Extract only the operating system type from the active histogram."""
    try:
      fd = aff4.FACTORY.Open("cron:/OSBreakDown", token=request.token)
      graph_series = fd.Get(getattr(fd.Schema, self.attribute_name))

      self.graph = analysis_pb2.Graph(title="Operating system break down.")
      for graph in graph_series:
        # Find the correct graph and merge the OS categories together
        if "%s day" % self.active_day in graph.title:
          for sample in graph.data:
            self.graph.data.add(label=sample.label,
                                y_value=sample.y_value)

          break
    except (IOError, TypeError):
      pass

    return super(OSBreakdown, self).Layout(request, response)


class VersionBreakdown(OSBreakdown):
  category = "/Clients/Version Breakdown/ 1 Day Active"
  title = "Operating system version break down."
  description = "This plot shows what OS clients active within the last day."
  active_day = 1
  attribute_name = "VERSION_HISTOGRAM"


class VersionBreakdown7(VersionBreakdown):
  category = "/Clients/Version Breakdown/ 7 Day Active"
  description = "What OS Version clients were active within the last week."
  active_day = 7


class VersionBreakdown14(VersionBreakdown):
  category = "/Clients/Version Breakdown/14 Day Active"
  description = "What OS Version clients were active within the last 2 weeks."
  active_day = 14


class VersionBreakdown30(VersionBreakdown):
  category = "/Clients/Version Breakdown/30 Day Active"
  description = "What OS Version clients were active within the last month."
  active_day = 30


class OSBreakdown7(OSBreakdown):
  category = "/Clients/OS Breakdown/ 7 Day Active"
  description = "Shows what OS clients were active within the last week."
  active_day = 7


class OSBreakdown14(OSBreakdown):
  category = "/Clients/OS Breakdown/14 Day Active"
  description = "Shows what OS clients were active within the last 2 weeks."
  active_day = 14


class OSBreakdown30(OSBreakdown):
  category = "/Clients/OS Breakdown/30 Day Active"
  description = "Shows what OS clients were active within the last month."
  active_day = 30


class LastActiveReport(OSBreakdown):
  """Display a histogram of last actives."""
  category = "/Clients/Last Active/ 1 Day"
  title = "One day Active Clients."
  description = """
This plot shows the number of clients active in the last day and how that number
evolves over time.
"""
  active_day = 1
  attribute_name = "VERSION_HISTOGRAM"

  layout_template = renderers.Template("""
{% if this.graphs %}
  <h1>{{this.title|escape}}</h1>
  <div id="{{unique|escape}}_click">
    {{this.description|escape}}
  </div>
  <div id="{{unique|escape}}" class="grr_graph"></div>
  <script>
  grr.fixHeight($("#{{unique|escapejs}}"));

  grr.subscribe("GeometryChange", function(id) {
    if(id != "{{id|escapejs}}") return;

    grr.fixHeight($("#{{unique|escapejs}}"));
  }, "{{unique|escapejs}}");

      var specs = [];

  {% for graph in this.graphs %}
    specs.push({
      label: "{{graph.title|escapejs}}",
      data: [
  {% for series in graph.data %}
        [ {{series.x_value|escapejs}}, {{series.y_value|escapejs}}],
  {% endfor %}
      ],
    });
  {% endfor %}

    var options = {
      xaxis: {mode: "time",
              timeformat: "%y/%m/%d"},
      lines: {show: true},
      points: {show: true},
      zoom: {interactive: true},
      pan: {interactive: true},
      grid: {clickable: true, autohighlight: true},
    };

    var placeholder = $("#{{unique|escapejs}}");
    var plot = $.plot(placeholder, specs, options);

    placeholder.bind("plotclick", function(event, pos, item) {
      if (item) {
        var date = new Date(item.datapoint[0]);
        $("#{{unique|escapejs}}_click").text("On " + date.toDateString() +
          ", there were " + item.datapoint[1] + " " + item.series.label +
          " systems.");
      };
    });
  </script>
{% else %}
  <h1>No data Available</h1>
{% endif %}
""")

  def Layout(self, request, response):
    """Show how the last active breakdown evolves over time."""
    try:
      fd = aff4.FACTORY.Open("cron:/OSBreakDown", token=request.token,
                             age=aff4.ALL_TIMES)
      categories = {}
      for graph_series in fd.GetValuesForAttribute(
          getattr(fd.Schema, self.attribute_name)):
        for graph in graph_series.data:
          # Find the correct graph and merge the OS categories together
          if "%s day" % self.active_day in graph.title:
            for sample in graph.data:
              # Provide the time in js timestamps (millisecond since the epoch)
              categories.setdefault(sample.label, []).append(
                  (graph_series.age/1000, sample.y_value))

            break

      self.graphs = []
      for k, v in categories.items():
        graph = analysis_pb2.Graph(title=k)
        for x, y in v:
          graph.data.add(x_value=x, y_value=y)

        self.graphs.append(graph)
    except IOError:
      pass

    return super(LastActiveReport, self).Layout(request, response)


class Last7DayActives(LastActiveReport):
  category = "/Clients/Last Active/ 7 Day"
  title = "One week active clients."
  description = """
This plot shows the number of clients active in the last week and how that
number evolves over time.
"""
  active_day = 7


class Last30DayActives(LastActiveReport):
  category = "/Clients/Last Active/30 Day"
  title = "One month active clients."
  description = """
This plot shows the number of clients active in the last 30 days and how that
number evolves over time.
"""
  active_day = 30
