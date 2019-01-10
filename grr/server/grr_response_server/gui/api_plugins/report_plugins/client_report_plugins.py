#!/usr/bin/env python
"""UI client report handling classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from future.utils import iteritems

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_server import client_report_utils
from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugin_base

TYPE = rdf_report_plugins.ApiReportDescriptor.ReportType.CLIENT


class GRRVersion1ReportPlugin(report_plugin_base.ReportPluginBase):
  """Display a histogram of last actives based on GRR Version."""

  TYPE = TYPE
  TITLE = "Active Clients - 1 Day Active"
  SUMMARY = ("This shows the number of clients active in the given timerange "
             "based on the GRR version.")

  ACTIVE_DAY = 1

  def _ProcessGraphSeries(self, graph_series, timestamp, categories):
    for graph in graph_series.graphs:
      # Find the correct graph and merge the OS categories together
      if "%d day" % self.__class__.ACTIVE_DAY in graph.title:
        for sample in graph:
          timestamp_millis = timestamp.AsMicrosecondsSinceEpoch() // 1000
          categories.setdefault(sample.label, []).append((timestamp_millis,
                                                          sample.y_value))
        break

  def GetReportData(self, get_report_args, token):
    """Show how the last active breakdown evolved over time."""
    report = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType
        .LINE_CHART)

    series_with_timestamps = client_report_utils.FetchAllGraphSeries(
        get_report_args.client_label,
        rdf_stats.ClientGraphSeries.ReportType.GRR_VERSION,
        period=rdfvalue.Duration("180d"))

    categories = {}
    for timestamp, graph_series in sorted(iteritems(series_with_timestamps)):
      self._ProcessGraphSeries(graph_series, timestamp, categories)

    graphs = []
    for k, v in iteritems(categories):
      graph = dict(label=k, data=v)
      graphs.append(graph)

    report.line_chart.data = sorted(
        (rdf_report_plugins.ApiReportDataSeries2D(
            label=label,
            points=(rdf_report_plugins.ApiReportDataPoint2D(x=x, y=y)
                    for x, y in points))
         for label, points in iteritems(categories)),
        key=lambda series: series.label)

    return report


class GRRVersion7ReportPlugin(GRRVersion1ReportPlugin):
  """Display a histogram of last actives based on GRR Version."""

  TITLE = "Active Clients - 7 Days Active"

  ACTIVE_DAY = 7


class GRRVersion30ReportPlugin(GRRVersion1ReportPlugin):
  """Display a histogram of last actives based on GRR Version."""

  TITLE = "Active Clients - 30 Days Active"

  ACTIVE_DAY = 30


class LastActiveReportPlugin(report_plugin_base.ReportPluginBase):
  """Displays a histogram of last client activities."""

  TYPE = TYPE
  TITLE = "Last Active"
  SUMMARY = ("Breakdown of Client Count Based on Last Activity of the Client. "
             "This plot shows the number of clients active in the last day and "
             "how that number evolved over time.")

  ACTIVE_DAYS_DISPLAY = [1, 3, 7, 30, 60]

  def _ProcessGraphSeries(self, graph_series, timestamp, categories):
    for sample in graph_series.graphs[0]:
      # Provide the time in js timestamps (milliseconds since the epoch).
      days = sample.x_value // 1000000 // 24 // 60 // 60
      if days in self.__class__.ACTIVE_DAYS_DISPLAY:
        label = "%s day active" % days
        timestamp_millis = timestamp.AsMicrosecondsSinceEpoch() // 1000
        categories.setdefault(label, []).append((timestamp_millis,
                                                 sample.y_value))

  def GetReportData(self, get_report_args, token):
    """Show how the last active breakdown evolved over time."""
    report = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType
        .LINE_CHART)

    series_with_timestamps = client_report_utils.FetchAllGraphSeries(
        get_report_args.client_label,
        rdf_stats.ClientGraphSeries.ReportType.N_DAY_ACTIVE,
        period=rdfvalue.Duration("180d"))

    categories = {}
    for timestamp, graph_series in sorted(iteritems(series_with_timestamps)):
      self._ProcessGraphSeries(graph_series, timestamp, categories)

    graphs = []
    for k, v in iteritems(categories):
      graph = dict(label=k, data=v)
      graphs.append(graph)

    report.line_chart.data = sorted(
        (rdf_report_plugins.ApiReportDataSeries2D(
            label=label,
            points=(rdf_report_plugins.ApiReportDataPoint2D(x=x, y=y)
                    for x, y in points))
         for label, points in iteritems(categories)),
        key=lambda series: int(series.label.split()[0]),
        reverse=True)

    return report


class OSBreakdown1ReportPlugin(report_plugin_base.ReportPluginBase):
  """Displays a histogram of last client activities."""

  TYPE = TYPE
  TITLE = "OS Breakdown - 1 Day Active"
  SUMMARY = ("Operating system break down. OS breakdown for clients that were "
             "active in the given timerange.")

  ACTIVE_DAYS = 1

  def GetReportData(self, get_report_args, token):
    """Extract only the operating system type from the active histogram."""
    report = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType
        .PIE_CHART)

    graph_series = client_report_utils.FetchMostRecentGraphSeries(
        get_report_args.client_label,
        rdf_stats.ClientGraphSeries.ReportType.OS_TYPE,
        token=token)
    if graph_series is not None:
      for graph in graph_series.graphs:
        # Find the correct graph and merge the OS categories together
        if "%s day" % self.__class__.ACTIVE_DAYS in graph.title:
          for sample in graph:
            report.pie_chart.data.Append(
                rdf_report_plugins.ApiReportDataPoint1D(
                    label=sample.label, x=sample.y_value))
          break

    report.pie_chart.data = sorted(
        report.pie_chart.data, key=lambda point: point.label)

    return report


class OSBreakdown7ReportPlugin(OSBreakdown1ReportPlugin):
  """Displays a histogram of last client activities."""

  TITLE = "OS Breakdown - 7 Days Active"

  ACTIVE_DAYS = 7


class OSBreakdown14ReportPlugin(OSBreakdown1ReportPlugin):
  """Displays a histogram of last client activities."""

  TITLE = "OS Breakdown - 14 Days Active"

  ACTIVE_DAYS = 14


class OSBreakdown30ReportPlugin(OSBreakdown1ReportPlugin):
  """Displays a histogram of last client activities."""

  TITLE = "OS Breakdown - 30 Days Active"

  ACTIVE_DAYS = 30


class OSReleaseBreakdown1ReportPlugin(report_plugin_base.ReportPluginBase):
  """Displays a histogram of last client activities."""

  TYPE = TYPE
  TITLE = "OS Release Breakdown - 1 Day Active"
  SUMMARY = ("Operating system version break down. What OS Version clients were"
             " active within the given timerange.")

  ACTIVE_DAYS = 1

  def GetReportData(self, get_report_args, token):
    """Extract only the operating system type from the active histogram."""
    report = rdf_report_plugins.ApiReportData(
        representation_type=rdf_report_plugins.ApiReportData.RepresentationType
        .PIE_CHART)

    graph_series = client_report_utils.FetchMostRecentGraphSeries(
        get_report_args.client_label,
        rdf_stats.ClientGraphSeries.ReportType.OS_RELEASE,
        token=token)
    if graph_series is not None:
      for graph in graph_series.graphs:
        # Find the correct graph and merge the OS categories together
        if "%s day" % self.__class__.ACTIVE_DAYS in graph.title:
          for sample in graph:
            report.pie_chart.data.Append(
                rdf_report_plugins.ApiReportDataPoint1D(
                    label=sample.label, x=sample.y_value))
          break
    report.pie_chart.data = sorted(
        report.pie_chart.data, key=lambda point: point.label)
    return report


class OSReleaseBreakdown7ReportPlugin(OSReleaseBreakdown1ReportPlugin):
  """Displays a histogram of last client activities."""

  TITLE = "OS Release Breakdown - 7 Days Active"

  ACTIVE_DAYS = 7


class OSReleaseBreakdown14ReportPlugin(OSReleaseBreakdown1ReportPlugin):
  """Displays a histogram of last client activities."""

  TITLE = "OS Release Breakdown - 14 Days Active"

  ACTIVE_DAYS = 14


class OSReleaseBreakdown30ReportPlugin(OSReleaseBreakdown1ReportPlugin):
  """Displays a histogram of last client activities."""

  TITLE = "OS Release Breakdown - 30 Days Active"

  ACTIVE_DAYS = 30
