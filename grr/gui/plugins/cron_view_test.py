#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the cron_view interface."""



from grr.gui import runtests_test
from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import cronjobs
from grr.lib.flows.cron import system as cron_system
from grr.lib.rdfvalues import grr_rdf


class TestCronView(test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def AddJobStatus(self, job_urn, status):
    with self.ACLChecksDisabled():
      with aff4.FACTORY.OpenWithLock(job_urn, token=self.token) as job:
        job.Set(job.Schema.LAST_RUN_TIME(rdfvalue.RDFDatetime().Now()))
        job.Set(job.Schema.LAST_RUN_STATUS(status=status))

  def setUp(self):
    super(TestCronView, self).setUp()

    with self.ACLChecksDisabled():
      for flow_name in [cron_system.GRRVersionBreakDown.__name__,
                        cron_system.OSBreakDown.__name__,
                        cron_system.LastAccessStats.__name__]:
        cron_args = cronjobs.CreateCronJobFlowArgs(periodicity="7d",
                                                   lifetime="1d")
        cron_args.flow_runner_args.flow_name = flow_name
        cronjobs.CRON_MANAGER.ScheduleFlow(cron_args,
                                           job_name=flow_name,
                                           token=self.token)

      cronjobs.CRON_MANAGER.RunOnce(token=self.token)

  def testCronView(self):
    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=crons]")

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
    self.Click("css=a[grrtarget=crons]")

    self.WaitUntil(self.IsTextPresent,
                   "Please select a cron job to see the details.")

  def testShowsCronJobDetailsOnClick(self):
    self.Open("/")
    self.Click("css=a[grrtarget=crons]")
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
      cronjobs.CRON_MANAGER.DisableJob(rdfvalue.RDFURN(
          "aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=crons]")
    self.Click("css=td:contains('OSBreakDown')")

    self.assertTrue(self.IsElementPresent(
        "css=button[name=EnableCronJob]:not([disabled])"))
    self.assertTrue(self.IsElementPresent(
        "css=button[name=DisableCronJob][disabled]"))
    self.assertTrue(self.IsElementPresent(
        "css=button[name=DeleteCronJob]:not([disabled])"))

  def testToolbarStateForEnabledCronJob(self):
    with self.ACLChecksDisabled():
      cronjobs.CRON_MANAGER.EnableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=crons]")
    self.Click("css=td:contains('OSBreakDown')")

    self.assertTrue(self.IsElementPresent(
        "css=button[name=EnableCronJob][disabled]"))
    self.assertTrue(self.IsElementPresent(
        "css=button[name=DisableCronJob]:not([disabled])"))
    self.assertTrue(self.IsElementPresent(
        "css=button[name=DeleteCronJob]:not([disabled])"))

  def testEnableCronJob(self):
    with self.ACLChecksDisabled():
      cronjobs.CRON_MANAGER.DisableJob(rdfvalue.RDFURN(
          "aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=crons]")
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
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "OSBreakDown")
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('OSBreakDown') *[state=ENABLED]")

  def testDisableCronJob(self):
    with self.ACLChecksDisabled():
      cronjobs.CRON_MANAGER.EnableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=crons]")
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
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Cancel" and check that dialog disappears.
    self.Click("css=button[name=Cancel]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsTextPresent, "OSBreakDown")
    self.WaitUntil(self.IsElementPresent,
                   "css=tr:contains('OSBreakDown') *[state=DISABLED]")

  def testDeleteCronJob(self):
    with self.ACLChecksDisabled():
      cronjobs.CRON_MANAGER.EnableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    self.Open("/")
    self.Click("css=a[grrtarget=crons]")
    self.Click("css=td:contains('OSBreakDown')")

    # Click on Delete button and check that dialog appears.
    self.Click("css=button[name=DeleteCronJob]:not([disabled])")
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

    # Click on Delete button and check that dialog appears.
    self.Click("css=button[name=DeleteCronJob]:not([disabled])")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to DELETE this cron job?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Cron job was deleted successfully!")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Close" and check that dialog disappears.
    self.Click("css=button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

    # View should be refreshed automatically.
    self.WaitUntil(self.IsElementPresent, "css=grr-cron-jobs-list "
                   "td:contains('GRRVersionBreakDown')")
    self.WaitUntilNot(self.IsElementPresent, "css=grr-cron-jobs-list "
                      "td:contains('OSBreakDown')")

  def testForceRunCronJob(self):
    with self.ACLChecksDisabled():
      cronjobs.CRON_MANAGER.EnableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    with test_lib.FakeTime(
        # 2274264646 corresponds to Sat, 25 Jan 2042 12:10:46 GMT.
        rdfvalue.RDFDatetime().FromSecondsFromEpoch(2274264646),
        increment=1e-6):
      self.Open("/")
      self.Click("css=a[grrtarget=crons]")
      self.Click("css=td:contains('OSBreakDown')")

      # Click on Force Run button and check that dialog appears.
      self.Click("css=button[name=ForceRunCronJob]:not([disabled])")
      self.WaitUntil(self.IsTextPresent,
                     "Are you sure you want to RUN this cron job?")

      # Click on "Proceed" and wait for authorization dialog to appear.
      self.Click("css=button[name=Proceed]")
      self.WaitUntil(self.IsTextPresent, "Create a new approval")

      self.Click("css=#acl_dialog button[name=Close]")
      # Wait for dialog to disappear.
      self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

      with self.ACLChecksDisabled():
        self.GrantCronJobApproval(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

      # Click on Force Run button and check that dialog appears.
      self.Click("css=button[name=ForceRunCronJob]:not([disabled])")
      self.WaitUntil(self.IsTextPresent,
                     "Are you sure you want to RUN this cron job?")

      # Click on "Proceed" and wait for success label to appear.
      # Also check that "Proceed" button gets disabled.
      self.Click("css=button[name=Proceed]")

      # TODO(user): "RUNd", really? :)
      self.WaitUntil(self.IsTextPresent, "Cron job was RUNd successfully!")
      self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

      # Click on "Cancel" and check that dialog disappears.
      self.Click("css=button[name=Cancel]")
      self.WaitUntilNot(self.IsVisible, "css=.modal-backdrop")

      # View should be refreshed automatically. The last run date should appear.
      self.WaitUntil(self.IsElementPresent, "css=grr-cron-jobs-list "
                     "tr:contains('OSBreakDown') td:contains('2042')")

  def testHuntSchedulingWorksCorrectly(self):
    self.Open("/")
    self.Click("css=a[grrtarget=crons]")

    self.Click("css=button[name=ScheduleHuntCronJob]")
    self.WaitUntil(self.IsTextPresent, "Cron Job properties")

    # Select daily periodicity
    self.Type("css=grr-new-cron-job-wizard-form "
              "label:contains('Periodicity') ~ * input", "1d")

    # Click on "Next" button
    self.Click("css=grr-new-cron-job-wizard-form button.Next")

    self.WaitUntil(self.IsTextPresent, "What to run?")

    # Click on Filesystem item in flows list
    self.WaitUntil(self.IsElementPresent, "css=#_Filesystem > i.jstree-icon")
    self.Click("css=#_Filesystem > i.jstree-icon")

    # Click on Find Files item in Filesystem flows list
    self.Click("link=File Finder")

    # Change "path" and "pathtype" values
    self.Type("css=grr-new-cron-job-wizard-form "
              "grr-form-proto-repeated-field:has(label:contains('Paths')) "
              "input", "/tmp")
    self.Select("css=grr-new-cron-job-wizard-form "
                "grr-form-proto-single-field:has(label:contains('Pathtype')) "
                "select", "TSK")

    # Click on "Next" button
    self.Click("css=grr-new-cron-job-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Output Processing")

    # Configure the hunt to use dummy output plugin.
    self.Click("css=grr-new-cron-job-wizard-form button[name=Add]")
    self.Select("css=grr-new-cron-job-wizard-form select", "DummyOutputPlugin")
    self.Type(
        "css=grr-new-cron-job-wizard-form "
        "grr-form-proto-single-field:has(label:contains('Filename Regex')) "
        "input", "some regex")

    # Click on "Next" button
    self.Click("css=.Wizard button.Next")
    self.WaitUntil(self.IsTextPresent, "Where to run?")

    # Create 3 foreman rules. Note that "Add" button adds rules to the beginning
    # of a list.
    self.Click("css=grr-new-cron-job-wizard-form button[name=Add]")
    self.Select("css=grr-new-cron-job-wizard-form div.well select", "Regex")
    self.Select("css=grr-new-cron-job-wizard-form div.well "
                "label:contains('Attribute name') ~ * select", "System")
    self.Type("css=grr-new-cron-job-wizard-form div.well "
              "label:contains('Attribute regex') ~ * input", "Linux")

    self.Click("css=grr-new-cron-job-wizard-form button[name=Add]")
    self.Select("css=grr-new-cron-job-wizard-form div.well select", "Integer")
    self.Select("css=grr-new-cron-job-wizard-form div.well "
                "label:contains('Attribute name') ~ * select", "Clock")
    self.Select("css=grr-new-cron-job-wizard-form div.well "
                "label:contains('Operator') ~ * select", "GREATER_THAN")
    self.Type("css=grr-new-cron-job-wizard-form div.well "
              "label:contains('Value') ~ * input", "1336650631137737")

    self.Click("css=grr-new-cron-job-wizard-form button[name=Add]")
    self.Click("css=grr-new-cron-job-wizard-form div.well "
               "label:contains('Os darwin') ~ * input[type=checkbox]")

    # Click on "Next" button
    self.Click("css=grr-new-cron-job-wizard-form button.Next")
    self.WaitUntil(self.IsTextPresent, "Review")

    # Check that the arguments summary is present.
    self.assertTrue(self.IsTextPresent("Paths"))
    self.assertTrue(self.IsTextPresent("/tmp"))

    # Check that output plugins are shown.
    self.assertTrue(self.IsTextPresent("DummyOutputPlugin"))

    # Check that rules summary is present.
    self.assertTrue(self.IsTextPresent("Client rule set"))

    # Check that periodicity information is present in the review.
    self.assertTrue(self.IsTextPresent("Periodicity"))
    self.assertTrue(self.IsTextPresent("1d"))

    # Click on "Schedule" button
    self.Click("css=grr-new-cron-job-wizard-form button.Next")

    # Anyone can schedule a hunt but we need an approval to actually start it.
    self.WaitUntil(self.IsTextPresent, "Created Cron Job:")

    # Close the window and check that cron job object was created.
    self.Click("css=grr-new-cron-job-wizard-form button.Next")

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
                        grr_rdf.CronJobRunStatus.Status.OK)

    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=crons]")

    # OSBreakDown's row should have a 'warn' class
    self.WaitUntil(self.IsElementPresent,
                   "css=tr.warning td:contains('OSBreakDown')")

    # Check that only OSBreakDown is highlighted
    self.WaitUntilNot(self.IsElementPresent,
                      "css=tr.warning td:contains('GRRVersionBreakDown')")

  def testFailingCronJobIsHighlighted(self):
    for _ in range(4):
      self.AddJobStatus("aff4:/cron/OSBreakDown",
                        grr_rdf.CronJobRunStatus.Status.ERROR)

    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=crons]")

    # OSBreakDown's row should have an 'error' class
    self.WaitUntil(self.IsElementPresent,
                   "css=tr.danger td:contains('OSBreakDown')")
    # Check that only OSBreakDown is highlighted
    self.WaitUntilNot(self.IsElementPresent,
                      "css=tr.danger td:contains('GRRVersionBreakDown')")

  def testCronJobNotificationIsShownAndClickable(self):
    with self.ACLChecksDisabled():
      self._SendNotification("ViewObject", "aff4:/cron/OSBreakDown",
                             "Test CronJob notification")

    self.Open("/")

    self.Click("css=button[id=notification_button]")
    self.Click("css=a:contains('Test CronJob notification')")

    self.WaitUntil(self.IsElementPresent,
                   "css=tr.row-selected td:contains('OSBreakDown')")
    self.WaitUntil(self.IsTextPresent, "cron/OSBreakDown")


def main(argv):
  # Run the full test suite
  runtests_test.SeleniumTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
