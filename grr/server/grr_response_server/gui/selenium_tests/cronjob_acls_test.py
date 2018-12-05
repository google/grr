#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests Cronjob ACLs."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib.util import compatibility
from grr_response_server import cronjobs
from grr_response_server import data_store
from grr_response_server.aff4_objects import cronjobs as aff4_cronjobs
from grr_response_server.flows.cron import system as cron_system
from grr_response_server.gui import gui_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class TestCronACLWorkflow(gui_test_lib.GRRSeleniumTest):

  reason = u"Cóż, po prostu taką miałem zachciankę."

  def _ScheduleCronJob(self):
    if data_store.RelationalDBReadEnabled(category="cronjobs"):
      cron_job_id = compatibility.GetName(cron_system.OSBreakDownCronJob)
      cronjobs.ScheduleSystemCronJobs(names=[cron_job_id])
    else:
      cron_job_id = compatibility.GetName(cron_system.OSBreakDown)
      aff4_cronjobs.ScheduleSystemCronFlows(
          names=[cron_job_id], token=self.token)
    aff4_cronjobs.GetCronManager().DisableJob(job_id=cron_job_id)
    return cron_job_id

  def testCronJobACLWorkflow(self):

    cron_job_id = self._ScheduleCronJob()

    # Open up and click on Cron Job Viewer.
    self.Open("/")
    self.WaitUntil(self.IsElementPresent, "client_query")
    self.Click("css=a[grrtarget=crons]")

    # Select a cron job
    self.Click("css=td:contains('%s')" % cron_job_id)

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=EnableCronJob]")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to ENABLE this cron job?")

    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")
    self.WaitUntil(self.IsElementPresent,
                   "css=h3:contains('Create a new approval')")

    # This asks the our user to approve the request.
    self.Type("css=grr-request-approval-dialog input[name=acl_approver]",
              self.token.username)
    self.Type("css=grr-request-approval-dialog input[name=acl_reason]",
              self.reason)
    self.Click(
        "css=grr-request-approval-dialog button[name=Proceed]:not([disabled])")

    # "Request Approval" dialog should go away
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    self.Open("/")

    self.WaitUntil(lambda: self.GetText("notification_button") != "0")

    self.Click("notification_button")

    self.Click("css=td:contains('Please grant access to a cron job')")

    self.WaitUntilContains("Grant access", self.GetText,
                           "css=h2:contains('Grant')")
    self.WaitUntil(self.IsTextPresent,
                   "The user %s has requested" % self.token.username)

    # Cron job overview should be visible
    self.WaitUntil(self.IsTextPresent, cron_system.OSBreakDown.__name__)
    self.WaitUntil(self.IsTextPresent, "Frequency")

    self.Click("css=button:contains('Approve')")
    self.WaitUntil(self.IsTextPresent, "Approval granted.")

    # Now test starts up
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntil(lambda: self.GetText("notification_button") != "0")
    self.Click("notification_button")
    self.WaitUntil(self.GetText, "css=td:contains('has granted you access to "
                   "a cron job')")
    self.Click("css=tr:contains('has granted you access') a")

    # Enable OSBreakDown cron job (it should be selected by default).
    self.Click("css=td:contains('%s')" % cron_job_id)

    # Click on Enable and wait for dialog again.
    self.Click("css=button[name=EnableCronJob]:not([disabled])")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to ENABLE this cron job?")
    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This is insufficient - we need 2 approvers.
    self.WaitUntilContains("Need at least 1 additional approver for access.",
                           self.GetText, "css=grr-request-approval-dialog")

    # Lets add another approver.
    approval_id = self.ListCronJobApprovals(requestor=self.token.username)[0].id
    self.GrantCronJobApproval(
        cron_job_id,
        approval_id=approval_id,
        approver=u"approver",
        requestor=self.token.username,
        admin=False)

    # Now test starts up
    self.Open("/")

    # We should be notified that we have an approval
    self.WaitUntil(lambda: self.GetText("notification_button") != "0")
    self.Click("notification_button")
    self.Click("css=tr:contains('has granted you access') a")
    # Wait for modal backdrop to go away.
    self.WaitUntilNot(self.IsVisible, "css=.modal-open")

    self.WaitUntil(self.IsTextPresent, cron_system.OSBreakDown.__name__)

    # Enable OSBreakDown cron job (it should be selected by default).
    self.Click("css=button[name=EnableCronJob]:not([disabled])")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to ENABLE this cron job?")
    # Click on "Proceed" and wait for authorization dialog to appear.
    self.Click("css=button[name=Proceed]")

    # This is still insufficient - one of the approvers should have
    # "admin" label.
    self.WaitUntilContains("Need at least 1 admin approver for access",
                           self.GetText, "css=grr-request-approval-dialog")

    # Let's make "approver" an admin.
    self.CreateAdminUser(u"approver")

    # And try again
    self.Open("/")
    self.Click("css=a[grrtarget=crons]")

    # Select and enable OSBreakDown cron job.
    self.Click("css=td:contains('%s')" % cron_job_id)

    # Click on Enable button and check that dialog appears.
    self.Click("css=button[name=EnableCronJob]:not([disabled])")
    self.WaitUntil(self.IsTextPresent,
                   "Are you sure you want to ENABLE this cron job?")

    # Click on "Proceed" and wait for success label to appear.
    # Also check that "Proceed" button gets disabled.
    self.Click("css=button[name=Proceed]")

    self.WaitUntil(self.IsTextPresent, "Cron job was ENABLED successfully!")


if __name__ == "__main__":
  flags.StartMain(test_lib.main)
