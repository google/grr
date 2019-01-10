#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import events as rdf_events
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server.gui import gui_test_lib
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


def AddFakeAuditLog(description=None,
                    client=None,
                    user=None,
                    action=None,
                    router_method_name=None,
                    flow_name=None,
                    token=None):
  events.Events.PublishEvent(
      "Audit",
      rdf_events.AuditEvent(
          description=description,
          client=client,
          user=user,
          action=action,
          flow_name=flow_name),
      token=token)

  if data_store.RelationalDBWriteEnabled():
    data_store.REL_DB.WriteAPIAuditEntry(
        rdf_objects.APIAuditEntry(
            username=user,
            router_method_name=router_method_name,
        ))


@db_test_lib.DualDBTest
class TestReports(gui_test_lib.GRRSeleniumTest):
  """Test the reports interface."""

  def testReports(self):
    """Test the reports interface."""
    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
      AddFakeAuditLog(client="C.123", user="User123", token=self.token)

    with test_lib.FakeTime(
        rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22")):
      AddFakeAuditLog(client="C.456", user="User456", token=self.token)

    # Make "test" user an admin.
    self.CreateAdminUser(u"test")

    self.Open("/#/stats/")

    # Go to reports.
    self.Click("css=#MostActiveUsersReportPlugin_anchor i.jstree-icon")
    self.WaitUntil(self.IsTextPresent, "Server | User Breakdown")

    # Enter a timerange that only matches one of the two fake events.
    self.Type("css=grr-form-datetime input", "2012-12-21 12:34")
    self.Click("css=button:contains('Show report')")

    self.WaitUntil(self.IsTextPresent, "User456")
    self.assertFalse(self.IsTextPresent("User123"))

  def testReportsDontIncludeTimerangesInUrlsOfReportsThatDontUseThem(self):
    client_id = self.SetupClient(0)

    self.AddClientLabel(client_id, u"owner", u"bar")

    self.Open("/#/stats/")

    # Go to reports.
    self.Click("css=#MostActiveUsersReportPlugin_anchor i.jstree-icon")
    self.WaitUntil(self.IsTextPresent, "Server | User Breakdown")

    # Default values aren't shown in the url.
    self.WaitUntilNot(lambda: "start_time" in self.GetCurrentUrlPath())
    self.assertNotIn("duration", self.GetCurrentUrlPath())

    # Enter a timerange.
    self.Type("css=grr-form-datetime input", "2012-12-21 12:34")
    self.Type("css=grr-form-duration input", "2w")
    self.Click("css=button:contains('Show report')")

    # Reports that require timeranges include nondefault values in the url when
    # `Show report' has been clicked.
    self.WaitUntil(lambda: "start_time" in self.GetCurrentUrlPath())
    self.assertIn("duration", self.GetCurrentUrlPath())

    # Select a different report.
    self.Click("css=#LastActiveReportPlugin_anchor i.jstree-icon")
    self.WaitUntil(self.IsTextPresent, "Client | Last Active")

    # The default label isn't included in the url.
    self.WaitUntilNot(lambda: "bar" in self.GetCurrentUrlPath())

    # Select a client label.
    self.Select("css=grr-report select", "bar")
    self.Click("css=button:contains('Show report')")

    # Reports that require labels include them in the url after `Show report'
    # has been clicked.
    self.WaitUntil(lambda: "bar" in self.GetCurrentUrlPath())
    # Reports that dont require timeranges don't mention them in the url.
    self.assertNotIn("start_time", self.GetCurrentUrlPath())
    self.assertNotIn("duration", self.GetCurrentUrlPath())

    # Select a different report.
    self.Click("css=#GRRVersion7ReportPlugin_anchor i.jstree-icon")
    self.WaitUntil(self.IsTextPresent, "Active Clients - 7 Days Active")

    # The label is cleared when report type is changed.
    self.WaitUntilNot(lambda: "bar" in self.GetCurrentUrlPath())
    self.assertNotIn("start_time", self.GetCurrentUrlPath())
    self.assertNotIn("duration", self.GetCurrentUrlPath())


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
