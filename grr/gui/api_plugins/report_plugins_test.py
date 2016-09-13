#!/usr/bin/env python
"""Tests for report plugins."""

from grr.gui.api_plugins import report_plugins

from grr.lib import flags
from grr.lib import test_lib
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


class ReportPluginsTest(test_lib.GRRBaseTest):

  def testGetAvailableReportPlugins(self):
    """Ensure GetAvailableReportPlugins lists ReportPluginBase's subclasses."""

    with utils.Stubber(report_plugins.ReportPluginBase, "classes", {
        "FooReportPlugin": FooReportPlugin,
        "BarReportPlugin": BarReportPlugin
    }):
      self.assertTrue(
          FooReportPlugin in report_plugins.GetAvailableReportPlugins())
      self.assertTrue(
          BarReportPlugin in report_plugins.GetAvailableReportPlugins())

  def testGetReportByName(self):
    """Ensure GetReportByName instantiates correct subclasses based on name."""

    with utils.Stubber(report_plugins.ReportPluginBase, "classes", {
        "FooReportPlugin": FooReportPlugin,
        "BarReportPlugin": BarReportPlugin
    }):
      report_object = report_plugins.GetReportByName("BarReportPlugin")
      self.assertTrue(isinstance(report_object, BarReportPlugin))

  def testGetReportDescriptor(self):
    """Ensure GetReportDescriptor returns a correctly filled in proto."""

    desc = BarReportPlugin.GetReportDescriptor()

    self.assertEqual(desc.type,
                     report_plugins.ApiReportDescriptor.ReportType.SERVER)
    self.assertEqual(desc.title, "Bar Activity")
    self.assertEqual(desc.summary,
                     "Reports bars' activity in the given time range.")
    self.assertEqual(desc.requires_time_range, True)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
