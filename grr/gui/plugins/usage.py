#!/usr/bin/env python
"""GUI elements to display usage statistics."""


import operator

from grr.gui import renderers
from grr.gui.plugins import semantic
from grr.gui.plugins import statistics
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow as lib_flow
from grr.lib import rdfvalue
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import users as aff4_users
from grr.lib.rdfvalues import stats as rdf_stats


def GetAuditLogFiles(offset, now, token):
  """Get fds for audit log files created between now-offset and now.

  Args:
    offset: rdfvalue.Duration how far back to look in time
    now: rdfvalue.RDFDatetime for current time
    token: GRR access token
  Returns:
    Open handles to all audit logs collections that match the time range
  Raises:
    ValueError: if no matching logs were found
  """
  # Go back offset seconds, and another rollover period to make sure we get
  # all the events
  oldest_time = now - offset - rdfvalue.Duration(config_lib.CONFIG[
      "Logging.aff4_audit_log_rollover"])
  parentdir = aff4.FACTORY.Open("aff4:/audit/logs", token=token)
  logs = list(parentdir.ListChildren(age=(oldest_time.AsMicroSecondsFromEpoch(),
                                          now.AsMicroSecondsFromEpoch())))
  if not logs:
    raise ValueError("Couldn't find any logs in aff4:/audit/logs "
                     "between %s and %s" % (oldest_time, now))

  return aff4.FACTORY.MultiOpen(logs,
                                aff4_type=collects.RDFValueCollection,
                                token=token)


def GetAuditLogEntries(offset, now, token):
  """Return all audit log entries between now-offset and now.

  Args:
    offset: rdfvalue.Duration how far back to look in time
    now: rdfvalue.RDFDatetime for current time
    token: GRR access token
  Yields:
    AuditEvents created during the time range
  """
  for fd in GetAuditLogFiles(offset, now, token):
    for event in fd.GenerateItems():
      if (now - offset) < event.timestamp < now:
        yield event


class MostActiveUsers(statistics.PieChart):
  category = "/Server/User Breakdown/ 7 Day"
  description = "Active User actions in the last week."

  def Layout(self, request, response):
    """Filter the last week of user actions."""
    try:
      offset = rdfvalue.Duration("7d")
      now = rdfvalue.RDFDatetime().Now()
      counts = {}
      for event in GetAuditLogEntries(offset, now, request.token):
        counts.setdefault(event.user, 0)
        counts[event.user] += 1

      self.graph = rdf_stats.Graph(title="User activity breakdown.")
      self.data = []
      for user, count in counts.items():
        if user not in aff4_users.GRRUser.SYSTEM_USERS:
          self.graph.Append(label=user, y_value=count)
          self.data.append(dict(label=user, data=count))
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
{% else %}
  <h3>No data Available</h3>
{% endif %}
</div>
""")

  def Layout(self, request, response):
    response = super(StackChart, self).Layout(request, response)
    if self.data:
      response = self.CallJavascript(response,
                                     "StackChart.Layout",
                                     specs=self.data)
    return response


class UserActivity(StackChart):
  """Display user activity by week."""
  category = "/Server/User Breakdown/Activity"
  description = "Number of flows ran by each user over the last few weeks."
  WEEKS = 10

  def Layout(self, request, response):
    """Filter the last week of user actions."""
    try:
      self.user_activity = {}
      week_duration = rdfvalue.Duration("7d")
      offset = rdfvalue.Duration(7 * 24 * 60 * 60 * self.WEEKS)
      now = rdfvalue.RDFDatetime().Now()
      for fd in GetAuditLogFiles(offset, now, request.token):
        for week in range(self.WEEKS):
          start = now - week * week_duration

          for event in fd.GenerateItems():
            if start < event.timestamp < (start + week_duration):
              self.weekly_activity = self.user_activity.setdefault(
                  event.user, [[x, 0] for x in range(-self.WEEKS, 0, 1)])
              self.weekly_activity[-week][1] += 1

      self.data = []
      for user, data in self.user_activity.items():
        if user not in aff4_users.GRRUser.SYSTEM_USERS:
          self.data.append(dict(label=user, data=data))

    except IOError:
      pass

    return super(UserActivity, self).Layout(request, response)


class SystemFlows(statistics.Report, renderers.TableRenderer):
  """Count last week's system-created flows by type."""
  category = "/Server/Flows/System/  7 days"
  title = "7-Day System Flow Count"
  description = ("Flows launched by GRR crons and workers over the last 7 days"
                 " grouped by type.")
  layout_template = renderers.Template("""
<div class="padded">
  <h3>{{this.title|escape}}</h3>
  <div>
  {{this.description|escape}}
  </div>
</div>
""") + renderers.TableRenderer.layout_template
  time_offset = rdfvalue.Duration("7d")

  def __init__(self, **kwargs):
    super(SystemFlows, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn("Flow Name"))
    self.AddColumn(semantic.RDFValueColumn("Run Count"))
    self.AddColumn(semantic.RDFValueColumn("Most Run By"))

  def UserFilter(self, username):
    return username in aff4_users.GRRUser.SYSTEM_USERS

  def BuildTable(self, start_row, end_row, request):
    # TODO(user): move the calculation to a cronjob and store results in
    # AFF4.
    try:
      now = rdfvalue.RDFDatetime().Now()
      # Store run count total and per-user
      counts = {}
      for event in GetAuditLogEntries(self.time_offset, now, request.token):
        if (event.action == lib_flow.AuditEvent.Action.RUN_FLOW and
            self.UserFilter(event.user)):
          counts.setdefault(event.flow_name, {"total": 0, event.user: 0})
          counts[event.flow_name]["total"] += 1
          counts[event.flow_name].setdefault(event.user, 0)
          counts[event.flow_name][event.user] += 1

      for flow, countdict in sorted(counts.iteritems(),
                                    key=lambda x: x[1]["total"], reverse=True):
        total_count = countdict["total"]
        countdict.pop("total")
        topusercounts = sorted(countdict.iteritems(),
                               key=operator.itemgetter(1),
                               reverse=True)[0:3]
        topusers = ", ".join("%s (%s)" % (user, count)
                             for user, count in topusercounts)
        self.AddRow({"Flow Name": flow,
                     "Run Count": total_count,
                     "Most Run By": topusers})
    except IOError:
      pass


class SystemFlows30(SystemFlows):
  """Count last month's system-created flows by type."""
  category = "/Server/Flows/System/ 30 days"
  title = "30-Day System Flow Count"
  description = ("Flows launched by GRR crons and workers over the last 30 days"
                 " grouped by type.")
  time_offset = rdfvalue.Duration("30d")


class UserFlows(SystemFlows):
  """Count last week's user-created flows by type."""
  category = "/Server/Flows/User/  7 days"
  title = "7-Day User Flow Count"
  description = ("Flows launched by GRR users over the last 7 days"
                 " grouped by type.")

  def UserFilter(self, username):
    return username not in aff4_users.GRRUser.SYSTEM_USERS


class UserFlows30(UserFlows):
  """Count last month's user-created flows by type."""
  category = "/Server/Flows/User/ 30 days"
  title = "30-Day User Flow Count"
  description = ("Flows launched by GRR users over the last 30 days"
                 " grouped by type.")
  time_offset = rdfvalue.Duration("30d")


class ClientActivity(StackChart):
  """Display client activity by week."""
  category = "/Server/Clients/Activity"
  description = ("Number of flows issued against each client over the "
                 "last few weeks.")

  WEEKS = 10

  def Layout(self, request, response):
    """Filter the last week of flows."""
    try:
      now = rdfvalue.RDFDatetime().Now()
      week_duration = rdfvalue.Duration("7d")
      offset = rdfvalue.Duration(7 * 24 * 60 * 60 * self.WEEKS)
      self.client_activity = {}

      for fd in GetAuditLogFiles(offset, now, request.token):
        for week in range(self.WEEKS):
          start = now - week * week_duration
          for event in fd.GenerateItems():
            if start < event.timestamp < (start + week_duration):
              self.weekly_activity = self.client_activity.setdefault(
                  event.client, [[x, 0] for x in range(-self.WEEKS, 0, 1)])
              self.weekly_activity[-week][1] += 1

      self.data = []
      for client, data in self.client_activity.items():
        if client:
          self.data.append(dict(label=str(client), data=data))

    except IOError:
      pass

    return super(ClientActivity, self).Layout(request, response)


class AuditTable(statistics.Report, renderers.TableRenderer):
  """Parent class for audit event tabular reports."""
  layout_template = renderers.Template("""
<div class="padded">
  <h3>{{this.title|escape}}</h3>
</div>
""") + renderers.TableRenderer.layout_template
  time_offset = rdfvalue.Duration("7d")
  column_map = {"Timestamp": "timestamp",
                "Action": "action",
                "User": "user",
                "Client": "client",
                "Flow Name": "flow_name",
                "URN": "urn",
                "Description": "description"}

  # To be set by subclass
  TYPES = []

  def __init__(self, **kwargs):
    super(AuditTable, self).__init__(**kwargs)
    for column_name in sorted(self.column_map):
      self.AddColumn(semantic.RDFValueColumn(column_name))

  def BuildTable(self, start_row, end_row, request):
    try:
      now = rdfvalue.RDFDatetime().Now()
      rows = []
      for event in GetAuditLogEntries(self.time_offset, now, request.token):
        if event.action in self.TYPES:
          row_dict = {}
          for column_name, attribute in self.column_map.iteritems():
            row_dict[column_name] = event.Get(attribute)
          rows.append(row_dict)

      for row in sorted(rows, key=lambda x: x["Timestamp"]):
        self.AddRow(row)

    except IOError:
      pass


class ClientApprovals(AuditTable):
  """Last week's client approvals."""
  category = "/Server/Approvals/Clients/  7 days"
  title = "Client approval requests and grants for the last 7 days"
  column_map = {"Timestamp": "timestamp",
                "Approval Type": "action",
                "User": "user",
                "Client": "client",
                "Reason": "description"}
  TYPES = [lib_flow.AuditEvent.Action.CLIENT_APPROVAL_BREAK_GLASS_REQUEST,
           lib_flow.AuditEvent.Action.CLIENT_APPROVAL_GRANT,
           lib_flow.AuditEvent.Action.CLIENT_APPROVAL_REQUEST]


class ClientApprovals30(ClientApprovals):
  """Last month's client approvals."""
  category = "/Server/Approvals/Clients/ 30 days"
  title = "Client approval requests and grants for the last 30 days"
  time_offset = rdfvalue.Duration("30d")


class HuntApprovals(AuditTable):
  """Last week's hunt approvals."""
  category = "/Server/Approvals/Hunts/  7 days"
  title = "Hunt approval requests and grants for the last 7 days"
  column_map = {"Timestamp": "timestamp",
                "Approval Type": "action",
                "User": "user",
                "URN": "urn",
                "Reason": "description"}
  TYPES = [lib_flow.AuditEvent.Action.HUNT_APPROVAL_GRANT,
           lib_flow.AuditEvent.Action.HUNT_APPROVAL_REQUEST]


class HuntApprovals30(HuntApprovals):
  """Last month's hunt approvals."""
  category = "/Server/Approvals/Hunts/ 30 days"
  title = "Hunt approval requests and grants for the last 30 days"
  time_offset = rdfvalue.Duration("30d")


class CronApprovals(HuntApprovals):
  """Last week's cron approvals."""
  category = "/Server/Approvals/Crons/  7 days"
  title = "Cron approval requests and grants for the last 7 days"
  TYPES = [lib_flow.AuditEvent.Action.CRON_APPROVAL_GRANT,
           lib_flow.AuditEvent.Action.CRON_APPROVAL_REQUEST]


class CronApprovals30(CronApprovals):
  """Last month's cron approvals."""
  category = "/Server/Approvals/Crons/ 30 days"
  title = "Cron approval requests and grants for the last 30 days"
  time_offset = rdfvalue.Duration("30d")


class HuntActions(AuditTable):
  """Last week's hunt actions."""
  category = "/Server/Hunts/  7 days"
  title = "Hunt management actions for the last 7 days"
  column_map = {"Timestamp": "timestamp",
                "Action": "action",
                "User": "user",
                "Flow Name": "flow_name",
                "URN": "urn",
                "Description": "description"}

  TYPES = [lib_flow.AuditEvent.Action.HUNT_CREATED,
           lib_flow.AuditEvent.Action.HUNT_MODIFIED,
           lib_flow.AuditEvent.Action.HUNT_PAUSED,
           lib_flow.AuditEvent.Action.HUNT_STARTED,
           lib_flow.AuditEvent.Action.HUNT_STOPPED]


class HuntActions30(HuntActions):
  """Last month's hunt actions."""
  category = "/Server/Hunts/ 30 days"
  title = "Hunt management actions for the last 30 days"
  time_offset = rdfvalue.Duration("30d")
