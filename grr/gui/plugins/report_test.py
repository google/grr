#!/usr/bin/env python
from grr.gui import gui_test_lib
from grr.gui import runtests_test

from grr.lib import flags


class TestReports(gui_test_lib.GRRSeleniumTest):
  """Test the reports interface."""

  def testReports(self):
    """Test the reports interface."""
    canary_mode_overrider = gui_test_lib.CanaryModeOverrider(self.token)

    # Make "test" user an admin.
    with self.ACLChecksDisabled():
      self.CreateAdminUser("test")

      canary_mode_overrider.Start()

    self.Open("/#/stats/")

    # Go to reports.
    self.Click("css=#MostActiveUsersReportPlugin_anchor i.jstree-icon")
    self.WaitUntil(self.IsTextPresent, "Server | User Breakdown")
    self.WaitUntil(self.IsTextPresent, "No data to display.")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
