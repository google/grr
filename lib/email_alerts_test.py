#!/usr/bin/env python
"""Tests for grr.lib.email_alerts."""


from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.rdfvalues import standard as rdf_standard


class SendEmailTests(test_lib.GRRBaseTest):

  def testSplitEmailsAndAppendEmailDomain(self):
    self.assertEqual(email_alerts.SplitEmailsAndAppendEmailDomain(""), [])

  def testSendEmail(self):
    testdomain = "test.com"
    config_lib.CONFIG.Set("Logging.domain", testdomain)
    smtp_conn = self.mock_smtp.return_value

    # Single fully qualified address
    to_address = "testto@example.com"
    from_address = "me@example.com"
    subject = "test"
    message = ""
    email_alerts.SendEmail(to_address, from_address, subject, message)
    c_from, c_to, msg = smtp_conn.sendmail.call_args[0]
    self.assertEqual(from_address, c_from)
    self.assertEqual([to_address], c_to)
    self.assertFalse("CC:" in msg)

    # Single fully qualified address as rdf_standard.DomainEmailAddress
    to_address = rdf_standard.DomainEmailAddress("testto@%s" % testdomain)
    from_address = "me@example.com"
    subject = "test"
    message = ""
    email_alerts.SendEmail(to_address, from_address, subject, message)
    c_from, c_to, msg = smtp_conn.sendmail.call_args[0]
    self.assertEqual(from_address, c_from)
    self.assertEqual([to_address], c_to)
    self.assertFalse("CC:" in msg)

    # Multiple unqualified to addresses, one cc
    to_address = "testto,abc,def"
    to_address_expected = [
        x + testdomain for x in ["testto@", "abc@", "def@"]]
    cc_address = "testcc"
    email_alerts.SendEmail(to_address, from_address, subject, message,
                           cc_addresses=cc_address)
    c_from, c_to, message = smtp_conn.sendmail.call_args[0]
    self.assertEqual(from_address, c_from)
    self.assertEqual(to_address_expected, c_to)
    self.assertTrue("CC: testcc@%s" % testdomain in message)

    # Multiple unqualified to addresses as DomainEmailAddress, one cc
    to_address = [rdf_standard.DomainEmailAddress("testto@%s" % testdomain),
                  rdf_standard.DomainEmailAddress("abc@%s" % testdomain),
                  rdf_standard.DomainEmailAddress("def@%s" % testdomain)]
    to_address_expected = [
        x + testdomain for x in ["testto@", "abc@", "def@"]]
    cc_address = "testcc"
    email_alerts.SendEmail(to_address, from_address, subject, message,
                           cc_addresses=cc_address)
    c_from, c_to, message = smtp_conn.sendmail.call_args[0]
    self.assertEqual(from_address, c_from)
    self.assertEqual(to_address_expected, c_to)
    self.assertTrue("CC: testcc@%s" % testdomain in message)

    # Multiple unqualified to addresses, two cc, message_id set
    to_address = "testto,abc,def"
    to_address_expected = [
        x + testdomain for x in ["testto@", "abc@", "def@"]]
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

    # Multiple address types, two cc, no default domain
    config_lib.CONFIG.Set("Logging.domain", None)
    to_address = ["testto@localhost", "hij",
                  rdf_standard.DomainEmailAddress("klm@localhost")]
    to_address_expected = ["testto@localhost", "hij@localhost", "klm@localhost"]
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
