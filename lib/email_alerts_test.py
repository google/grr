#!/usr/bin/env python
"""Tests for grr.lib.email_alerts."""

import smtplib

import mock

from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import test_lib


class SendEmailTests(test_lib.GRRBaseTest):

  def testSendEmail(self):
    testdomain = "test.com"
    config_lib.CONFIG.Set("Email.default_domain", testdomain)
    with mock.patch.object(smtplib, "SMTP") as mock_smtp:
      smtp_conn = mock_smtp.return_value

      # Single fully qualified address
      to_address = "testto@example.com"
      from_address = "me@example.com"
      subject = "test"
      message = ""
      email_alerts.SendEmail(to_address, from_address, subject, message)
      c_from, c_to, _ = smtp_conn.sendmail.call_args[0]
      self.assertEqual(from_address, c_from)
      self.assertEqual([to_address], c_to)

      # Multiple unqualified to addresses, one cc
      to_address = "testto,abc,def"
      to_address_expected = [x + testdomain for x in ["testto@", "abc@", "def@",
                                                      "testcc@"]]
      cc_address = "testcc"
      email_alerts.SendEmail(to_address, from_address, subject, message,
                             cc_addresses=cc_address)
      c_from, c_to, message = smtp_conn.sendmail.call_args[0]
      self.assertEqual(from_address, c_from)
      self.assertEqual(to_address_expected, c_to)
      self.assertTrue("CC: testcc@%s" % testdomain in message)

      # Multiple unqualified to addresses, two cc, message_id set
      to_address_expected = [x + testdomain for x in ["testto@", "abc@", "def@",
                                                      "testcc@", "testcc2@"]]
      cc_address = "testcc,testcc2"
      email_msg_id = "123123"
      email_alerts.SendEmail(to_address, from_address, subject, message,
                             cc_addresses=cc_address, message_id=email_msg_id)
      c_from, c_to, message = smtp_conn.sendmail.call_args[0]
      self.assertEqual(from_address, c_from)
      self.assertEqual(to_address_expected, c_to)
      self.assertTrue("CC: testcc@%s,testcc2@%s" % (testdomain, testdomain) in
                      message)
      self.assertTrue("Message-ID: %s" % email_msg_id)

      # Multiple unqualified to addresses, two cc, no default domain
      to_address_expected = ["testto", "abc", "def", "testcc", "testcc2"]
      config_lib.CONFIG.Set("Email.default_domain", None)
      email_alerts.SendEmail(to_address, from_address, subject, message,
                             cc_addresses=cc_address)
      c_from, c_to, message = smtp_conn.sendmail.call_args[0]
      self.assertEqual(from_address, c_from)
      self.assertEqual(to_address_expected, c_to)
      self.assertTrue("CC: testcc@%s,testcc2@%s" % (testdomain, testdomain) in
                      message)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)


