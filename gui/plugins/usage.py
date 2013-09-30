#!/usr/bin/env python
"""GUI elements to display usage statistics."""


from grr.gui import renderers
from grr.gui.plugins import statistics
from grr.lib import aff4
from grr.lib import rdfvalue


class MostActiveUsers(statistics.PieChart):
  category = "/Server/User Breakdown/ 7 Day"
  description = "Active User actions in the last week."

  def Layout(self, request, response):
    """Filter the last week of user actions."""
    try:
      # TODO(user): Replace with Duration().
      now = int(rdfvalue.RDFDatetime().Now())
      fd = aff4.FACTORY.Open("aff4:/audit/log", aff4_type="VersionedCollection",
                             token=request.token)

      counts = {}
      for event in fd.GenerateItems(
          timestamp=(now - 7 * 24 * 60 * 60 * 1000000, now)):
        counts.setdefault(event.user, 0)
        counts[event.user] += 1

      self.graph = rdfvalue.Graph(title="User activity breakdown.")
      for user, count in counts.items():
        self.graph.Append(label=user, y_value=count)
    except IOError:
      pass
    return super(MostActiveUsers, self).Layout(request, response)


class StackChart(statistics.Report):
  """Display category data in stacked histograms."""

  layout_template = renderers.Template("""
<div class="padded">
{% if this.data %}
  <h3>{{this.title|escape}}</h3>
  <div>
  {{this.description|escape}}
  </div>
  <div id="hover">Hover to show exact numbers.</div>
  <div id="{{unique|escape}}" class="grr_graph"></div>
  <script>

  var specs = {{this.data|safe}};

  $("#{{unique|escapejs}}").resize(function () {
    $("#{{unique|escapejs}}").html("");
    $.plot($("#{{unique|escapejs}}"), specs, {
      series: {
        stack: true,
        bars: {
          show: true,
          barWidth: 0.6,
        },
        label: {
          show: true,
          radius: 0.5,
        },
        background: { opacity: 0.8 },
      },
      grid: {
        hoverable: true,
        clickable: true
      },
    });
  });

  $("#{{unique|escapejs}}").bind("plothover", function(event, pos, obj) {
    if (obj) {
      grr.test_obj = obj;
      $("#hover").html(
        '<span style="font-weight: bold; color: ' +
        obj.series.color + '"> <b>' + obj.series.label + "</b>: " +
        (obj.datapoint[1] - obj.datapoint[2]) + '</span>');
    }
  });

  $("#{{unique|escapejs}}").resize();
  </script>
{% else %}
  <h3>No data Available</h3>
{% endif %}
</div>
""")


class UserActivity(StackChart):
  """Display user activity by week."""
  category = "/Server/User Breakdown/Activity"
  description = "Number of flows ran by each user over the last few weeks."

  WEEKS = 10

  def Layout(self, request, response):
    """Filter the last week of user actions."""
    try:
      # TODO(user): Replace with Duration().
      now = int(rdfvalue.RDFDatetime().Now())
      week_duration = 7 * 24 * 60 * 60 * 1000000

      fd = aff4.FACTORY.Open("aff4:/audit/log", aff4_type="VersionedCollection",
                             token=request.token)

      self.user_activity = {}

      for week in range(self.WEEKS):
        start = now - week * week_duration

        for event in fd.GenerateItems(timestamp=(start, start + week_duration)):
          self.weekly_activity = self.user_activity.setdefault(
              event.user, [[x, 0] for x in range(-self.WEEKS, 0, 1)])
          self.weekly_activity[-week][1] += 1

      self.data = []
      for user, data in self.user_activity.items():
        self.data.append(dict(label=user, data=data))

      self.data = renderers.JsonDumpForScriptContext(self.data)

    except IOError:
      pass

    return super(UserActivity, self).Layout(request, response)


class FlowsUsed(StackChart):
  """Display Flows issued by week."""
  category = "/Server/Flows/Activity"
  description = "Number of flows issued over the last few weeks."

  WEEKS = 10

  def Layout(self, request, response):
    """Filter the last week of flows."""
    try:
      # TODO(user): Replace with Duration().
      now = int(rdfvalue.RDFDatetime().Now())
      week_duration = 7 * 24 * 60 * 60 * 1000000

      fd = aff4.FACTORY.Open("aff4:/audit/log", aff4_type="VersionedCollection",
                             token=request.token)

      self.flow_activity = {}

      for week in range(self.WEEKS):
        start = now - week * week_duration

        for event in fd.GenerateItems(timestamp=(start, start + week_duration)):
          self.weekly_activity = self.flow_activity.setdefault(
              event.flow, [[x, 0] for x in range(-self.WEEKS, 0, 1)])
          self.weekly_activity[-week][1] += 1

      self.data = []
      for flow, data in self.flow_activity.items():
        self.data.append(dict(label=flow, data=data))

      self.data = renderers.JsonDumpForScriptContext(self.data)

    except IOError:
      pass

    return super(FlowsUsed, self).Layout(request, response)


class ClientActivity(StackChart):
  """Display client activity by week."""
  category = "/Server/Clients/Activity"
  description = ("Number of flows issued against each client over the "
                 "last few weeks.")

  WEEKS = 10

  def Layout(self, request, response):
    """Filter the last week of flows."""
    try:
      # TODO(user): Replace with Duration().
      now = int(rdfvalue.RDFDatetime().Now())
      week_duration = 7 * 24 * 60 * 60 * 1000000

      fd = aff4.FACTORY.Open("aff4:/audit/log", aff4_type="VersionedCollection",
                             token=request.token)

      self.client_activity = {}

      for week in range(self.WEEKS):
        start = now - week * week_duration

        for event in fd.GenerateItems(timestamp=(start, start + week_duration)):
          self.weekly_activity = self.client_activity.setdefault(
              event.client, [[x, 0] for x in range(-self.WEEKS, 0, 1)])
          self.weekly_activity[-week][1] += 1

      self.data = []
      for client, data in self.client_activity.items():
        self.data.append(dict(label=str(client), data=data))

      self.data = renderers.JsonDumpForScriptContext(self.data)

    except IOError:
      pass

    return super(ClientActivity, self).Layout(request, response)
