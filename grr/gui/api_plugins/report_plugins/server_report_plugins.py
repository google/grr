#!/usr/bin/env python
"""UI server report handling classes."""

from grr.gui.api_plugins.report_plugins import rdf_report_plugins
from grr.gui.api_plugins.report_plugins import report_plugin_base
from grr.gui.api_plugins.report_plugins import report_utils

from grr.lib import rdfvalue
from grr.lib.aff4_objects import users as aff4_users

TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER


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
          (rdf_report_plugins.ApiReportDataPoint1D(
              x=count, label=user) for user, count in counts.iteritems()
           if user not in aff4_users.GRRUser.SYSTEM_USERS),
          key=lambda series: series.label)

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
      offset = rdfvalue.Duration(7 * 24 * 60 * 60 * self.__class__.WEEKS)
      now = rdfvalue.RDFDatetime.Now()
      try:
        for fd in report_utils.GetAuditLogFiles(offset, now, token):
          for event in fd.GenerateItems():
            for week in xrange(self.__class__.WEEKS):
              start = now - week * week_duration
              if start < event.timestamp < (start + week_duration):
                weekly_activity = user_activity.setdefault(
                    event.user, [[x, 0]
                                 for x in xrange(-self.__class__.WEEKS, 0, 1)])
                weekly_activity[-week][1] += 1
      except ValueError:  # Couldn't find any logs..
        pass

      ret.stack_chart.data = sorted(
          (rdf_report_plugins.ApiReportDataSeries2D(
              label=user,
              points=(rdf_report_plugins.ApiReportDataPoint2D(
                  x=x, y=y) for x, y in data))
           for user, data in user_activity.iteritems()
           if user not in aff4_users.GRRUser.SYSTEM_USERS),
          key=lambda series: series.label)

    except IOError:
      pass

    return ret
