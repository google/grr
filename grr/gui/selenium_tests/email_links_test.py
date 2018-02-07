#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
"""Tests email links."""

import re
import urlparse

import unittest
from grr.gui import gui_test_lib

from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.server import access_control
from grr.server import email_alerts
from grr.server import foreman as rdf_foreman
from grr.server.aff4_objects import cronjobs
from grr.server.aff4_objects import security
from grr.server.flows.cron import system as cron_system
from grr.server.hunts import implementation
from grr.server.hunts import standard


class TestEmailLinks(gui_test_lib.GRRSeleniumTest):

  APPROVAL_REASON = "Please please let me"
  GRANTOR_TOKEN = access_control.ACLToken(
      username="igrantapproval", reason="test")

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
    client_rule_set = rdf_foreman.ForemanClientRuleSet(rules=[
        rdf_foreman.ForemanClientRule(
            rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
            regex=rdf_foreman.ForemanRegexClientRule(
                attribute_name="GRR client", attribute_regex="GRR"))
    ])

    with implementation.GRRHunt.StartHunt(
        hunt_name=standard.SampleHunt.__name__,
        client_rate=100,
        filename="TestFilename",
        client_rule_set=client_rule_set,
        token=token or self.token) as hunt:

      return hunt.session_id

  def testEmailClientApprovalRequestLinkLeadsToACorrectPage(self):
    client_id = self.SetupClient(0)

    security.ClientApprovalRequestor(
        reason="Please please let me",
        subject_urn=client_id,
        approver=self.GRANTOR_TOKEN.username,
        token=self.token).Request()

    self.assertEqual(len(self.messages_sent), 1)
    message = self.messages_sent[0]

    self.assertTrue(self.APPROVAL_REASON in message)
    self.assertTrue(self.token.username in message)
    self.assertTrue(client_id.Basename() in message)

    self.Open(self._ExtractLinkFromMessage(message))

    # Check that requestor's username and  reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, self.token.username)
    self.WaitUntil(self.IsTextPresent, self.APPROVAL_REASON)
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, client_id.Basename())
    self.WaitUntil(self.IsTextPresent, "Host-0")

  def testEmailClientApprovalGrantNotificationLinkLeadsToACorrectPage(self):
    client_id = self.SetupClient(0)

    security.ClientApprovalRequestor(
        reason=self.APPROVAL_REASON,
        subject_urn=client_id,
        approver=self.GRANTOR_TOKEN.username,
        token=self.token).Request()
    security.ClientApprovalGrantor(
        reason=self.APPROVAL_REASON,
        subject_urn=client_id,
        token=self.GRANTOR_TOKEN,
        delegate=self.token.username).Grant()

    # There should be 1 message for approval request and 1 message
    # for approval grant notification.
    self.assertEqual(len(self.messages_sent), 2)

    message = self.messages_sent[1]

    self.assertTrue(self.APPROVAL_REASON in message)
    self.assertTrue(self.GRANTOR_TOKEN.username in message)
    self.assertTrue(client_id.Basename() in message)

    self.Open(self._ExtractLinkFromMessage(message))

    # We should end up on client's page. Check that host information is
    # displayed.
    self.WaitUntil(self.IsTextPresent, client_id.Basename())
    self.WaitUntil(self.IsTextPresent, "Host-0")
    # Check that the reason is displayed.
    self.WaitUntil(self.IsTextPresent, self.APPROVAL_REASON)

  def testEmailHuntApprovalRequestLinkLeadsToACorrectPage(self):
    hunt_id = self.CreateSampleHunt()

    # Request client approval, it will trigger an email message.
    security.HuntApprovalRequestor(
        reason=self.APPROVAL_REASON,
        subject_urn=hunt_id,
        approver=self.GRANTOR_TOKEN.username,
        token=self.token).Request()

    self.assertEqual(len(self.messages_sent), 1)
    message = self.messages_sent[0]

    self.assertTrue(self.APPROVAL_REASON in message)
    self.assertTrue(self.token.username in message)
    self.assertTrue(hunt_id.Basename() in message)

    self.Open(self._ExtractLinkFromMessage(message))

    # Check that requestor's username and reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, self.token.username)
    self.WaitUntil(self.IsTextPresent, self.APPROVAL_REASON)
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, hunt_id.Basename())
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

  def testEmailHuntApprovalGrantNotificationLinkLeadsToCorrectPage(self):
    hunt_id = self.CreateSampleHunt()

    security.HuntApprovalRequestor(
        reason=self.APPROVAL_REASON,
        subject_urn=hunt_id,
        approver=self.GRANTOR_TOKEN.username,
        token=self.token).Request()
    security.HuntApprovalGrantor(
        reason=self.APPROVAL_REASON,
        subject_urn=hunt_id,
        token=self.GRANTOR_TOKEN,
        delegate=self.token.username).Grant()

    # There should be 1 message for approval request and 1 message
    # for approval grant notification.
    self.assertEqual(len(self.messages_sent), 2)

    message = self.messages_sent[1]
    self.assertTrue(self.APPROVAL_REASON in message)
    self.assertTrue(self.GRANTOR_TOKEN.username in message)
    self.assertTrue(hunt_id.Basename() in message)

    self.Open(self._ExtractLinkFromMessage(message))

    # We should end up on hunts's page.
    self.WaitUntil(self.IsTextPresent, hunt_id.Basename())

  def testEmailCronJobApprovalRequestLinkLeadsToACorrectPage(self):
    cronjobs.ScheduleSystemCronFlows(
        names=[cron_system.OSBreakDown.__name__], token=self.token)
    cronjobs.CRON_MANAGER.DisableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    security.CronJobApprovalRequestor(
        reason=self.APPROVAL_REASON,
        subject_urn="aff4:/cron/OSBreakDown",
        approver=self.GRANTOR_TOKEN.username,
        token=self.token).Request()

    self.assertEqual(len(self.messages_sent), 1)
    message = self.messages_sent[0]

    self.assertTrue(self.APPROVAL_REASON in message)
    self.assertTrue(self.token.username in message)
    self.assertTrue("OSBreakDown" in message)

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
    cronjobs.CRON_MANAGER.DisableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    security.CronJobApprovalRequestor(
        reason=self.APPROVAL_REASON,
        subject_urn="aff4:/cron/OSBreakDown",
        approver=self.GRANTOR_TOKEN.username,
        token=self.token).Request()
    security.CronJobApprovalGrantor(
        reason=self.APPROVAL_REASON,
        subject_urn="aff4:/cron/OSBreakDown",
        token=self.GRANTOR_TOKEN,
        delegate=self.token.username).Grant()

    # There should be 1 message for approval request and 1 message
    # for approval grant notification.
    self.assertEqual(len(self.messages_sent), 2)
    message = self.messages_sent[1]
    self.assertTrue(self.APPROVAL_REASON in message)
    self.assertTrue(self.GRANTOR_TOKEN.username in message)

    self.Open(self._ExtractLinkFromMessage(message))

    self.WaitUntil(self.IsTextPresent, "OSBreakDown")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
