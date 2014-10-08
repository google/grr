#!/usr/bin/env python
"""Tests for the standard hunts."""



import math
import time


import logging

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import access_control
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
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

    self.old_logging_error = logging.error
    logging.error = self.AssertNoCollectionCorruption

  def tearDown(self):
    super(StandardHuntTest, self).tearDown()

    logging.error = self.old_logging_error
    self.DeleteClients(10)

  def AssertNoCollectionCorruption(self, message, *args, **kwargs):
    self.assertFalse(
        "Results collection was changed outside of hunt" in message)
    self.old_logging_error(message, *args, **kwargs)

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

  def RunHunt(self, client_ids=None, **mock_kwargs):
    client_mock = test_lib.SampleHuntMock(**mock_kwargs)
    test_lib.TestHuntHelper(client_mock, client_ids or self.client_ids, False,
                            self.token)

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

      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 10)
      self.assertEqual(finished, 10)
      self.assertEqual(errors, 5)

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

    with utils.Stubber(time, "time", TimeStub):
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

    with utils.Stubber(time, "time", TimeStub):
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

    with utils.Stubber(DummyHuntOutputPlugin, "ProcessResponses",
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
    started, finished, errors = hunt_obj.GetClientsCounts()
    self.assertEqual(started, 2)
    # Amazing as it may sound, 3 is actually a correct value as we run 2 flows
    # on a second client.
    self.assertEqual(finished, 3)
    self.assertEqual(errors, 0)

  def testStatsHunt(self):
    interval = rdfvalue.Duration(
        config_lib.CONFIG["StatsHunt.CollectionInterval"])
    batch_size = 3
    config_lib.CONFIG.Set("StatsHunt.ClientBatchSize", batch_size)

    # Make one of the clients windows
    with aff4.FACTORY.Open(self.client_ids[3], mode="rw",
                           token=self.token) as win_client:
      win_client.Set(win_client.Schema.SYSTEM("Windows"))

    with test_lib.FakeTime(0, increment=0.01):
      with hunts.GRRHunt.StartHunt(
          hunt_name="StatsHunt", client_rate=0, token=self.token,
          output_plugins=[
              rdfvalue.OutputPlugin(plugin_name="DummyHuntOutputPlugin")
              ]) as hunt:
        hunt.Run()

      hunt_urn = hunt.urn
      # Run the hunt.
      self.AssignTasksToClients()

      client_mock = action_mocks.InterrogatedClient()
      client_mock.InitializeClient()
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      # At this time the clients should not receive any messages since messages
      # are posted in the future.
      self.assertEqual(client_mock.response_count, 0)

    # Lets advance the time and re-run the hunt. The clients should now receive
    # their messages.
    with test_lib.FakeTime(10 + interval.seconds, increment=0.01):
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      self.assertEqual(client_mock.response_count, len(self.client_ids))

      # Make sure the last message was of LOW_PRIORITY (all messages should be
      # LOW_PRIORITY but we only check the last one).
      self.assertEqual(client_mock.recorded_messages[-1].priority,
                       "LOW_PRIORITY")

      # Check fastpoll was false for all messages
      self.assertFalse(any([x.require_fastpoll for x in
                            client_mock.recorded_messages]))

    # Pause the hunt
    with aff4.FACTORY.OpenWithLock(hunt.urn, token=self.token) as hunt:
      hunt.GetRunner().Pause()

    # Advance time and re-run. We get the results back from last time, but don't
    # schedule any new ones because the hunt is now paused.
    with test_lib.FakeTime(20 + (interval.seconds * 2), increment=0.01):
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      self.assertEqual(client_mock.response_count, len(self.client_ids) * 2)

    # Advance time and re-run. We should have the same number of responses
    # still.
    with test_lib.FakeTime(30 + (interval.seconds * 3), increment=0.01):
      test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

      # All clients were called.
      self.assertEqual(client_mock.response_count, len(self.client_ids) * 2)

    # Check the results got written to the collection
    result_collection = aff4.FACTORY.Open(hunt_urn.Add("Results"),
                                          token=self.token)

    # The +1 is here because we write 2 responses for the single windows machine
    # (dnsconfig and interface)
    self.assertEqual(len(result_collection), (len(self.client_ids) + 1) * 2)

  def testStatsHuntFilterLocalhost(self):
    statshunt = aff4.FACTORY.Create("aff4:/temp", "StatsHunt")
    self.assertTrue(statshunt.ProcessInterface(
        rdfvalue.Interface(mac_address="123")))
    self.assertFalse(statshunt.ProcessInterface(
        rdfvalue.Interface(ifname="lo")))

  def testHuntTermination(self):
    """This tests that hunts with a client limit terminate correctly."""
    with test_lib.FakeTime(1000, increment=1e-6):
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

      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 5)
      self.assertEqual(finished, 5)
      self.assertEqual(errors, 2)

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

      # No client should be processed since the hunt is expired.
      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 0)
      self.assertEqual(finished, 0)
      self.assertEqual(errors, 0)

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

    # There should be only one client, due to the limit
    started, _, _ = hunt_obj.GetClientsCounts()
    self.assertEqual(started, 1)

    # Check the hunt is paused.
    self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "PAUSED")

    with aff4.FACTORY.Open(
        hunt_session_id, mode="rw", token=self.token) as hunt_obj:
      runner = hunt_obj.GetRunner()
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
    # There should be only one client, due to the limit
    started, _, _ = hunt_obj.GetClientsCounts()
    self.assertEqual(started, 10)

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

  def testHuntCollectionCorruptionIsProperlyDetected(self):
    corruption_found = []

    def CheckCorruption(message, *args, **kwargs):
      if "Results collection was changed outside of hunt" in message:
        corruption_found.append(True)
      self.old_logging_error(message, *args, **kwargs)

    logging.error = CheckCorruption

    # Run hunt on a client. There should be no collection corruption detected.
    hunt_urn = self.StartHunt()
    self.AssignTasksToClients(client_ids=[self.client_ids[0]])
    self.RunHunt(client_ids=[self.client_ids[0]], failrate=0)
    self.assertFalse(corruption_found)
    # We expect 1 result in the collection.
    with aff4.FACTORY.Open(hunt_urn.Add("Results"),
                           token=self.token) as hunt_results:
      self.assertEqual(len(hunt_results), 1)

    # Change the results collection (i.e. corrupt it).
    with aff4.FACTORY.Open(hunt_urn.Add("Results"), token=self.token,
                           mode="rw") as hunt_results:
      hunt_results.Add(rdfvalue.GrrMessage(name="foo"))

    # Run hunt on another client. Corrupption should be detected now.
    self.AssignTasksToClients(client_ids=[self.client_ids[1]])
    self.RunHunt(client_ids=[self.client_ids[1]], failrate=0)
    self.assertTrue(corruption_found)
    corruption_found = []
    # We expect to have 2 results in the collection (if corruption detection
    # didn't work, we'd have 3).
    with aff4.FACTORY.Open(hunt_urn.Add("Results"),
                           token=self.token) as hunt_results:
      self.assertEqual(len(hunt_results), 2)

    # Run hunt on yet another client. Now, again, there should be no
    # corruption detected.
    self.AssignTasksToClients(client_ids=self.client_ids[2:4])
    self.RunHunt(client_ids=self.client_ids[2:4], failrate=0)
    self.assertFalse(corruption_found)
    # We expect to have 3 results in the collection.
    with aff4.FACTORY.Open(hunt_urn.Add("Results"),
                           token=self.token) as hunt_results:
      self.assertEqual(len(hunt_results), 4)

  def testCreatorPropagation(self):
    self.CreateAdminUser("adminuser")
    admin_token = access_control.ACLToken(username="adminuser",
                                          reason="testing")
    # Start a flow that requires admin privileges in the hunt. The
    # parameters are not valid so the flow will error out but it's
    # enough to check if the flow was actually run (i.e., it passed
    # the label test).
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=rdfvalue.FlowRunnerArgs(flow_name="UpdateClient"),
        flow_args=rdfvalue.UpdateClientArgs(),
        regex_rules=[
            rdfvalue.ForemanAttributeRegex(attribute_name="GRR client",
                                           attribute_regex="GRR"),
            ],
        client_rate=0, token=admin_token) as hunt:
      hunt.Run()

    self.CreateUser("nonadmin")
    nonadmin_token = access_control.ACLToken(username="nonadmin",
                                             reason="testing")
    self.AssignTasksToClients()

    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False,
                            nonadmin_token)

    errors = list(hunt.GetClientsErrors())
    # Make sure there are errors...
    self.assertTrue(errors)
    # but they are not UnauthorizedAccess.
    for e in errors:
      self.assertTrue("UnauthorizedAccess" not in e.backtrace)


def main(args):
  test_lib.main(args)

if __name__ == "__main__":
  flags.StartMain(main)
