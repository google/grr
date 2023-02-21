#!/usr/bin/env python
"""Tests email links."""

import re
from unittest import mock
from urllib import parse as urlparse

from absl import app

from grr_response_server import cronjobs
from grr_response_server import email_alerts
from grr_response_server.flows.cron import system as cron_system
from grr_response_server.gui import gui_test_lib
from grr.test_lib import test_lib


class TestEmailLinks(gui_test_lib.GRRSeleniumHuntTest):

  APPROVAL_REASON = "Please please let me"
  GRANTOR_USERNAME = u"igrantapproval"

  def setUp(self):
    super().setUp()

    self.messages_sent = []

    def SendEmailStub(to_addresses, from_address, subject, message,
                      **unused_kwargs):
      del to_addresses, from_address, subject  # Unused.
      self.messages_sent.append(message)

    email_stubber = mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail",
                                      SendEmailStub)
    email_stubber.start()
    self.addCleanup(email_stubber.stop)

  def _ExtractLinkFromMessage(self, message):
    m = re.search(r"""href=['"](.+?)['"]""", message, re.MULTILINE)
    self.assertIsNotNone(m, f"No link found in {message}")

    link = urlparse.urlparse(m.group(1))
    return link.path + "/" + "#" + link.fragment

  def testEmailClientApprovalRequestLinkLeadsToACorrectPage(self):
    client_id = self.SetupClient(0)

    self.RequestClientApproval(
        client_id,
        reason="Please please let me",
        approver=self.GRANTOR_USERNAME,
        requestor=self.test_username)

    self.assertLen(self.messages_sent, 1)
    message = self.messages_sent[0]

    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.test_username, message)
    self.assertIn(client_id, message)

    self.Open(self._ExtractLinkFromMessage(message))

    # Check that requestor's username and  reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, self.test_username)
    self.WaitUntil(self.IsTextPresent, self.APPROVAL_REASON)
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, client_id)
    self.WaitUntil(self.IsTextPresent, "Host-0")

  def testEmailClientApprovalGrantNotificationLinkLeadsToACorrectPage(self):
    client_id = self.SetupClient(0)

    self.RequestAndGrantClientApproval(
        client_id,
        reason=self.APPROVAL_REASON,
        approver=self.GRANTOR_USERNAME,
        requestor=self.test_username)

    # There should be 1 message for approval request and 1 message
    # for approval grant notification.
    self.assertLen(self.messages_sent, 2)

    message = self.messages_sent[1]

    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.GRANTOR_USERNAME, message)
    self.assertIn(client_id, message)

    self.Open(self._ExtractLinkFromMessage(message))

    # We should end up on client's page. Check that host information is
    # displayed.
    self.WaitUntil(self.IsTextPresent, client_id)
    self.WaitUntil(self.IsTextPresent, "Host-0")

  def testEmailHuntApprovalRequestLinkLeadsToACorrectPage(self):
    hunt_id = self.StartHunt(description="foobar")

    # Request hunt approval, it will trigger an email message.
    self.RequestHuntApproval(
        hunt_id,
        reason=self.APPROVAL_REASON,
        approver=self.GRANTOR_USERNAME,
        requestor=self.test_username)

    self.assertLen(self.messages_sent, 1)
    message = self.messages_sent[0]

    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.test_username, message)
    self.assertIn(hunt_id, message)

    self.Open(self._ExtractLinkFromMessage(message))

    # Check that requestor's username and reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, self.test_username)
    self.WaitUntil(self.IsTextPresent, self.APPROVAL_REASON)
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, hunt_id)
    self.WaitUntil(self.IsTextPresent, "foobar")

  def testEmailHuntApprovalGrantNotificationLinkLeadsToCorrectPage(self):
    hunt_id = self.StartHunt()

    self.RequestAndGrantHuntApproval(
        hunt_id,
        reason=self.APPROVAL_REASON,
        approver=self.GRANTOR_USERNAME,
        requestor=self.test_username)

    # There should be 1 message for approval request and 1 message
    # for approval grant notification.
    self.assertLen(self.messages_sent, 2)

    message = self.messages_sent[1]
    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.GRANTOR_USERNAME, message)
    self.assertIn(hunt_id, message)

    self.Open(self._ExtractLinkFromMessage(message))

    # We should end up on hunts's page.
    self.WaitUntil(self.IsTextPresent, hunt_id)

  def _CreateOSBreakDownCronJobApproval(self):
    job_name = cron_system.OSBreakDownCronJob.__name__
    cronjobs.ScheduleSystemCronJobs(names=[job_name])
    cronjobs.CronManager().DisableJob(job_name)
    return job_name

  def testEmailCronJobApprovalRequestLinkLeadsToACorrectPage(self):
    job_name = self._CreateOSBreakDownCronJobApproval()

    self.RequestCronJobApproval(
        job_name,
        reason=self.APPROVAL_REASON,
        approver=self.GRANTOR_USERNAME,
        requestor=self.test_username)

    self.assertLen(self.messages_sent, 1)
    message = self.messages_sent[0]

    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.test_username, message)
    self.assertIn("OSBreakDownCronJob", message)

    # Extract link from the message text and open it.
    m = re.search(r"""href=['"](.+?)['"]""", message, re.MULTILINE)
    link = urlparse.urlparse(m.group(1))
    self.Open(link.path + "?" + link.query + "#" + link.fragment)

    # Check that requestor's username and reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, self.test_username)
    self.WaitUntil(self.IsTextPresent, self.APPROVAL_REASON)
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, cron_system.OSBreakDownCronJob.__name__)
    self.WaitUntil(self.IsTextPresent, "Frequency")

  def testEmailCronJobApprovalGrantNotificationLinkLeadsToCorrectPage(self):
    job_name = self._CreateOSBreakDownCronJobApproval()
    self.RequestAndGrantCronJobApproval(
        job_name,
        reason=self.APPROVAL_REASON,
        approver=self.GRANTOR_USERNAME,
        requestor=self.test_username)

    # There should be 1 message for approval request and 1 message
    # for approval grant notification.
    self.assertLen(self.messages_sent, 2)
    message = self.messages_sent[1]
    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.GRANTOR_USERNAME, message)

    self.Open(self._ExtractLinkFromMessage(message))

    self.WaitUntil(self.IsTextPresent, "OSBreakDownCronJob")


if __name__ == "__main__":
  app.run(test_lib.main)
