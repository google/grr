#!/usr/bin/env python
"""Tests for email output plugin."""
from unittest import mock

from absl import app

from grr_response_core import config
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import email_alerts
from grr_response_server.output_plugins import email_plugin
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class EmailOutputPluginTest(flow_test_lib.FlowTestsBaseclass):
  """Tests email output plugin."""

  def setUp(self):
    super().setUp()

    self.hostname = "somehostname"
    self.client_id = self.SetupClient(0, fqdn=self.hostname)
    self.results_urn = rdf_client.ClientURN(self.client_id).Add("Results")
    self.email_messages = []
    self.email_address = "notify@%s" % config.CONFIG["Logging.domain"]

  def ProcessResponses(self,
                       plugin_args=None,
                       responses=None,
                       process_responses_separately=False):
    plugin_cls = email_plugin.EmailOutputPlugin
    plugin, plugin_state = plugin_cls.CreatePluginAndDefaultState(
        source_urn=self.results_urn, args=plugin_args)

    messages = []
    for response in responses:
      messages.append(
          rdf_flows.GrrMessage(source=self.client_id, payload=response))

    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(
          dict(address=address, sender=sender, title=title, message=message))

    with mock.patch.object(email_alerts.EMAIL_ALERTER, "SendEmail", SendEmail):
      if process_responses_separately:
        for message in messages:
          plugin.ProcessResponses(plugin_state, [message])
      else:
        plugin.ProcessResponses(plugin_state, messages)

    plugin.Flush(plugin_state)
    plugin.UpdateState(plugin_state)

  def testEmailPluginSendsEmailPerEveyBatchOfResponses(self):
    self.ProcessResponses(
        plugin_args=email_plugin.EmailOutputPluginArgs(
            email_address=self.email_address),
        responses=[rdf_client.Process(pid=42)])

    self.assertLen(self.email_messages, 1)

    msg = self.email_messages[0]
    self.assertEqual(msg["address"], self.email_address)
    self.assertIn("got a new result in %s" % self.results_urn, msg["title"])
    self.assertIn(self.client_id, msg["message"])
    self.assertIn(self.hostname, msg["message"])

  def testEmailPluginStopsSendingEmailsAfterLimitIsReached(self):
    responses = [rdf_client.Process(pid=i) for i in range(11)]
    self.ProcessResponses(
        plugin_args=email_plugin.EmailOutputPluginArgs(
            email_address=self.email_address, emails_limit=10),
        responses=responses,
        process_responses_separately=True)

    self.assertLen(self.email_messages, 10)

    for msg in self.email_messages:
      self.assertEqual(msg["address"], self.email_address)
      self.assertIn("got a new result in %s" % self.results_urn, msg["title"])
      self.assertIn(self.client_id, msg["message"])
      self.assertIn(self.hostname, msg["message"])

    for msg in self.email_messages[:10]:
      self.assertNotIn("sending of emails will be disabled now", msg)

    self.assertIn("sending of emails will be disabled now",
                  self.email_messages[9]["message"])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
