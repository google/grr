#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

"""Test the cron_view interface."""


from grr.gui import runtests_test
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import cronjobs


class TestCronView(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def AddJobStatus(self, job, status):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.OpenWithLock("aff4:/cron/OSBreakDown",
                                     token=self.token) as job:
        job.Set(job.Schema.LAST_RUN_TIME(rdfvalue.RDFDatetime().Now()))
        job.Set(job.Schema.LAST_RUN_STATUS(status=status))

  def setUp(self):
    super(TestCronView, self).setUp()

    with self.ACLChecksDisabled():
      cronjobs.ScheduleSystemCronFlows(token=self.token)
      cronjobs.CRON_MANAGER.RunOnce(token=self.token)

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
    self.WaitUntil(self.IsTextPresent, "CRON_ARGS")

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
      cronjobs.CRON_MANAGER.DisableJob(
          rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

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
      cronjobs.CRON_MANAGER.EnableJob(
          rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

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
      cronjobs.CRON_MANAGER.DisableJob(
          rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=ManageCron]")
    self.Click("css=td:contains('OSBreakDown')")

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=EnableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to ENABLE this cron job?")

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
                   "Are you sure you want to ENABLE this cron job?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Cron job was ENABLEd successfully!")
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
      cronjobs.CRON_MANAGER.EnableJob(
          rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=ManageCron]")
    self.Click("css=td:contains('OSBreakDown')")

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=DisableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to DISABLE this cron job?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Create a new approval")

    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    with self.ACLChecksDisabled():
      self.GrantCronJobApproval(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    # Click on Disable button and check that dialog appears.
    self.Click("css=button[name=DisableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to DISABLE this cron job?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Cron job was DISABLEd successfully!")
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
      cronjobs.CRON_MANAGER.EnableJob(
          rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=ManageCron]")
    self.Click("css=td:contains('OSBreakDown')")

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=DeleteCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to DELETE this cron job?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsTextPresent, "Create a new approval")

    self.Click("css=#acl_dialog button[name=Close]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    with self.ACLChecksDisabled():
      self.GrantCronJobApproval(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    # Click on Disable button and check that dialog appears.
    self.Click("css=button[name=DeleteCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to DELETE this cron job?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Cron job was DELETEd successfully!")
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

    # Click on Find Files item in Filesystem flows list
    self.Click("link=File Finder")

    # Wait for flow configuration form to be rendered (just wait for first
    # input field).
    self.WaitUntil(self.IsElementPresent,
                   "css=.Wizard input[id=args-paths-0]")

    # Change "path", "pathtype", "depth" and "ignore_errors" values
    self.Type("css=.Wizard input[id=args-paths-0]", "/tmp")
    self.Select("css=.Wizard select[id=args-pathtype]", "TSK")

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Configure the hunt to use a collection and also send an email on results.
    self.Click("css=.Wizard button:contains('Add Output Plugin')")

    self.Select("css=.Wizard select[id=output_1-option]",
                "Send an email for each result.")
    self.Type("css=.Wizard input[id=output_1-email]",
              "test@%s" % config_lib.CONFIG["Logging.domain"])

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Create 3 foreman rules
    self.WaitUntil(
        self.IsElementPresent,
        "css=.Wizard select[id=rule_1-option]")
    self.Select("css=.Wizard select[id=rule_1-option]",
                "Regular Expressions")
    self.Select("css=.Wizard select[id=rule_1-attribute_name]",
                "System")
    self.Type("css=.Wizard input[id=rule_1-attribute_regex]",
              "Linux")

    # Make the button visible by scrolling to the bottom.
    self.driver.execute_script("""
$("button:contains('Add Rule')").parent().scrollTop(10000)
""")

    self.Click("css=.Wizard button:contains('Add Rule')")
    self.Select("css=.Wizard select[id=rule_2-option]",
                "Integer Rule")
    self.Select("css=.Wizard select[id=rule_2-attribute_name]",
                "Clock")
    self.Select("css=.Wizard select[id=rule_2-operator]",
                "GREATER_THAN")
    self.Type("css=.Wizard input[id=rule_2-value]",
              "1336650631137737")

    # Make the button visible by scrolling to the bottom.
    self.driver.execute_script("""
$("button:contains('Add Rule')").parent().scrollTop(10000)
""")

    self.Click("css=.Wizard button:contains('Add Rule')")
    self.Select("css=.Wizard select[id=rule_3-option]",
                "OSX")

    # Make the button visible by scrolling to the bottom.
    self.driver.execute_script("""
$("button:contains('Add Rule')").parent().scrollTop(10000)
""")

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "When to run?")

    # Select daily periodicity
    self.Type("css=.Wizard input[id=cron-periodicity]", "1d")

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Check that the arguments summary is present.
    self.assertTrue(self.IsTextPresent("Paths"))
    self.assertTrue(self.IsTextPresent("/tmp"))

    # Check that output plugins are shown.
    self.assertTrue(self.IsTextPresent("EmailPlugin"))
    self.assertTrue(self.IsTextPresent("test@%s" %
                                       config_lib.CONFIG["Logging.domain"]))

    # Check that rules summary is present.
    self.assertTrue(self.IsTextPresent("Regex rules"))

    # Check that periodicity information is present in the review.
    self.assertTrue(self.IsTextPresent("Hunt Periodicity"))
    self.assertTrue(self.IsTextPresent("Hunt will run 1d."))

    # Click on "Schedule" button
    self.Click("css=.Wizard button.Next")

    # Anyone can schedule a hunt but we need an approval to actually start it.
    self.WaitUntil(self.IsTextPresent,
                   "Hunt was successfully scheduled")

    # Close the window and check that cron job object was created.
    self.Click("css=button.Finish")

    # Select newly created cron job.
    self.Click("css=td:contains('cron/CreateAndRunGenericHuntFlow_')")

    # Check that correct details are displayed in cron job details tab.
    self.WaitUntil(self.IsTextPresent, "CreateAndRunGenericHuntFlow")
    self.WaitUntil(self.IsTextPresent, "Flow args")

    self.assertTrue(self.IsTextPresent("Paths"))
    self.assertTrue(self.IsTextPresent("/tmp"))

  def testStuckCronJobIsHighlighted(self):
    # Make sure a lot of time has passed since the last
    # execution
    with test_lib.FakeTime(0):
      self.AddJobStatus("aff4:/cron/OSBreakDown",
                        rdfvalue.CronJobRunStatus.Status.OK)

    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageCron]")

    # OSBreakDown's row should have a 'warn' class
    self.WaitUntil(self.IsElementPresent,
                   "css=tr.warning td:contains('OSBreakDown')")
    # Check that only OSBreakDown is highlighted
    self.WaitUntilNot(self.IsElementPresent,
                      "css=tr.warning td:contains('GRRVersionBreakDown')")

  def testFailingCronJobIsHighlighted(self):
    for _ in range(4):
      self.AddJobStatus("aff4:/cron/OSBreakDown",
                        rdfvalue.CronJobRunStatus.Status.ERROR)

    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=ManageCron]")

    # OSBreakDown's row should have an 'error' class
    self.WaitUntil(self.IsElementPresent,
                   "css=tr.danger td:contains('OSBreakDown')")
    # Check that only OSBreakDown is highlighted
    self.WaitUntilNot(self.IsElementPresent,
                      "css=tr.danger td:contains('GRRVersionBreakDown')")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
