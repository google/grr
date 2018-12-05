#!/usr/bin/env python
"""UI server report handling classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import operator


from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import events as rdf_events

from grr_response_server.aff4_objects import users as aff4_users
from grr_response_server.flows.general import audit
from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugin_base
from grr_response_server.gui.api_plugins.report_plugins import report_utils

TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER


class ClientApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's client approvals."""

  TYPE = TYPE
  TITLE = "Client Approvals"
  SUMMARY = "Client approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "client", "description", "timestamp", "user"]
  TYPES = [
      rdf_events.AuditEvent.Action.CLIENT_APPROVAL_BREAK_GLASS_REQUEST,
      rdf_events.AuditEvent.Action.CLIENT_APPROVAL_GRANT,
      rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST
  ]

  def GetReportData(self, get_report_args, token):
    """Filter the cron job approvals in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType.
        AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.__class__.USED_FIELDS))

    try:
      timerange_offset = get_report_args.duration
      timerange_end = get_report_args.start_time + timerange_offset

      rows = []
      try:
        for event in report_utils.GetAuditLogEntries(timerange_offset,
                                                     timerange_end, token):
          if event.action in self.__class__.TYPES:
            rows.append(event)

      except ValueError:  # Couldn't find any logs..
        pass

    except IOError:
      pass

    rows.sort(key=lambda row: row.timestamp, reverse=True)
    ret.audit_chart.rows = rows

    return ret


class CronApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's cron job approvals."""

  TYPE = TYPE
  TITLE = "Cron Job Approvals"
  SUMMARY = "Cron job approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "description", "timestamp", "urn", "user"]
  TYPES = [
      rdf_events.AuditEvent.Action.CRON_APPROVAL_GRANT,
      rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST
  ]

  def GetReportData(self, get_report_args, token):
    """Filter the cron job approvals in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType.
        AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.__class__.USED_FIELDS))

    try:
      timerange_offset = get_report_args.duration
      timerange_end = get_report_args.start_time + timerange_offset

      rows = []
      try:
        for event in report_utils.GetAuditLogEntries(timerange_offset,
                                                     timerange_end, token):
          if event.action in self.__class__.TYPES:
            rows.append(event)

      except ValueError:  # Couldn't find any logs..
        pass

    except IOError:
      pass

    rows.sort(key=lambda row: row.timestamp, reverse=True)
    ret.audit_chart.rows = rows

    return ret


class HuntActionsReportPlugin(report_plugin_base.ReportPluginBase):
  """Hunt actions in the given timerange."""

  TYPE = TYPE
  TITLE = "Hunts"
  SUMMARY = "Hunt management actions for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = [
      "action", "description", "flow_name", "timestamp", "urn", "user"
  ]
  TYPES = [
      rdf_events.AuditEvent.Action.HUNT_CREATED,
      rdf_events.AuditEvent.Action.HUNT_MODIFIED,
      rdf_events.AuditEvent.Action.HUNT_PAUSED,
      rdf_events.AuditEvent.Action.HUNT_STARTED,
      rdf_events.AuditEvent.Action.HUNT_STOPPED
  ]

  def GetReportData(self, get_report_args, token):
    """Filter the hunt actions in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType.
        AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.__class__.USED_FIELDS))

    try:
      timerange_offset = get_report_args.duration
      timerange_end = get_report_args.start_time + timerange_offset

      rows = []
      try:
        for event in report_utils.GetAuditLogEntries(timerange_offset,
                                                     timerange_end, token):
          if event.action in self.__class__.TYPES:
            rows.append(event)

      except ValueError:  # Couldn't find any logs..
        pass

    except IOError:
      pass

    rows.sort(key=lambda row: row.timestamp, reverse=True)
    ret.audit_chart.rows = rows

    return ret


class HuntApprovalsReportPlugin(report_plugin_base.ReportPluginBase):
  """Given timerange's hunt approvals."""

  TYPE = TYPE
  TITLE = "Hunt Approvals"
  SUMMARY = "Hunt approval requests and grants for the given timerange."
  REQUIRES_TIME_RANGE = True

  USED_FIELDS = ["action", "description", "timestamp", "urn", "user"]
  TYPES = [
      rdf_events.AuditEvent.Action.HUNT_APPROVAL_GRANT,
      rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST
  ]

  def GetReportData(self, get_report_args, token):
    """Filter the hunt approvals in the given timerange."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType.
        AUDIT_CHART,
        audit_chart=rdf_report_plugins.ApiAuditChartReportData(
            used_fields=self.__class__.USED_FIELDS))

    try:
      timerange_offset = get_report_args.duration
      timerange_end = get_report_args.start_time + timerange_offset

      rows = []
      try:
        for event in report_utils.GetAuditLogEntries(timerange_offset,
                                                     timerange_end, token):
          if event.action in self.__class__.TYPES:
            rows.append(event)

      except ValueError:  # Couldn't find any logs..
        pass

    except IOError:
      pass

    rows.sort(key=lambda row: row.timestamp, reverse=True)
    ret.audit_chart.rows = rows

    return ret


class MostActiveUsersReportPlugin(report_plugin_base.ReportPluginBase):
  """Reports client activity by week."""

  TYPE = TYPE
  TITLE = "User Breakdown"
  SUMMARY = "Active user actions."
  REQUIRES_TIME_RANGE = True

  def GetReportData(self, get_report_args, token):
    """Filter the last week of user actions."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType.
        PIE_CHART)

    try:
      timerange_offset = get_report_args.duration
      timerange_end = get_report_args.start_time + timerange_offset

      counts = {}
      try:
        for event in report_utils.GetAuditLogEntries(timerange_offset,
                                                     timerange_end, token):
          counts.setdefault(event.user, 0)
          counts[event.user] += 1
      except ValueError:  # Couldn't find any logs..
        pass

      ret.pie_chart.data = sorted(
          (rdf_report_plugins.ApiReportDataPoint1D(x=count, label=user)
           for user, count in iteritems(counts)
           if user not in aff4_users.GRRUser.SYSTEM_USERS),
          key=lambda series: series.label)

    except IOError:
      pass

    return ret


class SystemFlowsReportPlugin(report_plugin_base.ReportPluginBase):
  """Count given timerange's system-created flows by type."""

  TYPE = TYPE
  TITLE = "System Flows"
  SUMMARY = ("Flows launched by GRR crons and workers over the given timerange"
             " grouped by type.")
  REQUIRES_TIME_RANGE = True

  def UserFilter(self, username):
    return username in aff4_users.GRRUser.SYSTEM_USERS

  def GetReportData(self, get_report_args, token):
    ret = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType.
        STACK_CHART,
        stack_chart=rdf_report_plugins.ApiStackChartReportData(x_ticks=[]))

    # TODO(user): move the calculation to a cronjob and store results in
    # AFF4.
    try:
      timerange_offset = get_report_args.duration
      timerange_end = get_report_args.start_time + timerange_offset

      # Store run count total and per-user
      counts = {}
      try:
        for event in report_utils.GetAuditLogEntries(timerange_offset,
                                                     timerange_end, token):
          if (event.action == rdf_events.AuditEvent.Action.RUN_FLOW and
              self.UserFilter(event.user)):
            counts.setdefault(event.flow_name, {"total": 0, event.user: 0})
            counts[event.flow_name]["total"] += 1
            counts[event.flow_name].setdefault(event.user, 0)
            counts[event.flow_name][event.user] += 1
      except ValueError:  # Couldn't find any logs..
        pass

      for i, (flow, countdict) in enumerate(
          sorted(iteritems(counts), key=lambda x: x[1]["total"], reverse=True)):
        total_count = countdict["total"]
        countdict.pop("total")
        topusercounts = sorted(
            iteritems(countdict), key=operator.itemgetter(1), reverse=True)[:3]
        topusers = ", ".join("%s (%s)" % (user, count)
                             for user, count in topusercounts)

        ret.stack_chart.data.append(
            rdf_report_plugins.ApiReportDataSeries2D(
                # \u2003 is an emspace, a long whitespace character.
                label=u"%s\u2003Run By: %s" % (flow, topusers),
                points=[
                    rdf_report_plugins.ApiReportDataPoint2D(x=i, y=total_count)
                ]))

    except IOError:
      pass

    return ret


class UserActivityReportPlugin(report_plugin_base.ReportPluginBase):
  """Display user activity by week."""

  TYPE = TYPE
  TITLE = "User Activity"
  SUMMARY = "Number of flows ran by each user over the last few weeks."
  # TODO(user): Support timerange selection.

  WEEKS = 10

  def GetReportData(self, get_report_args, token):
    """Filter the last week of user actions."""
    ret = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType.
        STACK_CHART)

    try:
      user_activity = {}
      week_duration = rdfvalue.Duration("7d")
      offset = rdfvalue.Duration("%dw" % self.WEEKS)
      now = rdfvalue.RDFDatetime.Now()
      start_time = now - offset - audit.AUDIT_ROLLOVER_TIME
      try:
        for fd in audit.LegacyAuditLogsForTimespan(start_time, now, token):
          for event in fd.GenerateItems():
            for week in range(self.__class__.WEEKS):
              start = now - week * week_duration
              if start < event.timestamp < (start + week_duration):
                weekly_activity = user_activity.setdefault(
                    event.user,
                    [[x, 0] for x in range(-self.__class__.WEEKS, 0, 1)])
                weekly_activity[-week][1] += 1
      except ValueError:  # Couldn't find any logs..
        pass

      ret.stack_chart.data = sorted(
          (rdf_report_plugins.ApiReportDataSeries2D(
              label=user,
              points=(rdf_report_plugins.ApiReportDataPoint2D(x=x, y=y)
                      for x, y in data))
           for user, data in iteritems(user_activity)
           if user not in aff4_users.GRRUser.SYSTEM_USERS),
          key=lambda series: series.label)

    except IOError:
      pass

    return ret


class UserFlowsReportPlugin(report_plugin_base.ReportPluginBase):
  """Count given timerange's user-created flows by type."""

  TYPE = TYPE
  TITLE = "User Flows"
  SUMMARY = ("Flows launched by GRR users over the given timerange grouped by "
             "type.")
  REQUIRES_TIME_RANGE = True

  def UserFilter(self, username):
    return username not in aff4_users.GRRUser.SYSTEM_USERS

  def GetReportData(self, get_report_args, token):
    ret = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType.
        STACK_CHART,
        stack_chart=rdf_report_plugins.ApiStackChartReportData(x_ticks=[]))

    # TODO(user): move the calculation to a cronjob and store results in
    # AFF4.
    try:
      timerange_offset = get_report_args.duration
      timerange_end = get_report_args.start_time + timerange_offset

      # Store run count total and per-user
      counts = {}
      try:
        for event in report_utils.GetAuditLogEntries(timerange_offset,
                                                     timerange_end, token):
          if (event.action == rdf_events.AuditEvent.Action.RUN_FLOW and
              self.UserFilter(event.user)):
            counts.setdefault(event.flow_name, {"total": 0, event.user: 0})
            counts[event.flow_name]["total"] += 1
            counts[event.flow_name].setdefault(event.user, 0)
            counts[event.flow_name][event.user] += 1
      except ValueError:  # Couldn't find any logs..
        pass

      for i, (flow, countdict) in enumerate(
          sorted(iteritems(counts), key=lambda x: x[1]["total"], reverse=True)):
        total_count = countdict["total"]
        countdict.pop("total")
        topusercounts = sorted(
            iteritems(countdict), key=operator.itemgetter(1), reverse=True)[:3]
        topusers = ", ".join("%s (%s)" % (user, count)
                             for user, count in topusercounts)

        ret.stack_chart.data.append(
            rdf_report_plugins.ApiReportDataSeries2D(
                # \u2003 is an emspace, a long whitespace character.
                label=u"%s\u2003Run By: %s" % (flow, topusers),
                points=[
                    rdf_report_plugins.ApiReportDataPoint2D(x=i, y=total_count)
                ]))

    except IOError:
      pass

    return ret
