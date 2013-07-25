#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Test the cron_view interface."""


from grr.gui import runtests_test

from grr.lib import cron
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class TestCronView(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def setUp(self):
    super(TestCronView, self).setUp()

    with self.ACLChecksDisabled():
      cron.ScheduleSystemCronFlows(token=self.token)
      cron.CRON_MANAGER.RunOnce(token=self.token)

  def testCronView(self):
    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageCron]")

    # Table should contain Last Run
    self.WaitUntil(self.IsTextPresent, "Last Run")

    # Table should contain system cron jobs
    self.WaitUntil(self.IsTextPresent, "GRRVersionBreakDown")
    self.WaitUntil(self.IsTextPresent, "LastAccessStats")
    self.WaitUntil(self.IsTextPresent, "OSBreakDown")

    # Select a Cron.
    self.Click("css=td:contains('OSBreakDown')")

    # Check that there's one flow in the list.
    self.WaitUntil(self.IsElementPresent,
                   "css=#main_bottomPane td:contains('OSBreakDown')")

  def testMessageIsShownWhenNoCronJobSelected(self):
    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageCron]")

    self.WaitUntil(self.IsTextPresent,
                   "Please select a cron job to see the details.")

  def testShowsCronJobDetailsOnClick(self):
    self.Open("/")
    self.Click("css=a[grrtarget=ManageCron]")
    self.Click("css=td:contains('OSBreakDown')")

    # Tabs should appear in the bottom pane
    self.WaitUntil(self.IsElementPresent, "css=#main_bottomPane #Details")
    self.WaitUntil(self.IsElementPresent, "css=#main_bottomPane #Flows")

    self.WaitUntil(self.IsTextPresent, "CURRENT_FLOW_URN")
    self.WaitUntil(self.IsTextPresent, "FLOW_NAME")
    self.WaitUntil(self.IsTextPresent, "FLOW_ARGS")

    # Click on "Flows" tab
    self.Click("css=#main_bottomPane #Flows")

    # Click on the first flow and wait for flow details panel to appear.
    self.Click("css=#main_bottomPane td:contains('OSBreakDown')")
    self.WaitUntil(self.IsTextPresent, "FLOW_STATE")
    self.WaitUntil(self.IsTextPresent, "next_states")
    self.WaitUntil(self.IsTextPresent, "outstanding_requests")

    # Close the panel.
    self.Click("css=#main_bottomPane .panel button.close")
    self.WaitUntilNot(self.IsTextPresent, "FLOW_STATE")
    self.WaitUntilNot(self.IsTextPresent, "next_states")
    self.WaitUntilNot(self.IsTextPresent, "outstanding_requests")

  def testToolbarStateForDisabledCronJob(self):
    with self.ACLChecksDisabled():
      cron.CRON_MANAGER.DisableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=ManageCron]")
    self.Click("css=td:contains('OSBreakDown')")

    self.assertTrue(self.IsElementPresent(
        "css=button[name=EnableCronJob]:not([disabled])"))
    self.assertTrue(self.IsElementPresent(
        "css=button[name=DisableCronJob][disabled]"))
    self.assertTrue(self.IsElementPresent(
        "css=button[name=DeleteCronJob]:not([disabled])"))

  def testToolbarStateForEnabledCronJob(self):
    with self.ACLChecksDisabled():
      cron.CRON_MANAGER.EnableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=ManageCron]")
    self.Click("css=td:contains('OSBreakDown')")

    self.assertTrue(self.IsElementPresent(
        "css=button[name=EnableCronJob][disabled]"))
    self.assertTrue(self.IsElementPresent(
        "css=button[name=DisableCronJob]:not([disabled])"))
    self.assertTrue(self.IsElementPresent(
        "css=button[name=DeleteCronJob]:not([disabled])"))

  def testEnableCronJob(self):
    with self.ACLChecksDisabled():
      cron.CRON_MANAGER.DisableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=ManageCron]")
    self.Click("css=td:contains('OSBreakDown')")

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=EnableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to enable this cron job?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    with self.ACLChecksDisabled():
      self.GrantCronJobApproval(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=EnableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to enable this cron job?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Cron job was enabled successfully!")
    self.assertTrue(self.IsElementPresent("css=button[name=Proceed][disabled]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "OSBreakDown")
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('OSBreakDown') *[state=enabled]")

  def testDisableCronJob(self):
    with self.ACLChecksDisabled():
      cron.CRON_MANAGER.EnableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=ManageCron]")
    self.Click("css=td:contains('OSBreakDown')")

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=DisableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to disable this cron job?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    with self.ACLChecksDisabled():
      self.GrantCronJobApproval(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    # Click on Disable button and check that dialog appears.
    self.Click("css=button[name=DisableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to disable this cron job?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Cron job was disabled successfully!")
    self.assertTrue(self.IsElementPresent("css=button[name=Proceed][disabled]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "OSBreakDown")
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('OSBreakDown') *[state=disabled]")

  def testDeleteCronJob(self):
    with self.ACLChecksDisabled():
      cron.CRON_MANAGER.EnableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=ManageCron]")
    self.Click("css=td:contains('OSBreakDown')")

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=DeleteCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to delete this cron job?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    with self.ACLChecksDisabled():
      self.GrantCronJobApproval(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    # Click on Disable button and check that dialog appears.
    self.Click("css=button[name=DeleteCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to delete this cron job?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Cron job was deleted successfully!")
    self.assertTrue(self.IsElementPresent("css=button[name=Proceed][disabled]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsElementPresent,
                   "css=#main_topPane td:contains('GRRVersionBreakDown')")
    self.WaitUntilNot(self.IsElementPresent,
                      "css=#main_topPane td:contains('OSBreakDown')")

  def testHuntSchedulingWorksCorrectly(self):
    self.Open("/")
    self.Click("css=a[grrtarget=ManageCron]")

    self.Click("css=button[name=ScheduleHuntCronJob]")
    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Click on Filesystem item in flows list
    self.WaitUntil(self.IsElementPresent, "css=#_Filesystem > ins.jstree-icon")
    self.Click("css=#_Filesystem > ins.jstree-icon")

    # Click on DownloadDirectory item in Filesystem flows list
    self.WaitUntil(self.IsElementPresent,
                   "link=DownloadDirectory")
    self.Click("link=DownloadDirectory")

    # Wait for flow configuration form to be rendered (just wait for first
    # input field).
    self.WaitUntil(self.IsElementPresent,
                   "css=.Wizard .HuntFormBody input[name=pathspec_path]")

    # Change "path", "pathtype", "depth" and "ignore_errors" values
    self.Type("css=.Wizard .HuntFormBody input[name=pathspec_path]", "/tmp")
    self.Select("css=.Wizard .HuntFormBody select[name=pathspec_pathtype]",
                "TSK")
    self.Type("css=.Wizard .HuntFormBody input[name=depth]", "42")
    self.Click("css=.Wizard .HuntFormBody input[name=ignore_errors]")

    # Click on "Next" button
    self.Click("css=.Wizard input.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Configure the hunt to use a collection and also send an email on results.
    self.Select("css=.Wizard .Rule:nth-of-type(1) select[name=output_type]",
                "Send an email")
    self.Type("css=.Wizard .Rule:nth-of-type(1) input[name=email]",
              "test@grrserver.com")
    self.Click("css=.Wizard input[value='Add another output plugin']")
    self.Select("css=.Wizard .Rule:nth-of-type(2) select[name=output_type]",
                "Store results in a collection")

    # Click on "Next" button
    self.Click("css=.Wizard input.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Create 3 foreman rules
    self.WaitUntil(
        self.IsElementPresent,
        "css=.Wizard .Rule:nth-of-type(1) select[name=rule_type]")
    self.Select("css=.Wizard .Rule:nth-of-type(1) select[name=rule_type]",
                "Regular expression match")
    self.Type("css=.Wizard .Rule:nth-of-type(1) input[name=attribute_name]",
              "System")
    self.Type("css=.Wizard .Rule:nth-of-type(1) input[name=attribute_regex]",
              "Linux")

    self.Click("css=.Wizard input[value='Add Rule']")
    self.Select("css=.Wizard .Rule:nth-of-type(2) select[name=rule_type]",
                "Integer comparison")
    self.Type("css=.Wizard .Rule:nth-of-type(2) input[name=attribute_name]",
              "Clock")
    self.Select("css=.Wizard .Rule:nth-of-type(2) select[name=operator]",
                "GREATER_THAN")
    self.Type("css=.Wizard .Rule:nth-of-type(2) input[name=value]",
              "1336650631137737")

    self.Click("css=.Wizard input[value='Add Rule']")
    self.Select("css=.Wizard .Rule:nth-of-type(3) select[name=rule_type]",
                "Mac OS X systems")

    # Click on "Next" button
    self.Click("css=.Wizard input.Next")
    self.WaitUntil(self.IsTextPresent, "When to run?")

    # Select daily periodicity
    self.Select("css=.Wizard select[name=periodicity]", "Daily")

    # Click on "Next" button
    self.Click("css=.Wizard input.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Check that the arguments summary is present.
    self.assertTrue(self.IsTextPresent("Settings"))
    self.assertTrue(self.IsTextPresent("pathspec"))
    self.assertTrue(self.IsTextPresent("/tmp"))
    self.assertTrue(self.IsTextPresent("depth"))
    self.assertTrue(self.IsTextPresent("42"))

    # Check that output plugins are shown.
    self.assertTrue(self.IsTextPresent("Send an email"))
    self.assertTrue(self.IsTextPresent("test@grrserver.com"))
    self.assertTrue(self.IsTextPresent("Store results in a collection."))

    # Check that rules summary is present.
    self.assertTrue(self.IsTextPresent("Rules"))
    self.assertTrue(self.IsTextPresent("regex_rules"))
    self.assertTrue(self.IsTextPresent("actions"))

    # Check that periodicity information is present in the review.
    self.assertTrue(self.IsTextPresent("Hunt Periodicity"))
    self.assertTrue(self.IsTextPresent("Hunt will run daily."))

    # Click on "Schedule" button
    self.Click("css=.Wizard input.Next")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent,
                   "Create a new approval request")

    # Close the window and check that cron job object was created.
    self.Click("css=#acl_dialog button[name=Close]")

    # Select newly created cron job.
    self.Click("css=td:contains('cron/Hunt_DownloadDirectory_')")

    # Check that correct details are displayed in cron job details tab.
    self.WaitUntil(self.IsTextPresent, "CreateAndRunGenericHuntFlow")
    self.WaitUntil(self.IsTextPresent, "FLOW_ARGS")

    self.assertTrue(self.IsTextPresent("Settings"))
    self.assertTrue(self.IsTextPresent("pathspec"))
    self.assertTrue(self.IsTextPresent("/tmp"))
    self.assertTrue(self.IsTextPresent("depth"))
    self.assertTrue(self.IsTextPresent("42"))


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
