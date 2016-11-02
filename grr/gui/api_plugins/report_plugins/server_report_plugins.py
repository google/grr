#!/usr/bin/env python
"""UI server report handling classes."""

from grr.gui.api_plugins.report_plugins import report_plugins
from grr.gui.api_plugins.report_plugins import report_utils

from grr.lib import rdfvalue
from grr.lib.aff4_objects import users as aff4_users


class ClientsActivityReportPlugin(report_plugins.ReportPluginBase):
  """Reports client activity by week."""

  TYPE = report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Client Activity"
  SUMMARY = ("Number of flows issued against each client over the "
             "last few weeks.")

  WEEKS = 10

  def GetReportData(self, get_report_args, token):
    """Filter the last week of flows."""
    ret = report_plugins.ApiReportData(
        representation_type=report_plugins.ApiReportData.RepresentationType.
        STACK_CHART)

    try:
      now = rdfvalue.RDFDatetime().Now()
      week_duration = rdfvalue.Duration("7d")
      offset = week_duration * ClientsActivityReportPlugin.WEEKS
      client_activity = {}

      try:
        logs_gen = report_utils.GetAuditLogFiles(offset, now, token)
      except ValueError:  # Couldn't find any logs..
        logs_gen = iter(())

      for fd in logs_gen:
        for week in range(ClientsActivityReportPlugin.WEEKS):
          start = now - week * week_duration
          for event in fd.GenerateItems():
            if start <= event.timestamp < (start + week_duration):
              weekly_activity = client_activity.setdefault(
                  event.client,
                  [[x, 0]
                   for x in range(-ClientsActivityReportPlugin.WEEKS, 0, 1)])
              weekly_activity[-week][1] += 1

      ret.stack_chart.data = sorted(
          (report_plugins.ApiReportDataSeries2D(
              label=str(client),
              points=[
                  report_plugins.ApiReportDataPoint2D(
                      x=x, y=y) for x, y in client_data
              ]) for client, client_data in client_activity.iteritems()
           if client),
          key=lambda series: series.label)

    except IOError:
      pass

    return ret


class MostActiveUsersReportPlugin(report_plugins.ReportPluginBase):
  """Reports client activity by week."""

  TYPE = report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "User Breakdown"
  SUMMARY = "Active user actions in the last week."
  REQUIRES_TIME_RANGE = True

  def GetReportData(self, get_report_args, token):
    """Filter the last week of user actions."""
    ret = report_plugins.ApiReportData(
        representation_type=report_plugins.ApiReportData.RepresentationType.
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
          (report_plugins.ApiReportDataPoint1D(
              x=count, label=user) for user, count in counts.iteritems()
           if user not in aff4_users.GRRUser.SYSTEM_USERS),
          key=lambda series: series.label)

    except IOError:
      pass

    return ret
