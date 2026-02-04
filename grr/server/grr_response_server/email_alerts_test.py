#!/usr/bin/env python
from unittest import mock

from absl import app

from grr_response_core.lib.rdfvalues import standard as rdf_standard
from grr_response_server import email_alerts
from grr.test_lib import test_lib


class SendEmailTests(test_lib.GRRBaseTest):

  def setUp(self):
    super().setUp()
    # We have to stop mail_stubber, otherwise email_alerts.EMAIL_ALERTER will
    # be just a stub and there will be nothing to test.
    self.mail_stubber.Stop()

  def testSplitEmailsAndAppendEmailDomain(self):
    self.assertEqual(
        email_alerts.EMAIL_ALERTER.SplitEmailsAndAppendEmailDomain(""), []
    )

  def testSendEmail(self):
    # This is already patched out in tests but in this specific test we
    # are interested in the results so we just add another patcher.
    with mock.patch("smtplib.SMTP") as mock_smtp:
      testdomain = "test.com"
      with test_lib.ConfigOverrider({"Logging.domain": testdomain}):
        smtp_conn = mock_smtp.return_value

        # Single fully qualified address
        to_address = "testto@example.com"
        from_address = "me@example.com"
        subject = "test"
        message = ""
        email_alerts.EMAIL_ALERTER.SendEmail(
            to_address, from_address, subject, message
        )
        c_from, c_to, msg = smtp_conn.sendmail.call_args[0]
        self.assertCountEqual(from_address, c_from)
        self.assertCountEqual([to_address], c_to)
        self.assertNotIn("CC:", msg)

        # Single fully qualified address as rdf_standard.DomainEmailAddress
        to_address = rdf_standard.DomainEmailAddress("testto@%s" % testdomain)
        from_address = "me@example.com"
        subject = "test"
        message = ""
        email_alerts.EMAIL_ALERTER.SendEmail(
            to_address, from_address, subject, message
        )
        c_from, c_to, msg = smtp_conn.sendmail.call_args[0]
        self.assertCountEqual(from_address, c_from)
        self.assertCountEqual([to_address], c_to)
        self.assertNotIn("CC:", msg)

        # Multiple unqualified to addresses, one cc
        to_address = "testto,abc,def"
        to_address_expected = [
            x + testdomain for x in ["testto@", "abc@", "def@", "testcc@"]
        ]
        cc_address = "testcc"
        email_alerts.EMAIL_ALERTER.SendEmail(
            to_address, from_address, subject, message, cc_addresses=cc_address
        )
        c_from, c_to, message = smtp_conn.sendmail.call_args[0]
        self.assertCountEqual(from_address, c_from)
        self.assertCountEqual(to_address_expected, c_to)
        self.assertIn("CC: testcc@%s" % testdomain, message)

        # Multiple unqualified to addresses as DomainEmailAddress, one cc
        to_address = [
            rdf_standard.DomainEmailAddress("testto@%s" % testdomain),
            rdf_standard.DomainEmailAddress("abc@%s" % testdomain),
            rdf_standard.DomainEmailAddress("def@%s" % testdomain),
        ]
        to_address_expected = [
            x + testdomain for x in ["testto@", "abc@", "def@", "testcc@"]
        ]
        cc_address = "testcc"
        email_alerts.EMAIL_ALERTER.SendEmail(
            to_address, from_address, subject, message, cc_addresses=cc_address
        )
        c_from, c_to, message = smtp_conn.sendmail.call_args[0]
        self.assertCountEqual(from_address, c_from)
        self.assertCountEqual(to_address_expected, c_to)
        self.assertIn("CC: testcc@%s" % testdomain, message)

        # Multiple unqualified to addresses, two cc, message_id set
        to_address = "testto,abc,def"
        to_address_expected = [
            x + testdomain
            for x in ["testto@", "abc@", "def@", "testcc@", "testcc2@"]
        ]
        cc_address = "testcc,testcc2"
        email_msg_id = "123123"
        email_alerts.EMAIL_ALERTER.SendEmail(
            to_address,
            from_address,
            subject,
            message,
            cc_addresses=cc_address,
            message_id=email_msg_id,
        )
        c_from, c_to, message = smtp_conn.sendmail.call_args[0]
        self.assertCountEqual(from_address, c_from)
        self.assertCountEqual(to_address_expected, c_to)
        self.assertIn(
            "CC: testcc@%s,testcc2@%s" % (testdomain, testdomain), message
        )
        self.assertTrue("Message-ID: %s" % email_msg_id)

      # Multiple address types, two cc
      with test_lib.ConfigOverrider({"Logging.domain": "localhost"}):
        to_address = [
            "testto@localhost",
            "hij",
            rdf_standard.DomainEmailAddress("klm@localhost"),
        ]
        cc_address = "testcc,testcc2@localhost"
        to_address_expected = [
            "testto@localhost",
            "hij@localhost",
            "klm@localhost",
            "testcc@localhost",
            "testcc2@localhost",
        ]
        email_alerts.EMAIL_ALERTER.SendEmail(
            to_address, from_address, subject, message, cc_addresses=cc_address
        )
        c_from, c_to, message = smtp_conn.sendmail.call_args[0]
        self.assertCountEqual(from_address, c_from)
        self.assertCountEqual(to_address_expected, c_to)
        self.assertIn(
            "CC: testcc@%s,testcc2@%s" % (testdomain, testdomain), message
        )

  def testSendEmailWithStarttlsNotSupported(self):
    """Email should send when STARTTLS is not supported (non-strict mode)."""
    with mock.patch("smtplib.SMTP") as mock_smtp:
      with test_lib.ConfigOverrider({
          "Logging.domain": "test.com",
          "Worker.smtp_starttls": True,
      }):
        smtp_conn = mock_smtp.return_value
        smtp_conn.has_extn.return_value = False

        email_alerts.EMAIL_ALERTER.SendEmail(
            "testto@example.com", "me@example.com", "test", "test message"
        )

        smtp_conn.has_extn.assert_called_with("starttls")
        smtp_conn.starttls.assert_not_called()
        smtp_conn.sendmail.assert_called_once()

  def testSendEmailWithStarttlsSupported(self):
    """STARTTLS should be used when supported."""
    with mock.patch("smtplib.SMTP") as mock_smtp:
      with test_lib.ConfigOverrider({
          "Logging.domain": "test.com",
          "Worker.smtp_starttls": True,
      }):
        smtp_conn = mock_smtp.return_value
        smtp_conn.has_extn.return_value = True

        email_alerts.EMAIL_ALERTER.SendEmail(
            "testto@example.com", "me@example.com", "test", "test message"
        )

        smtp_conn.starttls.assert_called_once()
        smtp_conn.sendmail.assert_called_once()

  def testSendEmailAuthFailsWithoutStarttls(self):
    """Auth failure should provide helpful error when STARTTLS unavailable."""
    with mock.patch("smtplib.SMTP") as mock_smtp:
      with test_lib.ConfigOverrider({
          "Logging.domain": "test.com",
          "Worker.smtp_starttls": True,
          "Worker.smtp_user": "testuser",
          "Worker.smtp_password": "testpass",
      }):
        smtp_conn = mock_smtp.return_value
        smtp_conn.has_extn.return_value = False
        smtp_conn.login.side_effect = smtplib.SMTPAuthenticationError(
            535, b"Authentication failed"
        )

        with self.assertRaises(email_alerts.EmailNotSentError) as context:
          email_alerts.EMAIL_ALERTER.SendEmail(
              "testto@example.com", "me@example.com", "test", "test message"
          )

        self.assertIn("STARTTLS", str(context.exception))

  def testSendEmailWithStarttlsStrictMode(self):
    """Strict mode should fail when STARTTLS is not supported."""
    with mock.patch("smtplib.SMTP") as mock_smtp:
      with test_lib.ConfigOverrider({
          "Logging.domain": "test.com",
          "Worker.smtp_starttls": True,
          "Worker.smtp_starttls_strict": True,
      }):
        smtp_conn = mock_smtp.return_value
        smtp_conn.has_extn.return_value = False

        with self.assertRaises(email_alerts.EmailNotSentError):
          email_alerts.EMAIL_ALERTER.SendEmail(
              "testto@example.com", "me@example.com", "test", "test message"
          )

        smtp_conn.sendmail.assert_not_called()

  def testSendEmailWithStarttlsNonStrictMode(self):
    """Non-strict mode should continue when STARTTLS is not supported."""
    with mock.patch("smtplib.SMTP") as mock_smtp:
      with test_lib.ConfigOverrider({
          "Logging.domain": "test.com",
          "Worker.smtp_starttls": True,
          "Worker.smtp_starttls_strict": False,
      }):
        smtp_conn = mock_smtp.return_value
        smtp_conn.has_extn.return_value = False

        email_alerts.EMAIL_ALERTER.SendEmail(
            "testto@example.com", "me@example.com", "test", "test message"
        )

        smtp_conn.sendmail.assert_called_once()
        smtp_conn.starttls.assert_not_called()


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
