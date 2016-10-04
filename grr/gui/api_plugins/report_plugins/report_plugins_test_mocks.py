#!/usr/bin/env python
"""This module contains report plugin mocks used for testing."""

from grr.gui.api_plugins.report_plugins import report_plugins
from grr.lib import rdfvalue
from grr.lib import utils


class FooReportPlugin(report_plugins.ReportPluginBase):
  TYPE = report_plugins.ApiReportDescriptor.ReportType.CLIENT
  TITLE = "Foo"
  SUMMARY = "Reports all foos."


class BarReportPlugin(report_plugins.ReportPluginBase):
  TYPE = report_plugins.ApiReportDescriptor.ReportType.SERVER
  TITLE = "Bar Activity"
  SUMMARY = "Reports bars' activity in the given time range."
  REQUIRES_TIME_RANGE = True

  def GetReportData(self, get_report_args, token):
    ret = report_plugins.ApiReportData(
        representation_type=report_plugins.ApiReportData.RepresentationType.
        STACK_CHART)

    database = {
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/11"): (1, 0),
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/12"): (2, 1),
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/13"): (3, 2),
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14"): (5, 3),
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/15"): (8, 4),
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/16"): (13, 5),
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/17"): (21, 6),
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/18"): (34, 7)
    }

    ret.stack_chart.data = [
        report_plugins.ApiReportDataSeries2D(
            label="Bar",
            points=[
                report_plugins.ApiReportDataPoint2D(
                    x=x, y=y) for (t, (x, y)) in sorted(database.iteritems())
                if get_report_args.start_time <= t and t <
                get_report_args.start_time + get_report_args.duration
            ])
    ]

    return ret


class MockedReportPlugins(object):
  """A context manager that swaps available reports with the mocked reports."""

  def __init__(self):
    self.stubber = utils.Stubber(report_plugins.ReportPluginBase, "classes", {
        "FooReportPlugin": FooReportPlugin,
        "BarReportPlugin": BarReportPlugin
    })

  def __enter__(self):
    self.Start()

  def __exit__(self, *_):
    self.Stop()

  def Start(self):
    self.stubber.Start()

  def Stop(self):
    self.stubber.Stop()
