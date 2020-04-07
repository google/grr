#!/usr/bin/env python
# Lint as: python3
"""UI server report handling classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import math
import re


from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_server import access_control
from grr_response_server import data_store
from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugin_base

RepresentationType = rdf_report_plugins.ApiReportData.RepresentationType


def _LoadAuditEvents(handlers, get_report_args, transformers=None):
  """Returns AuditEvents for given handlers, actions, and timerange."""
  if transformers is None:
    transformers = {}

  entries = data_store.REL_DB.ReadAPIAuditEntries(
      min_timestamp=get_report_args.start_time,
      max_timestamp=get_report_args.start_time + get_report_args.duration,
      router_method_names=list(handlers.keys()))
  rows = [_EntryToEvent(entry, handlers, transformers) for entry in entries]
  rows.sort(key=lambda row: row.timestamp, reverse=True)
  return rows


def _EntryToEvent(entry, handlers, transformers):
  """Converts an APIAuditEntry to a legacy AuditEvent."""
  event = rdf_events.AuditEvent(
      timestamp=entry.timestamp,
      user=entry.username,
      action=handlers[entry.router_method_name])

  for fn in transformers:
    fn(entry, event)

  return event


def _ExtractClientIdFromPath(entry, event):
  """Extracts a Client ID from an APIAuditEntry's HTTP request path."""
  match = re.match(r".*(C\.[0-9a-fA-F]{16}).*", entry.http_request_path)
  if match:
    event.client = match.group(1)


# TODO: Remove AFF4 URNs from the API data format.
def _ExtractCronJobIdFromPath(entry, event):
  """Extracts a CronJob ID from an APIAuditEntry's HTTP request path."""
  match = re.match(r".*cron-job/([^/]+).*", entry.http_request_path)
  if match:
    event.urn = "aff4:/cron/{}".format(match.group(1))


def _ExtractHuntIdFromPath(entry, event):
  """Extracts a Hunt ID from an APIAuditEntry's HTTP request path."""
  match = re.match(r".*hunt/([^/]+).*", entry.http_request_path)
  if match:
    event.urn = "aff4:/hunts/{}".format(match.group(1))


class ClientApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's client approvals."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Client Approvals"
  SUMMARY = "Client approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "client", "timestamp", "user"]
  # TODO: Rework API data format, to remove need for legacy
  # AuditEvent.Action.
  HANDLERS = {
      "GrantClientApproval":
          rdf_events.AuditEvent.Action.CLIENT_APPROVAL_GRANT,
      "CreateClientApproval":
          rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST,
  }

  def GetReportData(self, get_report_args, token=None):
    """Filter the cron job approvals in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.USED_FIELDS))

    ret.audit_chart.rows = _LoadAuditEvents(
        self.HANDLERS, get_report_args, transformers=[_ExtractClientIdFromPath])
    return ret


class CronApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's cron job approvals."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Cron Job Approvals"
  SUMMARY = "Cron job approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "timestamp", "user", "urn"]
  HANDLERS = {
      "GrantCronJobApproval":
          rdf_events.AuditEvent.Action.CRON_APPROVAL_GRANT,
      "CreateCronJobApproval":
          rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
  }

  def GetReportData(self, get_report_args, token):
    """Filter the cron job approvals in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.USED_FIELDS))

    ret.audit_chart.rows = _LoadAuditEvents(
        self.HANDLERS,
        get_report_args,
        transformers=[_ExtractCronJobIdFromPath])
    return ret


# TODO: Migrate from AuditEvent to Hunts database table as source.
class HuntActionsReportPlugin(report_plugin_base.ReportPluginBase):
  """Hunt actions in the given timerange."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Hunts"
  SUMMARY = "Hunt management actions for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "timestamp", "user"]
  TYPES = [
      rdf_events.AuditEvent.Action.HUNT_CREATED,
      rdf_events.AuditEvent.Action.HUNT_MODIFIED,
      rdf_events.AuditEvent.Action.HUNT_PAUSED,
      rdf_events.AuditEvent.Action.HUNT_STARTED,
      rdf_events.AuditEvent.Action.HUNT_STOPPED
  ]
  HANDLERS = {
      "CreateHunt": rdf_events.AuditEvent.Action.HUNT_CREATED,
      "ModifyHunt": rdf_events.AuditEvent.Action.HUNT_MODIFIED,
  }

  def GetReportData(self, get_report_args, token):
    """Filter the hunt actions in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.USED_FIELDS))

    ret.audit_chart.rows = _LoadAuditEvents(self.HANDLERS, get_report_args)
    return ret


class HuntApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's hunt approvals."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Hunt Approvals"
  SUMMARY = "Hunt approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "timestamp", "user", "urn"]
  HANDLERS = {
      "GrantHuntApproval": rdf_events.AuditEvent.Action.HUNT_APPROVAL_GRANT,
      "CreateHuntApproval": rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
  }

  def GetReportData(self, get_report_args, token):
    """Filter the hunt approvals in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.USED_FIELDS))

    ret.audit_chart.rows = _LoadAuditEvents(
        self.HANDLERS, get_report_args, transformers=[_ExtractHuntIdFromPath])
    return ret


class MostActiveUsersReportPlugin(report_plugin_base.ReportPluginBase):
  """Reports client activity by week."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "User Breakdown"
  SUMMARY = "Active user actions."
  REQUIRES_TIME_RANGE = True

  def _GetUserCounts(self, get_report_args, token=None):
    counter = collections.Counter()
    entries = data_store.REL_DB.CountAPIAuditEntriesByUserAndDay(
        min_timestamp=get_report_args.start_time,
        max_timestamp=get_report_args.start_time + get_report_args.duration)
    for (username, _), count in entries.items():
      counter[username] += count
    return counter

  def GetReportData(self, get_report_args, token):
    """Filter the last week of user actions."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.PIE_CHART)

    counts = self._GetUserCounts(get_report_args, token)
    for username in access_control.SYSTEM_USERS:
      del counts[username]

    ret.pie_chart.data = [
        rdf_report_plugins.ApiReportDataPoint1D(x=count, label=user)
        for user, count in sorted(counts.items())
    ]

    return ret


class BaseUserFlowReportPlugin(report_plugin_base.ReportPluginBase):
  """Count given timerange's flows by type."""

  def IncludeUser(self, username):
    return True

  def _GetFlows(self, get_report_args, token):
    counts = collections.defaultdict(collections.Counter)

    flows = data_store.REL_DB.ReadAllFlowObjects(
        min_create_time=get_report_args.start_time,
        max_create_time=get_report_args.start_time + get_report_args.duration,
        include_child_flows=False)

    for flow in flows:
      if self.IncludeUser(flow.creator):
        counts[flow.flow_class_name][flow.creator] += 1

    return counts

  def GetReportData(self, get_report_args, token):
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.STACK_CHART,
        stack_chart=rdf_report_plugins.ApiStackChartReportData(x_ticks=[]))

    counts = self._GetFlows(get_report_args, token)
    total_counts = collections.Counter(
        {flow: sum(cts.values()) for flow, cts in counts.items()})

    for i, (flow, total_count) in enumerate(total_counts.most_common()):
      topusercounts = counts[flow].most_common(3)
      topusers = ", ".join(
          "{} ({})".format(user, count) for user, count in topusercounts)

      ret.stack_chart.data.append(
          rdf_report_plugins.ApiReportDataSeries2D(
              # \u2003 is an emspace, a long whitespace character.
              label="{}\u2003Run By: {}".format(flow, topusers),
              points=[
                  rdf_report_plugins.ApiReportDataPoint2D(x=i, y=total_count)
              ]))

    return ret


class UserFlowsReportPlugin(BaseUserFlowReportPlugin):
  """Count given timerange's user-created flows by type."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "User Flows"
  SUMMARY = ("Flows launched by GRR users over the given timerange grouped by "
             "type.")
  REQUIRES_TIME_RANGE = True

  def IncludeUser(self, username):
    return username not in access_control.SYSTEM_USERS


class SystemFlowsReportPlugin(BaseUserFlowReportPlugin):
  """Count given timerange's system-created flows by type."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "System Flows"
  SUMMARY = ("Flows launched by GRR crons and workers over the given timerange"
             " grouped by type.")
  REQUIRES_TIME_RANGE = True

  def IncludeUser(self, username):
    return username in access_control.SYSTEM_USERS


class UserActivityReportPlugin(report_plugin_base.ReportPluginBase):
  """Display user activity by week."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "User Activity"
  SUMMARY = "Number of flows ran by each user."
  REQUIRES_TIME_RANGE = True

  def _LoadUserActivity(self, start_time, end_time, token):
    counts = data_store.REL_DB.CountAPIAuditEntriesByUserAndDay(
        min_timestamp=start_time, max_timestamp=end_time)
    for (username, day), count in counts.items():
      yield username, day, count

  def GetReportData(self, get_report_args, token):
    """Filter the last week of user actions."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.STACK_CHART)

    week_duration = rdfvalue.Duration.From(7, rdfvalue.DAYS)
    num_weeks = int(
        math.ceil(
            rdfvalue.Duration(get_report_args.duration).ToFractional(
                rdfvalue.SECONDS) /
            week_duration.ToFractional(rdfvalue.SECONDS)))
    weeks = range(0, num_weeks)
    start_time = get_report_args.start_time
    end_time = start_time + num_weeks * week_duration
    user_activity = collections.defaultdict(lambda: {week: 0 for week in weeks})

    entries = self._LoadUserActivity(
        start_time=get_report_args.start_time, end_time=end_time, token=token)

    for username, timestamp, count in entries:
      week = (timestamp - start_time).ToInt(
          rdfvalue.SECONDS) // week_duration.ToInt(rdfvalue.SECONDS)
      if week in user_activity[username]:
        user_activity[username][week] += count

    user_activity = sorted(user_activity.items())
    user_activity = [(user, data)
                     for user, data in user_activity
                     if user not in access_control.SYSTEM_USERS]

    ret.stack_chart.data = [
        rdf_report_plugins.ApiReportDataSeries2D(
            label=user,
            points=(rdf_report_plugins.ApiReportDataPoint2D(x=x, y=y)
                    for x, y in sorted(data.items())))
        for user, data in user_activity
    ]

    return ret
