#!/usr/bin/env python
"""Tests for email output plugin."""

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.output_plugins import email_plugin


class EmailOutputPluginTest(test_lib.FlowTestsBaseclass):
  """Tests email output plugin."""

  def setUp(self):
    super(EmailOutputPluginTest, self).setUp()

    self.client_id = self.SetupClients(1)[0]
    self.hostname = aff4.FACTORY.Open(self.client_id, token=self.token).Get(
        aff4.VFSGRRClient.SchemaCls.HOSTNAME)
    self.results_urn = self.client_id.Add("Results")
    self.email_messages = []
    self.email_address = "notify@%s" % config_lib.CONFIG["Logging.domain"]

  def ProcessResponses(self, plugin_args=None, responses=None,
                       process_responses_separately=False):
    plugin = email_plugin.EmailOutputPlugin(source_urn=self.results_urn,
                                            args=plugin_args,
                                            token=self.token)
    plugin.Initialize()

    messages = []
    for response in responses:
      messages.append(rdfvalue.GrrMessage(source=self.client_id,
                                          payload=response))

    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(dict(address=address, sender=sender,
                                      title=title, message=message))

    with utils.Stubber(email_alerts, "SendEmail", SendEmail):
      if process_responses_separately:
        for message in messages:
          plugin.ProcessResponses([message])
      else:
        plugin.ProcessResponses(messages)

    plugin.Flush()

  def testEmailPluginSendsEmailPerEveyBatchOfResponses(self):
    self.ProcessResponses(
        plugin_args=rdfvalue.EmailOutputPluginArgs(
            email_address=self.email_address),
        responses=[rdfvalue.Process(pid=42)])

    self.assertEqual(len(self.email_messages), 1)

    msg = self.email_messages[0]
    self.assertEqual(msg["address"], self.email_address)
    self.assertTrue(
        "got a new result in %s" % self.results_urn in msg["title"])
    self.assertTrue(utils.SmartStr(self.client_id) in msg["message"])
    self.assertTrue(utils.SmartStr(self.hostname) in msg["message"])

  def testEmailPluginStopsSendingEmailsAfterLimitIsReached(self):
    responses = [rdfvalue.Process(pid=i) for i in range(11)]
    self.ProcessResponses(
        plugin_args=rdfvalue.EmailOutputPluginArgs(
            email_address=self.email_address,
            emails_limit=10),
        responses=responses,
        process_responses_separately=True)

    self.assertEqual(len(self.email_messages), 10)

    for msg in self.email_messages:
      self.assertEqual(msg["address"], self.email_address)
      self.assertTrue(
          "got a new result in %s" % self.results_urn in msg["title"])
      self.assertTrue(utils.SmartStr(self.client_id) in msg["message"])
      self.assertTrue(utils.SmartStr(self.hostname) in msg["message"])

    for msg in self.email_messages[:10]:
      self.assertFalse("sending of emails will be disabled now" in msg)

    self.assertTrue("sending of emails will be disabled now"
                    in self.email_messages[9]["message"])


def main(argv):
  test_lib.GrrTestProgram(argv=argv)

if __name__ == "__main__":
  flags.StartMain(main)
