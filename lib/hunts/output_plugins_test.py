#!/usr/bin/env python
"""Tests for hunts output plugins."""




# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib


class OutputPluginsTest(test_lib.FlowTestsBaseclass):
  """Tests hunt output plugins."""

  def RunHunt(self, plugin_name, plugin_args):
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt", pathtype=rdfvalue.PathSpec.PathType.OS)),
        regex_rules=[rdfvalue.ForemanAttributeRegex(
            attribute_name="GRR client",
            attribute_regex="GRR")],
        output_plugins=[rdfvalue.OutputPlugin(
            plugin_name=plugin_name,
            plugin_args=plugin_args)],
        client_rate=0, token=self.token) as hunt:
      hunt.Run()

      for client_id in self.client_ids:
        hunt.StartClient(hunt.session_id, client_id)

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      # Stop the hunt now.
      with hunt.GetRunner() as runner:
        runner.Stop()

    # Run cron flow that executes actual output plugins
    for _ in test_lib.TestFlowHelper("ProcessHuntResultsCronFlow",
                                     token=self.token):
      pass

    return hunt.urn

  def setUp(self):
    super(OutputPluginsTest, self).setUp()
    # Set up 10 clients.
    self.client_ids = self.SetupClients(40)

  def testEmailPlugin(self):
    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(dict(address=address, sender=sender,
                                      title=title, message=message))

    with test_lib.Stubber(email_alerts, "SendEmail", SendEmail):
      self.email_messages = []

      email_alerts.SendEmail = SendEmail
      email_address = "notify@%s" % config_lib.CONFIG["Logging.domain"]

      hunt_urn = self.RunHunt("EmailPlugin", rdfvalue.EmailPluginArgs(
          email=email_address, email_limit=10))

      hunt_obj = aff4.FACTORY.Open(hunt_urn, age=aff4.ALL_TIMES,
                                   mode="rw", token=self.token)

      self.client_ids = self.SetupClients(40)
      for client_id in self.client_ids:
        hunt_obj.StartClient(hunt_obj.session_id, client_id)

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      # Run cron flow that executes actual output plugins
      for _ in test_lib.TestFlowHelper("ProcessHuntResultsCronFlow",
                                       token=self.token):
        pass

      # Stop the hunt now.
      with hunt_obj.GetRunner() as runner:
        runner.Stop()

      hunt_obj = aff4.FACTORY.Open(hunt_urn, age=aff4.ALL_TIMES,
                                   token=self.token)

      started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
      finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
      errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

      self.assertEqual(len(set(started)), 40)
      self.assertEqual(len(set(finished)), 40)
      self.assertEqual(len(set(errors)), 20)

      collection = aff4.FACTORY.Open(hunt_urn.Add("Results"),
                                     mode="r", token=self.token)

      self.assertEqual(len(collection), 20)

      # Due to the limit there should only by 10 messages.
      self.assertEqual(len(self.email_messages), 10)

      for msg in self.email_messages:
        self.assertEqual(msg["address"], email_address)
        self.assertTrue(
            "%s produced a new result" % hunt_obj.session_id in msg["title"])
        self.assertTrue("fs/os/tmp/evil.txt" in msg["message"])

      self.assertTrue("sending of emails will be disabled now"
                      in self.email_messages[-1]["message"])


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.FlowTestsBaseclass


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
