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
    client_id = self.SetupClients(1)[0]

    messages_sent = []

    def SendEmailStub(unused_from_user, unused_to_user, unused_subject, message,
                      **unused_kwargs):
      messages_sent.append(message)

    # Request client approval, it will trigger an email message.
    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmailStub):
      security.ClientApprovalRequestor(
          reason="Please please let me",
          subject_urn=client_id,
          approver=self.token.username,
          token=access_control.ACLToken(
              username="iwantapproval", reason="test")).Request()
    self.assertEqual(len(messages_sent), 1)

    # Extract link from the message text and open it.
    m = re.search(r"href='(.+?)'", messages_sent[0], re.MULTILINE)
    link = urlparse.urlparse(m.group(1))
    self.Open(link.path + "?" + link.query + "#" + link.fragment)

    # Check that requestor's username and  reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, "iwantapproval")
    self.WaitUntil(self.IsTextPresent, "Please please let me")
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, client_id.Basename())
    self.WaitUntil(self.IsTextPresent, "Host-0")

  def testEmailHuntApprovalRequestLinkLeadsToACorrectPage(self):
    hunt_id = self.CreateSampleHunt()

    messages_sent = []

    def SendEmailStub(unused_from_user, unused_to_user, unused_subject, message,
                      **unused_kwargs):
      messages_sent.append(message)

    # Request client approval, it will trigger an email message.
    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmailStub):
      security.HuntApprovalRequestor(
          reason="Please please let me",
          subject_urn=hunt_id,
          approver=self.token.username,
          token=access_control.ACLToken(
              username="iwantapproval", reason="test")).Request()
    self.assertEqual(len(messages_sent), 1)

    # Extract link from the message text and open it.
    m = re.search(r"href='(.+?)'", messages_sent[0], re.MULTILINE)
    link = urlparse.urlparse(m.group(1))
    self.Open(link.path + "?" + link.query + "#" + link.fragment)

    # Check that requestor's username and reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, "iwantapproval")
    self.WaitUntil(self.IsTextPresent, "Please please let me")
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, str(hunt_id))
    self.WaitUntil(self.IsTextPresent, "SampleHunt")

  def testEmailCronJobApprovalRequestLinkLeadsToACorrectPage(self):
    cronjobs.ScheduleSystemCronFlows(
        names=[cron_system.OSBreakDown.__name__], token=self.token)
    cronjobs.CRON_MANAGER.DisableJob(rdfvalue.RDFURN("aff4:/cron/OSBreakDown"))

    messages_sent = []

    def SendEmailStub(unused_from_user, unused_to_user, unused_subject, message,
                      **unused_kwargs):
      messages_sent.append(message)

    # Request client approval, it will trigger an email message.
    with utils.Stubber(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmailStub):
      security.CronJobApprovalRequestor(
          reason="Please please let me",
          subject_urn="aff4:/cron/OSBreakDown",
          approver=self.token.username,
          token=access_control.ACLToken(
              username="iwantapproval", reason="test")).Request()
    self.assertEqual(len(messages_sent), 1)

    # Extract link from the message text and open it.
    m = re.search(r"href='(.+?)'", messages_sent[0], re.MULTILINE)
    link = urlparse.urlparse(m.group(1))
    self.Open(link.path + "?" + link.query + "#" + link.fragment)

    # Check that requestor's username and reason are correctly displayed.
    self.WaitUntil(self.IsTextPresent, "iwantapproval")
    self.WaitUntil(self.IsTextPresent, "Please please let me")
    # Check that host information is displayed.
    self.WaitUntil(self.IsTextPresent, cron_system.OSBreakDown.__name__)
    self.WaitUntil(self.IsTextPresent, "Periodicity")


def main(argv):
  del argv  # Unused.
  # Run the full test suite
  unittest.main()


if __name__ == "__main__":
  flags.StartMain(main)
