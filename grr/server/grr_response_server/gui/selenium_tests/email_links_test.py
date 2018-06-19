#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests email links."""

import re
import urlparse

import unittest
from grr.lib import flags

from grr.lib import utils
from grr.server.grr_response_server import email_alerts
from grr.server.grr_response_server.aff4_objects import cronjobs
from grr.server.grr_response_server.flows.cron import system as cron_system
from grr.server.grr_response_server.gui import gui_test_lib
from grr.server.grr_response_server.hunts import implementation
from grr.server.grr_response_server.hunts import standard
from grr.test_lib import db_test_lib


@db_test_lib.DualDBTest
class TestEmailLinks(gui_test_lib.GRRSeleniumHuntTest):

  APPROVAL_REASON = "Please please let me"
  GRANTOR_USERNAME = "igrantapproval"

  def setUp(self):
    super(TestEmailLinks, self).setUp()

    self.messages_sent = []

    def SendEmailStub(unused_from_user, unused_to_user, unused_subject, message,
                      **unused_kwargs):
      self.messages_sent.append(message)

    self.email_stubber = utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail",
                                       SendEmailStub)
    self.email_stubber.Start()

  def tearDown(self):
    super(TestEmailLinks, self).tearDown()
    self.email_stubber.Stop()

  def _ExtractLinkFromMessage(self, message):
    m = re.search(r"href='(.+?)'", message, re.MULTILINE)
    link = urlparse.urlparse(m.group(1))
    return link.path + "/" + "#" + link.fragment

  def CreateSampleHunt(self, token=None):

    with implementation.GRRHunt.StartHunt(
        hunt_name=standard.SampleHunt.__name__,
        client_rate=100,
        filename="TestFilename",
        client_rule_set=self._CreateForemanClientRuleSet(),
        token=token or self.token) as hunt:

      return hunt.session_id

  def testEmailClientApprovalRequestLinkLeadsToACorrectPage(self):
    client_id = self.SetupClient(0)

    self.RequestClientApproval(
        client_id.Basename(),
        reason="Please please let me",
        approver=self.GRANTOR_USERNAME,
        requestor=self.token.username)

    self.assertEqual(len(self.messages_sent), 1)
    message = self.messages_sent[0]

    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.token.username, message)
    self.assertIn(client_id.Basename(), message)

    self.Open(self._ExtractLinkFromMessage(message))

    # Check that requestor's username and  reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, self.token.username)
    self.WaitUntil(self.IsTextPresent, self.APPROVAL_REASON)
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, client_id.Basename())
    self.WaitUntil(self.IsTextPresent, "Host-0")

  def testEmailClientApprovalGrantNotificationLinkLeadsToACorrectPage(self):
    client_id = self.SetupClient(0)

    self.RequestAndGrantClientApproval(
        client_id,
        reason=self.APPROVAL_REASON,
        approver=self.GRANTOR_USERNAME,
        requestor=self.token.username)

    # There should be 1 message for approval request and 1 message
    # for approval grant notification.
    self.assertEqual(len(self.messages_sent), 2)

    message = self.messages_sent[1]

    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.GRANTOR_USERNAME, message)
    self.assertIn(client_id.Basename(), message)

    self.Open(self._ExtractLinkFromMessage(message))

    # We should end up on client's page. Check that host information is
    # displayed.
    self.WaitUntil(self.IsTextPresent, client_id.Basename())
    self.WaitUntil(self.IsTextPresent, "Host-0")
    # Check that the reason is displayed.
    self.WaitUntil(self.IsTextPresent, self.APPROVAL_REASON)

  def testEmailHuntApprovalRequestLinkLeadsToACorrectPage(self):
    hunt_id = self.CreateSampleHunt()

    # Request hunt approval, it will trigger an email message.
    self.RequestHuntApproval(
        hunt_id.Basename(),
        reason=self.APPROVAL_REASON,
        approver=self.GRANTOR_USERNAME,
        requestor=self.token.username)

    self.assertEqual(len(self.messages_sent), 1)
    message = self.messages_sent[0]

    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.token.username, message)
    self.assertIn(hunt_id.Basename(), message)

    self.Open(self._ExtractLinkFromMessage(message))

    # Check that requestor's username and reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, self.token.username)
    self.WaitUntil(self.IsTextPresent, self.APPROVAL_REASON)
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, hunt_id.Basename())
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

  def testEmailHuntApprovalGrantNotificationLinkLeadsToCorrectPage(self):
    hunt_id = self.CreateSampleHunt()

    self.RequestAndGrantHuntApproval(
        hunt_id.Basename(),
        reason=self.APPROVAL_REASON,
        approver=self.GRANTOR_USERNAME,
        requestor=self.token.username)

    # There should be 1 message for approval request and 1 message
    # for approval grant notification.
    self.assertEqual(len(self.messages_sent), 2)

    message = self.messages_sent[1]
    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.GRANTOR_USERNAME, message)
    self.assertIn(hunt_id.Basename(), message)

    self.Open(self._ExtractLinkFromMessage(message))

    # We should end up on hunts's page.
    self.WaitUntil(self.IsTextPresent, hunt_id.Basename())

  def testEmailCronJobApprovalRequestLinkLeadsToACorrectPage(self):
    cronjobs.ScheduleSystemCronFlows(
        names=[cron_system.OSBreakDown.__name__], token=self.token)
    cronjobs.GetCronManager().DisableJob(job_id="OSBreakDown")

    self.RequestCronJobApproval(
        "OSBreakDown",
        reason=self.APPROVAL_REASON,
        approver=self.GRANTOR_USERNAME,
        requestor=self.token.username)

    self.assertEqual(len(self.messages_sent), 1)
    message = self.messages_sent[0]

    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.token.username, message)
    self.assertIn("OSBreakDown", message)

    # Extract link from the message text and open it.
    m = re.search(r"href='(.+?)'", message, re.MULTILINE)
    link = urlparse.urlparse(m.group(1))
    self.Open(link.path + "?" + link.query + "#" + link.fragment)

    # Check that requestor's username and reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, self.token.username)
    self.WaitUntil(self.IsTextPresent, self.APPROVAL_REASON)
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, cron_system.OSBreakDown.__name__)
    self.WaitUntil(self.IsTextPresent, "Periodicity")

  def testEmailCronjobApprovalGrantNotificationLinkLeadsToCorrectPage(self):
    cronjobs.ScheduleSystemCronFlows(
        names=[cron_system.OSBreakDown.__name__], token=self.token)
    cronjobs.GetCronManager().DisableJob(job_id="OSBreakDown")

    self.RequestAndGrantCronJobApproval(
        "OSBreakDown",
        reason=self.APPROVAL_REASON,
        approver=self.GRANTOR_USERNAME,
        requestor=self.token.username)

    # There should be 1 message for approval request and 1 message
    # for approval grant notification.
    self.assertEqual(len(self.messages_sent), 2)
    message = self.messages_sent[1]
    self.assertIn(self.APPROVAL_REASON, message)
    self.assertIn(self.GRANTOR_USERNAME, message)

    self.Open(self._ExtractLinkFromMessage(message))

    self.WaitUntil(self.IsTextPresent, "OSBreakDown")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
