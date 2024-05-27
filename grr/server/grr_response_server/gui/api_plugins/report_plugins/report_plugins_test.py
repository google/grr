#!/usr/bin/env python
"""Tests for report plugins."""

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_proto import objects_pb2
from grr_response_server import data_store
from grr_response_server.gui.api_plugins import stats as stats_api
from grr_response_server.gui.api_plugins.report_plugins import rdf_report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugins
from grr_response_server.gui.api_plugins.report_plugins import report_plugins_test_mocks
from grr_response_server.gui.api_plugins.report_plugins import server_report_plugins
from grr.test_lib import test_lib

RepresentationType = rdf_report_plugins.ApiReportData.RepresentationType
Action = rdf_events.AuditEvent.Action


class ReportPluginsTest(test_lib.GRRBaseTest):

  def testGetAvailableReportPlugins(self):
    """Ensure GetAvailableReportPlugins lists ReportPluginBase's subclasses."""

    with report_plugins_test_mocks.MockedReportPlugins():
      self.assertIn(
          report_plugins_test_mocks.FooReportPlugin,
          report_plugins.GetAvailableReportPlugins(),
      )
      self.assertIn(
          report_plugins_test_mocks.BarReportPlugin,
          report_plugins.GetAvailableReportPlugins(),
      )

  def testGetReportByName(self):
    """Ensure GetReportByName instantiates correct subclasses based on name."""

    with report_plugins_test_mocks.MockedReportPlugins():
      report_object = report_plugins.GetReportByName("BarReportPlugin")
      self.assertIsInstance(
          report_object, report_plugins_test_mocks.BarReportPlugin
      )

  def testGetReportDescriptor(self):
    """Ensure GetReportDescriptor returns a correctly filled in proto."""

    desc = report_plugins_test_mocks.BarReportPlugin.GetReportDescriptor()

    self.assertEqual(
        desc.type, rdf_report_plugins.ApiReportDescriptor.ReportType.SERVER
    )
    self.assertEqual(desc.title, "Bar Activity")
    self.assertEqual(
        desc.summary, "Reports bars' activity in the given time range."
    )
    self.assertEqual(desc.requires_time_range, True)


def AddFakeAuditLog(user=None, router_method_name=None, http_request_path=None):
  data_store.REL_DB.WriteAPIAuditEntry(
      objects_pb2.APIAuditEntry(
          username=user,
          router_method_name=router_method_name,
          http_request_path=http_request_path,
      )
  )


class ServerReportPluginsTest(test_lib.GRRBaseTest):

  def testClientApprovalsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")
    ):
      AddFakeAuditLog(user="User123")

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1
    ):
      for i in range(10):
        AddFakeAuditLog(
            user="user{}".format(i),
            router_method_name="CreateClientApproval",
            http_request_path=(
                "/api/users/me/approvals/client/C.{:016X}".format(i)
            ),
        )

      AddFakeAuditLog(
          user="usera",
          router_method_name="GrantClientApproval",
          http_request_path="/api/users/user0/approvals/client/"
          + "C.0000000000000000/0/",
      )

    report = report_plugins.GetReportByName(
        server_report_plugins.ClientApprovalsReportPlugin.__name__
    )

    start = rdfvalue.RDFDatetime.FromHumanReadable("2012/12/15")
    month_duration = rdfvalue.Duration.From(30, rdfvalue.DAYS)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start,
            duration=month_duration,
        )
    )

    self.assertEqual(
        api_report_data.representation_type, RepresentationType.AUDIT_CHART
    )

    self.assertCountEqual(
        api_report_data.audit_chart.used_fields,
        ["action", "client", "timestamp", "user"],
    )

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
    self.assertEqual(
        [(row.action, row.user, row.client) for row in rows], expected
    )

  def testClientApprovalsReportPluginWithNoActivityToReport(self):
    report = report_plugins.GetReportByName(
        server_report_plugins.ClientApprovalsReportPlugin.__name__
    )

    now = rdfvalue.RDFDatetime().Now()
    month_duration = rdfvalue.Duration.From(30, rdfvalue.DAYS)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=now - month_duration,
            duration=month_duration,
        )
    )

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            representation_type=RepresentationType.AUDIT_CHART,
            audit_chart=rdf_report_plugins.ApiAuditChartReportData(
                used_fields=["action", "client", "timestamp", "user"], rows=[]
            ),
        ),
    )

  def testHuntActionsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")
    ):
      AddFakeAuditLog(user="User123", router_method_name="CreateHunt")

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1
    ):
      for i in range(10):
        AddFakeAuditLog(
            user="User{}".format(i), router_method_name="ModifyHunt"
        )

    report = report_plugins.GetReportByName(
        server_report_plugins.HuntActionsReportPlugin.__name__
    )

    start = rdfvalue.RDFDatetime.FromHumanReadable("2012/12/15")
    month_duration = rdfvalue.Duration.From(30, rdfvalue.DAYS)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start,
            duration=month_duration,
        )
    )

    self.assertEqual(
        api_report_data.representation_type, RepresentationType.AUDIT_CHART
    )

    self.assertCountEqual(
        api_report_data.audit_chart.used_fields, ["action", "timestamp", "user"]
    )

    self.assertEqual(
        [
            (row.action, row.timestamp.Format("%Y/%m/%d"), row.user)
            for row in api_report_data.audit_chart.rows
        ],
        [
            (Action.HUNT_MODIFIED, "2012/12/22", "User9"),
            (Action.HUNT_MODIFIED, "2012/12/22", "User8"),
            (Action.HUNT_MODIFIED, "2012/12/22", "User7"),
            (Action.HUNT_MODIFIED, "2012/12/22", "User6"),
            (Action.HUNT_MODIFIED, "2012/12/22", "User5"),
            (Action.HUNT_MODIFIED, "2012/12/22", "User4"),
            (Action.HUNT_MODIFIED, "2012/12/22", "User3"),
            (Action.HUNT_MODIFIED, "2012/12/22", "User2"),
            (Action.HUNT_MODIFIED, "2012/12/22", "User1"),
            (Action.HUNT_MODIFIED, "2012/12/22", "User0"),
        ],
    )

  def testHuntActionsReportPluginWithNoActivityToReport(self):
    report = report_plugins.GetReportByName(
        server_report_plugins.HuntActionsReportPlugin.__name__
    )

    now = rdfvalue.RDFDatetime().Now()
    month_duration = rdfvalue.Duration.From(30, rdfvalue.DAYS)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=now - month_duration,
            duration=month_duration,
        )
    )

    self.assertEqual(
        api_report_data,
        rdf_report_plugins.ApiReportData(
            representation_type=RepresentationType.AUDIT_CHART,
            audit_chart=rdf_report_plugins.ApiAuditChartReportData(
                used_fields=["action", "timestamp", "user"], rows=[]
            ),
        ),
    )

  def testHuntApprovalsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")
    ):
      AddFakeAuditLog(
          user="User123",
          router_method_name="GrantHuntApproval",
          http_request_path="/api/users/u0/approvals/hunt/H:000011/0/",
      )

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1
    ):
      for i in range(10):
        AddFakeAuditLog(
            user="User{}".format(i),
            router_method_name="CreateHuntApproval",
            http_request_path=(
                "/api/users/User{0}/approvals/hunt/H:{0:06d}/0/".format(i)
            ),
        )

      AddFakeAuditLog(
          user="User456",
          router_method_name="GrantHuntApproval",
          http_request_path="/api/users/u0/approvals/hunt/H:000010/0/",
      )

    report = report_plugins.GetReportByName(
        server_report_plugins.HuntApprovalsReportPlugin.__name__
    )

    start = rdfvalue.RDFDatetime.FromHumanReadable("2012/12/15")
    month_duration = rdfvalue.Duration.From(30, rdfvalue.DAYS)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start,
            duration=month_duration,
        )
    )

    self.assertEqual(
        api_report_data.representation_type,
        rdf_report_plugins.ApiReportData.RepresentationType.AUDIT_CHART,
    )

    self.assertCountEqual(
        api_report_data.audit_chart.used_fields,
        ["action", "timestamp", "user", "urn"],
    )
    expected = [
        (
            Action.HUNT_APPROVAL_GRANT,
            "2012/12/22",
            "User456",
            "aff4:/hunts/H:000010",
        ),
        (
            Action.HUNT_APPROVAL_REQUEST,
            "2012/12/22",
            "User9",
            "aff4:/hunts/H:000009",
        ),
        (
            Action.HUNT_APPROVAL_REQUEST,
            "2012/12/22",
            "User8",
            "aff4:/hunts/H:000008",
        ),
        (
            Action.HUNT_APPROVAL_REQUEST,
            "2012/12/22",
            "User7",
            "aff4:/hunts/H:000007",
        ),
        (
            Action.HUNT_APPROVAL_REQUEST,
            "2012/12/22",
            "User6",
            "aff4:/hunts/H:000006",
        ),
        (
            Action.HUNT_APPROVAL_REQUEST,
            "2012/12/22",
            "User5",
            "aff4:/hunts/H:000005",
        ),
        (
            Action.HUNT_APPROVAL_REQUEST,
            "2012/12/22",
            "User4",
            "aff4:/hunts/H:000004",
        ),
        (
            Action.HUNT_APPROVAL_REQUEST,
            "2012/12/22",
            "User3",
            "aff4:/hunts/H:000003",
        ),
        (
            Action.HUNT_APPROVAL_REQUEST,
            "2012/12/22",
            "User2",
            "aff4:/hunts/H:000002",
        ),
        (
            Action.HUNT_APPROVAL_REQUEST,
            "2012/12/22",
            "User1",
            "aff4:/hunts/H:000001",
        ),
        (
            Action.HUNT_APPROVAL_REQUEST,
            "2012/12/22",
            "User0",
            "aff4:/hunts/H:000000",
        ),
    ]
    self.assertEqual(
        [
            (
                row.action,
                row.timestamp.Format("%Y/%m/%d"),
                row.user,
                str(row.urn),
            )
            for row in api_report_data.audit_chart.rows
        ],
        expected,
    )

  def testHuntApprovalsReportPluginWithNoActivityToReport(self):
    report = report_plugins.GetReportByName(
        server_report_plugins.HuntApprovalsReportPlugin.__name__
    )

    now = rdfvalue.RDFDatetime().Now()
    month_duration = rdfvalue.Duration.From(30, rdfvalue.DAYS)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=now - month_duration,
            duration=month_duration,
        )
    )

    self.assertEqual(
        api_report_data.representation_type, RepresentationType.AUDIT_CHART
    )
    self.assertCountEqual(
        api_report_data.audit_chart.used_fields,
        ["action", "timestamp", "user", "urn"],
    )
    self.assertEmpty(api_report_data.audit_chart.rows)

  def testCronApprovalsReportPlugin(self):
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")
    ):
      AddFakeAuditLog(
          user="User123",
          router_method_name="GrantCronJobApproval",
          http_request_path="/api/users/u/approvals/cron-job/a/0/",
      )

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22"), increment=1
    ):
      for i in range(10):
        AddFakeAuditLog(
            user="User{}".format(i),
            router_method_name="CreateCronJobApproval",
            http_request_path=(
                "/api/users/u{0}/approvals/cron-job/a{0}/0/".format(i)
            ),
        )

      AddFakeAuditLog(
          user="User456",
          router_method_name="GrantCronJobApproval",
          http_request_path="/api/users/u0/approvals/cron-job/a0/0/",
      )

    report = report_plugins.GetReportByName(
        server_report_plugins.CronApprovalsReportPlugin.__name__
    )

    start = rdfvalue.RDFDatetime.FromHumanReadable("2012/12/15")
    month_duration = rdfvalue.Duration.From(30, rdfvalue.DAYS)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=start,
            duration=month_duration,
        )
    )

    self.assertEqual(
        api_report_data.representation_type,
        rdf_report_plugins.ApiReportData.RepresentationType.AUDIT_CHART,
    )

    self.assertCountEqual(
        api_report_data.audit_chart.used_fields,
        ["action", "timestamp", "user", "urn"],
    )

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
        [
            (
                row.action,
                row.timestamp.Format("%Y/%m/%d"),
                row.user,
                str(row.urn),
            )
            for row in api_report_data.audit_chart.rows
        ],
        expected,
    )

  def testCronApprovalsReportPluginWithNoActivityToReport(self):
    report = report_plugins.GetReportByName(
        server_report_plugins.CronApprovalsReportPlugin.__name__
    )

    now = rdfvalue.RDFDatetime().Now()
    month_duration = rdfvalue.Duration.From(30, rdfvalue.DAYS)

    api_report_data = report.GetReportData(
        stats_api.ApiGetReportArgs(
            name=report.__class__.__name__,
            start_time=now - month_duration,
            duration=month_duration,
        )
    )

    self.assertEqual(
        api_report_data.representation_type, RepresentationType.AUDIT_CHART
    )
    self.assertCountEqual(
        api_report_data.audit_chart.used_fields,
        ["action", "timestamp", "user", "urn"],
    )
    self.assertEmpty(api_report_data.audit_chart.rows)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
