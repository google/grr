#!/usr/bin/env python
"""UI server report handling classes."""

from grr.gui.api_plugins.report_plugins import report_plugins
from grr.gui.api_plugins.report_plugins import report_utils

from grr.lib.aff4_objects import users as aff4_users


class MostActiveUsersReportPlugin(report_plugins.ReportPluginBase):
  """Reports client activity by week."""

  TYPE = report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "User Breakdown"
  SUMMARY = "Active user actions."
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
