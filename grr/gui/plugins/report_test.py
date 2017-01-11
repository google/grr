#!/usr/bin/env python
from grr.gui import gui_test_lib
from grr.gui import runtests_test

from grr.lib import events
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


def AddFakeAuditLog(description=None,
                    client=None,
                    user=None,
                    token=None,
                    **kwargs):
  events.Events.PublishEventInline(
      "Audit",
      events.AuditEvent(
          description=description, client=client, user=user, **kwargs),
      token=token)


class TestReports(gui_test_lib.GRRSeleniumTest):
  """Test the reports interface."""

  def testReports(self):
    """Test the reports interface."""
    with self.ACLChecksDisabled():
      with test_lib.FakeTime(
          rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")):
        AddFakeAuditLog(
            "Fake audit description 14 Dec.",
            "C.123",
            "User123",
            token=self.token)

      with test_lib.FakeTime(
          rdfvalue.RDFDatetime.FromHumanReadable("2012/12/22")):
        AddFakeAuditLog(
            "Fake audit description 22 Dec.",
            "C.456",
            "User456",
            token=self.token)

      canary_mode_overrider = gui_test_lib.CanaryModeOverrider(self.token)

      # Make "test" user an admin.
      self.CreateAdminUser("test")

      canary_mode_overrider.Start()

    self.Open("/#/stats/")

    # Go to reports.
    self.Click("css=#MostActiveUsersReportPlugin_anchor i.jstree-icon")
    self.WaitUntil(self.IsTextPresent, "Server | User Breakdown")
    self.WaitUntil(self.IsTextPresent, "No data to display.")

    # Enter a timerange that only matches one of the two fake events.
    self.Type("css=grr-form-datetime input", "2012-12-21 12:34")
    self.Click("css=button:contains('Show report')")

    self.WaitUntil(self.IsTextPresent, "User456")
    self.WaitUntil(self.IsTextPresent, "100%")
    self.assertFalse(self.IsTextPresent("User123"))


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
