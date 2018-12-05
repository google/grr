#!/usr/bin/env python
"""Tests for report plugins."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
import math
import os

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import events
from grr_response_server.aff4_objects import filestore_test_lib
from grr_response_server.flows.cron import filestore_stats
from grr_response_server.flows.cron import system as cron_system

from grr_response_server.flows.general import audit
from grr_response_server.gui.api_plugins import stats as stats_api
from grr_response_server.gui.api_plugins.report_plugins import client_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import filestore_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugins_test_mocks
from grr_response_server.gui.api_plugins.report_plugins import server_report_plugins
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ReportPluginsTest(test_lib.GRRBaseTest):

  def testGetAvailableReportPlugins(self):
    """Ensure GetAvailableReportPlugins lists ReportPluginBase's subclasses."""

    with report_plugins_test_mocks.MockedReportPlugins():
      self.assertIn(report_plugins_test_mocks.FooReportPlugin,
                    report_plugins.GetAvailableReportPlugins())
      self.assertIn(report_plugins_test_mocks.BarReportPlugin,
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


def AddFakeAuditLog(description=None,
                    client=None,
                    user=None,
                    token=None,
                    **kwargs):
  events.Events.PublishEvent(
      "Audit",
      rdf_events.AuditEvent(
          description=description, client=client, user=user, **kwargs),
      token=token)


class ReportUtilsTest(test_lib.GRRBaseTest):

  def testAuditLogsForTimespan(self):
    two_weeks_ago = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("2w")
    with test_lib.FakeTime(two_weeks_ago):
      AddFakeAuditLog("Fake outdated audit log.", token=self.token)
    AddFakeAuditLog("Fake audit description foo.", token=self.token)
    AddFakeAuditLog("Fake audit description bar.", token=self.token)

    audit_events = {
        ev.description: ev for fd in audit.LegacyAuditLogsForTimespan(
            rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("1d"),
            rdfvalue.RDFDatetime.Now(),
            token=self.token) for ev in fd.GenerateItems()
    }

    self.assertIn("Fake audit description foo.", audit_events)
    self.assertIn("Fake audit description bar.", audit_events)
    self.assertNotIn("Fake outdated audit log.", audit_events)


class ClientReportPluginsTest(test_lib.GRRBaseTest):

  def MockClients(self):
    client_ping_time = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration("8d")
    self.SetupClients(20, ping=client_ping_time)

  def testGRRVersionReportPlugin(self):
    self.MockClients()

    # Scan for activity to be reported.
    flow_test_lib.TestFlowHelper(
        cron_system.GRRVersionBreakDown.__name__, token=self.token)

    report = report_plugins.GetReportByName(
        client_report_plugins.GRRVersion30ReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__, client_label="All"),
        token=self.token)

    self.assertEqual(
        api_report_data.representation_type,
        rdf_report_plugins.ApiReportData.RepresentationType.LINE_CHART)

    self.assertLen(api_report_data.line_chart.data, 1)
    self.assertEqual(api_report_data.line_chart.data[0].label,
                     "GRR Monitor %s" % config.CONFIG["Source.version_numeric"])
    self.assertLen(api_report_data.line_chart.data[0].points, 1)
    self.assertEqual(api_report_data.line_chart.data[0].points[0].y, 20)

  def testGRRVersionReportPluginWithNoActivityToReport(self):
    # Scan for activity to be reported.
    flow_test_lib.TestFlowHelper(
        cron_system.GRRVersionBreakDown.__name__, token=self.token)

    report = report_plugins.GetReportByName(
        client_report_plugins.GRRVersion30ReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__, client_label="All"),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.LINE_CHART,
            line_chart=rdf_report_plugins.ApiLineChartReportData(data=[])))

  def testLastActiveReportPlugin(self):
    self.MockClients()

    # Scan for activity to be reported.
    flow_test_lib.TestFlowHelper(
        cron_system.LastAccessStats.__name__, token=self.token)

    report = report_plugins.GetReportByName(
        client_report_plugins.LastActiveReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__, client_label="All"),
        token=self.token)

    self.assertEqual(
        api_report_data.representation_type,
        rdf_report_plugins.ApiReportData.RepresentationType.LINE_CHART)

    labels = [
        "60 day active", "30 day active", "7 day active", "3 day active",
        "1 day active"
    ]
    ys = [20, 20, 0, 0, 0]
    for series, label, y in itertools.izip(api_report_data.line_chart.data,
                                           labels, ys):
      self.assertEqual(series.label, label)
      self.assertLen(series.points, 1)
      self.assertEqual(series.points[0].y, y)

  def testLastActiveReportPluginWithNoActivityToReport(self):
    # Scan for activity to be reported.
    flow_test_lib.TestFlowHelper(
        cron_system.LastAccessStats.__name__, token=self.token)

    report = report_plugins.GetReportByName(
        client_report_plugins.LastActiveReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__, client_label="All"),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.LINE_CHART,
            line_chart=rdf_report_plugins.ApiLineChartReportData(data=[])))

  def testOSBreakdownReportPlugin(self):
    # Add a client to be reported.
    self.SetupClients(1)

    # Scan for clients to be reported (the one we just added).
    flow_test_lib.TestFlowHelper(
        cron_system.OSBreakDown.__name__, token=self.token)

    report = report_plugins.GetReportByName(
        client_report_plugins.OSBreakdown30ReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__, client_label="All"),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            pie_chart=rdf_report_plugins.ApiPieChartReportData(data=[
                rdf_report_plugins.ApiReportDataPoint1D(label="Linux", x=1)
            ]),
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.PIE_CHART))

  def testOSBreakdownReportPluginWithNoDataToReport(self):
    report = report_plugins.GetReportByName(
        client_report_plugins.OSBreakdown30ReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__, client_label="All"),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            pie_chart=rdf_report_plugins.ApiPieChartReportData(data=[]),
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.PIE_CHART))

  def testOSReleaseBreakdownReportPlugin(self):
    # Add a client to be reported.
    self.SetupClients(1)

    # Scan for clients to be reported (the one we just added).
    flow_test_lib.TestFlowHelper(
        cron_system.OSBreakDown.__name__, token=self.token)

    report = report_plugins.GetReportByName(
        client_report_plugins.OSReleaseBreakdown30ReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__, client_label="All"),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            pie_chart=rdf_report_plugins.ApiPieChartReportData(data=[
                rdf_report_plugins.ApiReportDataPoint1D(label="Unknown", x=1)
            ]),
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.PIE_CHART))

  def testOSReleaseBreakdownReportPluginWithNoDataToReport(self):
    report = report_plugins.GetReportByName(
        client_report_plugins.OSReleaseBreakdown30ReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__, client_label="All"),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            pie_chart=rdf_report_plugins.ApiPieChartReportData(data=[]),
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.PIE_CHART))


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
        math.log10(x) for x in [
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
    client_id = self.SetupClient(0)

    # Add a file to be reported.
    filestore_test_lib.AddFileToFileStore(
        rdf_paths.PathSpec(
            pathtype=rdf_paths.PathSpec.PathType.OS,
            path=os.path.join(self.base_path, filename)),
        client_id=client_id,
        token=self.token)

    # Scan for files to be reported (the one we just added).
    flow_test_lib.TestFlowHelper(
        filestore_stats.FilestoreStatsCronFlow.__name__, token=self.token)

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
    flow_test_lib.TestFlowHelper(
        filestore_stats.FilestoreStatsCronFlow.__name__, token=self.token)

    report = report_plugins.GetReportByName(
        filestore_report_plugins.FileSizeDistributionReportPlugin.__name__)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(name=report.__class__.__name__),
        token=self.token)

    self.checkStaticData(api_report_data)

    for series in api_report_data.stack_chart.data:
      self.assertEqual([p.y for p in series.points], [0])


class ServerReportPluginsTest(test_lib.GRRBaseTest):

  def testClientApprovalsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action
          .CLIENT_APPROVAL_BREAK_GLASS_REQUEST,
          user="User123",
          description="Approval request description.",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1):
      for i in range(10):
        AddFakeAuditLog(
            action=rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST,
            user="User%d" % i,
            description="Approval request.",
            token=self.token)

      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action.CLIENT_APPROVAL_GRANT,
          user="User456",
          description="Grant.",
          token=self.token)

    report = report_plugins.GetReportByName(
        server_report_plugins.ClientApprovalsReportPlugin.__name__)

    start = rdfvalue.RDFDatetime.FromHumanReadable("2012/12/15")
    month_duration = rdfvalue.Duration("30d")

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start,
            duration=month_duration),
        token=self.token)

    self.assertEqual(
        api_report_data.representation_type,
        rdf_report_plugins.ApiReportData.RepresentationType.AUDIT_CHART)

    self.assertEqual(api_report_data.audit_chart.used_fields,
                     ["action", "client", "description", "timestamp", "user"])

    rows = api_report_data.audit_chart.rows
    self.assertEqual(
        [(row.action, row.client, row.description, row.user) for row in rows],
        [
            (rdf_events.AuditEvent.Action.CLIENT_APPROVAL_GRANT, None,
             "Grant.", "User456"),
            (rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST, None,
             "Approval request.", "User9"),
            (rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST, None,
             "Approval request.", "User8"),
            (rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST, None,
             "Approval request.", "User7"),
            (rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST, None,
             "Approval request.", "User6"),
            (rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST, None,
             "Approval request.", "User5"),
            (rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST, None,
             "Approval request.", "User4"),
            (rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST, None,
             "Approval request.", "User3"),
            (rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST, None,
             "Approval request.", "User2"),
            (rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST, None,
             "Approval request.", "User1"),
            (rdf_events.AuditEvent.Action.CLIENT_APPROVAL_REQUEST, None,
             "Approval request.", "User0")])  # pyformat: disable

  def testClientApprovalsReportPluginWithNoActivityToReport(self):
    report = report_plugins.GetReportByName(
        server_report_plugins.ClientApprovalsReportPlugin.__name__)

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
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.AUDIT_CHART,
            audit_chart=rdf_report_plugins.ApiAuditChartReportData(
                used_fields=[
                    "action", "client", "description", "timestamp", "user"
                ],
                rows=[])))

  def testHuntActionsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action.HUNT_CREATED,
          user="User123",
          flow_name="Flow123",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1):
      for i in range(10):
        AddFakeAuditLog(
            action=rdf_events.AuditEvent.Action.HUNT_MODIFIED,
            user="User%d" % i,
            flow_name="Flow%d" % i,
            token=self.token)

      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action.HUNT_PAUSED,
          user="User456",
          flow_name="Flow456",
          token=self.token)

    report = report_plugins.GetReportByName(
        server_report_plugins.HuntActionsReportPlugin.__name__)

    start = rdfvalue.RDFDatetime.FromHumanReadable("2012/12/15")
    month_duration = rdfvalue.Duration("30d")

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start,
            duration=month_duration),
        token=self.token)

    self.assertEqual(
        api_report_data.representation_type,
        rdf_report_plugins.ApiReportData.RepresentationType.AUDIT_CHART)

    self.assertEqual(
        api_report_data.audit_chart.used_fields,
        ["action", "description", "flow_name", "timestamp", "urn", "user"])

    self.assertEqual([(row.action, row.description, row.flow_name,
                       row.timestamp.Format("%Y/%m/%d"), row.urn, row.user)
                      for row in api_report_data.audit_chart.rows],
                     [(rdf_events.AuditEvent.Action.HUNT_PAUSED, "", "Flow456",
                       "2012/12/22", None, "User456"),
                      (rdf_events.AuditEvent.Action.HUNT_MODIFIED, "", "Flow9",
                       "2012/12/22", None, "User9"),
                      (rdf_events.AuditEvent.Action.HUNT_MODIFIED, "", "Flow8",
                       "2012/12/22", None, "User8"),
                      (rdf_events.AuditEvent.Action.HUNT_MODIFIED, "", "Flow7",
                       "2012/12/22", None, "User7"),
                      (rdf_events.AuditEvent.Action.HUNT_MODIFIED, "", "Flow6",
                       "2012/12/22", None, "User6"),
                      (rdf_events.AuditEvent.Action.HUNT_MODIFIED, "", "Flow5",
                       "2012/12/22", None, "User5"),
                      (rdf_events.AuditEvent.Action.HUNT_MODIFIED, "", "Flow4",
                       "2012/12/22", None, "User4"),
                      (rdf_events.AuditEvent.Action.HUNT_MODIFIED, "", "Flow3",
                       "2012/12/22", None, "User3"),
                      (rdf_events.AuditEvent.Action.HUNT_MODIFIED, "", "Flow2",
                       "2012/12/22", None, "User2"),
                      (rdf_events.AuditEvent.Action.HUNT_MODIFIED, "", "Flow1",
                       "2012/12/22", None, "User1"),
                      (rdf_events.AuditEvent.Action.HUNT_MODIFIED, "",
                       "Flow0", "2012/12/22", None, "User0")
                     ])  # pyformat: disable

  def testHuntActionsReportPluginWithNoActivityToReport(self):
    report = report_plugins.GetReportByName(
        server_report_plugins.HuntActionsReportPlugin.__name__)

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
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.AUDIT_CHART,
            audit_chart=rdf_report_plugins.ApiAuditChartReportData(
                used_fields=[
                    "action", "description", "flow_name", "timestamp", "urn",
                    "user"
                ],
                rows=[])))

  def testHuntApprovalsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action.HUNT_APPROVAL_GRANT,
          user="User123",
          description="Approval grant description.",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1):
      for i in range(10):
        AddFakeAuditLog(
            action=rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
            user="User%d" % i,
            description="Approval request.",
            token=self.token)

      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action.HUNT_APPROVAL_GRANT,
          user="User456",
          description="Another grant.",
          token=self.token)

    report = report_plugins.GetReportByName(
        server_report_plugins.HuntApprovalsReportPlugin.__name__)

    start = rdfvalue.RDFDatetime.FromHumanReadable("2012/12/15")
    month_duration = rdfvalue.Duration("30d")

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start,
            duration=month_duration),
        token=self.token)

    self.assertEqual(
        api_report_data.representation_type,
        rdf_report_plugins.ApiReportData.RepresentationType.AUDIT_CHART)

    self.assertEqual(api_report_data.audit_chart.used_fields,
                     ["action", "description", "timestamp", "urn", "user"])
    self.assertEqual([(row.action, row.description,
                       row.timestamp.Format("%Y/%m/%d"), row.urn, row.user)
                      for row in api_report_data.audit_chart.rows],
                     [(rdf_events.AuditEvent.Action.HUNT_APPROVAL_GRANT,
                       "Another grant.", "2012/12/22", None, "User456"),
                      (rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User9"),
                      (rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User8"),
                      (rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User7"),
                      (rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User6"),
                      (rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User5"),
                      (rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User4"),
                      (rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User3"),
                      (rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User2"),
                      (rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User1"),
                      (rdf_events.AuditEvent.Action.HUNT_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User0")
                     ])  # pyformat: disable

  def testHuntApprovalsReportPluginWithNoActivityToReport(self):
    report = report_plugins.GetReportByName(
        server_report_plugins.HuntApprovalsReportPlugin.__name__)

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
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.AUDIT_CHART,
            audit_chart=rdf_report_plugins.ApiAuditChartReportData(
                used_fields=[
                    "action", "description", "timestamp", "urn", "user"
                ],
                rows=[])))

  def testCronApprovalsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action.CRON_APPROVAL_GRANT,
          user="User123",
          description="Approval grant description.",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1):
      for i in range(10):
        AddFakeAuditLog(
            action=rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
            user="User%d" % i,
            description="Approval request.",
            token=self.token)

      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action.CRON_APPROVAL_GRANT,
          user="User456",
          description="Another grant.",
          token=self.token)

    report = report_plugins.GetReportByName(
        server_report_plugins.CronApprovalsReportPlugin.__name__)

    start = rdfvalue.RDFDatetime.FromHumanReadable("2012/12/15")
    month_duration = rdfvalue.Duration("30d")

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start,
            duration=month_duration),
        token=self.token)

    self.assertEqual(
        api_report_data.representation_type,
        rdf_report_plugins.ApiReportData.RepresentationType.AUDIT_CHART)

    self.assertEqual(api_report_data.audit_chart.used_fields,
                     ["action", "description", "timestamp", "urn", "user"])

    self.assertEqual([(row.action, row.description,
                       row.timestamp.Format("%Y/%m/%d"), row.urn, row.user)
                      for row in api_report_data.audit_chart.rows],
                     [(rdf_events.AuditEvent.Action.CRON_APPROVAL_GRANT,
                       "Another grant.", "2012/12/22", None, "User456"),
                      (rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User9"),
                      (rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User8"),
                      (rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User7"),
                      (rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User6"),
                      (rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User5"),
                      (rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User4"),
                      (rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User3"),
                      (rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User2"),
                      (rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User1"),
                      (rdf_events.AuditEvent.Action.CRON_APPROVAL_REQUEST,
                       "Approval request.", "2012/12/22", None, "User0")
                     ])  # pyformat: disable

  def testCronApprovalsReportPluginWithNoActivityToReport(self):
    report = report_plugins.GetReportByName(
        server_report_plugins.CronApprovalsReportPlugin.__name__)

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
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.AUDIT_CHART,
            audit_chart=rdf_report_plugins.ApiAuditChartReportData(
                used_fields=[
                    "action", "description", "timestamp", "urn", "user"
                ],
                rows=[])))

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
      for _ in range(10):
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
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.PIE_CHART,
            pie_chart=rdf_report_plugins.ApiPieChartReportData(data=[])))

  def testSystemFlowsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action.RUN_FLOW,
          user="GRR",
          flow_name="Flow123",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22")):
      for _ in range(10):
        AddFakeAuditLog(
            action=rdf_events.AuditEvent.Action.RUN_FLOW,
            user="GRR",
            flow_name="Flow123",
            token=self.token)

      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action.RUN_FLOW,
          user="GRR",
          flow_name="Flow456",
          token=self.token)

    report = report_plugins.GetReportByName(
        server_report_plugins.SystemFlowsReportPlugin.__name__)

    start = rdfvalue.RDFDatetime.FromHumanReadable("2012/12/15")
    month_duration = rdfvalue.Duration("30d")

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start,
            duration=month_duration),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(
                x_ticks=[],
                data=[
                    rdf_report_plugins.ApiReportDataSeries2D(
                        label=u"Flow123\u2003Run By: GRR (10)",
                        points=[
                            rdf_report_plugins.ApiReportDataPoint2D(x=0, y=10)
                        ]),
                    rdf_report_plugins.ApiReportDataSeries2D(
                        label=u"Flow456\u2003Run By: GRR (1)",
                        points=[
                            rdf_report_plugins.ApiReportDataPoint2D(x=1, y=1)
                        ])
                ])))

  def testSystemFlowsReportPluginWithNoActivityToReport(self):
    report = report_plugins.GetReportByName(
        server_report_plugins.SystemFlowsReportPlugin.__name__)

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
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(x_ticks=[])))

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
      for _ in range(10):
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
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(data=[])))

  def testUserFlowsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action.RUN_FLOW,
          user="User123",
          flow_name="Flow123",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22")):
      for _ in range(10):
        AddFakeAuditLog(
            action=rdf_events.AuditEvent.Action.RUN_FLOW,
            user="User123",
            flow_name="Flow123",
            token=self.token)

      AddFakeAuditLog(
          action=rdf_events.AuditEvent.Action.RUN_FLOW,
          user="User456",
          flow_name="Flow456",
          token=self.token)

    report = report_plugins.GetReportByName(
        server_report_plugins.UserFlowsReportPlugin.__name__)

    start = rdfvalue.RDFDatetime.FromHumanReadable("2012/12/15")
    month_duration = rdfvalue.Duration("30d")

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start,
            duration=month_duration),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(
                x_ticks=[],
                data=[
                    rdf_report_plugins.ApiReportDataSeries2D(
                        label=u"Flow123\u2003Run By: User123 (10)",
                        points=[
                            rdf_report_plugins.ApiReportDataPoint2D(x=0, y=10)
                        ]),
                    rdf_report_plugins.ApiReportDataSeries2D(
                        label=u"Flow456\u2003Run By: User456 (1)",
                        points=[
                            rdf_report_plugins.ApiReportDataPoint2D(x=1, y=1)
                        ])
                ])))

  def testUserFlowsReportPluginWithNoActivityToReport(self):
    report = report_plugins.GetReportByName(
        server_report_plugins.UserFlowsReportPlugin.__name__)

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
            representation_type=rdf_report_plugins.ApiReportData
            .RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(x_ticks=[])))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
