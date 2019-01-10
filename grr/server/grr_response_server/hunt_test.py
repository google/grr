#!/usr/bin/env python
"""Tests for the hunt."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import glob
import os
import sys

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import compatibility
from grr_response_core.stats import stats_collector_instance
from grr_response_server import data_store
from grr_response_server import foreman
from grr_response_server import foreman_rules
from grr_response_server import hunt
from grr_response_server import output_plugin
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import processes
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import test_lib


class HuntTest(db_test_lib.RelationalDBEnabledMixin,
               notification_test_lib.NotificationTestMixin,
               test_lib.GRRBaseTest):
  """Tests for the relational hunts implementation."""

  def GetFileHuntArgs(self):
    return rdf_hunt_objects.HuntArguments.Standard(
        flow_name=compatibility.GetName(transfer.GetFile),
        flow_args=transfer.GetFileArgs(
            pathspec=rdf_paths.PathSpec(
                path="/tmp/evil.txt",
                pathtype=rdf_paths.PathSpec.PathType.OS,
            )))

  def _CreateHunt(self, **kwargs):
    hunt_obj = rdf_hunt_objects.Hunt(creator=self.token.username, **kwargs)
    data_store.REL_DB.WriteHuntObject(hunt_obj)
    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)

    return hunt_obj.hunt_id

  def _RunHunt(self, client_ids, client_mock=None, iteration_limit=None):
    foreman_obj = foreman.GetForeman()
    for client_id in client_ids:
      foreman_obj.AssignTasksToClient(client_id.Basename())

    if client_mock is None:
      client_mock = hunt_test_lib.SampleHuntMock()
    return hunt_test_lib.TestHuntHelper(
        client_mock, client_ids, False, iteration_limit=iteration_limit)

  def _CreateAndRunHunt(self,
                        num_clients=5,
                        client_mock=None,
                        iteration_limit=None,
                        **kwargs):
    client_ids = self.SetupClients(num_clients)

    hunt_id = self._CreateHunt(**kwargs)
    self._RunHunt(
        client_ids, client_mock=client_mock, iteration_limit=iteration_limit)

    return hunt_id, client_ids

  def setUp(self):
    super(HuntTest, self).setUp()

    # Making sure we don't use a system username here.
    self.token.username = "hunt_test"
    acl_test_lib.CreateUser(self.token.username)

  def testForemanRulesAreCorrectlyPropagatedWhenHuntStarts(self):
    client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
        foreman_rules.ForemanClientRule(
            rule_type=foreman_rules.ForemanClientRule.Type.REGEX,
            regex=foreman_rules.ForemanRegexClientRule(
                field="CLIENT_NAME", attribute_regex="HUNT")),
        foreman_rules.ForemanClientRule(
            rule_type=foreman_rules.ForemanClientRule.Type.INTEGER,
            integer=foreman_rules.ForemanIntegerClientRule(
                field="CLIENT_CLOCK",
                operator=foreman_rules.ForemanIntegerClientRule.Operator
                .GREATER_THAN,
                value=1336650631137737))
    ])

    self.assertEmpty(data_store.REL_DB.ReadAllForemanRules())

    hunt_obj = rdf_hunt_objects.Hunt(client_rule_set=client_rule_set)
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)

    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertLen(rules, 1)
    rule = rules[0]
    self.assertEqual(rule.client_rule_set, client_rule_set)
    self.assertEqual(rule.hunt_id, hunt_obj.hunt_id)
    self.assertEqual(rule.expiration_time, hunt_obj.expiry_time)

    # Running a second time should not change the rules any more.
    with self.assertRaises(hunt.OnlyPausedHuntCanBeStartedError):
      hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)
    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertEqual(len(rules), 1)

  def testForemanRulesAreCorrectlyRemovedWhenHuntIsStopped(self):
    client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
        foreman_rules.ForemanClientRule(
            rule_type=foreman_rules.ForemanClientRule.Type.REGEX,
            regex=foreman_rules.ForemanRegexClientRule(
                field="CLIENT_NAME", attribute_regex="HUNT")),
        foreman_rules.ForemanClientRule(
            rule_type=foreman_rules.ForemanClientRule.Type.INTEGER,
            integer=foreman_rules.ForemanIntegerClientRule(
                field="CLIENT_CLOCK",
                operator=foreman_rules.ForemanIntegerClientRule.Operator
                .GREATER_THAN,
                value=1336650631137737))
    ])

    hunt_obj = rdf_hunt_objects.Hunt(client_rule_set=client_rule_set)
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)
    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertLen(rules, 1)

    hunt_obj = hunt.StopHunt(hunt_obj.hunt_id)
    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertEqual(len(rules), 0)

  def testHuntWithInvalidForemanRulesDoesNotStart(self):
    client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
        foreman_rules.ForemanClientRule(
            rule_type=foreman_rules.ForemanClientRule.Type.REGEX,
            regex=foreman_rules.ForemanRegexClientRule(
                field="UNSET", attribute_regex="HUNT"))
    ])

    hunt_obj = rdf_hunt_objects.Hunt(client_rule_set=client_rule_set)
    data_store.REL_DB.WriteHuntObject(hunt_obj)
    with self.assertRaises(ValueError):
      hunt.StartHunt(hunt_obj.hunt_id)

  def testForemanRulesWorkCorrectlyWithStandardHunt(self):
    client_rule_set = foreman_rules.ForemanClientRuleSet(rules=[
        foreman_rules.ForemanClientRule(
            rule_type=foreman_rules.ForemanClientRule.Type.OS,
            os=foreman_rules.ForemanOsClientRule(os_windows=True))
    ])
    hunt_obj = rdf_hunt_objects.Hunt(
        client_rule_set=client_rule_set,
        client_rate=0,
        args=self.GetFileHuntArgs())
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)

    # Check matching client.
    client_id = self.SetupClient(0, system="Windows").Basename()
    foreman_obj = foreman.GetForeman()
    foreman_obj.AssignTasksToClient(client_id)

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
    self.assertLen(flows, 1)

    # Check non-matching client.
    client_id = self.SetupClient(1, system="Linux").Basename()
    foreman_obj.AssignTasksToClient(client_id)

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
    self.assertLen(flows, 0)

  def testForemanRulesWorkCorrectlyWithVariableHunt(self):
    # TODO(user): implement.
    pass

  def testStandardHuntFlowsReportBackToTheHunt(self):
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs())

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.num_clients, 10)
    self.assertEqual(hunt_obj.num_successful_clients, 5)
    self.assertEqual(hunt_obj.num_failed_clients, 5)

  def testHangingClientsAreCorrectlyAccountedFor(self):
    client_ids = self.SetupClients(10)

    hunt_obj = rdf_hunt_objects.Hunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs())
    data_store.REL_DB.WriteHuntObject(hunt_obj)
    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)

    foreman_obj = foreman.GetForeman()
    for client_id in client_ids:
      foreman_obj.AssignTasksToClient(client_id.Basename())

    client_mock = hunt_test_lib.SampleHuntMock()
    hunt_test_lib.TestHuntHelper(client_mock, client_ids[1:9], False)

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_obj.hunt_id)
    self.assertEqual(hunt_obj.num_clients, 10)
    self.assertEqual(hunt_obj.num_successful_clients, 4)
    self.assertEqual(hunt_obj.num_failed_clients, 4)

  def testPausingAndRestartingDoesNotStartHuntTwiceOnTheSameClient(self):
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs())

    for client_id in client_ids:
      flows = data_store.REL_DB.ReadAllFlowObjects(
          client_id=client_id.Basename())
      self.assertLen(flows, 1)

    hunt.PauseHunt(hunt_id)
    hunt.StartHunt(hunt_id)

    self._RunHunt(client_ids)

    for client_id in client_ids:
      flows = data_store.REL_DB.ReadAllFlowObjects(
          client_id=client_id.Basename())
      self.assertLen(flows, 1)

  def testHuntIsPausedOnReachingClientLimit(self):
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        client_limit=5,
        args=self.GetFileHuntArgs())

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.num_clients, 5)
    self.assertEqual(hunt_obj.hunt_state,
                     rdf_hunt_objects.Hunt.HuntState.PAUSED)

  def testHuntClientRateIsAppliedCorrectly(self):
    now = rdfvalue.RDFDatetime.Now()

    _, client_ids = self._CreateAndRunHunt(
        num_clients=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=1,
        args=self.GetFileHuntArgs())

    requests = data_store.REL_DB.ReadFlowProcessingRequests()
    requests.sort(key=lambda r: r.delivery_time)

    for i, (r, client_id) in enumerate(zip(requests, client_ids)):
      self.assertEqual(r.client_id, client_id.Basename())
      time_diff = r.delivery_time - (now + rdfvalue.Duration("1m") * i)
      self.assertLess(time_diff, rdfvalue.Duration("5s"))

  def testResultsAreCorrectlyCounted(self):
    path = os.path.join(self.base_path, "hello*")
    num_files = len(glob.glob(path))
    self.assertGreater(num_files, 1)

    hunt_args = rdf_hunt_objects.HuntArguments.Standard(
        flow_name=compatibility.GetName(file_finder.FileFinder),
        flow_args=rdf_file_finder.FileFinderArgs(
            paths=[path],
            action=rdf_file_finder.FileFinderAction(action_type="STAT"),
        ))
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=action_mocks.FileFinderClientMock(),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=hunt_args)

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.num_clients_with_results, 5)
    self.assertEqual(hunt_obj.num_results, 5 * num_files)

  def testStoppingHuntMarksHuntFlowsForTermination(self):
    hunt_args = rdf_hunt_objects.HuntArguments.Standard(
        flow_name=compatibility.GetName(flow_test_lib.InfiniteFlow))
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=5,
        iteration_limit=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=hunt_args)

    hunt.StopHunt(hunt_id)

    num_iterations = self._RunHunt(client_ids, iteration_limit=100)
    # If we did all of the planned 100 iterations, that's a clear indicator
    # that hunt's flows were not stopped.
    self.assertLess(num_iterations, 100)

    for client_id in client_ids:
      flows = data_store.REL_DB.ReadAllFlowObjects(
          client_id=client_id.Basename())
      self.assertLen(flows, 1)

      flow_obj = flows[0]
      self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.ERROR)
      self.assertEqual(flow_obj.error_message, "Parent hunt stopped.")

      req_resp = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
          client_id.Basename(), flow_obj.flow_id)
      self.assertFalse(req_resp)

  def testResultsAreCorrectlyWrittenAndAreFilterable(self):
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs())

    results = data_store.REL_DB.ReadHuntResults(hunt_id, 0, sys.maxsize)
    self.assertLen(results, 5)
    for r in results:
      self.assertIsInstance(r.payload, rdf_client_fs.StatEntry)
      self.assertEqual(r.payload.pathspec.CollapsePath(), "/tmp/evil.txt")

  def testOutputPluginsAreCorrectlyAppliedAndTheirStatusCanBeRead(self):
    hunt_test_lib.StatefulDummyHuntOutputPlugin.data = []
    hunt_test_lib.DummyHuntOutputPlugin.num_calls = 0
    hunt_test_lib.DummyHuntOutputPlugin.num_responses = 0

    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs(),
        output_plugins=[plugin_descriptor])

    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_calls, 5)
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_responses, 5)

    logs = hunt.GetHuntOutputPluginLogs(hunt_id, 0, sys.maxsize)
    self.assertLen(logs, 5)
    for l in logs:
      self.assertEqual(l.batch_size, 1)
      self.assertEqual(
          l.status,
          output_plugin.OutputPluginBatchProcessingStatus.Status.SUCCESS)
      self.assertEqual(l.plugin_descriptor, plugin_descriptor)

  def testOutputPluginsErrorsAreCorrectlyWrittenAndCanBeRead(self):
    failing_plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin")

    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs(),
        output_plugins=[failing_plugin_descriptor])

    errors = hunt.GetHuntOutputPluginErrors(hunt_id, 0, sys.maxsize)
    self.assertLen(errors, 5)
    for e in errors:
      self.assertEqual(e.batch_size, 1)
      self.assertEqual(
          e.status,
          output_plugin.OutputPluginBatchProcessingStatus.Status.ERROR)
      self.assertEqual(e.plugin_descriptor, failing_plugin_descriptor)
      self.assertEqual(e.summary, "Oh no!")

  def testOutputPluginsMaintainGlobalState(self):
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="StatefulDummyHuntOutputPlugin")

    self.assertListEqual(hunt_test_lib.StatefulDummyHuntOutputPlugin.data, [])

    _ = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs(),
        output_plugins=[plugin_descriptor])

    # Output plugins should have been called 5 times, adding a number
    # to the "data" list on every call and incrementing it each time.
    self.assertListEqual(hunt_test_lib.StatefulDummyHuntOutputPlugin.data,
                         [0, 1, 2, 3, 4])

  def testOutputPluginFlushErrorIsLoggedProperly(self):
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingInFlushDummyHuntOutputPlugin")

    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs(),
        output_plugins=[plugin_descriptor])

    logs = hunt.GetHuntOutputPluginLogs(hunt_id, 0, sys.maxsize)
    self.assertEmpty(logs)

    errors = hunt.GetHuntOutputPluginErrors(hunt_id, 0, sys.maxsize)
    self.assertLen(errors, 5)
    for e in errors:
      self.assertEqual(e.batch_size, 1)
      self.assertEqual(
          e.status,
          output_plugin.OutputPluginBatchProcessingStatus.Status.ERROR)
      self.assertEqual(e.plugin_descriptor, plugin_descriptor)
      self.assertEqual(e.summary, "Flush, oh no!")

  def testFailingOutputPluginDoesNotAffectOtherOutputPlugins(self):
    failing_plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin")
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")

    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs(),
        output_plugins=[failing_plugin_descriptor, plugin_descriptor])

    errors = hunt.GetHuntOutputPluginErrors(hunt_id, 0, sys.maxsize)
    self.assertLen(errors, 5)

    # Check that non-failing output plugin is still correctly processed.
    logs = hunt.GetHuntOutputPluginLogs(hunt_id, 0, sys.maxsize)
    self.assertLen(logs, 5)

  def testUpdatesStatsCounterOnOutputPluginSuccess(self):
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin")

    prev_success_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_results_ran_through_plugin", fields=["DummyHuntOutputPlugin"])
    prev_errors_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_output_plugin_errors", fields=["DummyHuntOutputPlugin"])

    self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs(),
        output_plugins=[plugin_descriptor])

    success_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_results_ran_through_plugin", fields=["DummyHuntOutputPlugin"])
    errors_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_output_plugin_errors", fields=["DummyHuntOutputPlugin"])

    # 1 result for each client makes it 5 results.
    self.assertEqual(success_count - prev_success_count, 5)
    self.assertEqual(errors_count - prev_errors_count, 0)

  def testUpdatesStatsCounterOnOutputPluginFailure(self):
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin")

    prev_success_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_results_ran_through_plugin",
        fields=["FailingDummyHuntOutputPlugin"])
    prev_errors_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_output_plugin_errors", fields=["FailingDummyHuntOutputPlugin"])

    self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs(),
        output_plugins=[plugin_descriptor])

    success_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_results_ran_through_plugin",
        fields=["FailingDummyHuntOutputPlugin"])
    errors_count = stats_collector_instance.Get().GetMetricValue(
        "hunt_output_plugin_errors", fields=["FailingDummyHuntOutputPlugin"])

    # 1 error for each client makes it 5 errors, 0 results.
    self.assertEqual(success_count - prev_success_count, 0)
    self.assertEqual(errors_count - prev_errors_count, 5)

  def _CheckHuntStoppedNotification(self, str_match):
    pending = self.GetUserNotifications(self.token.username)
    self.assertLen(pending, 1)
    self.assertIn(str_match, pending[0].message)

  def testHuntIsStoppedIfCrashNumberOverThreshold(self):
    client_ids = self.SetupClients(4)

    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        crash_limit=3,
        args=self.GetFileHuntArgs())

    client_mock = flow_test_lib.CrashClientMock()
    self._RunHunt(client_ids[:2], client_mock=client_mock)

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.hunt_state,
                     rdf_hunt_objects.Hunt.HuntState.STARTED)

    self._RunHunt(client_ids[2:], client_mock=client_mock)

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.hunt_state,
                     rdf_hunt_objects.Hunt.HuntState.STOPPED)

    self._CheckHuntStoppedNotification("reached the crashes limit")

  def testHuntIsStoppedIfAveragePerClientResultsCountTooHigh(self):
    client_ids = self.SetupClients(5)

    hunt_args = rdf_hunt_objects.HuntArguments.Standard(
        flow_name=compatibility.GetName(processes.ListProcesses))
    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        avg_results_per_client_limit=1,
        args=hunt_args)

    single_process = [rdf_client.Process(pid=1, exe="a.exe")]

    with utils.Stubber(hunt, "MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS", 4):

      def CheckState(hunt_state, num_results):
        hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
        self.assertEqual(hunt_obj.hunt_state, hunt_state)
        self.assertEqual(hunt_obj.num_results, num_results)

      self._RunHunt(
          client_ids[:2],
          client_mock=action_mocks.ListProcessesMock(single_process))

      # Hunt should still be running: we got 1 response from 2 clients. We need
      # at least 3 clients to start calculating the average.
      CheckState(rdf_hunt_objects.Hunt.HuntState.STARTED, 2)

      self._RunHunt([client_ids[2]],
                    client_mock=action_mocks.ListProcessesMock(
                        single_process * 2))

      # Hunt should still be running: we got 1 response for first 2 clients and
      # 2 responses for the third. This is over the limit but we need at least 4
      # clients to start applying thresholds.
      CheckState(rdf_hunt_objects.Hunt.HuntState.STARTED, 4)

      self._RunHunt([client_ids[3]],
                    client_mock=action_mocks.ListProcessesMock([]))

      # Hunt should still be running: we got 1 response for first 2 clients,
      # 2 responses for the third and zero for the 4th. This makes it 1 result
      # per client on average. This is within the limit of 1.
      CheckState(rdf_hunt_objects.Hunt.HuntState.STARTED, 4)

      self._RunHunt(
          client_ids[4:5],
          client_mock=action_mocks.ListProcessesMock(single_process * 2))

      # Hunt should be terminated: 5 clients did run and we got 6 results.
      # That's more than the allowed average of 1.
      # Note that this check also implicitly checks that the 6th client didn't
      # run at all (otherwise total number of results would be 8, not 6).
      CheckState(rdf_hunt_objects.Hunt.HuntState.STOPPED, 6)

      self._CheckHuntStoppedNotification(
          "reached the average results per client")

  def testHuntIsStoppedIfAveragePerClientCpuUsageTooHigh(self):
    client_ids = self.SetupClients(5)

    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        avg_cpu_seconds_per_client_limit=3,
        args=self.GetFileHuntArgs())

    with utils.Stubber(hunt, "MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS", 4):

      def CheckState(hunt_state, user_cpu_time, system_cpu_time):
        hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
        self.assertEqual(hunt_obj.hunt_state, hunt_state)
        self.assertEqual(hunt_obj.client_resources_stats.user_cpu_stats.sum,
                         user_cpu_time)
        self.assertEqual(hunt_obj.client_resources_stats.system_cpu_stats.sum,
                         system_cpu_time)

      self._RunHunt(
          client_ids[:2],
          client_mock=hunt_test_lib.SampleHuntMock(
              user_cpu_time=1, system_cpu_time=2, failrate=-1))

      # Hunt should still be running: we need at least 3 clients to start
      # calculating the average.
      CheckState(rdf_hunt_objects.Hunt.HuntState.STARTED, 2, 4)

      self._RunHunt([client_ids[2]],
                    client_mock=hunt_test_lib.SampleHuntMock(
                        user_cpu_time=2, system_cpu_time=4, failrate=-1))

      # Hunt should still be running: even though the average is higher than the
      # limit, number of clients is not enough.
      CheckState(rdf_hunt_objects.Hunt.HuntState.STARTED, 4, 8)

      self._RunHunt([client_ids[3]],
                    client_mock=hunt_test_lib.SampleHuntMock(
                        user_cpu_time=0, system_cpu_time=0, failrate=-1))

      # Hunt should still be running: we got 4 clients, which is enough to check
      # average per-client CPU usage. But 4 user cpu + 8 system cpu seconds for
      # 4 clients make an average of 3 seconds per client - this is within the
      # limit.
      CheckState(rdf_hunt_objects.Hunt.HuntState.STARTED, 4, 8)

      self._RunHunt([client_ids[4]],
                    client_mock=hunt_test_lib.SampleHuntMock(
                        user_cpu_time=2, system_cpu_time=4, failrate=-1))

      # Hunt should be terminated: the average is exceeded.
      CheckState(rdf_hunt_objects.Hunt.HuntState.STOPPED, 6, 12)

      self._CheckHuntStoppedNotification(
          "reached the average CPU seconds per client")

  def testHuntIsStoppedIfAveragePerClientNetworkUsageTooHigh(self):
    client_ids = self.SetupClients(5)

    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        avg_network_bytes_per_client_limit=1,
        args=self.GetFileHuntArgs())

    with utils.Stubber(hunt, "MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS", 4):

      def CheckState(hunt_state, network_bytes_sent):
        hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
        self.assertEqual(hunt_obj.hunt_state, hunt_state)
        self.assertEqual(
            hunt_obj.client_resources_stats.network_bytes_sent_stats.sum,
            network_bytes_sent)

      self._RunHunt(
          client_ids[:2],
          client_mock=hunt_test_lib.SampleHuntMock(
              network_bytes_sent=1, failrate=-1))

      # Hunt should still be running: we need at least 3 clients to start
      # calculating the average.
      CheckState(rdf_hunt_objects.Hunt.HuntState.STARTED, 2)

      self._RunHunt([client_ids[2]],
                    client_mock=hunt_test_lib.SampleHuntMock(
                        network_bytes_sent=2, failrate=-1))

      # Hunt should still be running: even though the average is higher than the
      # limit, number of clients is not enough.
      CheckState(rdf_hunt_objects.Hunt.HuntState.STARTED, 4)

      self._RunHunt([client_ids[3]],
                    client_mock=hunt_test_lib.SampleHuntMock(
                        network_bytes_sent=0, failrate=-1))

      # Hunt should still be running: we got 4 clients, which is enough to check
      # average per-client network bytes usage, but 4 bytes for 4 clients is
      # within the limit of 1 byte per client on average.
      CheckState(rdf_hunt_objects.Hunt.HuntState.STARTED, 4)

      self._RunHunt([client_ids[4]],
                    client_mock=hunt_test_lib.SampleHuntMock(
                        network_bytes_sent=2, failrate=-1))

      # Hunt should be terminated: the limit is exceeded.
      CheckState(rdf_hunt_objects.Hunt.HuntState.STOPPED, 6)

      self._CheckHuntStoppedNotification(
          "reached the average network bytes per client")

  def testHuntIsStoppedWhenExpirationTimeIsReached(self):
    client_ids = self.SetupClients(5)

    now = rdfvalue.RDFDatetime.Now()
    expiry_time = now + rdfvalue.Duration("1d")
    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        expiry_time=expiry_time,
        args=self.GetFileHuntArgs())

    client_mock = hunt_test_lib.SampleHuntMock(failrate=-1)
    foreman_obj = foreman.GetForeman()
    for client_id in client_ids:
      foreman_obj.AssignTasksToClient(client_id.Basename())

    hunt_test_lib.TestHuntHelper(client_mock, client_ids[:3], False)
    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.hunt_state,
                     rdf_hunt_objects.Hunt.HuntState.STARTED)

    with test_lib.FakeTime(expiry_time - rdfvalue.Duration("1s")):
      hunt_test_lib.TestHuntHelper(client_mock, client_ids[3:4], False)
      hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
      self.assertEqual(hunt_obj.hunt_state,
                       rdf_hunt_objects.Hunt.HuntState.STARTED)

    with test_lib.FakeTime(expiry_time + rdfvalue.Duration("1s")):
      hunt_test_lib.TestHuntHelper(client_mock, client_ids[4:5], False)
      hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
      self.assertEqual(hunt_obj.hunt_state,
                       rdf_hunt_objects.Hunt.HuntState.COMPLETED)

  def testPausingTheHuntChangingParametersAndStartingAgainWorksAsExpected(self):
    client_ids = self.SetupClients(2)

    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        client_limit=1,
        args=self.GetFileHuntArgs())

    self._RunHunt(client_ids[:2])
    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.hunt_state,
                     rdf_hunt_objects.Hunt.HuntState.PAUSED)
    # There should be only one client, due to the limit
    self.assertEqual(hunt_obj.num_clients, 1)

    hunt.UpdateHunt(hunt_id, client_limit=10)
    hunt.StartHunt(hunt_id)

    self._RunHunt(client_ids[:2])
    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.num_clients, 2)

  def testResourceUsageStatsAreReportedCorrectly(self):
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=10,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs())

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    usage_stats = hunt_obj.client_resources_stats

    # Values below are calculated based on SampleHuntMock's behavior.
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

  def testHuntFlowLogsAreCorrectlyWrittenAndCanBeRead(self):
    hunt_args = rdf_hunt_objects.HuntArguments.Standard(
        flow_name=compatibility.GetName(flow_test_lib.DummyLogFlow))
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=10,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=hunt_args)

    hunt_logs = data_store.REL_DB.ReadHuntLogEntries(hunt_id, 0, sys.maxsize)
    # 4 logs for each flow, 2 flow run per client.
    self.assertLen(hunt_logs, 8 * len(client_ids))
    self.assertCountEqual(
        set(log.client_id for log in hunt_logs),
        [c.Basename() for c in client_ids])
    self.assertCountEqual(
        set(log.message for log in hunt_logs),
        ["First", "Second", "Third", "Fourth", "Uno", "Dos", "Tres", "Cuatro"])

    for log in hunt_logs:
      self.assertEqual(log.hunt_id, hunt_id)

  def testCreatorUsernameIsPropagatedToChildrenFlows(self):
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=1,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.GetFileHuntArgs())

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.creator, self.token.username)

    flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id=client_ids[0].Basename())
    self.assertLen(flows, 1)
    self.assertEqual(flows[0].creator, hunt_obj.creator)

  def testPerClientLimitsArePropagatedToChildrenFlows(self):
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=1,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        per_client_cpu_limit=42,
        per_client_network_bytes_limit=43,
        args=self.GetFileHuntArgs())

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.creator, self.token.username)

    flows = data_store.REL_DB.ReadAllFlowObjects(
        client_id=client_ids[0].Basename())
    self.assertLen(flows, 1)
    self.assertEqual(flows[0].cpu_limit, 42)
    self.assertEqual(flows[0].network_bytes_limit, 43)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
