#!/usr/bin/env python
"""Tests for report plugins."""

from grr.gui.api_plugins import stats as stats_api
from grr.gui.api_plugins.report_plugins import rdf_report_plugins
from grr.gui.api_plugins.report_plugins import report_plugins
from grr.gui.api_plugins.report_plugins import report_plugins_test_mocks
from grr.gui.api_plugins.report_plugins import report_utils
from grr.gui.api_plugins.report_plugins import server_report_plugins

from grr.lib import events
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class ReportPluginsTest(test_lib.GRRBaseTest):

  def testGetAvailableReportPlugins(self):
    """Ensure GetAvailableReportPlugins lists ReportPluginBase's subclasses."""

    with report_plugins_test_mocks.MockedReportPlugins():
      self.assertTrue(report_plugins_test_mocks.FooReportPlugin in
                      report_plugins.GetAvailableReportPlugins())
      self.assertTrue(report_plugins_test_mocks.BarReportPlugin in
                      report_plugins.GetAvailableReportPlugins())

  def testGetReportByName(self):
    """Ensure GetReportByName instantiates correct subclasses based on name."""

    with report_plugins_test_mocks.MockedReportPlugins():
      report_object = report_plugins.GetReportByName("BarReportPlugin")
      self.assertTrue(
          isinstance(report_object, report_plugins_test_mocks.BarReportPlugin))

  def testGetReportDescriptor(self):
    """Ensure GetReportDescriptor returns a correctly filled in proto."""

    desc = report_plugins_test_mocks.BarReportPlugin.GetReportDescriptor()

    self.assertEqual(desc.type,
                     rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER)
    self.assertEqual(desc.title, "Bar Activity")
    self.assertEqual(desc.summary,
                     "Reports bars' activity in the given time range.")
    self.assertEqual(desc.requires_time_range, True)


def AddFakeAuditLog(description, client=None, user=None, token=None):
  events.Events.PublishEventInline(
      "Audit",
      events.AuditEvent(
          description=description, client=client, user=user),
      token=token)


class ReportUtilsTest(test_lib.GRRBaseTest):

  def testGetAuditLogFiles(self):
    AddFakeAuditLog("Fake audit description foo.", token=self.token)
    AddFakeAuditLog("Fake audit description bar.", token=self.token)

    audit_events = {
        ev.description: ev
        for fd in report_utils.GetAuditLogFiles(
            rdfvalue.Duration("1d"),
            rdfvalue.RDFDatetime.Now(),
            token=self.token) for ev in fd.GenerateItems()
    }

    self.assertIn("Fake audit description foo.", audit_events)
    self.assertIn("Fake audit description bar.", audit_events)


class ServerReportPluginsTest(test_lib.GRRBaseTest):

  def testMostActiveUsersReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          "Fake audit description 14 Dec.",
          "C.123",
          "User123",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22")):
      for _ in xrange(10):
        AddFakeAuditLog(
            "Fake audit description 22 Dec.",
            "C.123",
            "User123",
            token=self.token)

      AddFakeAuditLog(
          "Fake audit description 22 Dec.",
          "C.456",
          "User456",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/31")):
      report = server_report_plugins.MostActiveUsersReportPlugin()

      now = rdfvalue.RDFDatetime().Now()
      month_duration = rdfvalue.Duration("30d")

      api_report_data = report.GetReportData(
          stats_api.ApiGetReportArgs(
              name=report.__class__.__name__,
              start_time=now - month_duration,
              duration=month_duration),
          token=self.token)

      # pyformat: disable
      self.assertEqual(
          api_report_data,
          rdf_report_plugins.ApiReportData(
              representation_type=rdf_report_plugins.ApiReportData.
              RepresentationType.PIE_CHART,
              pie_chart=rdf_report_plugins.ApiPieChartReportData(
                  data=[
                      rdf_report_plugins.ApiReportDataPoint1D(
                          label="User123",
                          x=11
                      ),
                      rdf_report_plugins.ApiReportDataPoint1D(
                          label="User456",
                          x=1
                      )
                  ]
              )))
      # pyformat: enable

  def testMostActiveUsersReportPluginWithNoActivityToReport(self):
    report = server_report_plugins.MostActiveUsersReportPlugin()

    now = rdfvalue.RDFDatetime().Now()
    month_duration = rdfvalue.Duration("30d")

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=now - month_duration,
            duration=month_duration),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            representation_type=rdf_report_plugins.ApiReportData.
            RepresentationType.PIE_CHART,
            pie_chart=rdf_report_plugins.ApiPieChartReportData(data=[])))

  def testUserActivityReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          "Fake audit description 14 Dec.",
          "C.123",
          "User123",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22")):
      for _ in xrange(10):
        AddFakeAuditLog(
            "Fake audit description 22 Dec.",
            "C.123",
            "User123",
            token=self.token)

      AddFakeAuditLog(
          "Fake audit description 22 Dec.",
          "C.456",
          "User456",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/31")):
      report = server_report_plugins.UserActivityReportPlugin()

      api_report_data = report.GetReportData(
          stats_api.ApiGetReportArgs(name=report.__class__.__name__),
          token=self.token)

      # pyformat: disable
      self.assertEqual(
          api_report_data,
          rdf_report_plugins.ApiReportData(
              representation_type=rdf_report_plugins.ApiReportData.
              RepresentationType.STACK_CHART,
              stack_chart=rdf_report_plugins.ApiStackChartReportData(
                  data=[
                      rdf_report_plugins.ApiReportDataSeries2D(
                          label=u"User123",
                          points=[
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-10, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-9, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-8, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-7, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-6, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-5, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-4, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-3, y=1),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-2, y=10),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-1, y=0)
                          ]
                      ),
                      rdf_report_plugins.ApiReportDataSeries2D(
                          label=u"User456",
                          points=[
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-10, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-9, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-8, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-7, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-6, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-5, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-4, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-3, y=0),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-2, y=1),
                              rdf_report_plugins.ApiReportDataPoint2D(
                                  x=-1, y=0)
                          ])])))
      # pyformat: enable

  def testUserActivityReportPluginWithNoActivityToReport(self):
    report = server_report_plugins.UserActivityReportPlugin()

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(name=report.__class__.__name__),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            representation_type=rdf_report_plugins.ApiReportData.
            RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(data=[])))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
