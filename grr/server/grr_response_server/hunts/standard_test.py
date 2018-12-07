#!/usr/bin/env python
"""Tests for the standard hunts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import glob
import logging
import os
import time


from builtins import range  # pylint: disable=redefined-builtin
import mock

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.stats import stats_collector_instance
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import aff4_flows
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import notification as notification_lib
from grr_response_server import queue_manager
from grr_response_server import server_stubs
from grr_response_server.flows.general import administrative
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import processes
from grr_response_server.flows.general import transfer
from grr_response_server.hunts import implementation
from grr_response_server.hunts import process_results
from grr_response_server.hunts import standard
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import test_lib


@flow_base.DualDBFlow
class InfiniteFlowMixin(object):
  """Flow that never ends."""

  def Start(self):
    self.CallClient(server_stubs.GetFileStat, next_state="NextState")

  def NextState(self, responses):
    _ = responses
    self.CallState(next_state="Start")


@db_test_lib.DualDBTest
class StandardHuntTest(notification_test_lib.NotificationTestMixin,
                       flow_test_lib.FlowTestsBaseclass,
                       hunt_test_lib.StandardHuntTestMixin):
  """Tests the Hunt."""

  def setUp(self):
    super(StandardHuntTest, self).setUp()
    # Set up 10 clients.
    self.client_ids = self.SetupClients(10)
    self.CreateUser(self.token.username)

    hunt_test_lib.DummyHuntOutputPlugin.num_calls = 0
    hunt_test_lib.DummyHuntOutputPlugin.num_responses = 0
    hunt_test_lib.StatefulDummyHuntOutputPlugin.data = []
    hunt_test_lib.LongRunningDummyHuntOutputPlugin.num_calls = 0

    self.old_logging_error = logging.error
    logging.error = self.AssertNoCollectionCorruption

  def tearDown(self):
    super(StandardHuntTest, self).tearDown()

    logging.error = self.old_logging_error

  def AssertNoCollectionCorruption(self, message, *args, **kwargs):
    self.assertNotIn("Results collection was changed outside of hunt", message)
    self.old_logging_error(message, *args, **kwargs)

  def testResultCounting(self):
    path = os.path.join(self.base_path, "hello*")
    num_files = len(glob.glob(path))
    self.assertGreater(num_files, 0)

    hunt = implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=file_finder.FileFinder.__name__),
        flow_args=rdf_file_finder.FileFinderArgs(
            paths=[path],
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        ),
        client_rate=0,
        token=self.token)
    hunt.Run()

    client_ids = self.SetupClients(5)
    self.AssignTasksToClients(client_ids=client_ids)
    action_mock = action_mocks.FileFinderClientMock()
    hunt_test_lib.TestHuntHelper(action_mock, client_ids, token=self.token)

    hunt = aff4.FACTORY.Open(hunt.urn, token=self.token)
    self.assertEqual(hunt.context.clients_with_results_count, 5)
    self.assertEqual(hunt.context.results_count, 5 * num_files)

  @db_test_lib.LegacyDataStoreOnly
  def testCreatesSymlinksOnClientsForEveryStartedFlow(self):
    hunt_urn = self.StartHunt()
    self.AssignTasksToClients()
    self.RunHunt()

    for client_id in self.client_ids:
      flows_fd = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
      flows_urns = list(flows_fd.ListChildren())
      self.assertLen(flows_urns, 1)
      self.assertEqual(flows_urns[0].Basename(), hunt_urn.Basename() + ":hunt")

      # Check that the object is a symlink.
      fd = aff4.FACTORY.Open(
          flows_urns[0], follow_symlinks=False, token=self.token)
      self.assertEqual(fd.Get(fd.Schema.TYPE), "AFF4Symlink")

      target = fd.Get(fd.Schema.SYMLINK_TARGET)
      # Check that the symlink points into the hunt's namespace.
      self.assertStartsWith(str(target), str(hunt_urn))

  @db_test_lib.LegacyDataStoreOnly
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

  def testStoppingHuntMarksFlowsForTerminationAndCleansQueues(self):
    with implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name="InfiniteFlow"),
        client_rule_set=self._CreateForemanClientRuleSet(),
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()

    self.AssignTasksToClients()

    # Run long enough for InfiniteFlows to start.
    self.RunHunt(
        iteration_limit=len(self.client_ids) * 2,
        user_cpu_time=0,
        system_cpu_time=0,
        network_bytes_sent=0)
    self.StopHunt(hunt.urn)

    # All flows states should be destroyed by now.
    # If something is wrong with the GenericHunt.Stop implementation,
    # this will run forever.
    self.RunHunt(user_cpu_time=0, system_cpu_time=0, network_bytes_sent=0)

    if data_store.RelationalDBFlowsEnabled():
      for client_id in self.client_ids:
        flows = data_store.REL_DB.ReadAllFlowObjects(client_id.Basename())
        self.assertLen(flows, 1)

        flow_obj = flows[0]
        self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.ERROR)
        self.assertEqual(flow_obj.error_message, "Parent hunt stopped.")

        req_resp = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
            client_id.Basename(), flow_obj.flow_id)
        self.assertFalse(req_resp)
    else:
      for client_id in self.client_ids:
        flows_root = aff4.FACTORY.Open(client_id.Add("flows"), token=self.token)
        flows_list = list(flows_root.ListChildren())
        # Only one flow (issued by the hunt) is expected.
        self.assertLen(flows_list, 1)

        # Check that flow's queues are deleted.
        with queue_manager.QueueManager(token=self.token) as manager:
          req_resp = list(manager.FetchRequestsAndResponses(flows_list[0]))
          self.assertFalse(req_resp)

        flow_obj = aff4.FACTORY.Open(
            flows_list[0], aff4_type=aff4_flows.InfiniteFlow, token=self.token)
        self.assertEqual(
            flow_obj.Get(flow_obj.Schema.PENDING_TERMINATION).reason,
            "Parent hunt stopped.")

  def testGenericHuntWithoutOutputPlugins(self):
    """This tests running the hunt on some clients."""
    hunt_urn = self.StartHunt()
    self.AssignTasksToClients()
    self.RunHunt()
    self.StopHunt(hunt_urn)
    self.ProcessHuntOutputPlugins()

    with aff4.FACTORY.Open(
        hunt_urn, age=aff4.ALL_TIMES, token=self.token) as hunt_obj:

      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 10)
      self.assertEqual(finished, 10)
      self.assertEqual(errors, 5)

      # Results collection is always written, even if there are no output
      # plugins.
      collection = implementation.GRRHunt.ResultCollectionForHID(hunt_urn)

      # We should receive stat entries.
      i = 0
      for i, x in enumerate(collection):
        self.assertEqual(x.payload.__class__, rdf_client_fs.StatEntry)
        self.assertEqual(
            x.payload.AFF4Path(x.source).Split(2)[-1], "fs/os/tmp/evil.txt")

      self.assertEqual(i, 4)

      per_type_collection = implementation.GRRHunt.TypedResultCollectionForHID(
          hunt_urn)

      for i, x in enumerate(per_type_collection):
        self.assertEqual(x.payload.__class__, rdf_client_fs.StatEntry)
        self.assertEqual(
            x.payload.AFF4Path(x.source).Split(2)[-1], "fs/os/tmp/evil.txt")

      self.assertListEqual(
          list(per_type_collection.ListStoredTypes()),
          [rdf_client_fs.StatEntry.__name__])

      self.assertEqual(hunt_obj.context.clients_with_results_count, 5)
      self.assertEqual(hunt_obj.context.results_count, 5)

  def testHuntWithoutForemanRules(self):
    """Check no foreman rules are created if we pass add_foreman_rules=False."""
    hunt_urn = self.StartHunt(add_foreman_rules=False)
    self.assertFalse(self.FindForemanRules(None, token=self.token))

    self.AssignTasksToClients()
    self.RunHunt()
    self.StopHunt(hunt_urn)

    with aff4.FACTORY.Open(
        hunt_urn, age=aff4.ALL_TIMES, token=self.token) as hunt_obj:

      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 0)
      self.assertEqual(finished, 0)
      self.assertEqual(errors, 0)

  def testProcessHunResultsCronFlowDoesNothingWhenThereAreNoResults(self):
    # There's no hunt, nothing. Just assert that cron job completes
    # successfully.
    self.ProcessHuntOutputPlugins()

  def testOutputPluginsProcessOnlyNewResultsOnEveryRun(self):
    hunt_urn = self.StartHunt(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyHuntOutputPlugin")
    ])

    # Process hunt results.
    self.ProcessHuntOutputPlugins()

    # Check that nothing has happened because hunt hasn't reported any
    # results yet.
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_calls, 0)
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_responses, 0)

    # Process first 5 clients
    self.AssignTasksToClients(self.client_ids[:5])

    # Run the hunt.
    self.RunHunt(failrate=-1)

    # Although we call ProcessHuntResultCollectionsCronFlow multiple times, it
    # should only call actual plugin once.
    for _ in range(5):
      self.ProcessHuntOutputPlugins()

    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_calls, 1)
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_responses, 5)

    # Process last 5 clients
    self.AssignTasksToClients(self.client_ids[5:])

    # Run the hunt.
    self.RunHunt(failrate=-1)

    # Although we call ProcessHuntResultCollectionsCronFlow multiple times, it
    # should only call actual plugin once.
    for _ in range(5):
      self.ProcessHuntOutputPlugins()

    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_calls, 2)
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_responses, 10)
    hunt = aff4.FACTORY.Open(hunt_urn, token=self.token)
    self.assertEqual(hunt.context.clients_with_results_count, 10)
    self.assertEqual(hunt.context.results_count, 10)

  def testOutputPluginsProcessingStatusIsWrittenToStatusCollection(self):
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")
    hunt_urn = self.StartHunt(output_plugins=[plugin_descriptor])

    # Run the hunt and process output plugins.
    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)
    self.ProcessHuntOutputPlugins()

    status_collection = implementation.GRRHunt.PluginStatusCollectionForHID(
        hunt_urn)
    errors_collection = implementation.GRRHunt.PluginErrorCollectionForHID(
        hunt_urn)

    self.assertEmpty(errors_collection)
    self.assertLen(status_collection, 1)

    self.assertEqual(status_collection[0].status, "SUCCESS")
    self.assertEqual(status_collection[0].batch_index, 0)
    self.assertEqual(status_collection[0].batch_size, 10)
    self.assertEqual(status_collection[0].plugin_descriptor, plugin_descriptor)

  def testMultipleOutputPluginsProcessingStatusAreWrittenToStatusCollection(
      self):
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
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

    status_collection = implementation.GRRHunt.PluginStatusCollectionForHID(
        hunt_urn)
    errors_collection = implementation.GRRHunt.PluginErrorCollectionForHID(
        hunt_urn)

    self.assertEmpty(errors_collection)
    self.assertLen(status_collection, 2)

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
    failing_plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin")
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")
    hunt_urn = self.StartHunt(
        output_plugins=[failing_plugin_descriptor, plugin_descriptor])

    # Run the hunt and process output plugins.
    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)
    try:
      self.ProcessHuntOutputPlugins()
    except process_results.ResultsProcessingError:
      pass

    status_collection = implementation.GRRHunt.PluginStatusCollectionForHID(
        hunt_urn)
    errors_collection = implementation.GRRHunt.PluginErrorCollectionForHID(
        hunt_urn)

    self.assertLen(errors_collection, 1)
    self.assertLen(status_collection, 2)

    self.assertEqual(errors_collection[0].status, "ERROR")
    self.assertEqual(errors_collection[0].batch_index, 0)
    self.assertEqual(errors_collection[0].batch_size, 10)
    self.assertEqual(errors_collection[0].plugin_descriptor,
                     failing_plugin_descriptor)
    self.assertEqual(errors_collection[0].summary, "Oh no!")

    items = sorted(
        status_collection, key=lambda x: x.plugin_descriptor.plugin_name)
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
    failing_plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingInFlushDummyHuntOutputPlugin")
    hunt_urn = self.StartHunt(output_plugins=[failing_plugin_descriptor])

    # Run the hunt and process output plugins.
    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)
    try:
      self.ProcessHuntOutputPlugins()
    except process_results.ResultsProcessingError:
      pass

    status_collection = implementation.GRRHunt.PluginStatusCollectionForHID(
        hunt_urn)
    errors_collection = implementation.GRRHunt.PluginErrorCollectionForHID(
        hunt_urn)

    self.assertLen(errors_collection, 1)
    self.assertLen(status_collection, 1)

    self.assertEqual(errors_collection[0].status, "ERROR")
    self.assertEqual(errors_collection[0].batch_index, 0)
    self.assertEqual(errors_collection[0].batch_size, 10)
    self.assertEqual(errors_collection[0].plugin_descriptor,
                     failing_plugin_descriptor)
    self.assertEqual(errors_collection[0].summary, "Flush, oh no!")

    items = sorted(
        status_collection, key=lambda x: x.plugin_descriptor.plugin_name)

    self.assertEqual(items[0].status, "ERROR")
    self.assertEqual(items[0].batch_index, 0)
    self.assertEqual(items[0].batch_size, 10)
    self.assertEqual(items[0].plugin_descriptor, failing_plugin_descriptor)
    self.assertEqual(items[0].summary, "Flush, oh no!")

  def testFailingOutputPluginDoesNotAffectOtherOutputPlugins(self):
    self.StartHunt(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="FailingDummyHuntOutputPlugin"),
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyHuntOutputPlugin")
    ])

    # Process hunt results.
    self.ProcessHuntOutputPlugins()

    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_calls, 0)
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_responses, 0)

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)

    # We shouldn't get any more calls after the first call to
    # ProcessHuntResultCollectionsCronFlow.
    self.assertRaises(process_results.ResultsProcessingError,
                      self.ProcessHuntOutputPlugins)
    for _ in range(5):
      self.ProcessHuntOutputPlugins()

    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_calls, 1)
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_responses, 10)

  def testResultsProcessingErrorContainsDetailedFailureData(self):
    failing_plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin")
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")
    hunt_urn = self.StartHunt(
        output_plugins=[failing_plugin_descriptor, plugin_descriptor])

    # Process hunt results.
    self.ProcessHuntOutputPlugins()

    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_calls, 0)
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_responses, 0)

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)

    # We shouldn't get any more calls after the first call to
    # ProcessHuntResultCollectionsCronFlow.
    try:
      self.ProcessHuntOutputPlugins()

      # We shouldn't get here.
      self.fail()
    except process_results.ResultsProcessingError as e:
      self.assertLen(e.exceptions_by_hunt, 1)
      self.assertIn(hunt_urn, e.exceptions_by_hunt)
      self.assertLen(e.exceptions_by_hunt[hunt_urn], 1)
      self.assertIn(failing_plugin_descriptor, e.exceptions_by_hunt[hunt_urn])
      self.assertEqual(
          len(e.exceptions_by_hunt[hunt_urn][failing_plugin_descriptor]), 1)
      self.assertEqual(
          e.exceptions_by_hunt[hunt_urn][failing_plugin_descriptor][0].message,
          "Oh no!")

  @mock.patch.object(
      hunt_test_lib.FailingDummyHuntOutputPlugin,
      "ProcessResponses",
      side_effect=RuntimeError("Oh, no"))
  def testResultsAreNotProcessedAgainAfterPluginFailure(self,
                                                        process_responses_mock):
    failing_plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
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
    failing_plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")
    self.StartHunt(output_plugins=[failing_plugin_descriptor])

    prev_success_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_results_ran_through_plugin", fields=["DummyHuntOutputPlugin"])
    prev_errors_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_output_plugin_errors", fields=["DummyHuntOutputPlugin"])

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)
    self.ProcessHuntOutputPlugins()

    success_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_results_ran_through_plugin", fields=["DummyHuntOutputPlugin"])
    errors_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_output_plugin_errors", fields=["DummyHuntOutputPlugin"])

    # 1 result for each client makes it 10 results.
    self.assertEqual(success_count - prev_success_count, 10)

    self.assertEqual(errors_count - prev_errors_count, 0)

  def testUpdatesStatsCounterOnFailure(self):
    failing_plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin")
    self.StartHunt(output_plugins=[failing_plugin_descriptor])

    prev_success_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_results_ran_through_plugin",
        fields=["FailingDummyHuntOutputPlugin"])
    prev_errors_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_output_plugin_errors", fields=["FailingDummyHuntOutputPlugin"])

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)
    try:
      self.ProcessHuntOutputPlugins()
    except process_results.ResultsProcessingError:
      pass

    success_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_results_ran_through_plugin",
        fields=["FailingDummyHuntOutputPlugin"])
    errors_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_output_plugin_errors", fields=["FailingDummyHuntOutputPlugin"])

    self.assertEqual(success_count - prev_success_count, 0)
    self.assertEqual(errors_count - prev_errors_count, 1)

  def testOutputPluginsMaintainState(self):
    self.StartHunt(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="StatefulDummyHuntOutputPlugin")
    ])

    self.assertListEqual(hunt_test_lib.StatefulDummyHuntOutputPlugin.data, [])

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
    self.assertListEqual(hunt_test_lib.StatefulDummyHuntOutputPlugin.data,
                         [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

  def testMultipleHuntsOutputIsProcessedCorrectly(self):
    self.StartHunt(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyHuntOutputPlugin")
    ])
    self.StartHunt(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="StatefulDummyHuntOutputPlugin")
    ])

    self.AssignTasksToClients()
    self.RunHunt(failrate=-1)
    self.ProcessHuntOutputPlugins()

    # Check that plugins worked correctly
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_calls, 1)
    self.assertListEqual(hunt_test_lib.StatefulDummyHuntOutputPlugin.data, [0])

  def testProcessHuntResultCollectionsCronFlowAbortsIfRunningTooLong(self):
    self.assertEqual(hunt_test_lib.LongRunningDummyHuntOutputPlugin.num_calls,
                     0)

    test = [0]

    def TimeStub():
      test[0] += 1e-6
      return test[0]

    with utils.Stubber(time, "time", TimeStub):
      self.StartHunt(output_plugins=[
          rdf_output_plugin.OutputPluginDescriptor(
              plugin_name="LongRunningDummyHuntOutputPlugin")
      ])
      self.AssignTasksToClients()
      self.RunHunt(failrate=-1)

      # Max run time for the VerifyHuntOutputPluginsCronFlow is 0.6*lifetime so
      # 165s gives 99s max run time. LongRunningDummyHuntOutputPlugin will set
      # the time to 100s on the first run, which will effectively mean that it's
      # running for too long.
      phrccf = process_results.ProcessHuntResultCollectionsCronFlow
      with utils.MultiStubber((phrccf, "lifetime", rdfvalue.Duration("165s")),
                              (phrccf, "BATCH_SIZE", 1)):
        self.ProcessHuntOutputPlugins()

      # In normal conditions, there should be 10 results generated.
      # With batch size of 1 this should result in 10 calls to output plugin.
      # But as we were using TimeStub, the flow should have aborted after 1
      # call.
      self.assertEqual(hunt_test_lib.LongRunningDummyHuntOutputPlugin.num_calls,
                       1)

  def testProcessHuntResultCollectionsCronFlowDoesNotAbortIfRunningInTime(self):
    self.assertEqual(hunt_test_lib.LongRunningDummyHuntOutputPlugin.num_calls,
                     0)

    test = [0]

    def TimeStub():
      test[0] += 1e-6
      return test[0]

    with utils.Stubber(time, "time", TimeStub):
      self.StartHunt(output_plugins=[
          rdf_output_plugin.OutputPluginDescriptor(
              plugin_name="LongRunningDummyHuntOutputPlugin")
      ])
      self.AssignTasksToClients()
      self.RunHunt(failrate=-1)

      # Same as above, 170s lifetime gives 102s max run time which is longer
      # than 100s, the time LongRunningDummyHuntOutputPlugin will set on the
      # first run. This time, the flow will run in time.
      phrccf = process_results.ProcessHuntResultCollectionsCronFlow
      phrccj = process_results.ProcessHuntResultCollectionsCronJob
      with utils.MultiStubber((phrccf, "lifetime", rdfvalue.Duration("170s")),
                              (phrccf, "BATCH_SIZE", 1),
                              (phrccj, "lifetime", rdfvalue.Duration("170s")),
                              (phrccj, "BATCH_SIZE", 1)):
        self.ProcessHuntOutputPlugins()

      # In normal conditions, there should be 10 results generated.
      self.assertEqual(hunt_test_lib.LongRunningDummyHuntOutputPlugin.num_calls,
                       10)

  def testHuntResultsArrivingWhileOldResultsAreProcessedAreHandled(self):
    self.StartHunt(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyHuntOutputPlugin")
    ])

    # Process hunt results.
    self.ProcessHuntOutputPlugins()

    # Check that nothing has happened because hunt hasn't reported any
    # results yet.
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_calls, 0)
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_responses, 0)

    # Generate new results while the plugin is working.
    self.num_processed = 0

    def ProcessResponsesStub(_, state, responses):
      # Add 5 more results the first time we are called.
      del state
      if not self.num_processed:
        self.AssignTasksToClients(self.client_ids[5:])
        self.RunHunt(failrate=-1)
      # Just count the total number processed - we don't care about batch size
      # at this point.
      self.num_processed += len(responses)

    with utils.Stubber(hunt_test_lib.DummyHuntOutputPlugin, "ProcessResponses",
                       ProcessResponsesStub):
      self.AssignTasksToClients(self.client_ids[:5])
      self.RunHunt(failrate=-1)
      self.ProcessHuntOutputPlugins()

    self.assertEqual(10, self.num_processed)
    del self.num_processed

  def _AppendFlowRequest(self, flows, client_id, file_id):
    flows.Append(
        client_ids=["C.1%015d" % client_id],
        runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__),
        args=transfer.GetFileArgs(
            pathspec=rdf_paths.PathSpec(
                path="/tmp/evil%s.txt" % file_id,
                pathtype=rdf_paths.PathSpec.PathType.OS),))

  def RunVariableGenericHunt(self):
    args = standard.VariableGenericHuntArgs()
    self._AppendFlowRequest(args.flows, 1, 1)
    self._AppendFlowRequest(args.flows, 2, 2)
    self._AppendFlowRequest(args.flows, 2, 3)

    with implementation.StartHunt(
        hunt_name=standard.VariableGenericHunt.__name__,
        args=args,
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()
      hunt.ManuallyScheduleClients()

    # Run the hunt.
    client_mock = hunt_test_lib.SampleHuntMock(failrate=100)
    hunt_test_lib.TestHuntHelper(client_mock, self.client_ids, False,
                                 self.token)

    with aff4.FACTORY.Open(
        hunt.session_id, mode="rw", token=self.token) as hunt:
      hunt.Stop()

    return hunt

  def testVariableGenericHunt(self):
    """This tests running the hunt on some clients."""
    hunt = self.RunVariableGenericHunt()

    hunt_obj = aff4.FACTORY.Open(
        hunt.session_id, age=aff4.ALL_TIMES, token=self.token)
    started, finished, errors = hunt_obj.GetClientsCounts()
    self.assertEqual(started, 2)
    # Amazing as it may sound, 3 is actually a correct value as we run 2 flows
    # on a second client.
    self.assertEqual(finished, 3)
    self.assertEqual(errors, 0)

  def testHuntTermination(self):
    """This tests that hunts with a client limit terminate correctly."""
    with test_lib.FakeTime(1000, increment=1e-6):
      with implementation.StartHunt(
          hunt_name=standard.GenericHunt.__name__,
          flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
              flow_name=transfer.GetFile.__name__),
          flow_args=transfer.GetFileArgs(
              pathspec=rdf_paths.PathSpec(
                  path="/tmp/evil.txt",
                  pathtype=rdf_paths.PathSpec.PathType.OS)),
          client_rule_set=self._CreateForemanClientRuleSet(),
          client_limit=5,
          client_rate=0,
          expiry_time=rdfvalue.Duration("1000s"),
          token=self.token) as hunt:
        hunt.Run()

      # Pretend to be the foreman now and dish out hunting jobs to all the
      # clients (Note we have 10 clients here).
      self.AssignTasksToClients()

      # Run the hunt.
      client_mock = hunt_test_lib.SampleHuntMock()
      hunt_test_lib.TestHuntHelper(
          client_mock,
          self.client_ids,
          check_flow_errors=False,
          token=self.token)

      hunt_obj = aff4.FACTORY.Open(
          hunt.session_id, age=aff4.ALL_TIMES, token=self.token)

      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 5)
      self.assertEqual(finished, 5)
      self.assertEqual(errors, 2)

      hunt_obj = aff4.FACTORY.Open(
          hunt.session_id, age=aff4.ALL_TIMES, token=self.token)

      # Hunts are automatically paused when they reach the client limit.
      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "PAUSED")

  def testHuntIsStoppedIfCrashNumberOverThreshold(self):
    with self.CreateHunt(crash_limit=3, token=self.token) as hunt:
      hunt.Run()

    # Run the hunt on 2 clients.
    for client_id in self.client_ids[:2]:
      self.AssignTasksToClients([client_id])
      client_mock = flow_test_lib.CrashClientMock(client_id, token=self.token)
      hunt_test_lib.TestHuntHelper(
          client_mock, [client_id], check_flow_errors=False, token=self.token)

    # Hunt should still be running: 2 crashes are within the threshold.
    hunt_obj = aff4.FACTORY.Open(
        hunt.session_id, age=aff4.ALL_TIMES, token=self.token)
    self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "STARTED")

    # Run the hunt on another client.
    client_id = self.client_ids[2]
    client_mock = flow_test_lib.CrashClientMock(client_id, token=self.token)
    self.AssignTasksToClients([client_id])
    hunt_test_lib.TestHuntHelper(
        client_mock, [client_id], check_flow_errors=False, token=self.token)

    # Hunt should be terminated: 3 crashes are over the threshold.
    hunt_obj = aff4.FACTORY.Open(
        hunt.session_id, age=aff4.ALL_TIMES, token=self.token)
    self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "STOPPED")

  def _CheckHuntStoppedNotification(self, str_match):
    pending = self.GetUserNotifications(self.token.username)
    self.assertLen(pending, 1)
    self.assertIn(str_match, pending[0].message)

  def testHuntIsStoppedIfAveragePerClientResultsCountTooHigh(self):
    with utils.Stubber(implementation.GRRHunt,
                       "MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS", 4):

      flow_args = processes.ListProcessesArgs()
      flow_runner_args = rdf_flow_runner.FlowRunnerArgs(
          flow_name=processes.ListProcesses.__name__)

      hunt_urn = self.StartHunt(
          flow_args=flow_args,
          flow_runner_args=flow_runner_args,
          avg_results_per_client_limit=1,
          token=self.token)

      def RunOnClients(client_ids, num_processes):
        client_mock = action_mocks.ListProcessesMock(
            [rdf_client.Process(pid=1, exe="a.exe")] * num_processes)
        self.AssignTasksToClients(client_ids)
        hunt_test_lib.TestHuntHelper(
            client_mock, client_ids, check_flow_errors=False, token=self.token)

      def CheckState(expected_state, expected_results_count):
        hunt_obj = aff4.FACTORY.Open(hunt_urn, token=self.token)
        self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), expected_state)
        self.assertEqual(hunt_obj.context.results_count, expected_results_count)

      RunOnClients(self.client_ids[:2], 1)
      # Hunt should still be running: we got 1 response from 2 clients. We need
      # at least 3 clients to start calculating the average.
      CheckState("STARTED", 2)

      RunOnClients([self.client_ids[2]], 2)
      # Hunt should still be running: we got 1 response for first 2 clients and
      # 2 responses for the third. This is over the limit but we need at least 4
      # clients to start applying thresholds.
      CheckState("STARTED", 4)

      RunOnClients([self.client_ids[3]], 0)
      # Hunt should still be running: we got 1 response for first 2 clients,
      # 2 responses for the third and zero for the 4th. This makes it 1 result
      # per client on average. This is within the limit of 1.
      CheckState("STARTED", 4)

      RunOnClients(self.client_ids[4:5], 2)
      # Hunt should be terminated: 5 clients did run and we got 6 results.
      # That's more than the allowed average of 1.
      # Note that this check also implicitly checks that the 6th client didn't
      # run at all (otherwise total number of results would be 8, not 6).
      CheckState("STOPPED", 6)

      self._CheckHuntStoppedNotification(
          "reached the average results per client")

  def testHuntIsStoppedIfAveragePerClientCpuUsageTooHigh(self):
    with utils.Stubber(implementation.GRRHunt,
                       "MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS", 4):
      hunt_urn = self.StartHunt(
          avg_cpu_seconds_per_client_limit=3, token=self.token)

      def RunOnClients(client_ids, user_cpu_time, system_cpu_time):
        self.AssignTasksToClients(client_ids)
        self.RunHunt(
            client_ids=client_ids,
            user_cpu_time=user_cpu_time,
            system_cpu_time=system_cpu_time)

      def CheckState(expected_state, expected_user_cpu, expected_system_cpu):
        hunt_obj = aff4.FACTORY.Open(hunt_urn, token=self.token)
        self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), expected_state)
        self.assertEqual(
            hunt_obj.context.client_resources.cpu_usage.user_cpu_time,
            expected_user_cpu)
        self.assertEqual(
            hunt_obj.context.client_resources.cpu_usage.system_cpu_time,
            expected_system_cpu)

      RunOnClients(self.client_ids[:2], 1, 2)
      # Hunt should still be running: we need at least 3 clients to start
      # calculating the average.
      CheckState("STARTED", 2, 4)

      RunOnClients([self.client_ids[2]], 2, 4)
      # Hunt should still be running: even though the average is higher than the
      # limit, number of clients is not enough.
      CheckState("STARTED", 4, 8)

      RunOnClients([self.client_ids[3]], 0, 0)
      # Hunt should still be running: we got 4 clients, which is enough to check
      # average per-client CPU usage. But 4 user cpu + 8 system cpu seconds for
      # 4 clients make an average of 3 seconds per client - this is within the
      # limit.
      CheckState("STARTED", 4, 8)

      RunOnClients([self.client_ids[4]], 2, 4)
      # Hunt should be terminated: the average is exceeded.
      CheckState("STOPPED", 6, 12)

      self._CheckHuntStoppedNotification(
          "reached the average CPU seconds per client")

  def testHuntIsStoppedIfAveragePerClientNetworkUsageTooHigh(self):
    with utils.Stubber(implementation.GRRHunt,
                       "MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS", 4):
      hunt_urn = self.StartHunt(
          avg_network_bytes_per_client_limit=1, token=self.token)

      def RunOnClients(client_ids, network_bytes_sent):
        self.AssignTasksToClients(client_ids)
        self.RunHunt(
            client_ids=client_ids, network_bytes_sent=network_bytes_sent)

      def CheckState(expected_state, expected_network_bytes_sent):
        hunt_obj = aff4.FACTORY.Open(hunt_urn, token=self.token)
        self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), expected_state)
        self.assertEqual(hunt_obj.context.network_bytes_sent,
                         expected_network_bytes_sent)

      RunOnClients(self.client_ids[:2], 1)
      # Hunt should still be running: we need at least 3 clients to start
      # calculating the average.
      CheckState("STARTED", 2)

      RunOnClients([self.client_ids[2]], 2)
      # Hunt should still be running: even though the average is higher than the
      # limit, number of clients is not enough.
      CheckState("STARTED", 4)

      RunOnClients([self.client_ids[3]], 0)
      # Hunt should still be running: we got 4 clients, which is enough to check
      # average per-client network bytes usage, but 4 bytes for 4 clients is
      # within the limit of 1 byte per client on average.
      CheckState("STARTED", 4)

      RunOnClients([self.client_ids[4]], 2)
      # Hunt should be terminated: the limit is exceeded.
      CheckState("STOPPED", 6)

      self._CheckHuntStoppedNotification(
          "reached the average network bytes per client")

  def testHuntExpiration(self):
    """This tests that hunts with a client limit terminate correctly."""
    with test_lib.FakeTime(1000):
      with implementation.StartHunt(
          hunt_name=standard.GenericHunt.__name__,
          flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
              flow_name=transfer.GetFile.__name__),
          flow_args=transfer.GetFileArgs(
              pathspec=rdf_paths.PathSpec(
                  path="/tmp/evil.txt",
                  pathtype=rdf_paths.PathSpec.PathType.OS)),
          client_rule_set=self._CreateForemanClientRuleSet(),
          client_limit=5,
          expiry_time=rdfvalue.Duration("1000s"),
          token=self.token) as hunt:
        hunt.Run()

      # Pretend to be the foreman now and dish out hunting jobs to all the
      # clients (Note we have 10 clients here).
      self.AssignTasksToClients()

      hunt_obj = aff4.FACTORY.Open(
          hunt.session_id, age=aff4.ALL_TIMES, token=self.token)

      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "STARTED")

      # Now advance the time such that the hunt expires.
      time.time = lambda: 5000

      # Run the hunt.
      client_mock = hunt_test_lib.SampleHuntMock()
      hunt_test_lib.TestHuntHelper(
          client_mock,
          self.client_ids,
          check_flow_errors=False,
          token=self.token)

      # No client should be processed since the hunt is expired.
      started, finished, errors = hunt_obj.GetClientsCounts()
      self.assertEqual(started, 0)
      self.assertEqual(finished, 0)
      self.assertEqual(errors, 0)

      hunt_obj = aff4.FACTORY.Open(
          hunt.session_id, age=aff4.ALL_TIMES, token=self.token)

      # Hunts are automatically stopped when they expire.
      self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "COMPLETED")

  def testHuntModificationWorksCorrectly(self):
    """This tests running the hunt on some clients."""
    with implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__),
        flow_args=transfer.GetFileArgs(
            pathspec=rdf_paths.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdf_paths.PathSpec.PathType.OS),),
        client_rule_set=self._CreateForemanClientRuleSet(),
        client_limit=1,
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()

    # Forget about hunt object, we'll use AFF4 for everything.
    hunt_session_id = hunt.session_id
    hunt = None

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # client..
    self.AssignTasksToClients()

    # Run the hunt.
    client_mock = hunt_test_lib.SampleHuntMock()
    hunt_test_lib.TestHuntHelper(client_mock, self.client_ids, False,
                                 self.token)

    # Re-open the hunt to get fresh data.
    hunt_obj = aff4.FACTORY.Open(
        hunt_session_id, age=aff4.ALL_TIMES, token=self.token)

    # There should be only one client, due to the limit
    started, _, _ = hunt_obj.GetClientsCounts()
    self.assertEqual(started, 1)

    # Check the hunt is paused.
    self.assertEqual(hunt_obj.Get(hunt_obj.Schema.STATE), "PAUSED")

    with aff4.FACTORY.Open(
        hunt_session_id, mode="rw", token=self.token) as hunt_obj:
      runner = hunt_obj.GetRunner()
      runner.runner_args.client_limit = 10
      runner.Start()

    # Pretend to be the foreman now and dish out hunting jobs to all the
    # clients.
    self.AssignTasksToClients()
    hunt_test_lib.TestHuntHelper(client_mock, self.client_ids, False,
                                 self.token)

    hunt_obj = aff4.FACTORY.Open(
        hunt_session_id, age=aff4.ALL_TIMES, token=self.token)
    # There should be only one client, due to the limit
    started, _, _ = hunt_obj.GetClientsCounts()
    self.assertEqual(started, 10)

  def testResourceUsageStats(self):
    client_ids = self.SetupClients(10)

    with implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=transfer.GetFile.__name__),
        flow_args=transfer.GetFileArgs(
            pathspec=rdf_paths.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdf_paths.PathSpec.PathType.OS,
            )),
        client_rule_set=self._CreateForemanClientRuleSet(),
        output_plugins=[],
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()

    self.AssignTasksToClients(client_ids=client_ids)

    client_mock = hunt_test_lib.SampleHuntMock()
    hunt_test_lib.TestHuntHelper(client_mock, client_ids, False, self.token)

    hunt = aff4.FACTORY.Open(
        hunt.urn, aff4_type=standard.GenericHunt, token=self.token)

    # This is called once for each state method. Each flow above runs the
    # Start and the StoreResults methods.
    usage_stats = hunt.context.usage_stats
    self.assertEqual(usage_stats.user_cpu_stats.num, 10)
    self.assertAlmostEqual(usage_stats.user_cpu_stats.mean, 5.5)
    self.assertAlmostEqual(usage_stats.user_cpu_stats.std, 2.8722813)

    self.assertEqual(usage_stats.system_cpu_stats.num, 10)
    self.assertAlmostEqual(usage_stats.system_cpu_stats.mean, 11)
    self.assertAlmostEqual(usage_stats.system_cpu_stats.std, 5.7445626)

    self.assertEqual(usage_stats.network_bytes_sent_stats.num, 10)
    self.assertAlmostEqual(usage_stats.network_bytes_sent_stats.mean, 16.5)
    self.assertAlmostEqual(usage_stats.network_bytes_sent_stats.std, 8.61684396)

    # NOTE: Not checking histograms here. RunningStatsTest tests that mean,
    # standard deviation and histograms are calculated correctly. Therefore
    # if mean/stdev values are correct histograms should be ok as well.

    self.assertLen(usage_stats.worst_performers, 10)

    prev = usage_stats.worst_performers[0]
    for p in usage_stats.worst_performers[1:]:
      self.assertGreater(
          prev.cpu_usage.user_cpu_time + prev.cpu_usage.system_cpu_time,
          p.cpu_usage.user_cpu_time + p.cpu_usage.system_cpu_time)
      prev = p

  def testHuntCollectionLogging(self):
    """This tests running the hunt on some clients."""
    with implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=flow_test_lib.DummyLogFlow.__name__),
        client_rate=0,
        token=self.token) as hunt:
      hunt.Run()
      hunt.Log("Log from the hunt itself")

    hunt_urn = hunt.urn

    self.AssignTasksToClients()
    self.RunHunt()

    # Check logs were written to the hunt collection
    hunt_logs = implementation.GRRHunt.LogCollectionForHID(hunt_urn)
    count = 0
    for log in hunt_logs:
      if log.client_id:
        self.assertIn(log.client_id, self.client_ids)
        self.assertIn(log.log_message, [
            "First", "Second", "Third", "Fourth", "Uno", "Dos", "Tres", "Cuatro"
        ])
        self.assertIn(log.flow_name, [
            flow_test_lib.DummyLogFlow.__name__,
            flow_test_lib.DummyLogFlowChild.__name__
        ])
        self.assertIn(str(hunt_urn), str(log.urn))
      else:
        self.assertEqual(log.log_message, "Log from the hunt itself")
        self.assertEqual(log.flow_name, standard.GenericHunt.__name__)
        self.assertEqual(log.urn, hunt_urn)

      count += 1

    # 4 logs for each flow, 2 flow run.  One hunt-level log.
    self.assertEqual(count, 8 * len(self.client_ids) + 1)

  def testCreatorPropagation(self):
    self.CreateAdminUser("adminuser")
    admin_token = access_control.ACLToken(
        username="adminuser", reason="testing")
    # Start a flow that requires admin privileges in the hunt. The
    # parameters are not valid so the flow will error out but it's
    # enough to check if the flow was actually run (i.e., it passed
    # the label test).
    with implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=administrative.UpdateClient.__name__),
        flow_args=administrative.UpdateClientArgs(),
        client_rule_set=self._CreateForemanClientRuleSet(),
        client_rate=0,
        token=admin_token) as hunt:
      hunt.Run()

    self.CreateUser("nonadmin")
    nonadmin_token = access_control.ACLToken(
        username="nonadmin", reason="testing")
    self.AssignTasksToClients()

    client_mock = hunt_test_lib.SampleHuntMock()
    hunt_test_lib.TestHuntHelper(client_mock, self.client_ids, False,
                                 nonadmin_token)

    errors = list(hunt.GetClientsErrors())
    # Make sure there are errors...
    self.assertTrue(errors)
    # but they are not UnauthorizedAccess.
    for e in errors:
      self.assertNotIn("UnauthorizedAccess", e.backtrace)


@flow_base.DualDBFlow
class FlowWithCustomNotifyAboutEndMixin(object):
  """Flow that sends a notification."""

  def Start(self):
    pass

  def NotifyAboutEnd(self):
    notification_lib.Notify(
        self.creator, rdf_objects.UserNotification.Type.TYPE_FLOW_RUN_COMPLETED,
        "FlowWithCustomNotifyAboutEnd completed.",
        rdf_objects.ObjectReference())


@db_test_lib.DualDBTest
class StandardHuntNotificationsTest(notification_test_lib.NotificationTestMixin,
                                    hunt_test_lib.StandardHuntTestMixin,
                                    flow_test_lib.FlowTestsBaseclass):
  """Tests the Hunt."""

  def testNotifyAboutEndDoesNothingWhenFlowsRunInsideHunt(self):
    self.CreateUser(self.token.username)

    # Create a user with a custom name to make sure the name is not in the list
    # of system names and that notifications are going to be delivered.
    user_token = access_control.ACLToken(username="some_user", reason="testing")
    self.CreateUser(user_token.username)

    hunt = implementation.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=rdf_flow_runner.FlowRunnerArgs(
            flow_name=FlowWithCustomNotifyAboutEnd.__name__),  # pylint: disable=undefined-variable
        client_rate=0,
        token=user_token)
    hunt.Run()

    client_ids = self.SetupClients(5)
    self.AssignTasksToClients(client_ids=client_ids)
    hunt_test_lib.TestHuntHelper(None, client_ids, token=self.token)

    notifications = self.GetUserNotifications(user_token.username)
    self.assertEmpty(notifications)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
