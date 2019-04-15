#!/usr/bin/env python
"""Tests for report plugins."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
import math

from absl import app
from future.builtins import range

from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server.flows.cron import system as cron_system

from grr_response_server.flows.general import audit
from grr_response_server.gui.api_plugins import stats as stats_api
from grr_response_server.gui.api_plugins.report_plugins import client_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugins_test_mocks
from grr_response_server.gui.api_plugins.report_plugins import server_report_plugins
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

ApiReportDataPoint2D = rdf_report_plugins.ApiReportDataPoint2D
RepresentationType = rdf_report_plugins.ApiReportData.RepresentationType
Action = rdf_events.AuditEvent.Action


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
                    action=None,
                    flow_name=None,
                    urn=None,
                    router_method_name=None,
                    http_request_path=None,
                    token=None):
  events.Events.PublishEvent(
      "Audit",
      rdf_events.AuditEvent(
          description=description,
          client=client,
          urn=urn,
          user=user,
          action=action,
          flow_name=flow_name),
      token=token)

  if data_store.RelationalDBEnabled():
    data_store.REL_DB.WriteAPIAuditEntry(
        rdf_objects.APIAuditEntry(
            username=user,
            router_method_name=router_method_name,
            http_request_path=http_request_path,
        ))


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
            representation_type=RepresentationType.LINE_CHART,
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
            representation_type=RepresentationType.LINE_CHART,
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
            representation_type=RepresentationType.PIE_CHART))

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
            representation_type=RepresentationType.PIE_CHART))

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
            representation_type=RepresentationType.PIE_CHART))

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
            representation_type=RepresentationType.PIE_CHART))


class FileStoreReportPluginsTest(test_lib.GRRBaseTest):

  def checkStaticData(self, api_report_data):
    self.assertEqual(api_report_data.representation_type,
                     RepresentationType.STACK_CHART)

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


@db_test_lib.DualDBTest
class ServerReportPluginsTest(test_lib.GRRBaseTest):

  def testClientApprovalsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          action=Action.CLIENT_APPROVAL_BREAK_GLASS_REQUEST,
          user="User123",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1):
      for i in range(10):
        AddFakeAuditLog(
            action=Action.CLIENT_APPROVAL_REQUEST,
            user="user{}".format(i),
            router_method_name="CreateClientApproval",
            http_request_path="/api/users/me/approvals/client/C.{:016X}".format(
                i),
            client="C.{:016X}".format(i),
            token=self.token)

      AddFakeAuditLog(
          action=Action.CLIENT_APPROVAL_GRANT,
          user="usera",
          client="C.0000000000000000",
          router_method_name="GrantClientApproval",
          http_request_path="/api/users/user0/approvals/client/" +
          "C.0000000000000000/0/",
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

    self.assertEqual(api_report_data.representation_type,
                     RepresentationType.AUDIT_CHART)

    self.assertCountEqual(api_report_data.audit_chart.used_fields,
                          ["action", "client", "timestamp", "user"])

    expected = [
        (Action.CLIENT_APPROVAL_GRANT, "usera", "C.0000000000000000"),
        (Action.CLIENT_APPROVAL_REQUEST, "user9", "C.0000000000000009"),
        (Action.CLIENT_APPROVAL_REQUEST, "user8", "C.0000000000000008"),
        (Action.CLIENT_APPROVAL_REQUEST, "user7", "C.0000000000000007"),
        (Action.CLIENT_APPROVAL_REQUEST, "user6", "C.0000000000000006"),
        (Action.CLIENT_APPROVAL_REQUEST, "user5", "C.0000000000000005"),
        (Action.CLIENT_APPROVAL_REQUEST, "user4", "C.0000000000000004"),
        (Action.CLIENT_APPROVAL_REQUEST, "user3", "C.0000000000000003"),
        (Action.CLIENT_APPROVAL_REQUEST, "user2", "C.0000000000000002"),
        (Action.CLIENT_APPROVAL_REQUEST, "user1", "C.0000000000000001"),
        (Action.CLIENT_APPROVAL_REQUEST, "user0", "C.0000000000000000"),
    ]
    rows = api_report_data.audit_chart.rows
    self.assertEqual([(row.action, row.user, row.client) for row in rows],
                     expected)

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
            representation_type=RepresentationType.AUDIT_CHART,
            audit_chart=rdf_report_plugins.ApiAuditChartReportData(
                used_fields=["action", "client", "timestamp", "user"],
                rows=[])))

  def testHuntActionsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          action=Action.HUNT_CREATED,
          user="User123",
          flow_name="Flow123",
          router_method_name="CreateHunt",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1):
      for i in range(10):
        AddFakeAuditLog(
            action=Action.HUNT_MODIFIED,
            user="User{}".format(i),
            flow_name="Flow{}".format(i),
            router_method_name="ModifyHunt",
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

    self.assertEqual(api_report_data.representation_type,
                     RepresentationType.AUDIT_CHART)

    self.assertCountEqual(api_report_data.audit_chart.used_fields,
                          ["action", "timestamp", "user"])

    self.assertEqual([(row.action, row.timestamp.Format("%Y/%m/%d"), row.user)
                      for row in api_report_data.audit_chart.rows],
                     [(Action.HUNT_MODIFIED, "2012/12/22", "User9"),
                      (Action.HUNT_MODIFIED, "2012/12/22", "User8"),
                      (Action.HUNT_MODIFIED, "2012/12/22", "User7"),
                      (Action.HUNT_MODIFIED, "2012/12/22", "User6"),
                      (Action.HUNT_MODIFIED, "2012/12/22", "User5"),
                      (Action.HUNT_MODIFIED, "2012/12/22", "User4"),
                      (Action.HUNT_MODIFIED, "2012/12/22", "User3"),
                      (Action.HUNT_MODIFIED, "2012/12/22", "User2"),
                      (Action.HUNT_MODIFIED, "2012/12/22", "User1"),
                      (Action.HUNT_MODIFIED, "2012/12/22", "User0")])

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
            representation_type=RepresentationType.AUDIT_CHART,
            audit_chart=rdf_report_plugins.ApiAuditChartReportData(
                used_fields=["action", "timestamp", "user"], rows=[])))

  def testHuntApprovalsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          action=Action.HUNT_APPROVAL_GRANT,
          user="User123",
          urn="aff4:/hunts/H:000000",
          router_method_name="GrantHuntApproval",
          http_request_path="/api/users/u0/approvals/hunt/H:000011/0/",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1):
      for i in range(10):
        AddFakeAuditLog(
            action=Action.HUNT_APPROVAL_REQUEST,
            user="User{}".format(i),
            urn="aff4:/hunts/H:{0:06d}".format(i),
            router_method_name="CreateHuntApproval",
            http_request_path="/api/users/User{0}/approvals/hunt/H:{0:06d}/0/"
            .format(i),
            token=self.token)

      AddFakeAuditLog(
          action=Action.HUNT_APPROVAL_GRANT,
          user="User456",
          urn="aff4:/hunts/H:000010",
          router_method_name="GrantHuntApproval",
          http_request_path="/api/users/u0/approvals/hunt/H:000010/0/",
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

    self.assertCountEqual(api_report_data.audit_chart.used_fields,
                          ["action", "timestamp", "user", "urn"])
    expected = [
        (Action.HUNT_APPROVAL_GRANT, "2012/12/22", "User456",
         "aff4:/hunts/H:000010"),
        (Action.HUNT_APPROVAL_REQUEST, "2012/12/22", "User9",
         "aff4:/hunts/H:000009"),
        (Action.HUNT_APPROVAL_REQUEST, "2012/12/22", "User8",
         "aff4:/hunts/H:000008"),
        (Action.HUNT_APPROVAL_REQUEST, "2012/12/22", "User7",
         "aff4:/hunts/H:000007"),
        (Action.HUNT_APPROVAL_REQUEST, "2012/12/22", "User6",
         "aff4:/hunts/H:000006"),
        (Action.HUNT_APPROVAL_REQUEST, "2012/12/22", "User5",
         "aff4:/hunts/H:000005"),
        (Action.HUNT_APPROVAL_REQUEST, "2012/12/22", "User4",
         "aff4:/hunts/H:000004"),
        (Action.HUNT_APPROVAL_REQUEST, "2012/12/22", "User3",
         "aff4:/hunts/H:000003"),
        (Action.HUNT_APPROVAL_REQUEST, "2012/12/22", "User2",
         "aff4:/hunts/H:000002"),
        (Action.HUNT_APPROVAL_REQUEST, "2012/12/22", "User1",
         "aff4:/hunts/H:000001"),
        (Action.HUNT_APPROVAL_REQUEST, "2012/12/22", "User0",
         "aff4:/hunts/H:000000"),
    ]
    self.assertEqual(
        [(row.action, row.timestamp.Format("%Y/%m/%d"), row.user, str(row.urn))
         for row in api_report_data.audit_chart.rows], expected)

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

    self.assertEqual(api_report_data.representation_type,
                     RepresentationType.AUDIT_CHART)
    self.assertCountEqual(api_report_data.audit_chart.used_fields,
                          ["action", "timestamp", "user", "urn"])
    self.assertEmpty(api_report_data.audit_chart.rows)

  def testCronApprovalsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          action=Action.CRON_APPROVAL_GRANT,
          user="User123",
          urn="aff4:/cron/a",
          router_method_name="GrantCronJobApproval",
          http_request_path="/api/users/u/approvals/cron-job/a/0/",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1):
      for i in range(10):
        AddFakeAuditLog(
            action=Action.CRON_APPROVAL_REQUEST,
            user="User{}".format(i),
            urn="aff4:/cron/a{0}".format(i),
            router_method_name="CreateCronJobApproval",
            http_request_path="/api/users/u{0}/approvals/cron-job/a{0}/0/"
            .format(i),
            token=self.token)

      AddFakeAuditLog(
          action=Action.CRON_APPROVAL_GRANT,
          user="User456",
          urn="aff4:/cron/a0",
          router_method_name="GrantCronJobApproval",
          http_request_path="/api/users/u0/approvals/cron-job/a0/0/",
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

    self.assertCountEqual(api_report_data.audit_chart.used_fields,
                          ["action", "timestamp", "user", "urn"])

    expected = [
        (Action.CRON_APPROVAL_GRANT, "2012/12/22", "User456", "aff4:/cron/a0"),
        (Action.CRON_APPROVAL_REQUEST, "2012/12/22", "User9", "aff4:/cron/a9"),
        (Action.CRON_APPROVAL_REQUEST, "2012/12/22", "User8", "aff4:/cron/a8"),
        (Action.CRON_APPROVAL_REQUEST, "2012/12/22", "User7", "aff4:/cron/a7"),
        (Action.CRON_APPROVAL_REQUEST, "2012/12/22", "User6", "aff4:/cron/a6"),
        (Action.CRON_APPROVAL_REQUEST, "2012/12/22", "User5", "aff4:/cron/a5"),
        (Action.CRON_APPROVAL_REQUEST, "2012/12/22", "User4", "aff4:/cron/a4"),
        (Action.CRON_APPROVAL_REQUEST, "2012/12/22", "User3", "aff4:/cron/a3"),
        (Action.CRON_APPROVAL_REQUEST, "2012/12/22", "User2", "aff4:/cron/a2"),
        (Action.CRON_APPROVAL_REQUEST, "2012/12/22", "User1", "aff4:/cron/a1"),
        (Action.CRON_APPROVAL_REQUEST, "2012/12/22", "User0", "aff4:/cron/a0"),
    ]

    self.assertEqual(
        [(row.action, row.timestamp.Format("%Y/%m/%d"), row.user, str(row.urn))
         for row in api_report_data.audit_chart.rows], expected)

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

    self.assertEqual(api_report_data.representation_type,
                     RepresentationType.AUDIT_CHART)
    self.assertCountEqual(api_report_data.audit_chart.used_fields,
                          ["action", "timestamp", "user", "urn"])
    self.assertEmpty(api_report_data.audit_chart.rows)

  def testMostActiveUsersReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(client="C.123", user="User123", token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22")):
      for _ in range(10):
        AddFakeAuditLog(client="C.123", user="User123", token=self.token)

      AddFakeAuditLog(client="C.456", user="User456", token=self.token)

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

      self.assertEqual(
          api_report_data,
          rdf_report_plugins.ApiReportData(
              representation_type=RepresentationType.PIE_CHART,
              pie_chart=rdf_report_plugins.ApiPieChartReportData(data=[
                  rdf_report_plugins.ApiReportDataPoint1D(
                      label="User123", x=11),
                  rdf_report_plugins.ApiReportDataPoint1D(label="User456", x=1)
              ])))

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

    self.assertEqual(api_report_data.representation_type,
                     RepresentationType.PIE_CHART)
    self.assertEmpty(api_report_data.pie_chart.data)

  def testSystemFlowsReportPlugin(self):
    client_id = self.SetupClient(1).Basename()

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):

      if data_store.RelationalDBEnabled():
        data_store.REL_DB.WriteFlowObject(
            rdf_flow_objects.Flow(
                flow_class_name="GetClientStats",
                creator="GRR",
                client_id=client_id,
                flow_id="0000000B",
                create_time=rdfvalue.RDFDatetime.Now()))
      AddFakeAuditLog(
          action=Action.RUN_FLOW,
          user="GRR",
          flow_name="GetClientStats",
          token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22")):
      for i in range(10):
        if data_store.RelationalDBEnabled():
          data_store.REL_DB.WriteFlowObject(
              rdf_flow_objects.Flow(
                  flow_class_name="GetClientStats",
                  creator="GRR",
                  client_id=client_id,
                  flow_id="{:08X}".format(i),
                  create_time=rdfvalue.RDFDatetime.Now()))
        AddFakeAuditLog(
            action=Action.RUN_FLOW,
            user="GRR",
            flow_name="GetClientStats",
            token=self.token)

      if data_store.RelationalDBEnabled():
        data_store.REL_DB.WriteFlowObject(
            rdf_flow_objects.Flow(
                flow_class_name="ArtifactCollectorFlow",
                creator="GRR",
                client_id=client_id,
                flow_id="0000000A",
                create_time=rdfvalue.RDFDatetime.Now()))
      AddFakeAuditLog(
          action=Action.RUN_FLOW,
          user="GRR",
          flow_name="ArtifactCollectorFlow",
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
            representation_type=RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(
                x_ticks=[],
                data=[
                    rdf_report_plugins.ApiReportDataSeries2D(
                        label=u"GetClientStats\u2003Run By: GRR (10)",
                        points=[ApiReportDataPoint2D(x=0, y=10)]),
                    rdf_report_plugins.ApiReportDataSeries2D(
                        label=u"ArtifactCollectorFlow\u2003Run By: GRR (1)",
                        points=[ApiReportDataPoint2D(x=1, y=1)])
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
            representation_type=RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(x_ticks=[])))

  def testUserActivityReportPlugin(self):
    entries = {
        "2012/12/02": ["User123"],
        "2012/12/07": ["User123"],
        "2012/12/15": ["User123"] * 2 + ["User456"],
        "2012/12/23": ["User123"] * 10,
        "2012/12/28": ["User123"],
    }

    for date_string, usernames in entries.items():
      with test_lib.FakeTime(
          rdfvalue.RDFDatetime.FromHumanReadable(date_string)):
        for username in usernames:
          AddFakeAuditLog(user=username, token=self.token)

    report = report_plugins.GetReportByName(
        server_report_plugins.UserActivityReportPlugin.__name__)

    # Use 15 days which will be rounded up to 3 full weeks.
    duration = rdfvalue.Duration.FromDays(15)
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2012/12/07")

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start_time,
            duration=duration),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            representation_type=RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(data=[
                rdf_report_plugins.ApiReportDataSeries2D(
                    label=u"User123",
                    points=[
                        ApiReportDataPoint2D(x=0, y=1),
                        ApiReportDataPoint2D(x=1, y=2),
                        ApiReportDataPoint2D(x=2, y=10),
                    ]),
                rdf_report_plugins.ApiReportDataSeries2D(
                    label=u"User456",
                    points=[
                        ApiReportDataPoint2D(x=0, y=0),
                        ApiReportDataPoint2D(x=1, y=1),
                        ApiReportDataPoint2D(x=2, y=0),
                    ])
            ])))

  def testUserActivityReportPluginWithNoActivityToReport(self):
    report = report_plugins.GetReportByName(
        server_report_plugins.UserActivityReportPlugin.__name__)

    duration = rdfvalue.Duration.FromDays(14)
    start_time = rdfvalue.RDFDatetime.Now() - duration

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start_time,
            duration=duration),
        token=self.token)

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            representation_type=RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(data=[])))

  def testUserFlowsReportPlugin(self):
    client_id = self.SetupClient(1).Basename()

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(
          action=Action.RUN_FLOW,
          user="User123",
          flow_name="GetClientStats",
          token=self.token)
      if data_store.RelationalDBEnabled():
        data_store.REL_DB.WriteFlowObject(
            rdf_flow_objects.Flow(
                flow_class_name="GetClientStats",
                creator="User123",
                client_id=client_id,
                flow_id="E0000000",
                create_time=rdfvalue.RDFDatetime.Now()))

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22")):
      for i in range(10):
        if data_store.RelationalDBEnabled():
          data_store.REL_DB.WriteFlowObject(
              rdf_flow_objects.Flow(
                  flow_class_name="GetClientStats",
                  creator="User123",
                  client_id=client_id,
                  flow_id="{:08X}".format(i),
                  create_time=rdfvalue.RDFDatetime.Now()))
        AddFakeAuditLog(
            action=Action.RUN_FLOW,
            user="User123",
            flow_name="GetClientStats",
            token=self.token)

      if data_store.RelationalDBEnabled():
        data_store.REL_DB.WriteFlowObject(
            rdf_flow_objects.Flow(
                flow_class_name="ArtifactCollectorFlow",
                creator="User456",
                client_id=client_id,
                flow_id="F0000000",
                create_time=rdfvalue.RDFDatetime.Now()))
      AddFakeAuditLog(
          action=Action.RUN_FLOW,
          user="User456",
          flow_name="ArtifactCollectorFlow",
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
            representation_type=RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(
                x_ticks=[],
                data=[
                    rdf_report_plugins.ApiReportDataSeries2D(
                        label=u"GetClientStats\u2003Run By: User123 (10)",
                        points=[ApiReportDataPoint2D(x=0, y=10)]),
                    rdf_report_plugins.ApiReportDataSeries2D(
                        label=u"ArtifactCollectorFlow\u2003Run By: User456 (1)",
                        points=[ApiReportDataPoint2D(x=1, y=1)])
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
            representation_type=RepresentationType.STACK_CHART,
            stack_chart=rdf_report_plugins.ApiStackChartReportData(x_ticks=[])))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
