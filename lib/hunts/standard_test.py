#!/usr/bin/env python
"""Tests for the standard hunts."""



import math
import time


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import flags
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.hunts import output_plugins


class DummyHuntOutputPlugin(output_plugins.HuntOutputPlugin):
  num_calls = 0
  num_responses = 0

  def ProcessResponses(self, responses):
    DummyHuntOutputPlugin.num_calls += 1
    DummyHuntOutputPlugin.num_responses += len(list(responses))


class FailingDummyHuntOutputPlugin(output_plugins.HuntOutputPlugin):

  def ProcessResponses(self, unused_responses):
    raise RuntimeError("Oh no!")


class StatefulDummyHuntOutputPlugin(output_plugins.HuntOutputPlugin):
  data = []

  def Initialize(self):
    super(StatefulDummyHuntOutputPlugin, self).Initialize()
    self.state.Register("index", 0)

  def ProcessResponses(self, unused_responses):
    StatefulDummyHuntOutputPlugin.data.append(self.state.index)
    self.state.index += 1


class LongRunningDummyHuntOutputPlugin(output_plugins.HuntOutputPlugin):
  num_calls = 0

  def ProcessResponses(self, unused_responses):
    LongRunningDummyHuntOutputPlugin.num_calls += 1
    time.time = lambda: 100


class StandardHuntTest(test_lib.FlowTestsBaseclass):
  """Tests the Hunt."""

  def setUp(self):
    super(StandardHuntTest, self).setUp()
    # Set up 10 clients.
    self.client_ids = self.SetupClients(10)

    DummyHuntOutputPlugin.num_calls = 0
    DummyHuntOutputPlugin.num_responses = 0
    StatefulDummyHuntOutputPlugin.data = []
    LongRunningDummyHuntOutputPlugin.num_calls = 0

    with test_lib.FakeTime(0):
      # Clean up the foreman to remove any rules.
      with aff4.FACTORY.Open("aff4:/foreman", mode="rw",
                             token=self.token) as foreman:
        foreman.Set(foreman.Schema.RULES())

  def tearDown(self):
    super(StandardHuntTest, self).tearDown()
    self.DeleteClients(10)

  def StartHunt(self, **kwargs):
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(pathspec=rdfvalue.PathSpec(
            path="/tmp/evil.txt", pathtype=rdfvalue.PathSpec.PathType.OS)),
        regex_rules=[
            rdfvalue.ForemanAttributeRegex(attribute_name="GRR client",
                                           attribute_regex="GRR"),
            ],
        client_rate=0, token=self.token, **kwargs) as hunt:
      hunt.Run()

    return hunt.urn

  def AssignTasksToClients(self, client_ids=None):
    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients..
    client_ids = client_ids or self.client_ids
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

  def RunHunt(self, **mock_kwargs):
    client_mock = test_lib.SampleHuntMock(**mock_kwargs)
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

  def StopHunt(self, hunt_urn):
    # Stop the hunt now.
    with aff4.FACTORY.Open(hunt_urn, age=aff4.ALL_TIMES, mode="rw",
                           token=self.token) as hunt_obj:
      hunt_obj.Stop()

  def ProcessHuntOutputPlugins(self, **flow_args):
    flow_urn = flow.GRRFlow.StartFlow(flow_name="ProcessHuntResultsCronFlow",
                                      token=self.token, **flow_args)
    for _ in test_lib.TestFlowHelper(flow_urn, token=self.token):
      pass
    return flow_urn

  def testGenericHuntWithoutOutputPlugins(self):
    """This tests running the hunt on some clients."""
    hunt_urn = self.StartHunt()
    self.AssignTasksToClients()
    self.RunHunt()
    self.StopHunt(hunt_urn)
    self.ProcessHuntOutputPlugins()

    with aff4.FACTORY.Open(hunt_urn, age=aff4.ALL_TIMES,
                           token=self.token) as hunt_obj:
      started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
      finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
      errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

      self.assertEqual(len(set(started)), 10)
      self.assertEqual(len(set(finished)), 10)
      self.assertEqual(len(set(errors)), 5)

      # Results collection is always written, even if there are no output
      # plugins.
      collection = aff4.FACTORY.Open(
          hunt_obj.state.context.results_collection_urn,
          mode="r", token=self.token)

      # We should receive stat entries.
      i = 0
      for i, x in enumerate(collection):
        self.assertEqual(x.payload.__class__, rdfvalue.StatEntry)
        self.assertEqual(x.payload.aff4path.Split(2)[-1], "fs/os/tmp/evil.txt")

      self.assertEqual(i, 4)

  def testOutputPluginsProcessOnlyNewResultsOnEveryRun(self):
    self.StartHunt(output_plugins=[rdfvalue.OutputPlugin(
        plugin_name="DummyHuntOutputPlugin")])

    # Process hunt results.
    self.ProcessHuntOutputPlugins()

    # Check that nothing has happened because hunt hasn't reported any
    # results yet.
    self.assertEqual(DummyHuntOutputPlugin.num_calls, 0)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 0)

    # Process first 5 clients
    self.AssignTasksToClients(self.client_ids[:5])

    # Run the hunt.
    self.RunHunt(failrate=-1)

    # Although we call ProcessHuntResultsCronFlow multiple times, it should
    # only call actual plugin once.
    for _ in range(5):
      self.ProcessHuntOutputPlugins()

    self.assertEqual(DummyHuntOutputPlugin.num_calls, 1)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 5)

    # Process last 5 clients
    self.AssignTasksToClients(self.client_ids[5:])

    # Run the hunt.
    self.RunHunt(failrate=-1)

    # Although we call ProcessHuntResultsCronFlow multiple times, it should
    # only call actual plugin once.
    for _ in range(5):
      self.ProcessHuntOutputPlugins()

    self.assertEqual(DummyHuntOutputPlugin.num_calls, 2)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 10)

  def testFailingOutputPluginDoesNotAffectOtherOutputPlugins(self):
    self.StartHunt(output_plugins=[
        rdfvalue.OutputPlugin(plugin_name="FailingDummyHuntOutputPlugin"),
        rdfvalue.OutputPlugin(plugin_name="DummyHuntOutputPlugin")
        ])

    # Process hunt results.
    self.ProcessHuntOutputPlugins()

    self.assertEqual(DummyHuntOutputPlugin.num_calls, 0)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 0)

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)

    # We shouldn't get any more calls after the first call to
    # ProcessHuntResultsCronFlow.
    self.assertRaises(RuntimeError, self.ProcessHuntOutputPlugins)
    for _ in range(5):
      self.ProcessHuntOutputPlugins()

    self.assertEqual(DummyHuntOutputPlugin.num_calls, 1)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 10)

  def testOutputPluginsMaintainState(self):
    self.StartHunt(output_plugins=[rdfvalue.OutputPlugin(
        plugin_name="StatefulDummyHuntOutputPlugin")])

    self.assertListEqual(StatefulDummyHuntOutputPlugin.data, [])

    # Run the hunt on every client and separately and run the output
    # cron flow for every client to ensure that output plugin will
    # run multiple times.
    for index in range(10):
      self.AssignTasksToClients([self.client_ids[index]])

      # Run the hunt.
      self.RunHunt(failrate=-1)
      self.ProcessHuntOutputPlugins()

    # Output plugins should have been called 10 times, adding a number
    # to the "data" list on every call and incrementing it each time.
    self.assertListEqual(StatefulDummyHuntOutputPlugin.data,
                         [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

  def testMultipleHuntsOutputIsProcessedCorrectly(self):
    self.StartHunt(output_plugins=[rdfvalue.OutputPlugin(
        plugin_name="DummyHuntOutputPlugin")])
    self.StartHunt(output_plugins=[rdfvalue.OutputPlugin(
        plugin_name="StatefulDummyHuntOutputPlugin")])

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)
    self.ProcessHuntOutputPlugins()

    # Check that plugins worked correctly
    self.assertEqual(DummyHuntOutputPlugin.num_calls, 1)
    self.assertListEqual(StatefulDummyHuntOutputPlugin.data, [0])

  def testProcessHuntResultsCronFlowAbortsIfRunningTooLong(self):
    self.assertEqual(LongRunningDummyHuntOutputPlugin.num_calls, 0)

    test = [0]
    def TimeStub():
      test[0] += 1e-6
      return test[0]

    with test_lib.Stubber(time, "time", TimeStub):
      self.StartHunt(output_plugins=[rdfvalue.OutputPlugin(
          plugin_name="LongRunningDummyHuntOutputPlugin")])
      self.AssignTasksToClients()
      self.RunHunt(failrate=-1)

      # LongRunningDummyHuntOutputPlugin will set the time to 100s on the first
      # run, which will effectively mean that it's running for too long.
      self.ProcessHuntOutputPlugins(batch_size=1,
                                    max_running_time=rdfvalue.Duration("99s"))

      # In normal conditions, there should be 10 results generated.
      # With batch size of 1 this should result in 10 calls to output plugin.
      # But as we were using TimeStub, the flow should have aborted after 1
      # call.
      self.assertEqual(LongRunningDummyHuntOutputPlugin.num_calls, 1)

  def testProcessHuntResultsCronFlowDoesNotAbortsIfRunningInTime(self):
    self.assertEqual(LongRunningDummyHuntOutputPlugin.num_calls, 0)

    test = [0]
    def TimeStub():
      test[0] += 1e-6
      return test[0]

    with test_lib.Stubber(time, "time", TimeStub):
      self.StartHunt(output_plugins=[rdfvalue.OutputPlugin(
          plugin_name="LongRunningDummyHuntOutputPlugin")])
      self.AssignTasksToClients()
      self.RunHunt(failrate=-1)

      # LongRunningDummyHuntOutputPlugin will set the time to 100s on the first
      # run, which will effectively mean that it's running in time.
      self.ProcessHuntOutputPlugins(batch_size=1,
                                    max_running_time=rdfvalue.Duration("101s"))

      # In normal conditions, there should be 10 results generated.
      self.assertEqual(LongRunningDummyHuntOutputPlugin.num_calls, 10)

  def testHuntResultsArrivingWhileOldResultsAreProcessedAreHandled(self):
    self.StartHunt(output_plugins=[rdfvalue.OutputPlugin(
        plugin_name="DummyHuntOutputPlugin")])

    # Process hunt results.
    self.ProcessHuntOutputPlugins()

    # Check that nothing has happened because hunt hasn't reported any
    # results yet.
    self.assertEqual(DummyHuntOutputPlugin.num_calls, 0)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 0)

    # Generate new results while the plugin is working.
    def ProcessResponsesStub(_, responses):
      self.assertEqual(len(responses), 5)
      self.AssignTasksToClients(self.client_ids[5:])
      self.RunHunt(failrate=-1)

    with test_lib.Stubber(DummyHuntOutputPlugin, "ProcessResponses",
                          ProcessResponsesStub):
      # Process first 5 clients.
      self.AssignTasksToClients(self.client_ids[:5])
      self.RunHunt(failrate=-1)
      self.ProcessHuntOutputPlugins()

    self.ProcessHuntOutputPlugins()
    # New results should get processed, even though they were added to the
    # collection while plugin was processing previous results.
    self.assertEqual(DummyHuntOutputPlugin.num_calls, 1)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 5)

  def _AppendFlowRequest(self, flows, client_id, file_id):
    flows.Append(
        client_ids=["C.1%015d" % client_id],
        runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
        args=rdfvalue.GetFileArgs(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil%s.txt" % file_id,
                pathtype=rdfvalue.PathSpec.PathType.OS),
            )
        )

  def RunVariableGenericHunt(self):
    args = rdfvalue.VariableGenericHuntArgs()
    self._AppendFlowRequest(args.flows, 1, 1)
    self._AppendFlowRequest(args.flows, 2, 2)
    self._AppendFlowRequest(args.flows, 2, 3)

    with hunts.GRRHunt.StartHunt(hunt_name="VariableGenericHunt",
                                 args=args, client_rate=0,
                                 token=self.token) as hunt:
      hunt.Run()
      hunt.ManuallyScheduleClients()

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock(failrate=100)
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    # Stop the hunt now.
    with aff4.FACTORY.Open(hunt.session_id, mode="rw",
                           token=self.token) as hunt:
      hunt.Stop()

    return hunt

  def testVariableGenericHunt(self):
    """This tests running the hunt on some clients."""
    hunt = self.RunVariableGenericHunt()

    hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                 token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
    errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

    self.assertEqual(len(set(started)), 2)
    self.assertEqual(len(set(finished)), 2)
    self.assertEqual(len(set(errors)), 0)

  def testHuntTermination(self):
    """This tests that hunts with a client limit terminate correctly."""
    with test_lib.FakeTime(1000):
      with hunts.GRRHunt.StartHunt(
          hunt_name="GenericHunt",
          flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
          flow_args=rdfvalue.GetFileArgs(
              pathspec=rdfvalue.PathSpec(
                  path="/tmp/evil.txt",
                  pathtype=rdfvalue.PathSpec.PathType.OS)
              ),
          regex_rules=[rdfvalue.ForemanAttributeRegex(
              attribute_name="GRR client",
              attribute_regex="GRR")],
          client_limit=5, client_rate=0,
          expiry_time=rdfvalue.Duration("1000s"), token=self.token) as hunt:
        hunt.Run()

      # Pretend to be the foreman now and dish out hunting jobs to all the
      # clients (Note we have 10 clients here).
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids,
                              check_flow_errors=False, token=self.token)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)

      started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
      finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
      errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

      self.assertEqual(len(set(started)), 5)
      self.assertEqual(len(set(finished)), 5)
      self.assertEqual(len(set(errors)), 2)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)

      # Hunts are automatically paused when they reach the client limit.
      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "PAUSED")

  def testHuntExpiration(self):
    """This tests that hunts with a client limit terminate correctly."""
    with test_lib.FakeTime(1000):
      with hunts.GRRHunt.StartHunt(
          hunt_name="GenericHunt",
          flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
          flow_args=rdfvalue.GetFileArgs(
              pathspec=rdfvalue.PathSpec(
                  path="/tmp/evil.txt",
                  pathtype=rdfvalue.PathSpec.PathType.OS)
              ),
          regex_rules=[rdfvalue.ForemanAttributeRegex(
              attribute_name="GRR client",
              attribute_regex="GRR")],
          client_limit=5,
          expiry_time=rdfvalue.Duration("1000s"),
          token=self.token) as hunt:
        hunt.Run()

      # Pretend to be the foreman now and dish out hunting jobs to all the
      # clients (Note we have 10 clients here).
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)

      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "STARTED")

      # Now advance the time such that the hunt expires.
      time.time = lambda: 5000

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock, self.client_ids,
                              check_flow_errors=False, token=self.token)

      started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
      finished = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.FINISHED)
      errors = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.ERRORS)

      # No client should be processed since the hunt is expired.
      self.assertEqual(len(set(started)), 0)
      self.assertEqual(len(set(finished)), 0)
      self.assertEqual(len(set(errors)), 0)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id, age=aff4.ALL_TIMES,
                                   token=self.token)

      # Hunts are automatically stopped when they expire.
      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "STOPPED")

  def testHuntModificationWorksCorrectly(self):
    """This tests running the hunt on some clients."""
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.PathSpec.PathType.OS),
            ),
        regex_rules=[rdfvalue.ForemanAttributeRegex(
            attribute_name="GRR client",
            attribute_regex="GRR")],
        client_limit=1,
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()

    # Forget about hunt object, we'll use AFF4 for everything.
    hunt_session_id = hunt.session_id
    hunt = None

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # client..
    with aff4.FACTORY.Open(
        "aff4:/foreman", mode="rw", token=self.token) as foreman:
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    # Re-open the hunt to get fresh data.
    hunt_obj = aff4.FACTORY.Open(hunt_session_id, age=aff4.ALL_TIMES,
                                 ignore_cache=True, token=self.token)

    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)

    # There should be only one client, due to the limit
    self.assertEqual(len(set(started)), 1)

    # Check the hunt is paused.
    self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "PAUSED")

    with aff4.FACTORY.Open(
        hunt_session_id, mode="rw", token=self.token) as hunt_obj:
      with hunt_obj.GetRunner() as runner:
        runner.args.client_limit = 10
        runner.Start()

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients.
    with aff4.FACTORY.Open(
        "aff4:/foreman", mode="rw", token=self.token) as foreman:
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open(hunt_session_id, age=aff4.ALL_TIMES,
                                 token=self.token)
    started = hunt_obj.GetValuesForAttribute(hunt_obj.Schema.CLIENTS)
    # There should be only one client, due to the limit
    self.assertEqual(len(set(started)), 10)

  def testResourceUsageStats(self):
    client_ids = self.SetupClients(10)

    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(
            flow_name="GetFile"),
        flow_args=rdfvalue.GetFileArgs(
            pathspec=rdfvalue.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdfvalue.PathSpec.PathType.OS,
                )
            ),
        regex_rules=[rdfvalue.ForemanAttributeRegex(
            attribute_name="GRR client",
            attribute_regex="GRR")],
        output_plugins=[], client_rate=0, token=self.token) as hunt:
      hunt.Run()

    with aff4.FACTORY.Open(
        "aff4:/foreman", mode="rw", token=self.token) as foreman:
      for client_id in client_ids:
        foreman.AssignTasksToClient(client_id)

    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt = aff4.FACTORY.Open(hunt.urn, aff4_type="GenericHunt",
                             token=self.token)

    # This is called once for each state method. Each flow above runs the
    # Start and the StoreResults methods.
    usage_stats = hunt.state.context.usage_stats
    self.assertEqual(usage_stats.user_cpu_stats.num, 10)
    self.assertTrue(math.fabs(usage_stats.user_cpu_stats.mean -
                              5.5) < 1e-7)
    self.assertTrue(math.fabs(usage_stats.user_cpu_stats.std -
                              2.8722813) < 1e-7)

    self.assertEqual(usage_stats.system_cpu_stats.num, 10)
    self.assertTrue(math.fabs(usage_stats.system_cpu_stats.mean -
                              11) < 1e-7)
    self.assertTrue(math.fabs(usage_stats.system_cpu_stats.std -
                              5.7445626) < 1e-7)

    self.assertEqual(usage_stats.network_bytes_sent_stats.num, 10)
    self.assertTrue(math.fabs(usage_stats.network_bytes_sent_stats.mean -
                              16.5) < 1e-7)
    self.assertTrue(math.fabs(usage_stats.network_bytes_sent_stats.std -
                              8.61684396) < 1e-7)

    # NOTE: Not checking histograms here. RunningStatsTest tests that mean,
    # standard deviation and histograms are calculated correctly. Therefore
    # if mean/stdev values are correct histograms should be ok as well.

    self.assertEqual(len(usage_stats.worst_performers), 10)

    prev = usage_stats.worst_performers[0]
    for p in usage_stats.worst_performers[1:]:
      self.assertTrue(prev.cpu_usage.user_cpu_time +
                      prev.cpu_usage.system_cpu_time >
                      p.cpu_usage.user_cpu_time +
                      p.cpu_usage.system_cpu_time)
      prev = p

  def testHuntCollectionLogging(self):
    """This tests running the hunt on some clients."""
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="DummyLogFlow"),
        client_rate=0, token=self.token) as hunt:
      hunt.Run()
      hunt.Log("Log from the hunt itself")

    hunt_urn = hunt.urn

    self.AssignTasksToClients()
    self.RunHunt()
    self.StopHunt(hunt_urn)

    # Check logs were written to the hunt collection
    with aff4.FACTORY.Open(hunt_urn.Add("Logs"), token=self.token,
                           age=aff4.ALL_TIMES) as hunt_logs:

      # Can't use len with PackedVersionCollection
      count = 0
      for log in hunt_logs:
        if log.client_id:
          self.assertTrue(log.client_id in self.client_ids)
          self.assertTrue(log.log_message in ["First", "Second", "Third",
                                              "Fourth", "Uno", "Dos", "Tres",
                                              "Cuatro"])
          self.assertTrue(log.flow_name in ["DummyLogFlow",
                                            "DummyLogFlowChild"])
          self.assertTrue(str(hunt_urn) in str(log.urn))
        else:
          self.assertEqual(log.log_message, "Log from the hunt itself")
          self.assertEqual(log.flow_name, "GenericHunt")
          self.assertEqual(log.urn, hunt_urn)

        count += 1
      # 4 logs for each flow, 2 flow run.  One hunt-level log.
      self.assertEqual(count, 8 * len(self.client_ids) + 1)


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.FlowTestsBaseclass


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
