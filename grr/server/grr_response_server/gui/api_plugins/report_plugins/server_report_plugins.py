#!/usr/bin/env python
"""UI server report handling classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import math
import re


from future.builtins import range
from future.utils import iteritems

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_server import data_store
from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.flows.general import audit
from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugin_base
from grr_response_server.gui.api_plugins.report_plugins import report_utils

RepresentationType = rdf_report_plugins.ApiReportData.RepresentationType


def _LoadAuditEvents(handlers,
                     get_report_args,
                     actions=None,
                     token=None,
                     transformers=None):
  """Returns AuditEvents for given handlers, actions, and timerange."""
  if transformers is None:
    transformers = {}

  if data_store.RelationalDBEnabled():
    entries = data_store.REL_DB.ReadAPIAuditEntries(
        min_timestamp=get_report_args.start_time,
        max_timestamp=get_report_args.start_time + get_report_args.duration,
        router_method_names=list(handlers.keys()))
    rows = [_EntryToEvent(entry, handlers, transformers) for entry in entries]
  else:
    entries = report_utils.GetAuditLogEntries(
        offset=get_report_args.duration,
        now=get_report_args.start_time + get_report_args.duration,
        token=token)
    if actions is None:
      actions = set(handlers.values())
    rows = [entry for entry in entries if entry.action in actions]
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
        self.HANDLERS,
        get_report_args,
        transformers=[_ExtractClientIdFromPath],
        token=token)
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
        transformers=[_ExtractCronJobIdFromPath],
        token=token)
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

    ret.audit_chart.rows = _LoadAuditEvents(
        self.HANDLERS, get_report_args, actions=self.TYPES, token=token)
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
        self.HANDLERS,
        get_report_args,
        transformers=[_ExtractHuntIdFromPath],
        token=token)
    return ret


class MostActiveUsersReportPlugin(report_plugin_base.ReportPluginBase):
  """Reports client activity by week."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "User Breakdown"
  SUMMARY = "Active user actions."
  REQUIRES_TIME_RANGE = True

  def _GetUserCounts(self, get_report_args, token=None):
    if data_store.RelationalDBEnabled():
      counter = collections.Counter()
      entries = data_store.REL_DB.CountAPIAuditEntriesByUserAndDay(
          min_timestamp=get_report_args.start_time,
          max_timestamp=get_report_args.start_time + get_report_args.duration)
      for (username, _), count in iteritems(entries):
        counter[username] += count
      return counter
    else:
      events = report_utils.GetAuditLogEntries(
          offset=get_report_args.duration,
          now=get_report_args.start_time + get_report_args.duration,
          token=token)
      return collections.Counter(event.user for event in events)

  def GetReportData(self, get_report_args, token):
    """Filter the last week of user actions."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.PIE_CHART)

    counts = self._GetUserCounts(get_report_args, token)
    for username in aff4_users.GRRUser.SYSTEM_USERS:
      del counts[username]

    ret.pie_chart.data = [
        rdf_report_plugins.ApiReportDataPoint1D(x=count, label=user)
        for user, count in sorted(iteritems(counts))
    ]

    return ret


class BaseUserFlowReportPlugin(report_plugin_base.ReportPluginBase):
  """Count given timerange's flows by type."""

  def IncludeUser(self, username):
    return True

  def _GetFlows(self, get_report_args, token):
    counts = collections.defaultdict(collections.Counter)

    if data_store.RelationalDBEnabled():
      flows = data_store.REL_DB.ReadAllFlowObjects(
          min_create_time=get_report_args.start_time,
          max_create_time=get_report_args.start_time + get_report_args.duration,
          include_child_flows=False)

      for flow in flows:
        if self.IncludeUser(flow.creator):
          counts[flow.flow_class_name][flow.creator] += 1
    else:
      counts = collections.defaultdict(collections.Counter)
      for event in report_utils.GetAuditLogEntries(
          offset=get_report_args.duration,
          now=get_report_args.start_time + get_report_args.duration,
          token=token):
        if (event.action == rdf_events.AuditEvent.Action.RUN_FLOW and
            self.IncludeUser(event.user)):
          counts[event.flow_name][event.user] += 1

    return counts

  def GetReportData(self, get_report_args, token):
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.STACK_CHART,
        stack_chart=rdf_report_plugins.ApiStackChartReportData(x_ticks=[]))

    counts = self._GetFlows(get_report_args, token)
    total_counts = collections.Counter(
        {flow: sum(cts.values()) for flow, cts in iteritems(counts)})

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
    return username not in aff4_users.GRRUser.SYSTEM_USERS


class SystemFlowsReportPlugin(BaseUserFlowReportPlugin):
  """Count given timerange's system-created flows by type."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "System Flows"
  SUMMARY = ("Flows launched by GRR crons and workers over the given timerange"
             " grouped by type.")
  REQUIRES_TIME_RANGE = True

  def IncludeUser(self, username):
    return username in aff4_users.GRRUser.SYSTEM_USERS


class UserActivityReportPlugin(report_plugin_base.ReportPluginBase):
  """Display user activity by week."""

  TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "User Activity"
  SUMMARY = "Number of flows ran by each user."
  REQUIRES_TIME_RANGE = True

  def _LoadUserActivity(self, start_time, end_time, token):
    if data_store.RelationalDBEnabled():
      counts = data_store.REL_DB.CountAPIAuditEntriesByUserAndDay(
          min_timestamp=start_time, max_timestamp=end_time)
      for (username, day), count in iteritems(counts):
        yield username, day, count
    else:
      for fd in audit.LegacyAuditLogsForTimespan(
          start_time=start_time - audit.AUDIT_ROLLOVER_TIME,
          end_time=end_time,
          token=token):
        for event in fd.GenerateItems():
          yield event.user, event.timestamp, 1

  def GetReportData(self, get_report_args, token):
    """Filter the last week of user actions."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=RepresentationType.STACK_CHART)

    week_duration = rdfvalue.Duration("7d")
    num_weeks = math.ceil(get_report_args.duration.seconds /
                          week_duration.seconds)
    weeks = range(0, num_weeks)
    start_time = get_report_args.start_time
    end_time = start_time + num_weeks * week_duration
    user_activity = collections.defaultdict(lambda: {week: 0 for week in weeks})

    entries = self._LoadUserActivity(
        start_time=get_report_args.start_time, end_time=end_time, token=token)

    for username, timestamp, count in entries:
      week = (timestamp - start_time).seconds // week_duration.seconds
      if week in user_activity[username]:
        user_activity[username][week] += count

    user_activity = sorted(iteritems(user_activity))
    user_activity = [(user, data)
                     for user, data in user_activity
                     if user not in aff4_users.GRRUser.SYSTEM_USERS]

    ret.stack_chart.data = [
        rdf_report_plugins.ApiReportDataSeries2D(
            label=user,
            points=(rdf_report_plugins.ApiReportDataPoint2D(x=x, y=y)
                    for x, y in sorted(data.items())))
        for user, data in user_activity
    ]

    return ret
