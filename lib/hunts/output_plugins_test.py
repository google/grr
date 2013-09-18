#!/usr/bin/env python
"""Tests for hunts output plugins."""




# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import email_alerts
from grr.lib import flags
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib

from grr.lib.aff4_objects import cronjobs
from grr.lib.hunts import output_plugins

from grr.proto import flows_pb2


class DummyCronHuntOutputPluginArgs(rdfvalue.RDFProtoStruct):
  protobuf = flows_pb2.DummyCronHuntOutputPluginArgs


class DummyCronHuntOutputPlugin(output_plugins.CronHuntOutputPlugin):
  cron_flow_name = "DummyCronHuntOutputPluginFlow"
  args_type = DummyCronHuntOutputPluginArgs


class DummyCronHuntOutputPluginFlow(output_plugins.CronHuntOutputFlow):

  batch_started = 0
  processed_result = 0
  batch_ended = 0

  def StartBatch(self):
    if self.state.args.output_plugin_args.output_path != "/some/path":
      raise ValueError()

    DummyCronHuntOutputPluginFlow.batch_started += 1

  def ProcessResult(self, unused_result):
    DummyCronHuntOutputPluginFlow.processed_result += 1

  def EndBatch(self):
    DummyCronHuntOutputPluginFlow.batch_ended += 1


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
        token=self.token) as hunt:
      hunt.Run()

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients..
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in self.client_ids:
      foreman.AssignTasksToClient(client_id)

    # Run the hunt. Every client mock will be initialized with data equal
    # to: "x" * i. Therefore the file's st_size will be equal to i.
    client_mocks = dict()
    for i, client_id in enumerate(sorted(self.client_ids)):
      client_mocks[client_id] = test_lib.SampleHuntMock(failrate=-1, data="x"*i)

    test_lib.TestHuntHelperWithMultipleMocks(client_mocks,
                                             check_flow_errors=False,
                                             token=self.token)

    return hunt.urn

  def setUp(self):
    super(OutputPluginsTest, self).setUp()
    # Set up 10 clients.
    self.client_ids = self.SetupClients(10)

    DummyCronHuntOutputPluginFlow.batch_started = 0
    DummyCronHuntOutputPluginFlow.processed_result = 0
    DummyCronHuntOutputPluginFlow.batch_ended = 0

  def tearDown(self):
    super(OutputPluginsTest, self).tearDown()
    self.DeleteClients(10)

  def testCronHuntOutputPlugin(self):
    # Check that there are no cron jobs
    self.assertEqual([], list(cronjobs.CRON_MANAGER.ListJobs(token=self.token)))

    hunt_urn = self.RunHunt(plugin_name="DummyCronHuntOutputPlugin",
                            plugin_args=DummyCronHuntOutputPluginArgs(
                                output_path="/some/path",
                                collection_name="DummyResults"))

    # We expect a cron job with a certain name to be scheduled
    cron_jobs_list = list(cronjobs.CRON_MANAGER.ListJobs(token=self.token))
    expected_cron_job_urn = rdfvalue.RDFURN(
        "aff4:/cron/%s_DummyCronHuntOutputPluginFlow" % hunt_urn.Basename())
    self.assertEqual([expected_cron_job_urn], cron_jobs_list)

    # The cron job hasn't executed any flows yet
    cron_job = aff4.FACTORY.Open(expected_cron_job_urn, aff4_type="CronJob",
                                 mode="r", token=self.token)
    self.assertEqual([], list(cron_job.ListChildren()))

    cron_flow_urns = set()

    # Run cron manager and check that there's one flow ready for execution
    cronjobs.CRON_MANAGER.RunOnce(token=self.token)

    self.assertEqual(1, len(list(cron_job.ListChildren())))
    cron_flow_urn = list(cron_job.ListChildren())[0]
    cron_flow_urns.add(cron_flow_urn)

    for _ in test_lib.TestFlowHelper(cron_flow_urn, client_mock=None,
                                     token=self.token):
      pass

    self.assertEqual(DummyCronHuntOutputPluginFlow.batch_started, 1)
    self.assertEqual(DummyCronHuntOutputPluginFlow.processed_result, 10)
    self.assertEqual(DummyCronHuntOutputPluginFlow.batch_ended, 1)

    # Run cron manager again and check that no new batches were processed
    cronjobs.CRON_MANAGER.RunOnce(force=True, token=self.token)

    self.assertEqual(2, len(list(cron_job.ListChildren())))
    cron_flow_urn = list(set(cron_job.ListChildren()) - cron_flow_urns)[0]
    cron_flow_urns.add(cron_flow_urn)

    for _ in test_lib.TestFlowHelper(cron_flow_urn, client_mock=None,
                                     token=self.token):
      pass

    self.assertEqual(DummyCronHuntOutputPluginFlow.batch_started, 1)
    self.assertEqual(DummyCronHuntOutputPluginFlow.processed_result, 10)
    self.assertEqual(DummyCronHuntOutputPluginFlow.batch_ended, 1)

    # Stop the hunt and check that no new batches were processed and that
    # cron job is deleted.
    with aff4.FACTORY.Open(hunt_urn, mode="rw", token=self.token) as hunt:
      hunt.Stop()

    cronjobs.CRON_MANAGER.RunOnce(force=True, token=self.token)

    self.assertEqual(3, len(list(cron_job.ListChildren())))
    cron_flow_urn = list(set(cron_job.ListChildren()) - cron_flow_urns)[0]
    cron_flow_urns.add(cron_flow_urn)

    for _ in test_lib.TestFlowHelper(cron_flow_urn, client_mock=None,
                                     token=self.token,
                                     check_flow_errors=False):
      pass

    self.assertEqual(DummyCronHuntOutputPluginFlow.batch_started, 1)
    self.assertEqual(DummyCronHuntOutputPluginFlow.processed_result, 10)
    self.assertEqual(DummyCronHuntOutputPluginFlow.batch_ended, 1)

    # Cron job should have been disabled by now
    cron_jobs_list = list(cronjobs.CRON_MANAGER.ListJobs(token=self.token))
    self.assertTrue(cron_jobs_list)
    cron_job = aff4.FACTORY.Open(cron_jobs_list[0], aff4_type="CronJob",
                                 token=self.token)
    self.assertTrue(cron_job.Get(cron_job.Schema.DISABLED))

  def testCollectionPlugin(self):
    """Tests the output collection."""
    hunt_urn = self.RunHunt(plugin_name="CollectionPlugin",
                            plugin_args=rdfvalue.CollectionPluginArgs())

    hunt = aff4.FACTORY.Open(hunt_urn, token=self.token)
    collection = aff4.FACTORY.Open(
        hunt.state.context.output_plugins[0].collection.urn,
        mode="r", token=self.token, age=aff4.ALL_TIMES)

    # We should receive stat entries.
    self.assertEqual(len(collection), 10)

    # SampleHuntMock that is used to emulate this hunt
    # assigns different st_gid values depending on the
    # number of StatFile request.
    collection = sorted([x for x in collection],
                        key=lambda x: x.payload.st_size)
    stats = [x.payload for x in collection]

    for i in range(0, 10):
      self.assertEqual(stats[i].__class__, rdfvalue.StatEntry)
      self.assertEqual(stats[i].st_size, i)
      self.assertEqual(collection[i].source, "aff4:/C.1%015d" % i)

  def testEmailPlugin(self):
    def SendEmail(address, sender, title, message, **_):
      self.email_messages.append(dict(address=address, sender=sender,
                                      title=title, message=message))

    with test_lib.Stubber(email_alerts, "SendEmail", SendEmail):
      self.email_messages = []

      email_alerts.SendEmail = SendEmail

      with hunts.GRRHunt.StartHunt(
          hunt_name="GenericHunt",
          flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
          flow_args=rdfvalue.GetFileArgs(
              pathspec=rdfvalue.PathSpec(
                  path="/tmp/evil.txt",
                  pathtype=rdfvalue.PathSpec.PathType.OS,
                  )
              ),
          output_plugins=[
              rdfvalue.OutputPlugin(plugin_name="CollectionPlugin"),
              rdfvalue.OutputPlugin(
                  plugin_name="EmailPlugin",
                  plugin_args=rdfvalue.EmailPluginArgs(
                      email="notify@grrserver.com",
                      email_limit=10)
                  )],
          token=self.token) as hunt:
        hunt.Run()

      self.client_ids = self.SetupClients(40)
      for client_id in self.client_ids:
        hunt.StartClient(hunt.session_id, client_id)

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      # Stop the hunt now.
      with hunt.GetRunner() as runner:
        runner.Stop()

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)

      started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
      finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
      errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

      self.assertEqual(len(set(started)), 40)
      self.assertEqual(len(set(finished)), 40)
      self.assertEqual(len(set(errors)), 20)

      collection = aff4.FACTORY.Open(hunt.urn.Add("Results"),
                                     mode="r", token=self.token)

      self.assertEqual(len(collection), 20)

      # Due to the limit there should only by 10 messages.
      self.assertEqual(len(self.email_messages), 10)

      for msg in self.email_messages:
        self.assertEqual(msg["address"], "notify@grrserver.com")
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
