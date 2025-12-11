#!/usr/bin/env python
"""Tests for the hunt."""

import glob
import os
import sys
from typing import Optional
from unittest import mock

from absl import app

from google.protobuf import any_pb2
from google.protobuf import message as message_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import foreman
from grr_response_server import foreman_rules
from grr_response_server import hunt
from grr_response_server import mig_foreman_rules
from grr_response_server import output_plugin
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import processes
from grr_response_server.output_plugins import test_plugins
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import mig_hunt_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib


class OPPWithArgs(output_plugin.OutputPluginProto):
  """A dummy hunt output plugin that accepts arguments."""

  name = "OPPWithArgs"
  description = "Dummy hunt output plugin with arguments."
  args_type = jobs_pb2.LogMessage

  args_during_init: list[Optional[jobs_pb2.LogMessage]] = []

  def __init__(
      self,
      source_urn: Optional[rdfvalue.RDFURN] = None,
      args: Optional[jobs_pb2.LogMessage] = None,
  ):
    super().__init__(source_urn=source_urn, args=args)
    OPPWithArgs.args_during_init.append(args)

  def ProcessResults(self, replies: list[flows_pb2.FlowResult]) -> None:
    pass


class OPPInitFails(output_plugin.OutputPluginProto):

  def __init__(
      self,
      source_urn: Optional[rdfvalue.RDFURN] = None,
      args: Optional[message_pb2.Message] = None,
  ):
    super().__init__(source_urn=source_urn, args=args)
    raise RuntimeError("Init failed!")


class _DummyRDFOP(output_plugin.OutputPlugin):
  name = "_DummyRDFOP"
  description = "Dummy RDF Output Plugin."
  processed_values = []

  def ProcessResponses(self, state, values):
    _DummyRDFOP.processed_values.extend(values)


class _DummyProtoOP(output_plugin.OutputPluginProto):
  name = "_DummyProtoOP"
  description = "Dummy Proto Output Plugin."
  processed_values = []

  def ProcessResults(self, replies: list[flows_pb2.FlowResult]) -> None:
    _DummyProtoOP.processed_values.extend(replies)


class HuntTest(
    stats_test_lib.StatsTestMixin,
    notification_test_lib.NotificationTestMixin,
    test_lib.GRRBaseTest,
):
  """Tests for the relational hunts implementation."""

  def ClientFileFinderHuntArgs(self):
    args = rdf_file_finder.FileFinderArgs()
    args.paths = ["/tmp/evil.txt"]
    args.action.action_type = rdf_file_finder.FileFinderAction.Action.DOWNLOAD

    return rdf_hunt_objects.HuntArguments(
        hunt_type=rdf_hunt_objects.HuntArguments.HuntType.STANDARD,
        standard=rdf_hunt_objects.HuntArgumentsStandard(
            flow_name=file_finder.ClientFileFinder.__name__,
            flow_args=rdf_structs.AnyValue.Pack(args),
        ),
    )

  def _CreateHunt(self, **kwargs):
    hunt_obj = rdf_hunt_objects.Hunt(creator=self.test_username, **kwargs)
    hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
    hunt.CreateHunt(hunt_obj)
    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)

    return hunt_obj.hunt_id

  def _RunHunt(self, client_ids, client_mock=None, iteration_limit=None):
    foreman_obj = foreman.Foreman()
    for client_id in client_ids:
      foreman_obj.AssignTasksToClient(client_id)

    if client_mock is None:
      client_mock = hunt_test_lib.SampleHuntMock(failrate=2)
    return hunt_test_lib.TestHuntHelper(
        client_mock, client_ids, iteration_limit=iteration_limit
    )

  def _CreateAndRunHunt(
      self, num_clients=5, client_mock=None, iteration_limit=None, **kwargs
  ):
    client_ids = self.SetupClients(num_clients)

    hunt_id = self._CreateHunt(**kwargs)
    self._RunHunt(
        client_ids, client_mock=client_mock, iteration_limit=iteration_limit
    )

    return hunt_id, client_ids

  def setUp(self):
    super().setUp()

    # Making sure we don't use a system username here.
    self.test_username = "hunt_test"
    acl_test_lib.CreateUser(self.test_username)

  def testForemanRulesAreCorrectlyPropagatedWhenHuntStarts(self):
    client_rule_set = foreman_rules.ForemanClientRuleSet(
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.REGEX,
                regex=foreman_rules.ForemanRegexClientRule(
                    field="CLIENT_NAME", attribute_regex="HUNT"
                ),
            ),
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.INTEGER,
                integer=foreman_rules.ForemanIntegerClientRule(
                    field="CLIENT_VERSION",
                    operator=foreman_rules.ForemanIntegerClientRule.Operator.GREATER_THAN,
                    value=1337,
                ),
            ),
        ]
    )

    self.assertEmpty(data_store.REL_DB.ReadAllForemanRules())

    hunt_obj = rdf_hunt_objects.Hunt(client_rule_set=client_rule_set)
    hunt_obj.args.hunt_type = hunt_obj.args.HuntType.STANDARD
    hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)

    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertLen(rules, 1)
    rule = rules[0]
    self.assertEqual(
        rule.client_rule_set,
        mig_foreman_rules.ToProtoForemanClientRuleSet(client_rule_set),
    )
    self.assertEqual(rule.hunt_id, hunt_obj.hunt_id)
    self.assertEqual(
        rule.expiration_time,
        (
            hunt_obj.init_start_time + hunt_obj.duration
        ).AsMicrosecondsSinceEpoch(),
    )

    # Running a second time should not change the rules any more.
    with self.assertRaises(hunt.OnlyPausedHuntCanBeStartedError):
      hunt.StartHunt(hunt_obj.hunt_id)
    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertLen(rules, 1)

  def testForemanRulesAreCorrectlyRemovedWhenHuntIsStopped(self):
    client_rule_set = foreman_rules.ForemanClientRuleSet(
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.REGEX,
                regex=foreman_rules.ForemanRegexClientRule(
                    field="CLIENT_NAME", attribute_regex="HUNT"
                ),
            ),
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.INTEGER,
                integer=foreman_rules.ForemanIntegerClientRule(
                    field="CLIENT_VERSION",
                    operator=foreman_rules.ForemanIntegerClientRule.Operator.GREATER_THAN,
                    value=1337,
                ),
            ),
        ]
    )

    hunt_obj = rdf_hunt_objects.Hunt(client_rule_set=client_rule_set)
    hunt_obj.args.hunt_type = hunt_obj.args.HuntType.STANDARD
    hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)
    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertLen(rules, 1)

    hunt.StopHunt(hunt_obj.hunt_id)
    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertEmpty(rules)

  def testStopHuntWithReason(self):
    hunt_obj = rdf_hunt_objects.Hunt(creator=self.test_username)
    hunt_obj.args.hunt_type = hunt_obj.args.HuntType.STANDARD
    hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)

    hunt.StopHunt(
        hunt_obj.hunt_id,
        hunt_state_reason=rdf_hunt_objects.Hunt.HuntStateReason.AVG_NETWORK_EXCEEDED,
        reason_comment="not working",
    )

    hunt_obj2 = data_store.REL_DB.ReadHuntObject(hunt_obj.hunt_id)
    self.assertEqual(hunt_obj2.hunt_state, hunts_pb2.Hunt.HuntState.STOPPED)
    self.assertEqual(
        hunt_obj2.hunt_state_reason,
        hunts_pb2.Hunt.HuntStateReason.AVG_NETWORK_EXCEEDED,
    )
    self.assertEqual(hunt_obj2.hunt_state_comment, "not working")

  def testHuntWithInvalidForemanRulesDoesNotStart(self):
    client_rule_set = foreman_rules.ForemanClientRuleSet(
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.REGEX,
                regex=foreman_rules.ForemanRegexClientRule(
                    field="UNSET", attribute_regex="HUNT"
                ),
            )
        ]
    )

    hunt_obj = rdf_hunt_objects.Hunt(client_rule_set=client_rule_set)
    hunt_obj.args.hunt_type = hunt_obj.args.HuntType.STANDARD
    hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
    data_store.REL_DB.WriteHuntObject(hunt_obj)
    with self.assertRaises(ValueError):
      hunt.StartHunt(hunt_obj.hunt_id)

  def testForemanRulesWorkCorrectlyWithStandardHunt(self):
    client_rule_set = foreman_rules.ForemanClientRuleSet(
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(os_windows=True),
            )
        ]
    )
    hunt_obj = rdf_hunt_objects.Hunt(
        client_rule_set=client_rule_set,
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
    )
    hunt_obj.args.hunt_type = hunt_obj.args.HuntType.STANDARD
    hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    hunt.StartHunt(hunt_obj.hunt_id)

    # Check matching client.
    client_id = self.SetupClient(0, system="Windows")
    foreman_obj = foreman.Foreman()
    foreman_obj.AssignTasksToClient(client_id)

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
    self.assertLen(flows, 1)

    # Check non-matching client.
    client_id = self.SetupClient(1, system="Linux")
    foreman_obj.AssignTasksToClient(client_id)

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
    self.assertEmpty(flows)

  def testStandardHuntFlowsReportBackToTheHunt(self):
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
    )

    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
    self.assertEqual(hunt_counters.num_clients, 10)
    self.assertEqual(hunt_counters.num_successful_clients, 5)
    self.assertEqual(hunt_counters.num_failed_clients, 5)

  def testHangingClientsAreCorrectlyAccountedFor(self):
    client_ids = self.SetupClients(10)

    hunt_obj = rdf_hunt_objects.Hunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
    )
    hunt_obj = mig_hunt_objects.ToProtoHunt(hunt_obj)
    hunt.CreateHunt(hunt_obj)
    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)

    foreman_obj = foreman.Foreman()
    for client_id in client_ids:
      foreman_obj.AssignTasksToClient(client_id)

    client_mock = hunt_test_lib.SampleHuntMock(failrate=2)
    hunt_test_lib.TestHuntHelper(client_mock, client_ids[1:9])

    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_obj.hunt_id)
    self.assertEqual(hunt_counters.num_clients, 10)
    self.assertEqual(hunt_counters.num_successful_clients, 4)
    self.assertEqual(hunt_counters.num_failed_clients, 4)

  def testPausingAndRestartingDoesNotStartHuntTwiceOnTheSameClient(self):
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
    )

    for client_id in client_ids:
      flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
      self.assertLen(flows, 1)

    hunt.PauseHunt(hunt_id)
    hunt.StartHunt(hunt_id)

    self._RunHunt(client_ids)

    for client_id in client_ids:
      flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
      self.assertLen(flows, 1)

  def testHuntIsPausedOnReachingClientLimit(self):
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        client_limit=5,
        args=self.ClientFileFinderHuntArgs(),
    )

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.hunt_state, hunts_pb2.Hunt.HuntState.PAUSED)
    self.assertEqual(
        hunt_obj.hunt_state_reason,
        hunts_pb2.Hunt.HuntStateReason.TOTAL_CLIENTS_EXCEEDED,
    )

    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
    self.assertEqual(hunt_counters.num_clients, 5)

  def testHuntClientRateIsAppliedCorrectly(self):
    now = rdfvalue.RDFDatetime.Now()

    _, client_ids = self._CreateAndRunHunt(
        num_clients=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=1,
        args=self.ClientFileFinderHuntArgs(),
    )

    requests = data_store.REL_DB.ReadFlowProcessingRequests()
    requests.sort(key=lambda r: r.delivery_time)

    # The first request is scheduled to run immediately and has been processed
    # already.
    self.assertLen(requests, 9)
    for i, (r, client_id) in enumerate(zip(requests, client_ids[1:])):
      self.assertEqual(r.client_id, client_id)
      delivery_time = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
          r.delivery_time
      )
      time_diff = delivery_time - (
          now + rdfvalue.Duration.From(1, rdfvalue.MINUTES) * (i + 1)
      )
      self.assertLess(time_diff, rdfvalue.Duration.From(5, rdfvalue.SECONDS))

  def testResultsAreCorrectlyCounted(self):
    path = os.path.join(self.base_path, "*hello*")
    num_files = len(glob.glob(path))
    self.assertGreater(num_files, 1)

    flow_args = rdf_file_finder.FileFinderArgs()
    flow_args.paths = [path]
    flow_args.action.action_type = rdf_file_finder.FileFinderAction.Action.STAT

    hunt_args = rdf_hunt_objects.HuntArguments(
        hunt_type=rdf_hunt_objects.HuntArguments.HuntType.STANDARD,
        standard=rdf_hunt_objects.HuntArgumentsStandard(
            flow_name=file_finder.FileFinder.__name__,
            flow_args=rdf_structs.AnyValue.Pack(flow_args),
        ),
    )

    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=action_mocks.FileFinderClientMock(),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=hunt_args,
    )

    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
    self.assertEqual(hunt_counters.num_clients_with_results, 5)
    self.assertEqual(hunt_counters.num_results, 5 * num_files)

  def testStoppingHuntMarksHuntFlowsForTermination(self):
    hunt_args = rdf_hunt_objects.HuntArguments(
        hunt_type=rdf_hunt_objects.HuntArguments.HuntType.STANDARD,
        standard=rdf_hunt_objects.HuntArgumentsStandard(
            flow_name=flow_test_lib.InfiniteFlow.__name__
        ),
    )
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=5,
        iteration_limit=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=hunt_args,
    )

    hunt.StopHunt(hunt_id)

    num_iterations = self._RunHunt(client_ids, iteration_limit=100)
    # If we did all of the planned 100 iterations, that's a clear indicator
    # that hunt's flows were not stopped.
    self.assertLess(num_iterations, 100)

    for client_id in client_ids:
      flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_id)
      self.assertLen(flows, 1)

      flow_obj = flows[0]
      self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.ERROR)
      self.assertEqual(flow_obj.error_message, "Parent hunt stopped.")

      req_resp = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
          client_id, flow_obj.flow_id
      )
      self.assertFalse(req_resp)

  def testResultsAreCorrectlyWrittenAndAreFilterable(self):
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=10,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
    )

    results = data_store.REL_DB.ReadHuntResults(hunt_id, 0, sys.maxsize)
    self.assertLen(results, 5)
    for r in results:
      self.assertTrue(r.payload.Is(flows_pb2.FileFinderResult.DESCRIPTOR))
      ff_result = flows_pb2.FileFinderResult()
      r.payload.Unpack(ff_result)
      self.assertEqual(ff_result.stat_entry.pathspec.path, "/tmp/evil.txt")

  def testOutputPluginsAreCorrectlyAppliedAndTheirStatusCanBeRead(self):
    hunt_test_lib.StatefulDummyHuntOutputPlugin.data = []
    hunt_test_lib.DummyHuntOutputPlugin.num_calls = 0
    hunt_test_lib.DummyHuntOutputPlugin.num_responses = 0

    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin"
    )
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
        output_plugins=[plugin_descriptor],
    )

    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_calls, 5)
    self.assertEqual(hunt_test_lib.DummyHuntOutputPlugin.num_responses, 5)

    logs = data_store.REL_DB.ReadHuntOutputPluginLogEntries(
        hunt_id,
        # REL_DB code uses strings for output plugin ids for consistency (as
        # all other DB ids are strings). At the moment plugin_id in the database
        # is simply an index of the plugin in Flow/Hunt.output_plugins list.
        output_plugin_id="0",
        offset=0,
        count=sys.maxsize,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
    )
    self.assertLen(logs, 5)
    self.assertCountEqual([l.client_id for l in logs], client_ids)
    for l in logs:
      self.assertEqual(l.hunt_id, hunt_id)
      self.assertGreater(l.timestamp, 0)
      self.assertEqual(l.message, "Processed 1 replies.")

  def testOutputPluginsErrorsAreCorrectlyWrittenAndCanBeRead(self):
    failing_plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin"
    )

    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
        output_plugins=[failing_plugin_descriptor],
    )

    errors = data_store.REL_DB.ReadHuntOutputPluginLogEntries(
        hunt_id,
        # REL_DB code uses strings for output plugin ids for consistency (as
        # all other DB ids are strings). At the moment plugin_id in the database
        # is simply an index of the plugin in Flow/Hunt.output_plugins list.
        output_plugin_id="0",
        offset=0,
        count=sys.maxsize,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
    )
    self.assertLen(errors, 5)
    self.assertCountEqual([e.client_id for e in errors], client_ids)
    for e in errors:
      self.assertEqual(e.hunt_id, hunt_id)
      self.assertGreater(e.timestamp, 0)
      self.assertEqual(e.message, "Error while processing 1 replies: Oh no!")

  def testOutputPluginsMaintainGlobalState(self):
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="StatefulDummyHuntOutputPlugin"
    )

    self.assertListEqual(hunt_test_lib.StatefulDummyHuntOutputPlugin.data, [])

    _ = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
        output_plugins=[plugin_descriptor],
    )

    # Output plugins should have been called 5 times, adding a number
    # to the "data" list on every call and incrementing it each time.
    self.assertListEqual(
        hunt_test_lib.StatefulDummyHuntOutputPlugin.data, [0, 1, 2, 3, 4]
    )

  def testOutputPluginFlushErrorIsLoggedProperly(self):
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingInFlushDummyHuntOutputPlugin"
    )

    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
        output_plugins=[plugin_descriptor],
    )

    logs = data_store.REL_DB.ReadHuntOutputPluginLogEntries(
        hunt_id,
        output_plugin_id="0",
        offset=0,
        count=sys.maxsize,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
    )
    self.assertEmpty(logs)

    errors = data_store.REL_DB.ReadHuntOutputPluginLogEntries(
        hunt_id,
        output_plugin_id="0",
        offset=0,
        count=sys.maxsize,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
    )
    self.assertLen(errors, 5)
    self.assertCountEqual([e.client_id for e in errors], client_ids)
    for e in errors:
      self.assertEqual(e.hunt_id, hunt_id)
      self.assertGreater(e.timestamp, 0)
      self.assertEqual(
          e.message, "Error while processing 1 replies: Flush, oh no!"
      )

  def testFailingOutputPluginDoesNotAffectOtherOutputPlugins(self):
    failing_plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin"
    )
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin"
    )

    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
        output_plugins=[failing_plugin_descriptor, plugin_descriptor],
    )

    errors = data_store.REL_DB.ReadHuntOutputPluginLogEntries(
        hunt_id,
        output_plugin_id="0",
        offset=0,
        count=sys.maxsize,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
    )
    self.assertLen(errors, 5)

    # Check that non-failing output plugin is still correctly processed.
    logs = data_store.REL_DB.ReadHuntOutputPluginLogEntries(
        hunt_id,
        output_plugin_id="1",
        offset=0,
        count=sys.maxsize,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
    )
    self.assertLen(logs, 5)

  @test_plugins.WithOutputPluginProto(_DummyProtoOP)
  def testHuntFlowWithRDFAndProtoOutputPlugins(self):
    _DummyRDFOP.processed_values = []
    _DummyProtoOP.processed_values = []

    rdf_plugin = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=_DummyRDFOP.__name__
    )
    proto_plugin = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=_DummyProtoOP.__name__
    )

    self._CreateAndRunHunt(
        num_clients=1,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
        output_plugins=[rdf_plugin, proto_plugin],
    )

    self.assertLen(_DummyRDFOP.processed_values, 1)
    self.assertLen(_DummyProtoOP.processed_values, 1)

  def testUpdatesStatsCounterOnOutputPluginSuccess(self):
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="DummyHuntOutputPlugin"
    )

    # 1 result for each client makes it 5 results.
    with self.assertStatsCounterDelta(
        5,
        flow_base.HUNT_RESULTS_RAN_THROUGH_PLUGIN,
        fields=["DummyHuntOutputPlugin"],
    ):
      with self.assertStatsCounterDelta(
          0,
          flow_base.HUNT_OUTPUT_PLUGIN_ERRORS,
          fields=["DummyHuntOutputPlugin"],
      ):
        self._CreateAndRunHunt(
            num_clients=5,
            client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
            client_rule_set=foreman_rules.ForemanClientRuleSet(),
            client_rate=0,
            args=self.ClientFileFinderHuntArgs(),
            output_plugins=[plugin_descriptor],
        )

  def testUpdatesStatsCounterOnOutputPluginFailure(self):
    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyHuntOutputPlugin"
    )

    # 1 error for each client makes it 5 errors, 0 results.
    with self.assertStatsCounterDelta(
        0,
        flow_base.HUNT_RESULTS_RAN_THROUGH_PLUGIN,
        fields=["FailingDummyHuntOutputPlugin"],
    ):
      with self.assertStatsCounterDelta(
          5,
          flow_base.HUNT_OUTPUT_PLUGIN_ERRORS,
          fields=["FailingDummyHuntOutputPlugin"],
      ):
        self._CreateAndRunHunt(
            num_clients=5,
            client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
            client_rule_set=foreman_rules.ForemanClientRuleSet(),
            client_rate=0,
            args=self.ClientFileFinderHuntArgs(),
            output_plugins=[plugin_descriptor],
        )

  def _CheckHuntStoppedNotification(self, str_match):
    pending = self.GetUserNotifications(self.test_username)
    self.assertLen(pending, 1)
    self.assertIn(str_match, pending[0].message)

  def testHuntIsStoppedIfCrashNumberOverThreshold(self):
    client_ids = self.SetupClients(4)

    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        crash_limit=3,
        args=self.ClientFileFinderHuntArgs(),
    )

    client_mock = flow_test_lib.CrashClientMock()
    self._RunHunt(client_ids[:2], client_mock=client_mock)

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.hunt_state, hunts_pb2.Hunt.HuntState.STARTED)

    self._RunHunt(client_ids[2:], client_mock=client_mock)

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.hunt_state, hunts_pb2.Hunt.HuntState.STOPPED)

    self._CheckHuntStoppedNotification("reached the crashes limit")

  def testHuntIsStoppedIfAveragePerClientResultsCountTooHigh(self):
    client_ids = self.SetupClients(5)

    hunt_args = rdf_hunt_objects.HuntArguments(
        hunt_type=rdf_hunt_objects.HuntArguments.HuntType.STANDARD,
        standard=rdf_hunt_objects.HuntArgumentsStandard(
            flow_name=processes.ListProcesses.__name__
        ),
    )
    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        avg_results_per_client_limit=1,
        args=hunt_args,
    )

    single_process = [rdf_client.Process(pid=1, exe="a.exe")]

    with mock.patch.object(hunt, "MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS", 4):

      def CheckState(hunt_state, num_results):
        hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
        self.assertEqual(hunt_obj.hunt_state, hunt_state)
        hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
        self.assertEqual(hunt_counters.num_results, num_results)

      self._RunHunt(
          client_ids[:2],
          client_mock=action_mocks.ListProcessesMock(single_process),
      )

      # Hunt should still be running: we got 1 response from 2 clients. We need
      # at least 3 clients to start calculating the average.
      CheckState(hunts_pb2.Hunt.HuntState.STARTED, 2)

      self._RunHunt(
          [client_ids[2]],
          client_mock=action_mocks.ListProcessesMock(single_process * 2),
      )

      # Hunt should still be running: we got 1 response for first 2 clients and
      # 2 responses for the third. This is over the limit but we need at least 4
      # clients to start applying thresholds.
      CheckState(hunts_pb2.Hunt.HuntState.STARTED, 4)

      self._RunHunt(
          [client_ids[3]], client_mock=action_mocks.ListProcessesMock([])
      )

      # Hunt should still be running: we got 1 response for first 2 clients,
      # 2 responses for the third and zero for the 4th. This makes it 1 result
      # per client on average. This is within the limit of 1.
      CheckState(hunts_pb2.Hunt.HuntState.STARTED, 4)

      self._RunHunt(
          client_ids[4:5],
          client_mock=action_mocks.ListProcessesMock(single_process * 2),
      )

      # Hunt should be terminated: 5 clients did run and we got 6 results.
      # That's more than the allowed average of 1.
      # Note that this check also implicitly checks that the 6th client didn't
      # run at all (otherwise total number of results would be 8, not 6).
      CheckState(hunts_pb2.Hunt.HuntState.STOPPED, 6)

      self._CheckHuntStoppedNotification(
          "reached the average results per client"
      )

  def testHuntIsStoppedIfAveragePerClientCpuUsageTooHigh(self):
    client_ids = self.SetupClients(5)

    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        avg_cpu_seconds_per_client_limit=3,
        args=self.ClientFileFinderHuntArgs(),
    )

    with mock.patch.object(hunt, "MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS", 4):

      def CheckState(hunt_state, user_cpu_time, system_cpu_time):
        hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
        self.assertEqual(hunt_obj.hunt_state, hunt_state)
        hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
        self.assertAlmostEqual(
            hunt_counters.total_cpu_seconds, user_cpu_time + system_cpu_time
        )

      self._RunHunt(
          client_ids[:2],
          client_mock=hunt_test_lib.SampleHuntMock(
              user_cpu_time=1, system_cpu_time=2, failrate=-1
          ),
      )

      # Hunt should still be running: we need at least 3 clients to start
      # calculating the average.
      CheckState(hunts_pb2.Hunt.HuntState.STARTED, 2, 4)

      self._RunHunt(
          [client_ids[2]],
          client_mock=hunt_test_lib.SampleHuntMock(
              user_cpu_time=2, system_cpu_time=4, failrate=-1
          ),
      )

      # Hunt should still be running: even though the average is higher than the
      # limit, number of clients is not enough.
      CheckState(hunts_pb2.Hunt.HuntState.STARTED, 4, 8)

      self._RunHunt(
          [client_ids[3]],
          client_mock=hunt_test_lib.SampleHuntMock(
              user_cpu_time=0, system_cpu_time=0, failrate=-1
          ),
      )

      # Hunt should still be running: we got 4 clients, which is enough to check
      # average per-client CPU usage. But 4 user cpu + 8 system cpu seconds for
      # 4 clients make an average of 3 seconds per client - this is within the
      # limit.
      CheckState(hunts_pb2.Hunt.HuntState.STARTED, 4, 8)

      self._RunHunt(
          [client_ids[4]],
          client_mock=hunt_test_lib.SampleHuntMock(
              user_cpu_time=2, system_cpu_time=4, failrate=-1
          ),
      )

      # TODO: Re-enable the checks after the test is reworked to
      # run with approximate limits (flow not persisted in the DB every time).

      # # Hunt should be terminated: the average is exceeded.
      # CheckState(rdf_hunt_objects.Hunt.HuntState.STOPPED, 6, 12)

      # self._CheckHuntStoppedNotification(
      #     "reached the average CPU seconds per client")

  def testHuntIsStoppedIfAveragePerClientNetworkUsageTooHigh(self):
    client_ids = self.SetupClients(5)

    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        avg_network_bytes_per_client_limit=1,
        args=self.ClientFileFinderHuntArgs(),
    )

    with mock.patch.object(hunt, "MIN_CLIENTS_FOR_AVERAGE_THRESHOLDS", 4):

      def CheckState(hunt_state, network_bytes_sent):
        hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
        self.assertEqual(hunt_obj.hunt_state, hunt_state)
        hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
        self.assertEqual(
            hunt_counters.total_network_bytes_sent, network_bytes_sent
        )

      self._RunHunt(
          client_ids[:2],
          client_mock=hunt_test_lib.SampleHuntMock(
              network_bytes_sent=1, failrate=-1
          ),
      )

      # Hunt should still be running: we need at least 3 clients to start
      # calculating the average.
      CheckState(hunts_pb2.Hunt.HuntState.STARTED, 2)

      self._RunHunt(
          [client_ids[2]],
          client_mock=hunt_test_lib.SampleHuntMock(
              network_bytes_sent=2, failrate=-1
          ),
      )

      # Hunt should still be running: even though the average is higher than the
      # limit, number of clients is not enough.
      CheckState(hunts_pb2.Hunt.HuntState.STARTED, 4)

      self._RunHunt(
          [client_ids[3]],
          client_mock=hunt_test_lib.SampleHuntMock(
              network_bytes_sent=0, failrate=-1
          ),
      )

      # Hunt should still be running: we got 4 clients, which is enough to check
      # average per-client network bytes usage, but 4 bytes for 4 clients is
      # within the limit of 1 byte per client on average.
      CheckState(hunts_pb2.Hunt.HuntState.STARTED, 4)

      self._RunHunt(
          [client_ids[4]],
          client_mock=hunt_test_lib.SampleHuntMock(
              network_bytes_sent=2, failrate=-1
          ),
      )

      # TODO: Re-enable the checks after the test is reworked to
      # run with approximate limits (flow not persisted in the DB every time).

      # # Hunt should be terminated: the limit is exceeded.
      # CheckState(rdf_hunt_objects.Hunt.HuntState.STOPPED, 6)

      # self._CheckHuntStoppedNotification(
      #     "reached the average network bytes per client")

  def testHuntIsStoppedIfTotalNetworkUsageIsTooHigh(self):
    client_ids = self.SetupClients(5)

    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        total_network_bytes_limit=5,
        args=self.ClientFileFinderHuntArgs(),
    )

    def CheckState(hunt_state, network_bytes_sent):
      hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
      self.assertEqual(hunt_obj.hunt_state, hunt_state)
      hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
      self.assertEqual(
          hunt_counters.total_network_bytes_sent, network_bytes_sent
      )

    self._RunHunt(
        client_ids[:2],
        client_mock=hunt_test_lib.SampleHuntMock(network_bytes_sent=2),
    )

    # 4 is lower than the total limit. The hunt should still be running.
    CheckState(hunts_pb2.Hunt.HuntState.STARTED, 4)

    self._RunHunt(
        [client_ids[2]],
        client_mock=hunt_test_lib.SampleHuntMock(network_bytes_sent=1),
    )

    # 5 is equal to the total limit. Total network bytes sent should
    # go over the limit in order for the hunt to be stopped.
    CheckState(hunts_pb2.Hunt.HuntState.STARTED, 5)

    self._RunHunt(
        [client_ids[3]],
        client_mock=hunt_test_lib.SampleHuntMock(network_bytes_sent=1),
    )

    # TODO: Re-enable the checks after the test is reworked to
    # run with approximate limits (flow not persisted in the DB every time).

    # # 6 is greater than the total limit. The hunt should be stopped now.
    # CheckState(hunts_pb2.Hunt.HuntState.STOPPED, 6)

    # self._RunHunt([client_ids[4]],
    #               client_mock=hunt_test_lib.SampleHuntMock(
    #                   network_bytes_sent=2, failrate=-1))

    # self._CheckHuntStoppedNotification(
    #     "reached the total network bytes sent limit")

  def testHuntIsStoppedWhenExpirationTimeIsReached(self):
    client_ids = self.SetupClients(3)

    fake_time = rdfvalue.RDFDatetime.Now() - rdfvalue.Duration.From(
        30, rdfvalue.DAYS
    )

    duration = rdfvalue.Duration.From(1, rdfvalue.DAYS)
    expiry_time = fake_time + duration

    foreman_obj = foreman.Foreman()

    with test_lib.FakeTime(fake_time):
      hunt_id = self._CreateHunt(
          client_rule_set=foreman_rules.ForemanClientRuleSet(),
          client_rate=0,
          duration=duration,
          args=self.ClientFileFinderHuntArgs(),
      )

      foreman_obj.AssignTasksToClient(client_ids[0])

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.hunt_state, hunts_pb2.Hunt.HuntState.STARTED)

    with test_lib.FakeTime(
        expiry_time - rdfvalue.Duration.From(1, rdfvalue.SECONDS)
    ):
      foreman_obj.AssignTasksToClient(client_ids[1])
      hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
      self.assertEqual(hunt_obj.hunt_state, hunts_pb2.Hunt.HuntState.STARTED)
      hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
      self.assertEqual(hunt_counters.num_clients, 2)

    with test_lib.FakeTime(
        expiry_time + rdfvalue.Duration.From(1, rdfvalue.SECONDS)
    ):
      foreman_obj.AssignTasksToClient(client_ids[2])
      hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
      self.assertEqual(
          hunt_obj.hunt_state, rdf_hunt_objects.Hunt.HuntState.COMPLETED
      )
      hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
      self.assertEqual(hunt_counters.num_clients, 2)

  def testPausingTheHuntChangingParametersAndStartingAgainWorksAsExpected(self):
    client_ids = self.SetupClients(2)

    hunt_id = self._CreateHunt(
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        client_limit=1,
        args=self.ClientFileFinderHuntArgs(),
    )

    self._RunHunt(client_ids[:2])
    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.hunt_state, hunts_pb2.Hunt.HuntState.PAUSED)
    # There should be only one client, due to the limit
    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
    self.assertEqual(hunt_counters.num_clients, 1)

    hunt.UpdateHunt(hunt_id, client_limit=10)
    hunt.StartHunt(hunt_id)

    self._RunHunt(client_ids[:2])
    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
    self.assertEqual(hunt_counters.num_clients, 2)

  def testResourceUsageStatsAreReportedCorrectly(self):
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=10,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
    )

    usage_stats = data_store.REL_DB.ReadHuntClientResourcesStats(hunt_id)

    # Values below are calculated based on SampleHuntMock's behavior.
    self.assertEqual(usage_stats.user_cpu_stats.num, 10)
    self.assertAlmostEqual(usage_stats.user_cpu_stats.sum, 55)
    self.assertAlmostEqual(usage_stats.user_cpu_stats.stddev, 2.8722813)

    self.assertEqual(usage_stats.system_cpu_stats.num, 10)
    self.assertAlmostEqual(usage_stats.system_cpu_stats.sum, 110)
    self.assertAlmostEqual(usage_stats.system_cpu_stats.stddev, 5.7445626)

    self.assertEqual(usage_stats.network_bytes_sent_stats.num, 10)
    self.assertAlmostEqual(usage_stats.network_bytes_sent_stats.sum, 165)
    self.assertAlmostEqual(
        usage_stats.network_bytes_sent_stats.stddev, 8.61684396
    )

    # NOTE: Not checking histograms here. RunningStatsTest tests that mean,
    # standard deviation and histograms are calculated correctly. Therefore
    # if mean/stddev values are correct histograms should be ok as well.

    self.assertLen(usage_stats.worst_performers, 10)

    prev = usage_stats.worst_performers[0]
    for p in usage_stats.worst_performers[1:]:
      self.assertGreater(
          prev.cpu_usage.user_cpu_time + prev.cpu_usage.system_cpu_time,
          p.cpu_usage.user_cpu_time + p.cpu_usage.system_cpu_time,
      )
      prev = p

  def testHuntFlowLogsAreCorrectlyWrittenAndCanBeRead(self):
    hunt_args = rdf_hunt_objects.HuntArguments(
        hunt_type=rdf_hunt_objects.HuntArguments.HuntType.STANDARD,
        standard=rdf_hunt_objects.HuntArgumentsStandard(
            flow_name=flow_test_lib.DummyLogFlow.__name__
        ),
    )
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=10,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=hunt_args,
    )

    hunt_logs = data_store.REL_DB.ReadHuntLogEntries(hunt_id, 0, sys.maxsize)
    # 4 logs for each flow. Note: DummyLogFlow also calls DummyLogFlowChild,
    # but children flows logs should not be present in the output.
    self.assertLen(hunt_logs, 4 * len(client_ids))
    self.assertCountEqual(set(log.client_id for log in hunt_logs), client_ids)

    messages_set = set(log.message for log in hunt_logs)
    self.assertCountEqual(messages_set, ["First", "Second", "Third", "Fourth"])

    for nested_flow_log in ["Uno", "Dos", "Tres", "Cuatro"]:
      self.assertNotIn(nested_flow_log, messages_set)

    for log in hunt_logs:
      self.assertEqual(log.hunt_id, hunt_id)

  def testCreatorUsernameIsPropagatedToChildrenFlows(self):
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=1,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        args=self.ClientFileFinderHuntArgs(),
    )

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.creator, self.test_username)

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_ids[0])
    self.assertLen(flows, 1)
    self.assertEqual(flows[0].creator, hunt_obj.creator)

  def testPerClientLimitsArePropagatedToChildrenFlows(self):
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=1,
        client_rule_set=foreman_rules.ForemanClientRuleSet(),
        client_rate=0,
        per_client_cpu_limit=42,
        per_client_network_bytes_limit=43,
        args=self.ClientFileFinderHuntArgs(),
    )

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.creator, self.test_username)

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_ids[0])
    self.assertLen(flows, 1)
    self.assertEqual(flows[0].cpu_limit, 42)
    self.assertEqual(flows[0].network_bytes_limit, 43)

  def testHuntIDFromURN(self):
    self.assertEqual(
        hunt.HuntIDFromURN(rdfvalue.RDFURN("aff4:/hunts/H:12345678")),
        "12345678",
    )

  def testHuntURNFromID(self):
    hunt_urn = hunt.HuntURNFromID("12345678")
    self.assertIsInstance(hunt_urn, rdfvalue.RDFURN)
    self.assertEqual(hunt_urn, rdfvalue.RDFURN("aff4:/hunts/H:12345678"))

  def testScheduleHuntRaceCondition(self):
    client_id = self.SetupClient(0)
    hunt_id = self._CreateHunt(args=self.ClientFileFinderHuntArgs())
    original = data_store.REL_DB.delegate.WriteFlowObject

    def WriteFlowObject(*args, **kwargs):
      with mock.patch.object(
          data_store.REL_DB.delegate, "WriteFlowObject", original
      ):
        try:
          hunt.StartHuntFlowOnClient(client_id, hunt_id)
        except Exception as e:
          raise AssertionError(e)
        return data_store.REL_DB.WriteFlowObject(*args, **kwargs)

    # Patch WriteFlowObject to execute another hunt.StartHuntFlowOnClient() for
    # the same flow and client during the initial StartHuntFlowOnClient().
    with mock.patch.object(
        data_store.REL_DB.delegate, "WriteFlowObject", WriteFlowObject
    ):
      with self.assertRaises(hunt.flow.CanNotStartFlowWithExistingIdError):
        hunt.StartHuntFlowOnClient(client_id, hunt_id)

  def testCreateHuntWithRDFPluginInitializesState(self):
    plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name="StatefulDummyHuntOutputPlugin"
    )
    args = flows_pb2.FileFinderArgs(
        paths=["/tmp/evil.txt"],
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
        ),
    )
    packed_args = any_pb2.Any()
    packed_args.Pack(args)
    hunt_args = hunts_pb2.HuntArguments(
        hunt_type=hunts_pb2.HuntArguments.HuntType.STANDARD,
        standard=hunts_pb2.HuntArgumentsStandard(
            flow_name=file_finder.ClientFileFinder.__name__,
            flow_args=packed_args,
        ),
    )
    hunt_obj = hunts_pb2.Hunt(
        hunt_id=rdf_hunt_objects.RandomHuntId(),
        creator=self.test_username,
        args=hunt_args,
        hunt_state=hunts_pb2.Hunt.HuntState.PAUSED,
        output_plugins=[plugin_descriptor],
    )
    hunt.CreateHunt(hunt_obj)

    states = data_store.REL_DB.ReadHuntOutputPluginsStates(hunt_obj.hunt_id)
    self.assertLen(states, 1)
    self.assertEqual(
        states[0].plugin_descriptor.plugin_name, "StatefulDummyHuntOutputPlugin"
    )

  @test_plugins.WithOutputPluginProto(OPPInitFails)
  def testCreateHuntWithProtoPluginInitFails(self):
    args = flows_pb2.FileFinderArgs(
        paths=["/tmp/evil.txt"],
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
        ),
    )
    packed_args = any_pb2.Any()
    packed_args.Pack(args)
    hunt_args = hunts_pb2.HuntArguments(
        hunt_type=hunts_pb2.HuntArguments.HuntType.STANDARD,
        standard=hunts_pb2.HuntArgumentsStandard(
            flow_name=file_finder.ClientFileFinder.__name__,
            flow_args=packed_args,
        ),
    )
    hunt_obj = hunts_pb2.Hunt(
        hunt_id=rdf_hunt_objects.RandomHuntId(),
        creator=self.test_username,
        args=hunt_args,  # Should be irrelevant.
        hunt_state=hunts_pb2.Hunt.HuntState.PAUSED,
        output_plugins=[
            output_plugin_pb2.OutputPluginDescriptor(
                plugin_name=OPPInitFails.__name__
            )
        ],
    )
    with self.assertRaisesRegex(RuntimeError, "Init failed!"):
      hunt.CreateHunt(hunt_obj)

  @test_plugins.WithOutputPluginProto(OPPWithArgs)
  def testCreateHuntWithOutputPluginProtoWithArgs(self):
    OPPWithArgs.args_during_init = []

    args = jobs_pb2.LogMessage(data="args")
    any_args = any_pb2.Any()
    any_args.Pack(args)
    plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=OPPWithArgs.__name__,
        args=any_args,
    )

    hunt_args = hunts_pb2.HuntArguments(
        hunt_type=hunts_pb2.HuntArguments.HuntType.STANDARD,
        standard=hunts_pb2.HuntArgumentsStandard(
            flow_name=flow_test_lib.DummyFlowWithSingleReply.__name__,
        ),
    )

    hunt_obj = hunts_pb2.Hunt(
        hunt_id=rdf_hunt_objects.RandomHuntId(),
        creator=self.test_username,
        args=hunt_args,
        hunt_state=hunts_pb2.Hunt.HuntState.PAUSED,
        output_plugins=[plugin_descriptor],
    )
    hunt.CreateHunt(hunt_obj)

    self.assertCountEqual(
        OPPWithArgs.args_during_init,
        [jobs_pb2.LogMessage(data="args")],
    )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
