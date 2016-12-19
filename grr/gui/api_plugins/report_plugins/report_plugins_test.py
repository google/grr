#!/usr/bin/env python
"""Tests for report plugins."""

import itertools
import math
import os

from grr.gui.api_plugins import stats as stats_api
from grr.gui.api_plugins.report_plugins import filestore_report_plugins
from grr.gui.api_plugins.report_plugins import rdf_report_plugins
from grr.gui.api_plugins.report_plugins import report_plugins
from grr.gui.api_plugins.report_plugins import report_plugins_test_mocks
from grr.gui.api_plugins.report_plugins import report_utils
from grr.gui.api_plugins.report_plugins import server_report_plugins

from grr.lib import events
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import filestore_test
from grr.lib.flows.cron import filestore_stats
from grr.lib.rdfvalues import paths as rdf_paths


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


class FileStoreReportPluginsTest(test_lib.GRRBaseTest):

  def checkStaticData(self, api_report_data):
    self.assertEqual(
        api_report_data.representation_type,
        rdf_report_plugins.ApiReportData.RepresentationType.STACK_CHART)

    labels = [
        "0 B - 2 B", "2 B - 50 B", "50 B - 100 B", "100 B - 1000 B",
        "1000 B - 9.8 KiB", "9.8 KiB - 97.7 KiB", "97.7 KiB - 488.3 KiB",
        "488.3 KiB - 976.6 KiB", "976.6 KiB - 4.8 MiB", "4.8 MiB - 9.5 MiB",
        "9.5 MiB - 47.7 MiB", "47.7 MiB - 95.4 MiB", "95.4 MiB - 476.8 MiB",
        "476.8 MiB - 953.7 MiB", "953.7 MiB - 4.7 GiB", "4.7 GiB - 9.3 GiB",
        u"9.3 GiB - \u221E"
    ]

    xs = [0.] + [
        math.log10(x)
        for x in [
            2, 50, 100, 1e3, 10e3, 100e3, 500e3, 1e6, 5e6, 10e6, 50e6, 100e6,
            500e6, 1e9, 5e9, 10e9
        ]
    ]

    for series, label, x in itertools.izip(api_report_data.stack_chart.data,
                                           labels, xs):
      self.assertEqual(series.label, label)
      self.assertAlmostEqual([p.x for p in series.points], [x])

    self.assertEqual(api_report_data.stack_chart.bar_width, .2)
    self.assertEqual([t.label for t in api_report_data.stack_chart.x_ticks], [
        "1 B", "32 B", "1 KiB", "32 KiB", "1 MiB", "32 MiB", "1 GiB", "32 GiB",
        "1 TiB", "32 TiB", "1 PiB", "32 PiB", "1024 PiB", "32768 PiB",
        "1048576 PiB"
    ])

    self.assertAlmostEqual(api_report_data.stack_chart.x_ticks[0].x, 0.)
    for diff in (
        t2.x - t1.x
        for t1, t2 in itertools.izip(api_report_data.stack_chart.x_ticks[:-1],
                                     api_report_data.stack_chart.x_ticks[1:])):
      self.assertAlmostEqual(math.log10(32), diff)

  def testFileSizeDistributionReportPlugin(self):
    filename = "winexec_img.dd"
    client_id, = self.SetupClients(1)

    # Add a file to be reported.
    filestore_test.HashFileStoreTest.AddFileToFileStore(
        rdf_paths.PathSpec(
            pathtype=rdf_paths.PathSpec.PathType.OS,
            path=os.path.join(self.base_path, filename)),
        client_id=client_id,
        token=self.token)

    # Scan for files to be reported (the one we just added).
    for _ in test_lib.TestFlowHelper(
        filestore_stats.FilestoreStatsCronFlow.__name__, token=self.token):
      pass

    report = report_plugins.GetReportByName(
        filestore_report_plugins.FileSizeDistributionReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(name=report.__class__.__name__),
        token=self.token)

    self.checkStaticData(api_report_data)

    for series in api_report_data.stack_chart.data:
      if series.label == "976.6 KiB - 4.8 MiB":
        self.assertEqual([p.y for p in series.points], [1])
      else:
        self.assertEqual([p.y for p in series.points], [0])

  def testFileSizeDistributionReportPluginWithNothingToReport(self):
    # Scan for files to be reported.
    for _ in test_lib.TestFlowHelper(
        filestore_stats.FilestoreStatsCronFlow.__name__, token=self.token):
      pass

    report = report_plugins.GetReportByName(
        filestore_report_plugins.FileSizeDistributionReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(name=report.__class__.__name__),
        token=self.token)

    self.checkStaticData(api_report_data)

    for series in api_report_data.stack_chart.data:
      self.assertEqual([p.y for p in series.points], [0])

  def testFileClientCountReportPlugin(self):
    filename = "winexec_img.dd"
    client_id, = self.SetupClients(1)

    # Add a file to be reported.
    filestore_test.HashFileStoreTest.AddFileToFileStore(
        rdf_paths.PathSpec(
            pathtype=rdf_paths.PathSpec.PathType.OS,
            path=os.path.join(self.base_path, filename)),
        client_id=client_id,
        token=self.token)

    # Scan for files to be reported (the one we just added).
    for _ in test_lib.TestFlowHelper(
        filestore_stats.FilestoreStatsCronFlow.__name__, token=self.token):
      pass

    report = report_plugins.GetReportByName(
        filestore_report_plugins.FileClientCountReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(name=report.__class__.__name__),
        token=self.token)

    # pyformat: disable
    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            representation_type=rdf_report_plugins.ApiReportData.
            RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(data=[
                rdf_report_plugins.ApiReportDataSeries2D(
                    label=u"0",
                    points=[rdf_report_plugins.ApiReportDataPoint2D(x=0, y=0)]
                ),
                rdf_report_plugins.ApiReportDataSeries2D(
                    label=u"1",
                    points=[rdf_report_plugins.ApiReportDataPoint2D(x=1, y=1)]
                ),
                rdf_report_plugins.ApiReportDataSeries2D(
                    label=u"5",
                    points=[rdf_report_plugins.ApiReportDataPoint2D(x=5, y=0)]
                ),
                rdf_report_plugins.ApiReportDataSeries2D(
                    label=u"10",
                    points=[rdf_report_plugins.ApiReportDataPoint2D(x=10, y=0)]
                ),
                rdf_report_plugins.ApiReportDataSeries2D(
                    label=u"20",
                    points=[rdf_report_plugins.ApiReportDataPoint2D(x=20, y=0)]
                ),
                rdf_report_plugins.ApiReportDataSeries2D(
                    label=u"50",
                    points=[rdf_report_plugins.ApiReportDataPoint2D(x=50, y=0)]
                ),
                rdf_report_plugins.ApiReportDataSeries2D(
                    label=u"100",
                    points=[rdf_report_plugins.ApiReportDataPoint2D(x=100, y=0)]
                )
            ])))
    # pyformat: enable


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

    report = report_plugins.GetReportByName(
        server_report_plugins.MostActiveUsersReportPlugin.__name__)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/31")):

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
    report = report_plugins.GetReportByName(
        server_report_plugins.MostActiveUsersReportPlugin.__name__)

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


class UserActivityReportPluginTest(test_lib.GRRBaseTest):

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

    report = report_plugins.GetReportByName(
        server_report_plugins.UserActivityReportPlugin.__name__)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/31")):

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
    report = report_plugins.GetReportByName(
        server_report_plugins.UserActivityReportPlugin.__name__)

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
