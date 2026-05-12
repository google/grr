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
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import foreman
from grr_response_server import hunt
from grr_response_server import output_plugin
from grr_response_server.flows.general import file_finder
from grr_response_server.flows.general import processes
from grr_response_server.models import hunts as models_hunts
from grr_response_server.output_plugins import test_plugins
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
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


class OPPBadProcessResultsFails(output_plugin.OutputPluginProto):

  def ProcessResults(self, replies: list[flows_pb2.FlowResult]) -> None:
    raise RuntimeError("ProcessResults failed!")


class OPPFlushFails(output_plugin.OutputPluginProto):

  def Flush(self) -> None:
    raise RuntimeError("Flush failed!")


class _DummyProtoOP(output_plugin.OutputPluginProto):
  name = "_DummyProtoOP"
  description = "Dummy Proto Output Plugin."
  processed_values = []

  def ProcessResults(self, replies: list[flows_pb2.FlowResult]) -> None:
    _DummyProtoOP.processed_values.extend(replies)


class OPPTracksCallsAndNumResponses(output_plugin.OutputPluginProto):
  """Dummy hunt output plugin."""

  name = "OPPTracksCallsAndNumResponses"
  description = "Dummy hunt output plugin."
  num_calls = 0
  num_responses = 0

  def ProcessResults(self, replies: list[flows_pb2.FlowResult]) -> None:
    OPPTracksCallsAndNumResponses.num_calls += 1
    OPPTracksCallsAndNumResponses.num_responses += len(replies)


class HuntTest(
    stats_test_lib.StatsTestMixin,
    test_lib.GRRBaseTest,
):
  """Tests for the relational hunts implementation."""

  def _CreateClientFileFinderHuntObject(self) -> hunts_pb2.Hunt:
    return models_hunts.CreateDefaultHuntForFlow(
        flow_name=file_finder.ClientFileFinder.__name__,
        flow_args=flows_pb2.FileFinderArgs(
            paths=["/tmp/evil.txt"],
            action=flows_pb2.FileFinderAction(
                action_type=flows_pb2.FileFinderAction.Action.DOWNLOAD
            ),
        ),
        creator=self.test_username,
    )

  def _CreateHunt(self, hunt_obj: Optional[hunts_pb2.Hunt]):
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
      self, num_clients=5, client_mock=None, iteration_limit=None, hunt_obj=None
  ):
    client_ids = self.SetupClients(num_clients)

    hunt_id = self._CreateHunt(hunt_obj=hunt_obj)
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
    client_rule_set = jobs_pb2.ForemanClientRuleSet(
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.REGEX,
                regex=jobs_pb2.ForemanRegexClientRule(
                    field=jobs_pb2.ForemanRegexClientRule.CLIENT_NAME,
                    attribute_regex="HUNT",
                ),
            ),
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.INTEGER,
                integer=jobs_pb2.ForemanIntegerClientRule(
                    field=jobs_pb2.ForemanIntegerClientRule.CLIENT_VERSION,
                    operator=jobs_pb2.ForemanIntegerClientRule.Operator.GREATER_THAN,
                    value=1337,
                ),
            ),
        ]
    )

    self.assertEmpty(data_store.REL_DB.ReadAllForemanRules())

    hunt_obj = models_hunts.CreateDefaultHunt()
    hunt_obj.client_rule_set.CopyFrom(client_rule_set)
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)

    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertLen(rules, 1)
    rule = rules[0]
    self.assertEqual(
        rule.client_rule_set,
        client_rule_set,
    )
    self.assertEqual(rule.hunt_id, hunt_obj.hunt_id)
    self.assertEqual(
        rule.expiration_time,
        hunt.GetExpiryTimeMicros(hunt_obj),
    )

    # Running a second time should not change the rules any more.
    with self.assertRaises(hunt.OnlyPausedHuntCanBeStartedError):
      hunt.StartHunt(hunt_obj.hunt_id)
    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertLen(rules, 1)

  def testForemanRulesAreCorrectlyRemovedWhenHuntIsStopped(self):
    client_rule_set = jobs_pb2.ForemanClientRuleSet(
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.REGEX,
                regex=jobs_pb2.ForemanRegexClientRule(
                    field=jobs_pb2.ForemanRegexClientRule.CLIENT_NAME,
                    attribute_regex="HUNT",
                ),
            ),
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.INTEGER,
                integer=jobs_pb2.ForemanIntegerClientRule(
                    field=jobs_pb2.ForemanIntegerClientRule.CLIENT_VERSION,
                    operator=jobs_pb2.ForemanIntegerClientRule.Operator.GREATER_THAN,
                    value=1337,
                ),
            ),
        ]
    )

    hunt_obj = models_hunts.CreateDefaultHunt()
    hunt_obj.client_rule_set.CopyFrom(client_rule_set)
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)
    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertLen(rules, 1)

    hunt.StopHunt(hunt_obj.hunt_id)
    rules = data_store.REL_DB.ReadAllForemanRules()
    self.assertEmpty(rules)

  def testStopHuntWithReason(self):
    hunt_obj = models_hunts.CreateDefaultHunt()
    hunt_obj.creator = self.test_username
    data_store.REL_DB.WriteHuntObject(hunt_obj)

    hunt_obj = hunt.StartHunt(hunt_obj.hunt_id)

    hunt.StopHunt(
        hunt_obj.hunt_id,
        hunt_state_reason=hunts_pb2.Hunt.HuntStateReason.AVG_NETWORK_EXCEEDED,
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
    client_rule_set = jobs_pb2.ForemanClientRuleSet(
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.REGEX,
                regex=jobs_pb2.ForemanRegexClientRule(
                    field=jobs_pb2.ForemanRegexClientRule.UNSET,
                    attribute_regex="HUNT",
                ),
            )
        ]
    )

    hunt_obj = models_hunts.CreateDefaultHunt()
    hunt_obj.client_rule_set.CopyFrom(client_rule_set)
    data_store.REL_DB.WriteHuntObject(hunt_obj)
    with self.assertRaises(ValueError):
      hunt.StartHunt(hunt_obj.hunt_id)

  def testForemanRulesWorkCorrectlyWithStandardHunt(self):
    client_rule_set = jobs_pb2.ForemanClientRuleSet(
        rules=[
            jobs_pb2.ForemanClientRule(
                rule_type=jobs_pb2.ForemanClientRule.Type.OS,
                os=jobs_pb2.ForemanOsClientRule(os_windows=True),
            )
        ]
    )
    self.assertEmpty(data_store.REL_DB.ReadAllForemanRules())

    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rule_set.CopyFrom(client_rule_set)
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
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_id, _ = self._CreateAndRunHunt(num_clients=10, hunt_obj=hunt_obj)

    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
    self.assertEqual(hunt_counters.num_clients, 10)
    self.assertEqual(hunt_counters.num_successful_clients, 5)
    self.assertEqual(hunt_counters.num_failed_clients, 5)

  def testHangingClientsAreCorrectlyAccountedFor(self):
    client_ids = self.SetupClients(10)

    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
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
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=10, hunt_obj=hunt_obj
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
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.client_limit = 5
    hunt_id, _ = self._CreateAndRunHunt(num_clients=10, hunt_obj=hunt_obj)

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

    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 1
    _, client_ids = self._CreateAndRunHunt(num_clients=10, hunt_obj=hunt_obj)

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

    flow_args = flows_pb2.FileFinderArgs(
        paths=[path],
        action=flows_pb2.FileFinderAction(
            action_type=flows_pb2.FileFinderAction.Action.STAT
        ),
    )
    hunt_obj = models_hunts.CreateDefaultHuntForFlow(
        flow_name=file_finder.ClientFileFinder.__name__,
        flow_args=flow_args,
        creator=self.test_username,
    )
    hunt_obj.client_rate = 0

    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=action_mocks.FileFinderClientMock(),
        hunt_obj=hunt_obj,
    )

    hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
    self.assertEqual(hunt_counters.num_clients_with_results, 5)
    self.assertEqual(hunt_counters.num_results, 5 * num_files)

  def testStoppingHuntMarksHuntFlowsForTermination(self):
    hunt_obj = models_hunts.CreateDefaultHunt()
    hunt_obj.client_rate = 0
    hunt_obj.args.standard.flow_name = flow_test_lib.InfiniteFlow.__name__
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=5,
        iteration_limit=10,
        hunt_obj=hunt_obj,
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
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=10,
        hunt_obj=hunt_obj,
    )

    results = data_store.REL_DB.ReadHuntResults(hunt_id, 0, sys.maxsize)
    self.assertLen(results, 5)
    for r in results:
      self.assertTrue(r.payload.Is(flows_pb2.FileFinderResult.DESCRIPTOR))
      ff_result = flows_pb2.FileFinderResult()
      r.payload.Unpack(ff_result)
      self.assertEqual(ff_result.stat_entry.pathspec.path, "/tmp/evil.txt")

  @test_plugins.WithOutputPluginProto(OPPTracksCallsAndNumResponses)
  def testOutputPluginsAreCorrectlyAppliedAndTheirStatusCanBeRead(self):
    OPPTracksCallsAndNumResponses.num_calls = 0
    OPPTracksCallsAndNumResponses.num_responses = 0

    plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=OPPTracksCallsAndNumResponses.__name__
    )
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.output_plugins.append(plugin_descriptor)
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        hunt_obj=hunt_obj,
    )

    self.assertEqual(OPPTracksCallsAndNumResponses.num_calls, 5)
    self.assertEqual(OPPTracksCallsAndNumResponses.num_responses, 5)

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

  @test_plugins.WithOutputPluginProto(OPPBadProcessResultsFails)
  def testOutputPluginsErrorsAreCorrectlyWrittenAndCanBeRead(self):
    failing_plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=OPPBadProcessResultsFails.__name__
    )
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.output_plugins.append(failing_plugin_descriptor)

    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        hunt_obj=hunt_obj,
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
      self.assertEqual(
          e.message, "Error while processing 1 replies: ProcessResults failed!"
      )

  @test_plugins.WithOutputPluginProto(OPPFlushFails)
  def testOutputPluginFlushErrorIsLoggedProperly(self):
    plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=OPPFlushFails.__name__
    )
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.output_plugins.append(plugin_descriptor)

    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        hunt_obj=hunt_obj,
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
          e.message, "Error while processing 1 replies: Flush failed!"
      )

  @test_plugins.WithOutputPluginProto(OPPBadProcessResultsFails)
  @test_plugins.WithOutputPluginProto(OPPTracksCallsAndNumResponses)
  def testFailingOutputPluginDoesNotAffectOtherOutputPlugins(self):
    failing_plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=OPPBadProcessResultsFails.__name__
    )
    OPPTracksCallsAndNumResponses.num_calls = 0
    OPPTracksCallsAndNumResponses.num_responses = 0
    plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=OPPTracksCallsAndNumResponses.__name__
    )
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.output_plugins.extend([
        failing_plugin_descriptor,
        plugin_descriptor,
    ])

    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=5,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        hunt_obj=hunt_obj,
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
  def testHuntWithUnknownOutputPluginFails(self):
    exists = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=_DummyProtoOP.__name__
    )
    does_not_exist = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name="IDontExist"
    )
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.output_plugins.extend([exists, does_not_exist])

    with self.assertRaises(hunt.UnknownOutputPluginError):
      self._CreateAndRunHunt(
          num_clients=1,
          client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
          hunt_obj=hunt_obj,
      )

  @test_plugins.WithOutputPluginProto(OPPTracksCallsAndNumResponses)
  def testUpdatesStatsCounterOnOutputPluginSuccess(self):
    OPPTracksCallsAndNumResponses.num_calls = 0
    OPPTracksCallsAndNumResponses.num_responses = 0
    plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=OPPTracksCallsAndNumResponses.__name__
    )
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.output_plugins.append(plugin_descriptor)

    # 1 result for each client makes it 5 results.
    with self.assertStatsCounterDelta(
        5,
        flow_base.HUNT_RESULTS_RAN_THROUGH_PLUGIN,
        fields=[OPPTracksCallsAndNumResponses.__name__],
    ):
      with self.assertStatsCounterDelta(
          0,
          flow_base.HUNT_OUTPUT_PLUGIN_ERRORS,
          fields=[OPPTracksCallsAndNumResponses.__name__],
      ):
        self._CreateAndRunHunt(
            num_clients=5,
            client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
            hunt_obj=hunt_obj,
        )

  @test_plugins.WithOutputPluginProto(OPPBadProcessResultsFails)
  def testUpdatesStatsCounterOnOutputPluginFailure(self):
    plugin_descriptor = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=OPPBadProcessResultsFails.__name__
    )
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.output_plugins.append(plugin_descriptor)

    # 1 error for each client makes it 5 errors, 0 results.
    with self.assertStatsCounterDelta(
        0,
        flow_base.HUNT_RESULTS_RAN_THROUGH_PLUGIN,
        fields=[OPPBadProcessResultsFails.__name__],
    ):
      with self.assertStatsCounterDelta(
          5,
          flow_base.HUNT_OUTPUT_PLUGIN_ERRORS,
          fields=[OPPBadProcessResultsFails.__name__],
      ):
        self._CreateAndRunHunt(
            num_clients=5,
            client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
            hunt_obj=hunt_obj,
        )

  def _CheckHuntStoppedNotification(self, str_match):
    pending = data_store.REL_DB.ReadUserNotifications(self.test_username)
    self.assertLen(pending, 1)
    self.assertIn(str_match, pending[0].message)

  def testHuntIsStoppedIfCrashNumberOverThreshold(self):
    client_ids = self.SetupClients(4)
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.crash_limit = 3

    hunt_id = self._CreateHunt(
        hunt_obj=hunt_obj,
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

    hunt_obj = models_hunts.CreateDefaultHuntForFlow(
        flow_name=processes.ListProcesses.__name__,
        flow_args=flows_pb2.ListProcessesArgs(),
        creator=self.test_username,
    )
    hunt_obj.client_rate = 0
    hunt_obj.avg_results_per_client_limit = 1

    hunt_id = self._CreateHunt(
        hunt_obj=hunt_obj,
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
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.avg_cpu_seconds_per_client_limit = 3

    hunt_id = self._CreateHunt(
        hunt_obj=hunt_obj,
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

      # TODO - Re-enable the checks after the test is reworked to
      # run with approximate limits (flow not persisted in the DB every time).

      # # Hunt should be terminated: the average is exceeded.
      # CheckState(rdf_hunt_objects.Hunt.HuntState.STOPPED, 6, 12)

      # self._CheckHuntStoppedNotification(
      #     "reached the average CPU seconds per client")

  def testHuntIsStoppedIfAveragePerClientNetworkUsageTooHigh(self):
    client_ids = self.SetupClients(5)
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.avg_network_bytes_per_client_limit = 1

    hunt_id = self._CreateHunt(
        hunt_obj=hunt_obj,
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

      # TODO - Re-enable the checks after the test is reworked to
      # run with approximate limits (flow not persisted in the DB every time).

      # # Hunt should be terminated: the limit is exceeded.
      # CheckState(rdf_hunt_objects.Hunt.HuntState.STOPPED, 6)

      # self._CheckHuntStoppedNotification(
      #     "reached the average network bytes per client")

  def testHuntIsStoppedIfTotalNetworkUsageIsTooHigh(self):
    client_ids = self.SetupClients(5)
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.total_network_bytes_limit = 5

    hunt_id = self._CreateHunt(
        hunt_obj=hunt_obj,
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

    # TODO - Re-enable the checks after the test is reworked to
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

    # Hunt duration is set in DurationSeconds (not Duration).
    # If you assign rdf_hunt_objects.Hunt.duration with the wrong RDF primitive
    # (this case before the refactor), it'll be automatically converted and
    # interpreted to DurationSeconds. The same is not true for protos, so we
    # explicitly create the right type here, and then convert it to an int
    # when setting the proto value.
    hunt_duration = rdfvalue.DurationSeconds.From(1, rdfvalue.DAYS)
    expiry_time = fake_time + hunt_duration

    foreman_obj = foreman.Foreman()

    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.duration = hunt_duration.SerializeToWireFormat()

    with test_lib.FakeTime(fake_time):
      hunt_id = self._CreateHunt(
          hunt_obj=hunt_obj,
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
      self.assertEqual(hunt_obj.hunt_state, hunts_pb2.Hunt.HuntState.COMPLETED)
      hunt_counters = data_store.REL_DB.ReadHuntCounters(hunt_id)
      self.assertEqual(hunt_counters.num_clients, 2)

  def testPausingTheHuntChangingParametersAndStartingAgainWorksAsExpected(self):
    client_ids = self.SetupClients(2)

    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.client_limit = 1

    hunt_id = self._CreateHunt(
        hunt_obj=hunt_obj,
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
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_id, _ = self._CreateAndRunHunt(
        num_clients=10,
        client_mock=hunt_test_lib.SampleHuntMock(failrate=-1),
        hunt_obj=hunt_obj,
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
    hunt_obj = models_hunts.CreateDefaultHuntForFlow(
        flow_name=flow_test_lib.DummyLogFlow.__name__,
        flow_args=flows_pb2.EmptyFlowArgs(),
        creator=self.test_username,
    )
    hunt_obj.client_rate = 0

    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=10,
        hunt_obj=hunt_obj,
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
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=1,
        hunt_obj=hunt_obj,
    )

    hunt_obj = data_store.REL_DB.ReadHuntObject(hunt_id)
    self.assertEqual(hunt_obj.creator, self.test_username)

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id=client_ids[0])
    self.assertLen(flows, 1)
    self.assertEqual(flows[0].creator, hunt_obj.creator)

  def testPerClientLimitsArePropagatedToChildrenFlows(self):
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.client_rate = 0
    hunt_obj.per_client_cpu_limit = 42
    hunt_obj.per_client_network_bytes_limit = 43
    hunt_id, client_ids = self._CreateAndRunHunt(
        num_clients=1,
        hunt_obj=hunt_obj,
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
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_id = self._CreateHunt(hunt_obj=hunt_obj)
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

  @test_plugins.WithOutputPluginProto(OPPInitFails)
  def testCreateHuntWithProtoPluginInitFails(self):
    hunt_obj = self._CreateClientFileFinderHuntObject()
    hunt_obj.output_plugins.append(
        output_plugin_pb2.OutputPluginDescriptor(
            plugin_name=OPPInitFails.__name__
        )
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

    hunt_obj = models_hunts.CreateDefaultHuntForFlow(
        flow_name=flow_test_lib.DummyFlowWithSingleReply.__name__,
        flow_args=flows_pb2.EmptyFlowArgs(),
        creator=self.test_username,
    )
    hunt_obj.output_plugins.append(plugin_descriptor)

    hunt.CreateHunt(hunt_obj)

    self.assertCountEqual(
        OPPWithArgs.args_during_init,
        [jobs_pb2.LogMessage(data="args")],
    )


class GetExpiryTimeMicrosTest(test_lib.GRRBaseTest):

  def testGetExpiryTimeNoStartTimeReturnsNone(self):
    hunt_obj = hunts_pb2.Hunt()
    self.assertIsNone(hunt.GetExpiryTimeMicros(hunt_obj))

  def testGetExpiryTimeReturnsCorrectTime(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2020-01-01")
    duration = rdfvalue.Duration.From(1, rdfvalue.DAYS)
    expected_expiry = start_time + duration

    hunt_obj = hunts_pb2.Hunt()
    hunt_obj.init_start_time = start_time.AsMicrosecondsSinceEpoch()
    hunt_obj.duration = duration.ToInt(rdfvalue.SECONDS)

    self.assertEqual(
        hunt.GetExpiryTimeMicros(hunt_obj),
        expected_expiry.AsMicrosecondsSinceEpoch(),
    )


class IsExpiredTest(test_lib.GRRBaseTest):

  def testIsExpiredNoStartTimeReturnsFalse(self):
    hunt_obj = hunts_pb2.Hunt()
    self.assertFalse(hunt.IsExpired(hunt_obj))

  def testIsExpiredReturnsFalseBeforeExpiry(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2020-01-01")
    duration = rdfvalue.DurationSeconds.From(1, rdfvalue.DAYS)

    hunt_obj = hunts_pb2.Hunt()
    hunt_obj.init_start_time = start_time.AsMicrosecondsSinceEpoch()
    hunt_obj.duration = duration.SerializeToWireFormat()

    fake_1h_after_start = start_time + rdfvalue.Duration.From(1, rdfvalue.HOURS)
    with test_lib.FakeTime(fake_1h_after_start):
      self.assertFalse(hunt.IsExpired(hunt_obj))

  def testIsExpiredReturnsFalseBeforeExpiryBorderCase(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2020-01-01")
    duration = rdfvalue.DurationSeconds.From(1, rdfvalue.DAYS)

    hunt_obj = hunts_pb2.Hunt()
    hunt_obj.init_start_time = start_time.AsMicrosecondsSinceEpoch()
    hunt_obj.duration = duration.SerializeToWireFormat()

    fake_1s_before_expiry = (
        start_time + duration - rdfvalue.Duration.From(1, rdfvalue.SECONDS)
    )
    with test_lib.FakeTime(fake_1s_before_expiry):
      self.assertFalse(hunt.IsExpired(hunt_obj))

  def testIsExpiredExactExpiry(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2020-01-01")
    duration = rdfvalue.DurationSeconds.From(1, rdfvalue.DAYS)

    hunt_obj = hunts_pb2.Hunt()
    hunt_obj.init_start_time = start_time.AsMicrosecondsSinceEpoch()
    hunt_obj.duration = duration.SerializeToWireFormat()

    fake_exact_expiry = start_time + duration
    with test_lib.FakeTime(fake_exact_expiry):
      self.assertFalse(hunt.IsExpired(hunt_obj))

  def testIsExpiredReturnsTrueAfterExpiry(self):
    start_time = rdfvalue.RDFDatetime.FromHumanReadable("2020-01-01")
    duration = rdfvalue.DurationSeconds.From(1, rdfvalue.DAYS)

    hunt_obj = hunts_pb2.Hunt()
    hunt_obj.init_start_time = start_time.AsMicrosecondsSinceEpoch()
    hunt_obj.duration = duration.SerializeToWireFormat()

    fake_1s_after_expiry = (
        start_time + duration + rdfvalue.Duration.From(1, rdfvalue.SECONDS)
    )
    with test_lib.FakeTime(fake_1s_after_expiry):
      self.assertTrue(hunt.IsExpired(hunt_obj))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
