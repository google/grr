#!/usr/bin/env python
"""Tests for the standard hunts."""



import math
import time


import mock

import logging

from grr.lib import access_control
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import hunts
from grr.lib import output_plugin
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import test_lib
from grr.lib import utils
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import collects
from grr.lib.aff4_objects import user_managers
from grr.lib.flows.general import administrative
from grr.lib.flows.general import transfer
from grr.lib.hunts import implementation
from grr.lib.hunts import process_results
from grr.lib.hunts import standard
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.server import foreman as rdf_foreman


class DummyHuntOutputPlugin(output_plugin.OutputPlugin):
  num_calls = 0
  num_responses = 0

  def ProcessResponses(self, responses):
    DummyHuntOutputPlugin.num_calls += 1
    DummyHuntOutputPlugin.num_responses += len(list(responses))


class FailingDummyHuntOutputPlugin(output_plugin.OutputPlugin):

  def ProcessResponses(self, unused_responses):
    raise RuntimeError("Oh no!")


class FailingInFlushDummyHuntOutputPlugin(output_plugin.OutputPlugin):

  def ProcessResponses(self, unused_responses):
    pass

  def Flush(self):
    raise RuntimeError("Flush, oh no!")


class StatefulDummyHuntOutputPlugin(output_plugin.OutputPlugin):
  data = []

  def Initialize(self):
    super(StatefulDummyHuntOutputPlugin, self).Initialize()
    self.state.Register("index", 0)

  def ProcessResponses(self, unused_responses):
    StatefulDummyHuntOutputPlugin.data.append(self.state.index)
    self.state.index += 1


class LongRunningDummyHuntOutputPlugin(output_plugin.OutputPlugin):
  num_calls = 0

  def ProcessResponses(self, unused_responses):
    LongRunningDummyHuntOutputPlugin.num_calls += 1
    time.time = lambda: 100


class VerifiableDummyHuntOutputPlugin(output_plugin.OutputPlugin):

  def ProcessResponses(self, unused_responses):
    pass


class VerifiableDummyHuntOutputPluginVerfier(
    output_plugin.OutputPluginVerifier):
  plugin_name = VerifiableDummyHuntOutputPlugin.__name__

  num_calls = 0

  def VerifyHuntOutput(self, plugin, hunt):
    # Check that we get the plugin object we expected to get.
    # Actual verifiers implementations don't have to do this check.
    if not isinstance(plugin, VerifiableDummyHuntOutputPlugin):
      raise ValueError("Passed plugin must be an "
                       "VerifiableDummyHuntOutputPlugin, got: " %
                       plugin.__class__.__name__)

    VerifiableDummyHuntOutputPluginVerfier.num_calls += 1
    return output_plugin.OutputPluginVerificationResult(status="SUCCESS",
                                                        status_message="yo")

  def VerifyFlowOutput(self, plugin, hunt):
    pass


class DummyHuntOutputPluginWithRaisingVerifier(output_plugin.OutputPlugin):

  def ProcessResponses(self, unused_responses):
    pass


class DummyHuntOutputPluginWithRaisingVerifierVerifier(
    output_plugin.OutputPluginVerifier):
  plugin_name = DummyHuntOutputPluginWithRaisingVerifier.__name__

  def VerifyHuntOutput(self, plugin, hunt):
    # Check that we get the plugin object we expected to get.
    # Actual verifiers implementations don't have to do this check.
    if not isinstance(plugin, DummyHuntOutputPluginWithRaisingVerifier):
      raise ValueError("Passed plugin must be an "
                       "VerifiableDummyHuntOutputPlugin, got: " %
                       plugin.__class__.__name__)

    raise RuntimeError("foobar")

  def VerifyFlowOutput(self, plugin, hunt):
    pass


class InfiniteFlow(flow.GRRFlow):
  """Flow that never ends."""

  @flow.StateHandler(next_state="NextState")
  def Start(self):
    self.CallState(next_state="NextState")

  @flow.StateHandler(next_state="Start")
  def NextState(self):
    self.CallState(next_state="Start")


class StandardHuntTestMixin(object):
  """Mixin with helper methods for hunt tests."""

  def CreateHunt(self, token=None, **kwargs):
    return hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.OS)),
        client_rule_set=rdf_foreman.ForemanClientRuleSet(rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
                regex=rdf_foreman.ForemanRegexClientRule(
                    attribute_name="GRR client",
                    attribute_regex="GRR"))
        ]),
        client_rate=0,
        token=token or self.token,
        **kwargs)

  def StartHunt(self, **kwargs):
    with self.CreateHunt(**kwargs) as hunt:
      hunt.Run()

    return hunt.urn

  def AssignTasksToClients(self, client_ids=None):
    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients..
    client_ids = client_ids or self.client_ids
    foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
    for client_id in client_ids:
      foreman.AssignTasksToClient(client_id)

  def RunHunt(self, client_ids=None, iteration_limit=None, **mock_kwargs):
    client_mock = test_lib.SampleHuntMock(**mock_kwargs)
    test_lib.TestHuntHelper(client_mock,
                            client_ids or self.client_ids,
                            check_flow_errors=False,
                            iteration_limit=iteration_limit,
                            token=self.token)

  def StopHunt(self, hunt_urn):
    # Stop the hunt now.
    with aff4.FACTORY.Open(hunt_urn,
                           age=aff4.ALL_TIMES,
                           mode="rw",
                           token=self.token) as hunt_obj:
      hunt_obj.Stop()

  def ProcessHuntOutputPlugins(self, **flow_args):
    flow_urn = flow.GRRFlow.StartFlow(
        flow_name=process_results.ProcessHuntResultCollectionsCronFlow.__name__,
        token=self.token,
        **flow_args)
    for _ in test_lib.TestFlowHelper(flow_urn, token=self.token):
      pass
    return flow_urn


class StandardHuntTest(test_lib.FlowTestsBaseclass, StandardHuntTestMixin):
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
      with aff4.FACTORY.Open("aff4:/foreman",
                             mode="rw",
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

  def testCreatesSymlinksOnClientsForEveryStartedFlow(self):
    hunt_urn = self.StartHunt()
    self.AssignTasksToClients()
    self.RunHunt()

    for client_id in self.client_ids:
      flows_fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
      flows_urns = list(flows_fd.ListChildren())
      self.assertEqual(len(flows_urns), 1)
      self.assertEqual(flows_urns[0].Basename(), hunt_urn.Basename() + ":hunt")

      # Check that the object is a symlink.
      fd = aff4.FACTORY.Open(flows_urns[0],
                             follow_symlinks=False,
                             token=self.token)
      self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4Symlink")

      target = fd.Get(fd.Schema.SYMLINK_TARGET)
      # Check that the symlink points into the hunt's namespace.
      self.assertTrue(str(target).startswith(str(hunt_urn)))

  def testDeletesSymlinksOnClientsWhenGetsDeletedItself(self):
    hunt_urn = self.StartHunt()
    self.AssignTasksToClients()
    self.RunHunt()

    for client_id in self.client_ids:
      # Check that symlinks to hunt-initiated flows are there as the hunt is
      # not deleted yet.
      flows_fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
      self.assertTrue(list(flows_fd.ListChildren()))

    aff4.FACTORY.Delete(hunt_urn, token=self.token)

    for client_id in self.client_ids:
      # Check that symlinks to hunt-initiated flows were deleted.
      flows_fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
      self.assertFalse(list(flows_fd.ListChildren()))

  def testStoppingHuntMarksAllStartedFlowsAsPendingForTermination(self):
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="InfiniteFlow"),
        client_rule_set=rdf_foreman.ForemanClientRuleSet(rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
                regex=rdf_foreman.ForemanRegexClientRule(
                    attribute_name="GRR client",
                    attribute_regex="GRR"))
        ]),
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()

    self.AssignTasksToClients()

    # Run long enough for InfiniteFlows to start.
    self.RunHunt(iteration_limit=len(self.client_ids) * 2)
    self.StopHunt(hunt.urn)

    # All flows should be marked for termination now. RunHunt should raise.
    # If something is wrong with GRRFlow.MarkForTermination mechanism, then
    # this will run forever.
    self.RunHunt()

    for client_id in self.client_ids:
      flows_root = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
      flows_list = list(flows_root.ListChildren())
      # Only one flow (issued by the hunt) is expected.
      self.assertEqual(len(flows_list), 1)

      flow_obj = aff4.FACTORY.Open(flows_list[0],
                                   aff4_type=InfiniteFlow,
                                   token=self.token)
      self.assertEqual(flow_obj.state.context.state, "ERROR")
      self.assertEqual(flow_obj.state.context.backtrace, "Parent hunt stopped.")

  def testGenericHuntWithoutOutputPlugins(self):
    """This tests running the hunt on some clients."""
    hunt_urn = self.StartHunt()
    self.AssignTasksToClients()
    self.RunHunt()
    self.StopHunt(hunt_urn)
    self.ProcessHuntOutputPlugins()

    with aff4.FACTORY.Open(hunt_urn,
                           age=aff4.ALL_TIMES,
                           token=self.token) as hunt_obj:

      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 10)
      self.assertEqual(finished, 10)
      self.assertEqual(errors, 5)

      # Results collection is always written, even if there are no output
      # plugins.
      collection = aff4.FACTORY.Open(
          hunt_obj.state.context.results_collection_urn,
          mode="r",
          token=self.token)

      # We should receive stat entries.
      i = 0
      for i, x in enumerate(collection):
        self.assertEqual(x.payload.__class__, rdf_client.StatEntry)
        self.assertEqual(x.payload.aff4path.Split(2)[-1], "fs/os/tmp/evil.txt")

      self.assertEqual(i, 4)

  def testHuntWithoutForemanRules(self):
    """Check no foreman rules are created if we pass add_foreman_rules=False."""
    hunt_urn = self.StartHunt(add_foreman_rules=False)
    with aff4.FACTORY.Open("aff4:/foreman",
                           mode="r",
                           token=self.token,
                           aff4_type=aff4_grr.GRRForeman,
                           ignore_cache=True) as foreman:
      foreman_rules = foreman.Get(foreman.Schema.RULES,
                                  default=foreman.Schema.RULES())
      self.assertFalse(foreman_rules)

    self.AssignTasksToClients()
    self.RunHunt()
    self.StopHunt(hunt_urn)

    with aff4.FACTORY.Open(hunt_urn,
                           age=aff4.ALL_TIMES,
                           token=self.token) as hunt_obj:

      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 0)
      self.assertEqual(finished, 0)
      self.assertEqual(errors, 0)

  def testProcessHunResultsCronFlowDoesNothingWhenThereAreNoResults(self):
    # There's no hunt, nothing. Just assert that cron job completes
    # successfully.
    self.ProcessHuntOutputPlugins()

  def testProcessHuntResultCronFlowDoesNothingOnFalseNotifications(self):
    # There may be cases when we've got the notification, but for some reason
    # there are no new results in the corresponding hunt. Assert that cron
    # job handles this scenario gracefully.
    hunt_urn = self.StartHunt()
    hunt_obj = aff4.FACTORY.Open(hunt_urn, token=self.token)
    collects.ResultsOutputCollection.ScheduleNotification(
        hunt_obj.state.context.results_collection_urn,
        token=self.token)
    self.ProcessHuntOutputPlugins()

  def testOutputPluginsProcessOnlyNewResultsOnEveryRun(self):
    self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
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

    # Although we call ProcessHuntResultCollectionsCronFlow multiple times, it
    # should only call actual plugin once.
    for _ in range(5):
      self.ProcessHuntOutputPlugins()

    self.assertEqual(DummyHuntOutputPlugin.num_calls, 1)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 5)

    # Process last 5 clients
    self.AssignTasksToClients(self.client_ids[5:])

    # Run the hunt.
    self.RunHunt(failrate=-1)

    # Although we call ProcessHuntResultCollectionsCronFlow multiple times, it
    # should only call actual plugin once.
    for _ in range(5):
      self.ProcessHuntOutputPlugins()

    self.assertEqual(DummyHuntOutputPlugin.num_calls, 2)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 10)

  def testOutputPluginsProcessingStatusIsWrittenToStatusCollection(self):
    plugin_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")
    hunt_urn = self.StartHunt(output_plugins=[plugin_descriptor])

    # Run the hunt and process output plugins.
    self.AssignTasksToClients(self.client_ids)
    self.RunHunt(failrate=-1)
    self.ProcessHuntOutputPlugins()

    hunt = aff4.FACTORY.Open(hunt_urn, token=self.token)
    status_collection = aff4.FACTORY.Open(
        hunt.output_plugins_status_collection_urn,
        token=self.token)
    errors_collection = aff4.FACTORY.Open(
        hunt.output_plugins_errors_collection_urn,
        token=self.token)

    self.assertEqual(len(errors_collection), 0)
    self.assertEqual(len(status_collection), 1)

    self.assertEqual(status_collection[0].status, "SUCCESS")
    self.assertEqual(status_collection[0].batch_index, 0)
    self.assertEqual(status_collection[0].batch_size, 10)
    self.assertEqual(status_collection[0].plugin_descriptor, plugin_descriptor)

  def testMultipleOutputPluginsProcessingStatusAreWrittenToStatusCollection(
      self):
    plugin_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")
    hunt_urn = self.StartHunt(output_plugins=[plugin_descriptor])

    # Run the hunt on first 4 clients and process output plugins.
    self.AssignTasksToClients(self.client_ids[:4])
    self.RunHunt(failrate=-1)
    self.ProcessHuntOutputPlugins()

    # Run the hunt on last 6 clients and process output plugins.
    self.AssignTasksToClients(self.client_ids[4:])
    self.RunHunt(failrate=-1)
    self.ProcessHuntOutputPlugins()

    hunt = aff4.FACTORY.Open(hunt_urn, token=self.token)
    status_collection = aff4.FACTORY.Open(
        hunt.output_plugins_status_collection_urn,
        token=self.token)
    errors_collection = aff4.FACTORY.Open(
        hunt.output_plugins_errors_collection_urn,
        token=self.token)

    self.assertEqual(len(errors_collection), 0)
    self.assertEqual(len(status_collection), 2)

    items = sorted(status_collection, key=lambda x: x.age)
    self.assertEqual(items[0].status, "SUCCESS")
    self.assertEqual(items[0].batch_index, 0)
    self.assertEqual(items[0].batch_size, 4)
    self.assertEqual(items[0].plugin_descriptor, plugin_descriptor)

    self.assertEqual(items[1].status, "SUCCESS")
    self.assertEqual(items[1].batch_index, 0)
    self.assertEqual(items[1].batch_size, 6)
    self.assertEqual(items[1].plugin_descriptor, plugin_descriptor)

  def testErrorOutputPluginStatusIsAlsoWrittenToErrorsCollection(self):
    failing_plugin_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin")
    plugin_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")
    hunt_urn = self.StartHunt(output_plugins=[
        failing_plugin_descriptor, plugin_descriptor
    ])

    # Run the hunt and process output plugins.
    self.AssignTasksToClients(self.client_ids)
    self.RunHunt(failrate=-1)
    try:
      self.ProcessHuntOutputPlugins()
    except process_results.ResultsProcessingError:
      pass

    hunt = aff4.FACTORY.Open(hunt_urn, token=self.token)
    status_collection = aff4.FACTORY.Open(
        hunt.output_plugins_status_collection_urn,
        token=self.token)
    errors_collection = aff4.FACTORY.Open(
        hunt.output_plugins_errors_collection_urn,
        token=self.token)

    self.assertEqual(len(errors_collection), 1)
    self.assertEqual(len(status_collection), 2)

    self.assertEqual(errors_collection[0].status, "ERROR")
    self.assertEqual(errors_collection[0].batch_index, 0)
    self.assertEqual(errors_collection[0].batch_size, 10)
    self.assertEqual(errors_collection[0].plugin_descriptor,
                     failing_plugin_descriptor)
    self.assertEqual(errors_collection[0].summary, "Oh no!")

    items = sorted(status_collection,
                   key=lambda x: x.plugin_descriptor.plugin_name)
    self.assertEqual(items[0].status, "SUCCESS")
    self.assertEqual(items[0].batch_index, 0)
    self.assertEqual(items[0].batch_size, 10)
    self.assertEqual(items[0].plugin_descriptor, plugin_descriptor)

    self.assertEqual(items[1].status, "ERROR")
    self.assertEqual(items[1].batch_index, 0)
    self.assertEqual(items[1].batch_size, 10)
    self.assertEqual(items[1].plugin_descriptor, failing_plugin_descriptor)
    self.assertEqual(items[1].summary, "Oh no!")

  def testOutputPluginFlushErrorIsLoggedProperly(self):
    failing_plugin_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name="FailingInFlushDummyHuntOutputPlugin")
    hunt_urn = self.StartHunt(output_plugins=[failing_plugin_descriptor])

    # Run the hunt and process output plugins.
    self.AssignTasksToClients(self.client_ids)
    self.RunHunt(failrate=-1)
    try:
      self.ProcessHuntOutputPlugins()
    except process_results.ResultsProcessingError:
      pass

    hunt = aff4.FACTORY.Open(hunt_urn, token=self.token)
    status_collection = aff4.FACTORY.Open(
        hunt.output_plugins_status_collection_urn,
        token=self.token)
    errors_collection = aff4.FACTORY.Open(
        hunt.output_plugins_errors_collection_urn,
        token=self.token)

    self.assertEqual(len(errors_collection), 1)
    self.assertEqual(len(status_collection), 1)

    self.assertEqual(errors_collection[0].status, "ERROR")
    self.assertEqual(errors_collection[0].batch_index, 0)
    self.assertEqual(errors_collection[0].batch_size, 10)
    self.assertEqual(errors_collection[0].plugin_descriptor,
                     failing_plugin_descriptor)
    self.assertEqual(errors_collection[0].summary, "Flush, oh no!")

    items = sorted(status_collection,
                   key=lambda x: x.plugin_descriptor.plugin_name)

    self.assertEqual(items[0].status, "ERROR")
    self.assertEqual(items[0].batch_index, 0)
    self.assertEqual(items[0].batch_size, 10)
    self.assertEqual(items[0].plugin_descriptor, failing_plugin_descriptor)
    self.assertEqual(items[0].summary, "Flush, oh no!")

  def testFailingOutputPluginDoesNotAffectOtherOutputPlugins(self):
    self.StartHunt(output_plugins=[
        output_plugin.OutputPluginDescriptor(
            plugin_name="FailingDummyHuntOutputPlugin"),
        output_plugin.OutputPluginDescriptor(
            plugin_name="DummyHuntOutputPlugin")
    ])

    # Process hunt results.
    self.ProcessHuntOutputPlugins()

    self.assertEqual(DummyHuntOutputPlugin.num_calls, 0)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 0)

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)

    # We shouldn't get any more calls after the first call to
    # ProcessHuntResultCollectionsCronFlow.
    self.assertRaises(process_results.ResultsProcessingError,
                      self.ProcessHuntOutputPlugins)
    for _ in range(5):
      self.ProcessHuntOutputPlugins()

    self.assertEqual(DummyHuntOutputPlugin.num_calls, 1)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 10)

  def testResultsProcessingErrorContainsDetailedFailureData(self):
    failing_plugin_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin")
    plugin_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")
    hunt_urn = self.StartHunt(output_plugins=[
        failing_plugin_descriptor, plugin_descriptor
    ])

    # Process hunt results.
    self.ProcessHuntOutputPlugins()

    self.assertEqual(DummyHuntOutputPlugin.num_calls, 0)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 0)

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)

    # We shouldn't get any more calls after the first call to
    # ProcessHuntResultCollectionsCronFlow.
    try:
      self.ProcessHuntOutputPlugins()

      # We shouldn't get here.
      self.fail()
    except process_results.ResultsProcessingError as e:
      self.assertEqual(len(e.exceptions_by_hunt), 1)
      self.assertTrue(hunt_urn in e.exceptions_by_hunt)
      self.assertEqual(len(e.exceptions_by_hunt[hunt_urn]), 1)
      self.assertTrue(
          failing_plugin_descriptor in e.exceptions_by_hunt[hunt_urn])
      self.assertEqual(
          len(e.exceptions_by_hunt[hunt_urn][failing_plugin_descriptor]), 1)
      self.assertEqual(
          e.exceptions_by_hunt[hunt_urn][failing_plugin_descriptor][0].message,
          "Oh no!")

  @mock.patch.object(FailingDummyHuntOutputPlugin,
                     "ProcessResponses",
                     side_effect=RuntimeError("Oh, no"))
  def testResultsAreNotProcessedAgainAfterPluginFailure(self,
                                                        process_responses_mock):
    failing_plugin_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin")
    self.StartHunt(output_plugins=[failing_plugin_descriptor])

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)

    # Process hunt results.
    try:
      self.ProcessHuntOutputPlugins()
    except process_results.ResultsProcessingError:
      pass
    self.assertEqual(process_responses_mock.call_count, 1)

    self.ProcessHuntOutputPlugins()
    # Check that call count hasn't changed.
    self.assertEqual(process_responses_mock.call_count, 1)

  def testUpdatesStatsCounterOnSuccess(self):
    failing_plugin_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")
    self.StartHunt(output_plugins=[failing_plugin_descriptor])

    prev_success_count = stats.STATS.GetMetricValue(
        "hunt_results_ran_through_plugin",
        fields=["DummyHuntOutputPlugin"])
    prev_errors_count = stats.STATS.GetMetricValue(
        "hunt_output_plugin_errors",
        fields=["DummyHuntOutputPlugin"])

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)
    self.ProcessHuntOutputPlugins()

    success_count = stats.STATS.GetMetricValue(
        "hunt_results_ran_through_plugin",
        fields=["DummyHuntOutputPlugin"])
    errors_count = stats.STATS.GetMetricValue("hunt_output_plugin_errors",
                                              fields=["DummyHuntOutputPlugin"])

    # 1 result for each client makes it 10 results.
    self.assertEqual(success_count - prev_success_count, 10)

    self.assertEqual(errors_count - prev_errors_count, 0)

  def testUpdatesStatsCounterOnFailure(self):
    failing_plugin_descriptor = output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin")
    self.StartHunt(output_plugins=[failing_plugin_descriptor])

    prev_success_count = stats.STATS.GetMetricValue(
        "hunt_results_ran_through_plugin",
        fields=["FailingDummyHuntOutputPlugin"])
    prev_errors_count = stats.STATS.GetMetricValue(
        "hunt_output_plugin_errors",
        fields=["FailingDummyHuntOutputPlugin"])

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)
    try:
      self.ProcessHuntOutputPlugins()
    except process_results.ResultsProcessingError:
      pass

    success_count = stats.STATS.GetMetricValue(
        "hunt_results_ran_through_plugin",
        fields=["FailingDummyHuntOutputPlugin"])
    errors_count = stats.STATS.GetMetricValue(
        "hunt_output_plugin_errors",
        fields=["FailingDummyHuntOutputPlugin"])

    self.assertEqual(success_count - prev_success_count, 0)
    self.assertEqual(errors_count - prev_errors_count, 1)

  def testOutputPluginsMaintainState(self):
    self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
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
    self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")])
    self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
        plugin_name="StatefulDummyHuntOutputPlugin")])

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)
    self.ProcessHuntOutputPlugins()

    # Check that plugins worked correctly
    self.assertEqual(DummyHuntOutputPlugin.num_calls, 1)
    self.assertListEqual(StatefulDummyHuntOutputPlugin.data, [0])

  def testProcessHuntResultCollectionsCronFlowAbortsIfRunningTooLong(self):
    self.assertEqual(LongRunningDummyHuntOutputPlugin.num_calls, 0)

    test = [0]

    def TimeStub():
      test[0] += 1e-6
      return test[0]

    with utils.Stubber(time, "time", TimeStub):
      self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
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

  def testProcessHuntResultCollectionsCronFlowDoesNotAbortsIfRunningInTime(
      self):
    self.assertEqual(LongRunningDummyHuntOutputPlugin.num_calls, 0)

    test = [0]

    def TimeStub():
      test[0] += 1e-6
      return test[0]

    with utils.Stubber(time, "time", TimeStub):
      self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
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
    self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")])

    # Process hunt results.
    self.ProcessHuntOutputPlugins()

    # Check that nothing has happened because hunt hasn't reported any
    # results yet.
    self.assertEqual(DummyHuntOutputPlugin.num_calls, 0)
    self.assertEqual(DummyHuntOutputPlugin.num_responses, 0)

    # Generate new results while the plugin is working.
    self.num_processed = 0

    def ProcessResponsesStub(_, responses):
      # Add 5 more results the first time we are called.
      if not self.num_processed:
        self.AssignTasksToClients(self.client_ids[5:])
        self.RunHunt(failrate=-1)
      # Just count the total number processed - we don't care about batch size
      # at this point.
      self.num_processed += len(responses)

    with utils.Stubber(DummyHuntOutputPlugin, "ProcessResponses",
                       ProcessResponsesStub):
      self.AssignTasksToClients(self.client_ids[:5])
      self.RunHunt(failrate=-1)
      self.ProcessHuntOutputPlugins()

    self.assertEqual(10, self.num_processed)
    del self.num_processed

  def _AppendFlowRequest(self, flows, client_id, file_id):
    flows.Append(client_ids=["C.1%015d" % client_id],
                 runner_args=flow_runner.FlowRunnerArgs(flow_name="GetFile"),
                 args=transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
                     path="/tmp/evil%s.txt" % file_id,
                     pathtype=rdf_paths.PathSpec.PathType.OS),))

  def RunVariableGenericHunt(self):
    args = standard.VariableGenericHuntArgs()
    self._AppendFlowRequest(args.flows, 1, 1)
    self._AppendFlowRequest(args.flows, 2, 2)
    self._AppendFlowRequest(args.flows, 2, 3)

    with hunts.GRRHunt.StartHunt(hunt_name="VariableGenericHunt",
                                 args=args,
                                 client_rate=0,
                                 token=self.token) as hunt:
      hunt.Run()
      hunt.ManuallyScheduleClients()

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock(failrate=100)
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    with aff4.FACTORY.Open(hunt.session_id,
                           mode="rw",
                           token=self.token) as hunt:
      hunt.Stop()

    return hunt

  def testVariableGenericHunt(self):
    """This tests running the hunt on some clients."""
    hunt = self.RunVariableGenericHunt()

    hunt_obj = aff4.FACTORY.Open(hunt.session_id,
                                 age=aff4.ALL_TIMES,
                                 token=self.token)
    started, finished, errors = hunt_obj.GetClientsCounts()
    self.assertEqual(started, 2)
    # Amazing as it may sound, 3 is actually a correct value as we run 2 flows
    # on a second client.
    self.assertEqual(finished, 3)
    self.assertEqual(errors, 0)

  def testStatsHunt(self):
    interval = rdfvalue.Duration(config_lib.CONFIG[
        "StatsHunt.CollectionInterval"])
    batch_size = 3
    with test_lib.ConfigOverrider({"StatsHunt.ClientBatchSize": batch_size}):
      # Make one of the clients windows
      with aff4.FACTORY.Open(self.client_ids[3],
                             mode="rw",
                             token=self.token) as win_client:
        win_client.Set(win_client.Schema.SYSTEM("Windows"))

      with test_lib.FakeTime(0, increment=1e-6):
        with hunts.GRRHunt.StartHunt(
            hunt_name="StatsHunt",
            client_rate=0,
            token=self.token,
            output_plugins=[
                output_plugin.OutputPluginDescriptor(
                    plugin_name="DummyHuntOutputPlugin")
            ]) as hunt:
          hunt.Run()

        hunt_urn = hunt.urn
        # Run the hunt.
        self.AssignTasksToClients()

        client_mock = action_mocks.InterrogatedClient()
        client_mock.InitializeClient()
        test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

        # At this time the clients should not receive any messages since
        # messages are posted in the future.
        self.assertEqual(client_mock.response_count, 0)

      # Lets advance the time and re-run the hunt. The clients should now
      # receive their messages.
      with test_lib.FakeTime(10 + interval.seconds, increment=1e-6):
        test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

        self.assertEqual(client_mock.response_count, len(self.client_ids))

        # Make sure the last message was of LOW_PRIORITY (all messages should be
        # LOW_PRIORITY but we only check the last one).
        self.assertEqual(client_mock.recorded_messages[-1].priority,
                         "LOW_PRIORITY")

        # Check fastpoll was false for all messages
        self.assertFalse(any([x.require_fastpoll
                              for x in client_mock.recorded_messages]))

        # Pause the hunt
        with aff4.FACTORY.OpenWithLock(hunt.urn, token=self.token) as hunt:
          hunt.GetRunner().Pause()

      # Advance time and re-run. We get the results back from last time, but
      # don't schedule any new ones because the hunt is now paused.
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
      result_collection = aff4.FACTORY.Open(
          hunt_urn.Add("Results"), token=self.token)

      # The +1 is here because we write 2 responses for the single windows
      # machine (dnsconfig and interface)
      self.assertEqual(len(result_collection), (len(self.client_ids) + 1) * 2)

  def testStatsHuntFilterLocalhost(self):
    statshunt = aff4.FACTORY.Create("aff4:/temp", standard.StatsHunt)
    self.assertTrue(statshunt.ProcessInterface(rdf_client.Interface(
        mac_address="123")))
    self.assertFalse(statshunt.ProcessInterface(rdf_client.Interface(
        ifname="lo")))

  def testHuntTermination(self):
    """This tests that hunts with a client limit terminate correctly."""
    with test_lib.FakeTime(1000, increment=1e-6):
      with hunts.GRRHunt.StartHunt(
          hunt_name="GenericHunt",
          flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="GetFile"),
          flow_args=transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
              path="/tmp/evil.txt",
              pathtype=rdf_paths.PathSpec.PathType.OS)),
          client_rule_set=rdf_foreman.ForemanClientRuleSet(rules=[
              rdf_foreman.ForemanClientRule(
                  rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
                  regex=rdf_foreman.ForemanRegexClientRule(
                      attribute_name="GRR client",
                      attribute_regex="GRR"))
          ]),
          client_limit=5,
          client_rate=0,
          expiry_time=rdfvalue.Duration("1000s"),
          token=self.token) as hunt:
        hunt.Run()

      # Pretend to be the foreman now and dish out hunting jobs to all the
      # clients (Note we have 10 clients here).
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock,
                              self.client_ids,
                              check_flow_errors=False,
                              token=self.token)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id,
                                   age=aff4.ALL_TIMES,
                                   token=self.token)

      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 5)
      self.assertEqual(finished, 5)
      self.assertEqual(errors, 2)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id,
                                   age=aff4.ALL_TIMES,
                                   token=self.token)

      # Hunts are automatically paused when they reach the client limit.
      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "PAUSED")

  def testHuntExpiration(self):
    """This tests that hunts with a client limit terminate correctly."""
    with test_lib.FakeTime(1000):
      with hunts.GRRHunt.StartHunt(
          hunt_name="GenericHunt",
          flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="GetFile"),
          flow_args=transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
              path="/tmp/evil.txt",
              pathtype=rdf_paths.PathSpec.PathType.OS)),
          client_rule_set=rdf_foreman.ForemanClientRuleSet(rules=[
              rdf_foreman.ForemanClientRule(
                  rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
                  regex=rdf_foreman.ForemanRegexClientRule(
                      attribute_name="GRR client",
                      attribute_regex="GRR"))
          ]),
          client_limit=5,
          expiry_time=rdfvalue.Duration("1000s"),
          token=self.token) as hunt:
        hunt.Run()

      # Pretend to be the foreman now and dish out hunting jobs to all the
      # clients (Note we have 10 clients here).
      foreman = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=self.token)
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id,
                                   age=aff4.ALL_TIMES,
                                   token=self.token)

      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "STARTED")

      # Now advance the time such that the hunt expires.
      time.time = lambda: 5000

      # Run the hunt.
      client_mock = test_lib.SampleHuntMock()
      test_lib.TestHuntHelper(client_mock,
                              self.client_ids,
                              check_flow_errors=False,
                              token=self.token)

      # No client should be processed since the hunt is expired.
      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 0)
      self.assertEqual(finished, 0)
      self.assertEqual(errors, 0)

      hunt_obj = aff4.FACTORY.Open(hunt.session_id,
                                   age=aff4.ALL_TIMES,
                                   token=self.token)

      # Hunts are automatically stopped when they expire.
      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "COMPLETED")

  def testHuntModificationWorksCorrectly(self):
    """This tests running the hunt on some clients."""
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.OS),),
        client_rule_set=rdf_foreman.ForemanClientRuleSet(rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
                regex=rdf_foreman.ForemanRegexClientRule(
                    attribute_name="GRR client",
                    attribute_regex="GRR"))
        ]),
        client_limit=1,
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()

    # Forget about hunt object, we'll use AFF4 for everything.
    hunt_session_id = hunt.session_id
    hunt = None

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # client..
    with aff4.FACTORY.Open("aff4:/foreman",
                           mode="rw",
                           token=self.token) as foreman:
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

    # Run the hunt.
    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    # Re-open the hunt to get fresh data.
    hunt_obj = aff4.FACTORY.Open(hunt_session_id,
                                 age=aff4.ALL_TIMES,
                                 ignore_cache=True,
                                 token=self.token)

    # There should be only one client, due to the limit
    started, _, _ = hunt_obj.GetClientsCounts()
    self.assertEqual(started, 1)

    # Check the hunt is paused.
    self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "PAUSED")

    with aff4.FACTORY.Open(hunt_session_id,
                           mode="rw",
                           token=self.token) as hunt_obj:
      runner = hunt_obj.GetRunner()
      runner.args.client_limit = 10
      runner.Start()

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients.
    with aff4.FACTORY.Open("aff4:/foreman",
                           mode="rw",
                           token=self.token) as foreman:
      for client_id in self.client_ids:
        foreman.AssignTasksToClient(client_id)

    test_lib.TestHuntHelper(client_mock, self.client_ids, False, self.token)

    hunt_obj = aff4.FACTORY.Open(hunt_session_id,
                                 age=aff4.ALL_TIMES,
                                 token=self.token)
    # There should be only one client, due to the limit
    started, _, _ = hunt_obj.GetClientsCounts()
    self.assertEqual(started, 10)

  def testResourceUsageStats(self):
    client_ids = self.SetupClients(10)

    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.OS,)),
        client_rule_set=rdf_foreman.ForemanClientRuleSet(rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
                regex=rdf_foreman.ForemanRegexClientRule(
                    attribute_name="GRR client",
                    attribute_regex="GRR"))
        ]),
        output_plugins=[],
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()

    with aff4.FACTORY.Open("aff4:/foreman",
                           mode="rw",
                           token=self.token) as foreman:
      for client_id in client_ids:
        foreman.AssignTasksToClient(client_id)

    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt = aff4.FACTORY.Open(hunt.urn,
                             aff4_type=standard.GenericHunt,
                             token=self.token)

    # This is called once for each state method. Each flow above runs the
    # Start and the StoreResults methods.
    usage_stats = hunt.state.context.usage_stats
    self.assertEqual(usage_stats.user_cpu_stats.num, 10)
    self.assertTrue(math.fabs(usage_stats.user_cpu_stats.mean - 5.5) < 1e-7)
    self.assertTrue(
        math.fabs(usage_stats.user_cpu_stats.std - 2.8722813) < 1e-7)

    self.assertEqual(usage_stats.system_cpu_stats.num, 10)
    self.assertTrue(math.fabs(usage_stats.system_cpu_stats.mean - 11) < 1e-7)
    self.assertTrue(
        math.fabs(usage_stats.system_cpu_stats.std - 5.7445626) < 1e-7)

    self.assertEqual(usage_stats.network_bytes_sent_stats.num, 10)
    self.assertTrue(
        math.fabs(usage_stats.network_bytes_sent_stats.mean - 16.5) < 1e-7)
    self.assertTrue(
        math.fabs(usage_stats.network_bytes_sent_stats.std - 8.61684396) < 1e-7)

    # NOTE: Not checking histograms here. RunningStatsTest tests that mean,
    # standard deviation and histograms are calculated correctly. Therefore
    # if mean/stdev values are correct histograms should be ok as well.

    self.assertEqual(len(usage_stats.worst_performers), 10)

    prev = usage_stats.worst_performers[0]
    for p in usage_stats.worst_performers[1:]:
      self.assertTrue(
          prev.cpu_usage.user_cpu_time + prev.cpu_usage.system_cpu_time >
          p.cpu_usage.user_cpu_time + p.cpu_usage.system_cpu_time)
      prev = p

  def testHuntCollectionLogging(self):
    """This tests running the hunt on some clients."""
    with hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="DummyLogFlow"),
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()
      hunt.Log("Log from the hunt itself")

    hunt_urn = hunt.urn

    self.AssignTasksToClients()
    self.RunHunt()

    # Check logs were written to the hunt collection
    with aff4.FACTORY.Open(
        hunt_urn.Add("Logs"),
        token=self.token,
        age=aff4.ALL_TIMES) as hunt_logs:

      # Can't use len with PackedVersionCollection
      count = 0
      for log in hunt_logs:
        if log.client_id:
          self.assertTrue(log.client_id in self.client_ids)
          self.assertTrue(
              log.log_message in ["First", "Second", "Third", "Fourth", "Uno",
                                  "Dos", "Tres", "Cuatro"])
          self.assertTrue(
              log.flow_name in ["DummyLogFlow", "DummyLogFlowChild"])
          self.assertTrue(str(hunt_urn) in str(log.urn))
        else:
          self.assertEqual(log.log_message, "Log from the hunt itself")
          self.assertEqual(log.flow_name, "GenericHunt")
          self.assertEqual(log.urn, hunt_urn)

        count += 1
      # 4 logs for each flow, 2 flow run.  One hunt-level log.
      self.assertEqual(count, 8 * len(self.client_ids) + 1)

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
        flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="UpdateClient"),
        flow_args=administrative.UpdateClientArgs(),
        client_rule_set=rdf_foreman.ForemanClientRuleSet(rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
                regex=rdf_foreman.ForemanRegexClientRule(
                    attribute_name="GRR client",
                    attribute_regex="GRR"))
        ]),
        client_rate=0,
        token=admin_token) as hunt:
      hunt.Run()

    self.CreateUser("nonadmin")
    nonadmin_token = access_control.ACLToken(username="nonadmin",
                                             reason="testing")
    self.AssignTasksToClients()

    client_mock = test_lib.SampleHuntMock()
    test_lib.TestHuntHelper(client_mock, self.client_ids, False, nonadmin_token)

    errors = list(hunt.GetClientsErrors())
    # Make sure there are errors...
    self.assertTrue(errors)
    # but they are not UnauthorizedAccess.
    for e in errors:
      self.assertTrue("UnauthorizedAccess" not in e.backtrace)

  def _CreateHunt(self, token):
    return hunts.GRRHunt.StartHunt(
        hunt_name="GenericHunt",
        flow_runner_args=flow_runner.FlowRunnerArgs(flow_name="GetFile"),
        flow_args=transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
            path="/tmp/evil.txt",
            pathtype=rdf_paths.PathSpec.PathType.OS)),
        client_rule_set=rdf_foreman.ForemanClientRuleSet(rules=[
            rdf_foreman.ForemanClientRule(
                rule_type=rdf_foreman.ForemanClientRule.Type.REGEX,
                regex=rdf_foreman.ForemanRegexClientRule(
                    attribute_name="GRR client",
                    attribute_regex="GRR"))
        ]),
        client_rate=0,
        token=token)

  def _CheckHuntIsDeleted(self, hunt_urn, token=None):
    with self.assertRaises(aff4.InstantiationError):
      aff4.FACTORY.Open(hunt_urn,
                        aff4_type=implementation.GRRHunt,
                        token=token or self.token)

  def testDeleteHuntFlow(self):
    # We'll need two users for this test.
    self.CreateUser("user1")
    token1 = access_control.ACLToken(username="user1", reason="testing")
    self.CreateUser("user2")
    token2 = access_control.ACLToken(username="user2", reason="testing")

    manager = user_managers.FullAccessControlManager()
    with utils.Stubber(data_store.DB, "security_manager", manager):

      # Let user1 create a hunt and delete it, this should work.
      hunt = self._CreateHunt(token1.SetUID())
      aff4.FACTORY.Open(hunt.urn,
                        aff4_type=implementation.GRRHunt,
                        token=token1)

      flow.GRRFlow.StartFlow(flow_name="DeleteHuntFlow",
                             token=token1,
                             hunt_urn=hunt.urn)
      self._CheckHuntIsDeleted(hunt.urn)

      # Let user1 create a hunt and user2 delete it, this should fail.
      hunt = self._CreateHunt(token1.SetUID())
      aff4.FACTORY.Open(hunt.urn,
                        aff4_type=implementation.GRRHunt,
                        token=token1)

      with self.assertRaises(access_control.UnauthorizedAccess):
        flow.GRRFlow.StartFlow(flow_name="DeleteHuntFlow",
                               token=token2,
                               hunt_urn=hunt.urn)
      # Hunt is still there.
      aff4.FACTORY.Open(hunt.urn,
                        aff4_type=implementation.GRRHunt,
                        token=token1)

      # If user2 gets an approval, deletion is ok though.
      self.GrantHuntApproval(hunt.urn, token=token2)
      flow.GRRFlow.StartFlow(flow_name="DeleteHuntFlow",
                             token=token2,
                             hunt_urn=hunt.urn)

      self._CheckHuntIsDeleted(hunt.urn)

      # Let user1 create a hunt and run it. We are not allowed to delete
      # running hunts.
      hunt = self._CreateHunt(token1.SetUID())
      hunt.Run()
      hunt.Flush()

      aff4.FACTORY.Open(hunt.urn,
                        aff4_type=implementation.GRRHunt,
                        token=token1)

      with self.assertRaises(RuntimeError):
        flow.GRRFlow.StartFlow(flow_name="DeleteHuntFlow",
                               token=token1,
                               hunt_urn=hunt.urn)

      # The same is true if the hunt was scheduled on at least one client.
      hunt = self._CreateHunt(token1.SetUID())
      hunt.Set(hunt.Schema.CLIENT_COUNT(1))
      hunt.Flush()

      aff4.FACTORY.Open(hunt.urn,
                        aff4_type=implementation.GRRHunt,
                        token=token1)

      with self.assertRaises(RuntimeError):
        flow.GRRFlow.StartFlow(flow_name="DeleteHuntFlow",
                               token=token1,
                               hunt_urn=hunt.urn)


class VerifyHuntOutputPluginsCronFlowTest(test_lib.FlowTestsBaseclass,
                                          StandardHuntTestMixin):
  """Tests VerifyHuntOutputPluginsCronFlow."""

  def setUp(self):
    super(VerifyHuntOutputPluginsCronFlowTest, self).setUp()
    self.client_ids = self.SetupClients(1)
    VerifiableDummyHuntOutputPluginVerfier.num_calls = 0

  def GetVerificationsStats(self):
    fields = stats.STATS.GetMetricFields("hunt_output_plugin_verifications")

    result = {}
    for field_value in fields:
      result[field_value[0]] = stats.STATS.GetMetricValue(
          "hunt_output_plugin_verifications",
          fields=field_value)

    return sum(result.values()), result

  def testDoesNothingWithNonGenericHunts(self):
    hunts.GRRHunt.StartHunt(hunt_name="SampleHunt", token=self.token)

    prev_count, _ = self.GetVerificationsStats()
    flow.GRRFlow.StartFlow(flow_name="VerifyHuntOutputPluginsCronFlow",
                           token=self.token)
    count, _ = self.GetVerificationsStats()

    self.assertEqual(count - prev_count, 0)

  def testDoesNothinngWithGenericHuntWithNoPlugins(self):
    self.StartHunt()
    self.AssignTasksToClients()
    self.RunHunt()

    prev_count, _ = self.GetVerificationsStats()
    flow.GRRFlow.StartFlow(flow_name="VerifyHuntOutputPluginsCronFlow",
                           token=self.token)
    count, _ = self.GetVerificationsStats()

    self.assertEqual(count - prev_count, 0)

  def testReturnsNAStatusForGenericHuntWithUnverifiableOutputPlugins(self):
    self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
        plugin_name=DummyHuntOutputPlugin.__name__)])
    self.AssignTasksToClients()
    self.RunHunt()

    _, prev_results = self.GetVerificationsStats()
    flow.GRRFlow.StartFlow(flow_name="VerifyHuntOutputPluginsCronFlow",
                           token=self.token)
    _, results = self.GetVerificationsStats()

    self.assertEqual(results["N_A"] - prev_results.get("N_A", 0), 1)

  def testWritesStatusToHuntResultsMetadata(self):
    hunt_urn = self.StartHunt(
        output_plugins=[output_plugin.OutputPluginDescriptor(
            plugin_name=DummyHuntOutputPlugin.__name__)])
    self.AssignTasksToClients()
    self.RunHunt()

    flow.GRRFlow.StartFlow(flow_name="VerifyHuntOutputPluginsCronFlow",
                           token=self.token)

    results_metadata = aff4.FACTORY.Open(
        hunt_urn.Add("ResultsMetadata"),
        token=self.token)
    verification_results_list = results_metadata.Get(
        results_metadata.Schema.OUTPUT_PLUGINS_VERIFICATION_RESULTS)
    self.assertEqual(len(verification_results_list.results), 1)
    self.assertEqual(verification_results_list.results[0].status, "N_A")

  def testRunsCorrespondingVerifierIfThereIsOne(self):
    self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
        plugin_name=VerifiableDummyHuntOutputPlugin.__name__)])
    self.AssignTasksToClients()
    self.RunHunt()

    _, prev_results = self.GetVerificationsStats()
    flow.GRRFlow.StartFlow(flow_name="VerifyHuntOutputPluginsCronFlow",
                           token=self.token)
    _, results = self.GetVerificationsStats()

    self.assertEqual(results["SUCCESS"] - prev_results.get("SUCCESS", 0), 1)

  def testRaisesIfVerifierRaises(self):
    self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
        plugin_name=DummyHuntOutputPluginWithRaisingVerifier.__name__)])
    self.AssignTasksToClients()
    self.RunHunt()

    prev_count, _ = self.GetVerificationsStats()
    self.assertRaises(standard.HuntVerificationError,
                      flow.GRRFlow.StartFlow,
                      flow_name="VerifyHuntOutputPluginsCronFlow",
                      token=self.token)
    count, _ = self.GetVerificationsStats()
    self.assertEqual(count - prev_count, 0)

  def testUpdatesStatsCounterOnException(self):
    self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
        plugin_name=DummyHuntOutputPluginWithRaisingVerifier.__name__)])
    self.AssignTasksToClients()
    self.RunHunt()

    prev_count = stats.STATS.GetMetricValue(
        "hunt_output_plugin_verification_errors")
    try:
      flow.GRRFlow.StartFlow(flow_name="VerifyHuntOutputPluginsCronFlow",
                             token=self.token)
    except standard.HuntVerificationError:
      pass
    count = stats.STATS.GetMetricValue("hunt_output_plugin_verification_errors")
    self.assertEqual(count - prev_count, 1)

  def testChecksAllHuntsEvenIfOneRaises(self):
    self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
        plugin_name=DummyHuntOutputPluginWithRaisingVerifier.__name__)])
    self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
        plugin_name=VerifiableDummyHuntOutputPlugin.__name__)])
    self.AssignTasksToClients()
    self.RunHunt()

    _, prev_results = self.GetVerificationsStats()
    self.assertRaises(standard.HuntVerificationError,
                      flow.GRRFlow.StartFlow,
                      flow_name="VerifyHuntOutputPluginsCronFlow",
                      token=self.token)
    _, results = self.GetVerificationsStats()
    self.assertEqual(results["SUCCESS"] - prev_results.get("SUCCESS", 0), 1)

  def testDoesNotCheckHuntsOutsideOfCheckRange(self):
    now = rdfvalue.RDFDatetime().Now()
    with test_lib.FakeTime(now - rdfvalue.Duration("61m"), increment=1e-6):
      self.StartHunt(output_plugins=[output_plugin.OutputPluginDescriptor(
          plugin_name=VerifiableDummyHuntOutputPlugin.__name__)])
      self.AssignTasksToClients()
      self.RunHunt()

    prev_count, _ = self.GetVerificationsStats()
    flow.GRRFlow.StartFlow(flow_name="VerifyHuntOutputPluginsCronFlow",
                           check_range="60m",
                           token=self.token)
    count, _ = self.GetVerificationsStats()
    self.assertEqual(count - prev_count, 0)


def main(argv):
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
