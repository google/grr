#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Test the cron_view interface."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import compatibility
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import notification
from grr_response_server.aff4_objects import cronjobs
from grr_response_server.flows.cron import system as cron_system
from grr_response_server.gui import gui_test_lib
from grr_response_server.gui.api_plugins import cron
from grr_response_server.rdfvalues import cronjobs as rdf_cronjobs
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestCronView(gui_test_lib.GRRSeleniumTest):
  """Test the Cron view GUI."""

  def AddJobStatus(self, job_id, status):
    if data_store.RelationalDBReadEnabled("cronjobs"):
      status = cron.ApiCronJob().status_map[status]
      data_store.REL_DB.UpdateCronJob(
          job_id,
          last_run_time=rdfvalue.RDFDatetime.Now(),
          last_run_status=status)
    else:
      urn = cronjobs.CronManager.CRON_JOBS_PATH.Add(job_id)
      with aff4.FACTORY.OpenWithLock(urn, token=self.token) as job:
        job.Set(job.Schema.LAST_RUN_TIME(rdfvalue.RDFDatetime.Now()))
        job.Set(job.Schema.LAST_RUN_STATUS(status=status))

  def setUp(self):
    super(TestCronView, self).setUp()

    for flow_name in [
        cron_system.GRRVersionBreakDown.__name__,
        cron_system.OSBreakDown.__name__, cron_system.LastAccessStats.__name__
    ]:
      cron_args = rdf_cronjobs.CreateCronJobArgs(
          frequency="7d", lifetime="1d", flow_name=flow_name)
      cronjobs.GetCronManager().CreateJob(
          cron_args, job_id=flow_name, token=self.token)

    manager = cronjobs.GetCronManager()
    manager.RunOnce(token=self.token)
    if data_store.RelationalDBReadEnabled("cronjobs"):
      manager._GetThreadPool().Stop()

  def testCronView(self):
    self.Open("/")

    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=crons]")

    # Table should contain Last Run
    self.WaitUntil(self.IsTextPresent, "Last Run")

    # Table should contain system cron jobs
    self.WaitUntil(self.IsTextPresent, cron_system.GRRVersionBreakDown.__name__)
    self.WaitUntil(self.IsTextPresent, cron_system.LastAccessStats.__name__)
    self.WaitUntil(self.IsTextPresent, cron_system.OSBreakDown.__name__)

    # Select a Cron.
    self.Click("css=td:contains('OSBreakDown')")

    # Check that the cron job is displayed.
    self.WaitUntil(self.IsElementPresent,
                   "css=#main_bottomPane dd:contains('OSBreakDown')")

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
    self.WaitUntil(self.IsElementPresent, "css=#main_bottomPane #Runs")

    self.WaitUntil(self.IsTextPresent, "Allow Overruns")
    self.WaitUntil(self.IsTextPresent, "Cron Arguments")

    # Click on "Runs" tab
    self.Click("css=#main_bottomPane #Runs")

    # Click on the first flow and wait for flow details panel to appear.
    runs = cronjobs.GetCronManager().ReadJobRuns(
        compatibility.GetName(cron_system.OSBreakDown))
    try:
      run_id = runs[0].run_id
    except AttributeError:
      run_id = runs[0].urn.Basename()

    self.assertLen(runs, 1)
    self.WaitUntil(self.IsElementPresent, "css=td:contains('%s')" % run_id)

  def testToolbarStateForDisabledCronJob(self):
    cronjobs.GetCronManager().DisableJob(job_id=u"OSBreakDown")

    self.Open("/")
    self.Click("css=a[grrtarget=crons]")
    self.Click("css=td:contains('OSBreakDown')")

    self.assertTrue(
        self.IsElementPresent("css=button[name=EnableCronJob]:not([disabled])"))
    self.assertTrue(
        self.IsElementPresent("css=button[name=DisableCronJob][disabled]"))
    self.assertTrue(
        self.IsElementPresent("css=button[name=DeleteCronJob]:not([disabled])"))

  def testToolbarStateForEnabledCronJob(self):
    cronjobs.GetCronManager().EnableJob(job_id=u"OSBreakDown")

    self.Open("/")
    self.Click("css=a[grrtarget=crons]")
    self.Click("css=td:contains('OSBreakDown')")

    self.assertTrue(
        self.IsElementPresent("css=button[name=EnableCronJob][disabled]"))
    self.assertTrue(
        self.IsElementPresent(
            "css=button[name=DisableCronJob]:not([disabled])"))
    self.assertTrue(
        self.IsElementPresent("css=button[name=DeleteCronJob]:not([disabled])"))

  def testUserCanSendApprovalRequestWhenDeletingCronJob(self):
    self.assertEqual(
        len(self.ListCronJobApprovals(requestor=self.token.username)), 0)

    self.Open("/")
    self.Click("css=a[grrtarget=crons]")
    self.Click("css=td:contains('OSBreakDown')")

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=DeleteCronJob]:not([disabled])")
    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This should be rejected now and a form request is made.
    self.WaitUntil(self.IsTextPresent, "Create a new approval")
    # This asks the user "test" (which is us) to approve the request.
    self.Type("css=grr-request-approval-dialog input[name=acl_approver]",
              self.token.username)
    self.Type("css=grr-request-approval-dialog input[name=acl_reason]",
              "some reason")
    self.Click(
        "css=grr-request-approval-dialog button[name=Proceed]:not([disabled])")

    self.WaitUntilEqual(
        1, lambda: len(
            self.ListCronJobApprovals(requestor=self.token.username)))

  def testEnableCronJob(self):
    cronjobs.GetCronManager().DisableJob(job_id=u"OSBreakDown")

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
    self.Click("css=grr-request-approval-dialog button[name=Cancel]")

    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    self.RequestAndGrantCronJobApproval(u"OSBreakDown")

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=EnableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to ENABLE this cron job?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Cron job was ENABLED successfully!")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Close" and check that dialog disappears.
    self.Click("css=button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    # TODO(amoser): The lower pane does not refresh automatically so we need to
    # workaround. Remove when we have implemented this auto refresh.
    self.Open("/")
    self.Click("css=a[grrtarget=crons]")
    self.Click("css=td:contains('OSBreakDown')")

    self.WaitUntil(self.IsTextPresent, cron_system.OSBreakDown.__name__)
    self.WaitUntil(self.IsElementPresent,
                   "css=div:contains('Enabled') dd:contains('true')")

  def testDisableCronJob(self):
    cronjobs.GetCronManager().EnableJob(job_id=u"OSBreakDown")

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

    self.Click("css=grr-request-approval-dialog button[name=Cancel]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    self.RequestAndGrantCronJobApproval(u"OSBreakDown")

    # Click on Disable button and check that dialog appears.
    self.Click("css=button[name=DisableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to DISABLE this cron job?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Cron job was DISABLED successfully!")
    self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

    # Click on "Close" and check that dialog disappears.
    self.Click("css=button[name=Close]")
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    # TODO(amoser): The lower pane does not refresh automatically so we need to
    # workaround. Remove when we have implemented this auto refresh.
    self.Open("/")
    self.Click("css=a[grrtarget=crons]")
    self.Click("css=td:contains('OSBreakDown')")

    self.WaitUntil(self.IsTextPresent, cron_system.OSBreakDown.__name__)
    self.WaitUntil(self.IsElementPresent,
                   "css=div:contains('Enabled') dd:contains('false')")

  def testDeleteCronJob(self):
    cronjobs.GetCronManager().EnableJob(job_id=u"OSBreakDown")

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

    self.Click("css=grr-request-approval-dialog button[name=Cancel]")
    # Wait for dialog to disappear.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    self.RequestAndGrantCronJobApproval(u"OSBreakDown")

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
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    # View should be refreshed automatically.
    self.WaitUntil(
        self.IsElementPresent, "css=grr-cron-jobs-list "
        "td:contains('GRRVersionBreakDown')")
    self.WaitUntilNot(self.IsElementPresent, "css=grr-cron-jobs-list "
                      "td:contains('OSBreakDown')")

  def testForceRunCronJob(self):
    cronjobs.GetCronManager().EnableJob(job_id=u"OSBreakDown")

    with test_lib.FakeTime(
        # 2274264646 corresponds to Sat, 25 Jan 2042 12:10:46 GMT.
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(2274264646),
        increment=1e-6):
      self.Open("/")
      self.Click("css=a[grrtarget=crons]")
      self.Click("css=td:contains('OSBreakDown')")

      # Click on Force Run button and check that dialog appears.
      self.Click("css=button[name=ForceRunCronJob]:not([disabled])")
      self.WaitUntil(self.IsTextPresent,
                     "Are you sure you want to FORCE-RUN this cron job?")

      # Click on "Proceed" and wait for authorization dialog to appear.
      self.Click("css=button[name=Proceed]")
      self.WaitUntil(self.IsTextPresent, "Create a new approval")

      self.Click("css=grr-request-approval-dialog button[name=Cancel]")
      # Wait for dialog to disappear.
      self.WaitUntilNot(self.IsVisible, "css=.modal-open")

      self.RequestAndGrantCronJobApproval(u"OSBreakDown")

      # Click on Force Run button and check that dialog appears.
      self.Click("css=button[name=ForceRunCronJob]:not([disabled])")
      self.WaitUntil(self.IsTextPresent,
                     "Are you sure you want to FORCE-RUN this cron job?")

      # Click on "Proceed" and wait for success label to appear.
      # Also check that "Proceed" button gets disabled.
      self.Click("css=button[name=Proceed]")

      self.WaitUntil(self.IsTextPresent,
                     "Cron job flow was FORCE-STARTED successfully!")
      self.assertFalse(self.IsElementPresent("css=button[name=Proceed]"))

      # Click on "Close" and check that dialog disappears.
      self.Click("css=button[name=Close]")
      self.WaitUntilNot(self.IsVisible, "css=.modal-open")

      # Relational cron jobs will only be run the next time a worker checks in.
      if data_store.RelationalDBReadEnabled("cronjobs"):
        manager = cronjobs.GetCronManager()
        manager.RunOnce(token=self.token)
        manager._GetThreadPool().Stop()

      # TODO(amoser): The lower pane does not refresh automatically so we need
      # to workaround. Remove when we have implemented this auto refresh.
      self.Open("/")
      self.Click("css=a[grrtarget=crons]")
      self.Click("css=td:contains('OSBreakDown')")

      # View should be refreshed automatically. The last run date should appear.
      self.WaitUntil(
          self.IsElementPresent, "css=grr-cron-jobs-list "
          "tr:contains('OSBreakDown') td:contains('2042')")

  def testStuckCronJobIsHighlighted(self):
    # Make sure a lot of time has passed since the last
    # execution
    with test_lib.FakeTime(0):
      self.AddJobStatus(u"OSBreakDown", rdf_cronjobs.CronJobRunStatus.Status.OK)

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
    self.AddJobStatus(u"OSBreakDown",
                      rdf_cronjobs.CronJobRunStatus.Status.ERROR)

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
    notification.Notify(
        self.token.username,
        rdf_objects.UserNotification.Type.TYPE_CRON_JOB_APPROVAL_GRANTED,
        "Test CronJob notification",
        rdf_objects.ObjectReference(
            reference_type=rdf_objects.ObjectReference.Type.CRON_JOB,
            cron_job=rdf_objects.CronJobReference(cron_job_id=u"OSBreakDown")))

    self.Open("/")

    self.Click("css=button[id=notification_button]")
    self.Click("css=a:contains('Test CronJob notification')")

    self.WaitUntil(self.IsElementPresent,
                   "css=tr.row-selected td:contains('OSBreakDown')")
    self.WaitUntil(self.IsElementPresent, "css=dd:contains('OSBreakDown')")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
