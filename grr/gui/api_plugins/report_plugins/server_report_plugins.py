#!/usr/bin/env python
"""UI server report handling classes."""

from grr.gui.api_plugins.report_plugins import report_plugins
from grr.gui.api_plugins.report_plugins import report_utils

from grr.lib import rdfvalue


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
