#!/usr/bin/env python
"""Tests for the hunt database api."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
import random

from future.utils import text_type

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.lib.util import compatibility
from grr_response_server import db
from grr_response_server import flow
from grr_response_server.output_plugins import email_plugin
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin


class DatabaseTestHuntMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of hunts.
  """

  def _SetupHuntClientAndFlow(self,
                              client_id=None,
                              hunt_id=None,
                              flow_id=None,
                              **additional_flow_args):
    client_id = self.InitializeClient(client_id=client_id)
    # Top-level hunt-induced flows should have hunt's id.
    flow_id = flow_id or hunt_id
    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id=flow_id,
        parent_hunt_id=hunt_id,
        create_time=rdfvalue.RDFDatetime.Now(),
        **additional_flow_args)
    self.db.WriteFlowObject(rdf_flow)

    return client_id, flow_id

  def testWritingAndReadingHuntObjectWorks(self):
    hunt_obj = rdf_hunt_objects.Hunt()
    self.db.WriteHuntObject(hunt_obj)

    read_hunt_obj = self.db.ReadHuntObject(hunt_obj.hunt_id)
    # Last update time is set automatically when the object is written.
    # Setting it on hunt_obj to make sure it doesn't influence the equality
    # check.
    hunt_obj.last_update_time = read_hunt_obj.last_update_time
    self.assertEqual(hunt_obj, read_hunt_obj)

  def testHuntObjectCanBeOverwritten(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    read_hunt_obj = self.db.ReadHuntObject(hunt_obj.hunt_id)
    self.assertEqual(read_hunt_obj.description, "foo")

    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt_obj.hunt_id, description="bar")
    self.db.WriteHuntObject(hunt_obj)

    read_hunt_obj = self.db.ReadHuntObject(hunt_obj.hunt_id)
    self.assertEqual(read_hunt_obj.description, "bar")

  def testReadingNonExistentHuntObjectRaises(self):
    with self.assertRaises(db.UnknownHuntError):
      self.db.ReadHuntObject(rdf_hunt_objects.RandomHuntId())

  def testUpdateHuntObjectRaisesIfHuntDoesNotExist(self):
    with self.assertRaises(db.UnknownHuntError):
      self.db.UpdateHuntObject(
          rdf_hunt_objects.RandomHuntId(),
          hunt_state=rdf_hunt_objects.Hunt.HuntState.STARTED)

  def testUpdateHuntObjectCorrectlyUpdatesHuntObject(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    self.db.UpdateHuntObject(
        hunt_obj.hunt_id,
        expiry_time=rdfvalue.RDFDatetime(42),
        client_rate=33,
        client_limit=48,
        hunt_state=rdf_hunt_objects.Hunt.HuntState.STOPPED,
        hunt_state_comment="foo",
        start_time=rdfvalue.RDFDatetime(43),
        num_clients_at_start_time=44)

    updated_hunt_obj = self.db.ReadHuntObject(hunt_obj.hunt_id)
    self.assertEqual(updated_hunt_obj.expiry_time, rdfvalue.RDFDatetime(42))
    self.assertEqual(updated_hunt_obj.client_rate, 33)
    self.assertEqual(updated_hunt_obj.client_limit, 48)
    self.assertEqual(updated_hunt_obj.hunt_state,
                     rdf_hunt_objects.Hunt.HuntState.STOPPED)
    self.assertEqual(updated_hunt_obj.hunt_state_comment, "foo")
    self.assertEqual(updated_hunt_obj.start_time, rdfvalue.RDFDatetime(43))
    self.assertEqual(updated_hunt_obj.num_clients_at_start_time, 44)

  def testDeletingHuntObjectWorks(self):
    hunt_obj = rdf_hunt_objects.Hunt()
    self.db.WriteHuntObject(hunt_obj)

    # This shouldn't raise.
    self.db.ReadHuntObject(hunt_obj.hunt_id)

    self.db.DeleteHuntObject(hunt_obj.hunt_id)

    # The hunt is deleted: this should raise now.
    with self.assertRaises(db.UnknownHuntError):
      self.db.ReadHuntObject(hunt_obj.hunt_id)

  def testReadAllHuntObjectsReturnsEmptyListWhenNoHunts(self):
    self.assertEqual(self.db.ReadAllHuntObjects(), [])

  def testReadAllHuntObjectsReturnsAllWrittenObjects(self):
    hunt_obj_1 = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj_1)

    hunt_obj_2 = rdf_hunt_objects.Hunt(description="bar")
    self.db.WriteHuntObject(hunt_obj_2)

    read_hunt_objs = self.db.ReadAllHuntObjects()
    self.assertLen(read_hunt_objs, 2)
    self.assertCountEqual(["foo", "bar"],
                          [h.description for h in read_hunt_objs])

  def testWritingAndReadingHuntOutputPluginsStatesWorks(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=compatibility.GetName(email_plugin.EmailOutputPlugin),
        plugin_args=email_plugin.EmailOutputPluginArgs(emails_limit=42))
    state_1 = rdf_flow_runner.OutputPluginState(
        plugin_descriptor=plugin_descriptor, plugin_state={})

    plugin_descriptor = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=compatibility.GetName(email_plugin.EmailOutputPlugin),
        plugin_args=email_plugin.EmailOutputPluginArgs(emails_limit=43))
    state_2 = rdf_flow_runner.OutputPluginState(
        plugin_descriptor=plugin_descriptor, plugin_state={})

    written_states = [state_1, state_2]
    self.db.WriteHuntOutputPluginsStates(hunt_obj.hunt_id, written_states)

    read_states = self.db.ReadHuntOutputPluginsStates(hunt_obj.hunt_id)
    self.assertEqual(read_states, written_states)

  def testReadingHuntOutputPluginsReturnsThemInOrderOfWriting(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    states = []
    for i in range(100):
      states.append(
          rdf_flow_runner.OutputPluginState(
              plugin_descriptor=rdf_output_plugin.OutputPluginDescriptor(
                  plugin_name="DummyHuntOutputPlugin_%d" % i),
              plugin_state={}))
    random.shuffle(states)

    self.db.WriteHuntOutputPluginsStates(hunt_obj.hunt_id, states)

    read_states = self.db.ReadHuntOutputPluginsStates(hunt_obj.hunt_id)
    self.assertEqual(read_states, states)

  def testWritingHuntOutputStatesForZeroPlugins(self):
    # Passing an empty list of states is always a no-op so this should not
    # raise, even if the hunt does not exist.
    self.db.WriteHuntOutputPluginsStates(rdf_hunt_objects.RandomHuntId(), [])

  def testWritingHuntOutputStatesForUnknownHuntRaises(self):
    state = rdf_flow_runner.OutputPluginState(
        plugin_descriptor=rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyHuntOutputPlugin1"),
        plugin_state={})

    with self.assertRaises(db.UnknownHuntError):
      self.db.WriteHuntOutputPluginsStates(rdf_hunt_objects.RandomHuntId(),
                                           [state])

  def testReadingHuntOutputStatesForUnknownHuntRaises(self):
    with self.assertRaises(db.UnknownHuntError):
      self.db.ReadHuntOutputPluginsStates(rdf_hunt_objects.RandomHuntId())

  def testUpdatingHuntOutputStateForUnknownHuntRaises(self):
    with self.assertRaises(db.UnknownHuntError):
      self.db.UpdateHuntOutputPluginState(rdf_hunt_objects.RandomHuntId(),
                                          0, lambda x: x)

  def testUpdatingHuntOutputStateWorksCorrectly(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    state_1 = rdf_flow_runner.OutputPluginState(
        plugin_descriptor=rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyHuntOutputPlugin1"),
        plugin_state={})

    state_2 = rdf_flow_runner.OutputPluginState(
        plugin_descriptor=rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyHuntOutputPlugin2"),
        plugin_state={})

    self.db.WriteHuntOutputPluginsStates(hunt_obj.hunt_id, [state_1, state_2])

    def Update(s):
      s["foo"] = "bar"
      return s

    self.db.UpdateHuntOutputPluginState(hunt_obj.hunt_id, 0, Update)

    states = self.db.ReadHuntOutputPluginsStates(hunt_obj.hunt_id)
    self.assertEqual(states[0].plugin_state, {"foo": "bar"})
    self.assertEqual(states[1].plugin_state, {})

    self.db.UpdateHuntOutputPluginState(hunt_obj.hunt_id, 1, Update)

    states = self.db.ReadHuntOutputPluginsStates(hunt_obj.hunt_id)
    self.assertEqual(states[0].plugin_state, {"foo": "bar"})
    self.assertEqual(states[1].plugin_state, {"foo": "bar"})

  def testReadHuntLogEntriesReturnsEntryFromSingleHuntFlow(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(
        client_id="C.12345678901234aa", hunt_id=hunt_obj.hunt_id)
    self.db.WriteFlowLogEntries([
        rdf_flow_objects.FlowLogEntry(
            client_id=client_id,
            flow_id=flow_id,
            hunt_id=hunt_obj.hunt_id,
            message="blah")
    ])

    hunt_log_entries = self.db.ReadHuntLogEntries(hunt_obj.hunt_id, 0, 10)
    self.assertLen(hunt_log_entries, 1)
    self.assertIsInstance(hunt_log_entries[0], rdf_flow_objects.FlowLogEntry)
    self.assertEqual(hunt_log_entries[0].hunt_id, hunt_obj.hunt_id)
    self.assertEqual(hunt_log_entries[0].client_id, client_id)
    self.assertEqual(hunt_log_entries[0].flow_id, flow_id)
    self.assertEqual(hunt_log_entries[0].message, "blah")

  def _WriteNestedAndNonNestedLogEntries(self, hunt_obj):
    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    self.db.WriteFlowLogEntries([
        rdf_flow_objects.FlowLogEntry(
            client_id=client_id,
            # Top-level hunt-induced flows should have hunt's ids.
            flow_id=flow_id,
            hunt_id=hunt_obj.hunt_id,
            message="blah")
    ])

    for i in range(10):
      _, nested_flow_id = self._SetupHuntClientAndFlow(
          client_id=client_id,
          parent_flow_id=flow_id,
          hunt_id=hunt_obj.hunt_id,
          flow_id=flow.RandomFlowId())
      self.db.WriteFlowLogEntries([
          rdf_flow_objects.FlowLogEntry(
              client_id=client_id,
              flow_id=nested_flow_id,
              hunt_id=hunt_obj.hunt_id,
              message="blah_%d" % i)
      ])

  def testReadHuntLogEntriesIgnoresNestedFlows(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    self._WriteNestedAndNonNestedLogEntries(hunt_obj)

    hunt_log_entries = self.db.ReadHuntLogEntries(hunt_obj.hunt_id, 0, 10)
    self.assertLen(hunt_log_entries, 1)
    self.assertEqual(hunt_log_entries[0].message, "blah")

  def testCountHuntLogEntriesIgnoresNestedFlows(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    self._WriteNestedAndNonNestedLogEntries(hunt_obj)

    num_hunt_log_entries = self.db.CountHuntLogEntries(hunt_obj.hunt_id)
    self.assertEqual(num_hunt_log_entries, 1)

  def _WriteHuntLogEntries(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          client_id="C.12345678901234a%d" % i, hunt_id=hunt_obj.hunt_id)
      self.db.WriteFlowLogEntries([
          rdf_flow_objects.FlowLogEntry(
              client_id=client_id,
              flow_id=flow_id,
              hunt_id=hunt_obj.hunt_id,
              message="blah%d" % i)
      ])

    return hunt_obj

  def testReadHuntLogEntriesReturnsEntryFromMultipleHuntFlows(self):
    hunt_obj = self._WriteHuntLogEntries()

    hunt_log_entries = self.db.ReadHuntLogEntries(hunt_obj.hunt_id, 0, 100)
    self.assertLen(hunt_log_entries, 10)
    # Make sure messages are returned in timestamps-ascending order.
    for i, e in enumerate(hunt_log_entries):
      self.assertEqual(e.message, "blah%d" % i)

  def testReadHuntLogEntriesCorrectlyAppliesOffsetAndCountFilters(self):
    hunt_obj = self._WriteHuntLogEntries()

    for i in range(10):
      hunt_log_entries = self.db.ReadHuntLogEntries(hunt_obj.hunt_id, i, 1)
      self.assertLen(hunt_log_entries, 1)
      self.assertEqual(hunt_log_entries[0].message, "blah%d" % i)

  def testReadHuntLogEntriesCorrectlyAppliesWithSubstringFilter(self):
    hunt_obj = self._WriteHuntLogEntries()

    hunt_log_entries = self.db.ReadHuntLogEntries(
        hunt_obj.hunt_id, 0, 100, with_substring="foo")
    self.assertEmpty(hunt_log_entries)

    hunt_log_entries = self.db.ReadHuntLogEntries(
        hunt_obj.hunt_id, 0, 100, with_substring="blah")
    self.assertLen(hunt_log_entries, 10)
    # Make sure messages are returned in timestamps-ascending order.
    for i, e in enumerate(hunt_log_entries):
      self.assertEqual(e.message, "blah%d" % i)

    hunt_log_entries = self.db.ReadHuntLogEntries(
        hunt_obj.hunt_id, 0, 100, with_substring="blah1")
    self.assertLen(hunt_log_entries, 1)
    self.assertEqual(hunt_log_entries[0].message, "blah1")

  def testReadHuntLogEntriesCorrectlyAppliesCombinationOfFilters(self):
    hunt_obj = self._WriteHuntLogEntries()

    hunt_log_entries = self.db.ReadHuntLogEntries(
        hunt_obj.hunt_id, 0, 1, with_substring="blah")
    self.assertLen(hunt_log_entries, 1)
    self.assertEqual(hunt_log_entries[0].message, "blah0")

  def testCountHuntLogEntriesReturnsCorrectHuntLogEntriesCount(self):
    hunt_obj = self._WriteHuntLogEntries()

    num_entries = self.db.CountHuntLogEntries(hunt_obj.hunt_id)
    self.assertEqual(num_entries, 10)

  def _WriteHuntResults(self, sample_results=None):
    self._WriteFlowResults(
        multiple_timestamps=True,
        sample_results=sample_results,
    )

  def _SampleSingleTypeHuntResults(self,
                                   client_id=None,
                                   flow_id=None,
                                   hunt_id=None,
                                   count=10):
    self.assertIsNotNone(client_id)
    self.assertIsNotNone(flow_id)
    self.assertIsNotNone(hunt_id)

    return [
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            hunt_id=hunt_id,
            tag="tag_%d" % i,
            payload=rdf_client.ClientSummary(
                client_id=client_id,
                system_manufacturer="manufacturer_%d" % i,
                install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10 +
                                                                        i)))
        for i in range(count)
    ]

  def _SampleTwoTypeHuntResults(self,
                                client_id=None,
                                flow_id=None,
                                hunt_id=None,
                                count_per_type=5,
                                timestamp_start=10):
    self.assertIsNotNone(client_id)
    self.assertIsNotNone(flow_id)
    self.assertIsNotNone(hunt_id)

    return [
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            hunt_id=hunt_id,
            tag="tag_%d" % i,
            payload=rdf_client.ClientSummary(
                client_id=client_id,
                system_manufacturer="manufacturer_%d" % i,
                install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                    timestamp_start + i))) for i in range(count_per_type)
    ] + [
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            hunt_id=hunt_id,
            tag="tag_%d" % i,
            payload=rdf_client.ClientCrash(
                client_id=client_id,
                timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                    timestamp_start + i))) for i in range(count_per_type)
    ]

  def testReadHuntResultsReadsSingleResultOfSingleType(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_obj.hunt_id, count=1)
    self._WriteHuntResults(sample_results)

    results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 10)
    self.assertLen(results, 1)
    self.assertEqual(results[0].hunt_id, hunt_obj.hunt_id)
    self.assertEqual(results[0].payload, sample_results[0].payload)

  def testReadHuntResultsReadsMultipleResultOfSingleType(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id,
        flow_id=flow_id,
        hunt_id=hunt_obj.hunt_id,
        count=10)
    self._WriteHuntResults(sample_results)

    results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 1000)
    self.assertLen(results, 10)
    for i in range(10):
      self.assertEqual(results[i].hunt_id, hunt_obj.hunt_id)
      self.assertEqual(results[i].payload, sample_results[i].payload)

  def testReadHuntResultsReadsMultipleResultOfMultipleTypes(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id_1, flow_id_1 = self._SetupHuntClientAndFlow(
        hunt_id=hunt_obj.hunt_id)
    sample_results_1 = self._SampleTwoTypeHuntResults(
        client_id=client_id_1, flow_id=flow_id_1, hunt_id=hunt_obj.hunt_id)
    self._WriteHuntResults(sample_results_1)

    client_id_2, flow_id_2 = self._SetupHuntClientAndFlow(
        hunt_id=hunt_obj.hunt_id)
    sample_results_2 = self._SampleTwoTypeHuntResults(
        client_id=client_id_2, flow_id=flow_id_2, hunt_id=hunt_obj.hunt_id)
    self._WriteHuntResults(sample_results_2)

    sample_results = sample_results_1 + sample_results_2
    results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 1000)
    self.assertLen(results, len(sample_results))
    self.assertListEqual([i.payload for i in results],
                         [i.payload for i in sample_results])

  def testReadHuntResultsCorrectlyAppliedOffsetAndCountFilters(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    sample_results = []
    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          hunt_id=hunt_obj.hunt_id)
      results = self._SampleSingleTypeHuntResults(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_obj.hunt_id,
          count=1)
      sample_results.extend(results)
      self._WriteHuntResults(results)

    for l in range(1, 11):
      for i in range(10):
        results = self.db.ReadHuntResults(hunt_obj.hunt_id, i, l)
        expected = sample_results[i:i + l]

        result_payloads = [x.payload for x in results]
        expected_payloads = [x.payload for x in expected]
        self.assertEqual(
            result_payloads, expected_payloads,
            "Results differ from expected (from %d, size %d): %s vs %s" %
            (i, l, result_payloads, expected_payloads))

  def testReadHuntResultsCorrectlyAppliesWithTagFilter(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_obj.hunt_id)
    self._WriteHuntResults(sample_results)

    results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 100, with_tag="blah")
    self.assertFalse(results)

    results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 100, with_tag="tag")
    self.assertFalse(results)

    results = self.db.ReadHuntResults(
        hunt_obj.hunt_id, 0, 100, with_tag="tag_1")
    self.assertEqual([i.payload for i in results],
                     [i.payload for i in sample_results if i.tag == "tag_1"])

  def testReadHuntResultsCorrectlyAppliesWithTypeFilter(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    sample_results = []
    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          hunt_id=hunt_obj.hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_obj.hunt_id,
          count_per_type=1)
      sample_results.extend(results)
      self._WriteHuntResults(results)

    results = self.db.ReadHuntResults(
        hunt_obj.hunt_id,
        0,
        100,
        with_type=compatibility.GetName(rdf_client.ClientInformation))
    self.assertFalse(results)

    results = self.db.ReadHuntResults(
        hunt_obj.hunt_id,
        0,
        100,
        with_type=compatibility.GetName(rdf_client.ClientSummary))
    self.assertCountEqual(
        [i.payload for i in results],
        [
            i.payload
            for i in sample_results
            if isinstance(i.payload, rdf_client.ClientSummary)
        ],
    )

  def testReadHuntResultsCorrectlyAppliesWithSubstringFilter(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_obj.hunt_id)
    self._WriteHuntResults(sample_results)

    results = self.db.ReadHuntResults(
        hunt_obj.hunt_id, 0, 100, with_substring="blah")
    self.assertFalse(results)

    results = self.db.ReadHuntResults(
        hunt_obj.hunt_id, 0, 100, with_substring="manufacturer")
    self.assertEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results],
    )

    results = self.db.ReadHuntResults(
        hunt_obj.hunt_id, 0, 100, with_substring="manufacturer_1")
    self.assertEqual([i.payload for i in results], [sample_results[1].payload])

  def testReadHuntResultsCorrectlyAppliesVariousCombinationsOfFilters(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    sample_results = []
    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          hunt_id=hunt_obj.hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_obj.hunt_id,
          count_per_type=5)
      sample_results.extend(results)
      self._WriteHuntResults(results)

    tags = {"tag_1": set(s for s in sample_results if s.tag == "tag_1")}
    substrings = {
        "manufacturer":
            set(s for s in sample_results if "manufacturer" in getattr(
                s.payload, "system_manufacturer", "")),
        "manufacturer_1":
            set(s for s in sample_results if "manufacturer_1" in getattr(
                s.payload, "system_manufacturer", ""))
    }
    types = {
        compatibility.GetName(rdf_client.ClientSummary):
            set(
                s for s in sample_results
                if isinstance(s.payload, rdf_client.ClientSummary))
    }

    no_tag = [(None, set(sample_results))]

    for tag_value, tag_expected in itertools.chain(tags.items(), no_tag):
      for substring_value, substring_expected in itertools.chain(
          substrings.items(), no_tag):
        for type_value, type_expected in itertools.chain(types.items(), no_tag):
          expected = tag_expected & substring_expected & type_expected
          results = self.db.ReadHuntResults(
              hunt_obj.hunt_id,
              0,
              100,
              with_tag=tag_value,
              with_type=type_value,
              with_substring=substring_value)

          self.assertCountEqual(
              [i.payload for i in expected], [i.payload for i in results],
              "Result items do not match for "
              "(tag=%s, type=%s, substring=%s): %s vs %s" %
              (tag_value, type_value, substring_value, expected, results))

  def testReadHuntResultsReturnsPayloadWithMissingTypeAsSpecialValue(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_obj.hunt_id)
    self._WriteHuntResults(sample_results)

    type_name = compatibility.GetName(rdf_client.ClientSummary)
    try:
      cls = rdfvalue.RDFValue.classes.pop(type_name)

      results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 100)
    finally:
      rdfvalue.RDFValue.classes[type_name] = cls

    self.assertLen(sample_results, len(results))
    for r in results:
      self.assertTrue(
          isinstance(r.payload, rdf_objects.SerializedValueOfUnrecognizedType))
      self.assertEqual(r.payload.type_name, type_name)

  def testCountHuntResultsReturnsCorrectResultsCount(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_obj.hunt_id)
    self._WriteHuntResults(sample_results)

    num_results = self.db.CountHuntResults(hunt_obj.hunt_id)
    self.assertEqual(num_results, len(sample_results))

  def testCountHuntResultsCorrectlyAppliesWithTagFilter(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_obj.hunt_id)
    self._WriteHuntResults(sample_results)

    num_results = self.db.CountHuntResults(hunt_obj.hunt_id, with_tag="blah")
    self.assertEqual(num_results, 0)

    num_results = self.db.CountHuntResults(hunt_obj.hunt_id, with_tag="tag_1")
    self.assertEqual(num_results, 1)

  def testCountHuntResultsCorrectlyAppliesWithTypeFilter(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    sample_results = []
    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          hunt_id=hunt_obj.hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_obj.hunt_id,
          count_per_type=1)
      sample_results.extend(results)
      self._WriteHuntResults(results)

    num_results = self.db.CountHuntResults(
        hunt_obj.hunt_id,
        with_type=compatibility.GetName(rdf_client.ClientInformation))
    self.assertEqual(num_results, 0)

    num_results = self.db.CountHuntResults(
        hunt_obj.hunt_id,
        with_type=compatibility.GetName(rdf_client.ClientSummary))
    self.assertEqual(num_results, 10)

    num_results = self.db.CountHuntResults(
        hunt_obj.hunt_id,
        with_type=compatibility.GetName(rdf_client.ClientCrash))
    self.assertEqual(num_results, 10)

  def testCountHuntResultsCorrectlyAppliesWithTagAndWithTypeFilters(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    sample_results = []
    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          hunt_id=hunt_obj.hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_obj.hunt_id,
          count_per_type=5)
      sample_results.extend(results)
      self._WriteHuntResults(results)

    num_results = self.db.CountHuntResults(
        hunt_obj.hunt_id,
        with_tag="tag_1",
        with_type=compatibility.GetName(rdf_client.ClientSummary))
    self.assertEqual(num_results, 10)

  def testCountHuntResultsCorrectlyAppliesWithTimestampFilter(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    sample_results = []
    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          hunt_id=hunt_obj.hunt_id)
      sample_results = self._SampleSingleTypeHuntResults(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_obj.hunt_id,
          count=10)
      self._WriteHuntResults(sample_results[:5])
      self._WriteHuntResults(sample_results[5:])

    hunt_results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 10)

    for hr in hunt_results:
      self.assertEqual([hr],
                       self.db.ReadHuntResults(
                           hunt_obj.hunt_id, 0, 10,
                           with_timestamp=hr.timestamp))

  def testCountHuntResultsByTypeGroupsResultsCorrectly(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    results = self._SampleTwoTypeHuntResults(
        client_id=client_id,
        flow_id=flow_id,
        hunt_id=hunt_obj.hunt_id,
        count_per_type=5)
    self._WriteHuntResults(results)

    counts = self.db.CountHuntResultsByType(hunt_obj.hunt_id)
    for key in counts:
      self.assertIsInstance(key, text_type)

    self.assertEqual(
        counts, {
            compatibility.GetName(rdf_client.ClientSummary): 5,
            compatibility.GetName(rdf_client.ClientCrash): 5
        })

  def testReadHuntFlowsReturnsEmptyListWhenNoFlows(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    self.assertEmpty(self.db.ReadHuntFlows(hunt_obj.hunt_id, 0, 10))

  def testReadHuntFlowsReturnsAllHuntFlowsWhenNoFilterCondition(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    _, flow_id_1 = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    _, flow_id_2 = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)

    flows = self.db.ReadHuntFlows(hunt_obj.hunt_id, 0, 10)
    self.assertCountEqual([f.flow_id for f in flows], [flow_id_1, flow_id_2])

  def _BuildFilterConditionExpectations(self, hunt_obj):
    _, running_flow_id = self._SetupHuntClientAndFlow(
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING,
        hunt_id=hunt_obj.hunt_id)
    _, succeeded_flow_id = self._SetupHuntClientAndFlow(
        flow_state=rdf_flow_objects.Flow.FlowState.FINISHED,
        hunt_id=hunt_obj.hunt_id)
    _, failed_flow_id = self._SetupHuntClientAndFlow(
        flow_state=rdf_flow_objects.Flow.FlowState.ERROR,
        hunt_id=hunt_obj.hunt_id)
    _, crashed_flow_id = self._SetupHuntClientAndFlow(
        flow_state=rdf_flow_objects.Flow.FlowState.CRASHED,
        hunt_id=hunt_obj.hunt_id)
    client_id, flow_with_results_id = self._SetupHuntClientAndFlow(
        hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(
        client_id=client_id,
        flow_id=flow_with_results_id,
        hunt_id=hunt_obj.hunt_id)
    self._WriteHuntResults(sample_results)

    return {
        db.HuntFlowsCondition.UNSET: [
            running_flow_id, succeeded_flow_id, failed_flow_id, crashed_flow_id,
            flow_with_results_id
        ],
        db.HuntFlowsCondition.FAILED_FLOWS_ONLY: [failed_flow_id],
        db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY: [succeeded_flow_id],
        db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY: [
            failed_flow_id, succeeded_flow_id
        ],
        db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY: [running_flow_id],
        db.HuntFlowsCondition.CRASHED_FLOWS_ONLY: [crashed_flow_id],
    }

  def testReadHuntFlowsAppliesFilterConditionCorrectly(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    expectations = self._BuildFilterConditionExpectations(hunt_obj)
    for filter_condition, expected in expectations.items():
      results = self.db.ReadHuntFlows(
          hunt_obj.hunt_id, 0, 10, filter_condition=filter_condition)
      results_ids = [r.flow_id for r in results]
      self.assertCountEqual(
          results_ids, expected, "Result items do not match for "
          "(filter_condition=%d): %s vs %s" %
          (filter_condition, expected, results_ids))

  def testReadHuntFlowsCorrectlyAppliesOffsetAndCountFilters(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    expectations = self._BuildFilterConditionExpectations(hunt_obj)
    for filter_condition, _ in expectations.items():
      full_results = self.db.ReadHuntFlows(
          hunt_obj.hunt_id, 0, 1024, filter_condition=filter_condition)
      full_results_ids = [r.flow_id for r in full_results]
      for index in range(0, 2):
        for count in range(1, 3):
          results = self.db.ReadHuntFlows(
              hunt_obj.hunt_id, index, count, filter_condition=filter_condition)
          results_ids = [r.flow_id for r in results]
          expected_ids = full_results_ids[index:index + count]
          self.assertCountEqual(
              results_ids, expected_ids, "Result items do not match for "
              "(filter_condition=%d, index=%d, count=%d): %s vs %s" %
              (filter_condition, index, count, expected_ids, results_ids))

  def testReadHuntFlowsIgnoresSubflows(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)
    hunt_id = hunt_obj.hunt_id

    _, flow_id = self._SetupHuntClientAndFlow(
        hunt_id=hunt_id, flow_state=rdf_flow_objects.Flow.FlowState.RUNNING)

    # Whatever state the subflow is in, it should be ignored.
    self._SetupHuntClientAndFlow(
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.ERROR)
    self._SetupHuntClientAndFlow(
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.FINISHED)
    self._SetupHuntClientAndFlow(
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING)

    for state, expceted_results in [
        (db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY, 0),
        (db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY, 0),
        (db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY, 1)
    ]:
      results = self.db.ReadHuntFlows(hunt_id, 0, 10, filter_condition=state)
      self.assertLen(results, expceted_results)

  def testCountHuntFlowsIgnoresSubflows(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)
    hunt_id = hunt_obj.hunt_id

    _, flow_id = self._SetupHuntClientAndFlow(
        hunt_id=hunt_id, flow_state=rdf_flow_objects.Flow.FlowState.RUNNING)

    # Whatever state the subflow is in, it should be ignored.
    self._SetupHuntClientAndFlow(
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.ERROR)
    self._SetupHuntClientAndFlow(
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.FINISHED)
    self._SetupHuntClientAndFlow(
        hunt_id=hunt_id,
        flow_id=flow.RandomFlowId(),
        parent_flow_id=flow_id,
        flow_state=rdf_flow_objects.Flow.FlowState.RUNNING)

    self.assertEqual(self.db.CountHuntFlows(hunt_id), 1)

  def testCountHuntFlowsReturnsEmptyListWhenNoFlows(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    self.assertEqual(self.db.CountHuntFlows(hunt_obj.hunt_id), 0)

  def testCountHuntFlowsReturnsAllHuntFlowsWhenNoFilterCondition(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)

    self.assertEqual(self.db.CountHuntFlows(hunt_obj.hunt_id), 2)

  def testCountHuntFlowsAppliesFilterConditionCorrectly(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    expectations = self._BuildFilterConditionExpectations(hunt_obj)
    for filter_condition, expected in expectations.items():
      result = self.db.CountHuntFlows(
          hunt_obj.hunt_id, filter_condition=filter_condition)
      self.assertEqual(
          result, len(expected), "Result count does not match for "
          "(filter_condition=%d): %d vs %d" %
          (filter_condition, len(expected), result))

  def testReadHuntCountersCorrectlyAggregatesResultsAmongDifferentFlows(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    expectations = self._BuildFilterConditionExpectations(hunt_obj)

    hunt_counters = self.db.ReadHuntCounters(hunt_obj.hunt_id)
    self.assertEqual(hunt_counters.num_clients,
                     len(expectations[db.HuntFlowsCondition.UNSET]))
    self.assertEqual(
        hunt_counters.num_successful_clients,
        len(expectations[db.HuntFlowsCondition.SUCCEEDED_FLOWS_ONLY]))
    self.assertEqual(hunt_counters.num_failed_clients,
                     len(expectations[db.HuntFlowsCondition.FAILED_FLOWS_ONLY]))

    # _BuildFilterConditionExpectations writes 10 sample results for one client.
    self.assertEqual(hunt_counters.num_clients_with_results, 1)
    self.assertEqual(
        hunt_counters.num_crashed_clients,
        len(expectations[db.HuntFlowsCondition.CRASHED_FLOWS_ONLY]))

    # _BuildFilterConditionExpectations writes 10 sample results.
    self.assertEqual(hunt_counters.num_results, 10)

    self.assertEqual(hunt_counters.total_cpu_seconds, 0)
    self.assertEqual(hunt_counters.total_network_bytes_sent, 0)

    # Check that after adding a flow with resource metrics, total counters
    # get updated.
    self._SetupHuntClientAndFlow(
        flow_state=rdf_flow_objects.Flow.FlowState.FINISHED,
        cpu_time_used=rdf_client_stats.CpuSeconds(
            user_cpu_time=4.5, system_cpu_time=10),
        network_bytes_sent=42,
        hunt_id=hunt_obj.hunt_id)
    hunt_counters = self.db.ReadHuntCounters(hunt_obj.hunt_id)
    self.assertAlmostEqual(hunt_counters.total_cpu_seconds, 14.5)
    self.assertEqual(hunt_counters.total_network_bytes_sent, 42)

  def testReadHuntClientResourcesStatsCorrectlyAggregatesData(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    flow_data = []
    expected_user_cpu_histogram = rdf_stats.StatsHistogram.FromBins(
        rdf_stats.ClientResourcesStats.CPU_STATS_BINS)
    expected_system_cpu_histogram = rdf_stats.StatsHistogram.FromBins(
        rdf_stats.ClientResourcesStats.CPU_STATS_BINS)
    expected_network_histogram = rdf_stats.StatsHistogram.FromBins(
        rdf_stats.ClientResourcesStats.NETWORK_STATS_BINS)
    for i in range(10):
      user_cpu_time = 4.5 + i
      system_cpu_time = 10 + i * 2
      network_bytes_sent = 42 + i * 3

      client_id, flow_id = self._SetupHuntClientAndFlow(
          flow_state=rdf_flow_objects.Flow.FlowState.FINISHED,
          cpu_time_used=rdf_client_stats.CpuSeconds(
              user_cpu_time=user_cpu_time, system_cpu_time=system_cpu_time),
          network_bytes_sent=network_bytes_sent,
          hunt_id=hunt_obj.hunt_id)

      expected_user_cpu_histogram.RegisterValue(user_cpu_time)
      expected_system_cpu_histogram.RegisterValue(system_cpu_time)
      expected_network_histogram.RegisterValue(network_bytes_sent)

      flow_data.append((client_id, flow_id, (user_cpu_time, system_cpu_time,
                                             network_bytes_sent)))

    usage_stats = self.db.ReadHuntClientResourcesStats(hunt_obj.hunt_id)

    self.assertEqual(usage_stats.user_cpu_stats.num, 10)
    self.assertAlmostEqual(usage_stats.user_cpu_stats.mean, 9)
    self.assertAlmostEqual(usage_stats.user_cpu_stats.std, 2.8722813232690143)
    self.assertLen(usage_stats.user_cpu_stats.histogram.bins,
                   len(expected_user_cpu_histogram.bins))
    for b, model_b in zip(usage_stats.user_cpu_stats.histogram.bins,
                          expected_user_cpu_histogram.bins):
      self.assertAlmostEqual(b.range_max_value, model_b.range_max_value)
      self.assertEqual(b.num, model_b.num)

    self.assertEqual(usage_stats.system_cpu_stats.num, 10)
    self.assertAlmostEqual(usage_stats.system_cpu_stats.mean, 19)
    self.assertAlmostEqual(usage_stats.system_cpu_stats.std, 5.744562646538029)
    self.assertLen(usage_stats.system_cpu_stats.histogram.bins,
                   len(expected_system_cpu_histogram.bins))
    for b, model_b in zip(usage_stats.system_cpu_stats.histogram.bins,
                          expected_system_cpu_histogram.bins):
      self.assertAlmostEqual(b.range_max_value, model_b.range_max_value)
      self.assertEqual(b.num, model_b.num)

    self.assertEqual(usage_stats.network_bytes_sent_stats.num, 10)
    self.assertAlmostEqual(usage_stats.network_bytes_sent_stats.mean, 55.5)
    self.assertAlmostEqual(usage_stats.network_bytes_sent_stats.std,
                           8.616843969807043)
    self.assertLen(usage_stats.network_bytes_sent_stats.histogram.bins,
                   len(expected_network_histogram.bins))
    for b, model_b in zip(usage_stats.network_bytes_sent_stats.histogram.bins,
                          expected_network_histogram.bins):
      self.assertAlmostEqual(b.range_max_value, model_b.range_max_value)
      self.assertEqual(b.num, model_b.num)

    self.assertLen(usage_stats.worst_performers, 10)
    for worst_performer, flow_d in zip(usage_stats.worst_performers,
                                       reversed(flow_data)):
      client_id, flow_id, (user_cpu_time, system_cpu_time,
                           network_bytes_sent) = flow_d
      self.assertEqual(worst_performer.client_id.Basename(), client_id)
      self.assertAlmostEqual(worst_performer.cpu_usage.user_cpu_time,
                             user_cpu_time)
      self.assertAlmostEqual(worst_performer.cpu_usage.system_cpu_time,
                             system_cpu_time)
      self.assertEqual(worst_performer.network_bytes_sent, network_bytes_sent)
      self.assertEqual(worst_performer.session_id.Path(),
                       "/%s/%s" % (client_id, flow_id))

  def testReadHuntOutputPluginLogEntriesReturnsEntryFromSingleHuntFlow(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    output_plugin_id = "1"
    client_id, flow_id = self._SetupHuntClientAndFlow(
        client_id="C.12345678901234aa", hunt_id=hunt_obj.hunt_id)
    self.db.WriteFlowOutputPluginLogEntries([
        rdf_flow_objects.FlowOutputPluginLogEntry(
            client_id=client_id,
            flow_id=flow_id,
            output_plugin_id=output_plugin_id,
            hunt_id=hunt_obj.hunt_id,
            message="blah")
    ])

    hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_obj.hunt_id, output_plugin_id, 0, 10)
    self.assertLen(hunt_op_log_entries, 1)
    self.assertIsInstance(hunt_op_log_entries[0],
                          rdf_flow_objects.FlowOutputPluginLogEntry)
    self.assertEqual(hunt_op_log_entries[0].hunt_id, hunt_obj.hunt_id)
    self.assertEqual(hunt_op_log_entries[0].client_id, client_id)
    self.assertEqual(hunt_op_log_entries[0].flow_id, flow_id)
    self.assertEqual(hunt_op_log_entries[0].message, "blah")

  def _WriteHuntOutputPluginLogEntries(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)

    output_plugin_id = "1"
    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          client_id="C.12345678901234a%d" % i, hunt_id=hunt_obj.hunt_id)
      enum = rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType
      if i % 3 == 0:
        log_entry_type = enum.ERROR
      else:
        log_entry_type = enum.LOG
      self.db.WriteFlowOutputPluginLogEntries([
          rdf_flow_objects.FlowOutputPluginLogEntry(
              client_id=client_id,
              flow_id=flow_id,
              hunt_id=hunt_obj.hunt_id,
              output_plugin_id=output_plugin_id,
              log_entry_type=log_entry_type,
              message="blah%d" % i)
      ])

    return hunt_obj

  def testReadHuntOutputPluginLogEntriesReturnsEntryFromMultipleHuntFlows(self):
    hunt_obj = self._WriteHuntOutputPluginLogEntries()

    hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_obj.hunt_id, "1", 0, 100)
    self.assertLen(hunt_op_log_entries, 10)
    # Make sure messages are returned in timestamps-ascending order.
    for i, e in enumerate(hunt_op_log_entries):
      self.assertEqual(e.message, "blah%d" % i)

  def testReadHuntOutputPluginLogEntriesCorrectlyAppliesOffsetAndCountFilters(
      self):
    hunt_obj = self._WriteHuntOutputPluginLogEntries()

    for i in range(10):
      hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
          hunt_obj.hunt_id, "1", i, 1)
      self.assertLen(hunt_op_log_entries, 1)
      self.assertEqual(hunt_op_log_entries[0].message, "blah%d" % i)

  def testReadHuntOutputPluginLogEntriesCorrectlyAppliesWithTypeFilter(self):
    hunt_obj = self._WriteHuntOutputPluginLogEntries()

    hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_obj.hunt_id,
        "1",
        0,
        100,
        with_type=rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.UNSET)
    self.assertEmpty(hunt_op_log_entries)

    hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_obj.hunt_id,
        "1",
        0,
        100,
        with_type=rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.ERROR)
    self.assertLen(hunt_op_log_entries, 4)

    hunt_op_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_obj.hunt_id,
        "1",
        0,
        100,
        with_type=rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.LOG)
    self.assertLen(hunt_op_log_entries, 6)

  def testReadHuntOutputPluginLogEntriesCorrectlyAppliesCombinationOfFilters(
      self):
    hunt_obj = self._WriteHuntOutputPluginLogEntries()

    hunt_log_entries = self.db.ReadHuntOutputPluginLogEntries(
        hunt_obj.hunt_id,
        "1",
        0,
        1,
        with_type=rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.LOG)
    self.assertLen(hunt_log_entries, 1)
    self.assertEqual(hunt_log_entries[0].message, "blah1")

  def testCountHuntOutputPluginLogEntriesReturnsCorrectCount(self):
    hunt_obj = self._WriteHuntOutputPluginLogEntries()

    num_entries = self.db.CountHuntOutputPluginLogEntries(hunt_obj.hunt_id, "1")
    self.assertEqual(num_entries, 10)

  def testCountHuntOutputPluginLogEntriesRespectsWithTypeFilter(self):
    hunt_obj = self._WriteHuntOutputPluginLogEntries()

    num_entries = self.db.CountHuntOutputPluginLogEntries(
        hunt_obj.hunt_id,
        "1",
        with_type=rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.LOG)
    self.assertEqual(num_entries, 6)

    num_entries = self.db.CountHuntOutputPluginLogEntries(
        hunt_obj.hunt_id,
        "1",
        with_type=rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.ERROR)
    self.assertEqual(num_entries, 4)

  def testFlowStateUpdateUsingUpdateFlow(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)
    hunt_id = hunt_obj.hunt_id

    client_id, flow_id = self._SetupHuntClientAndFlow(
        hunt_id=hunt_id, flow_state=rdf_flow_objects.Flow.FlowState.RUNNING)

    results = self.db.ReadHuntFlows(
        hunt_id,
        0,
        10,
        filter_condition=db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY)
    self.assertLen(results, 1)

    results = self.db.ReadHuntFlows(
        hunt_id,
        0,
        10,
        filter_condition=db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY)
    self.assertEmpty(results)

    rdf_flow = self.db.ReadFlowObject(client_id, flow_id)
    rdf_flow.flow_state = rdf_flow_objects.Flow.FlowState.FINISHED
    self.db.UpdateFlow(client_id, rdf_flow.flow_id, flow_obj=rdf_flow)

    results = self.db.ReadHuntFlows(
        hunt_id,
        0,
        10,
        filter_condition=db.HuntFlowsCondition.FLOWS_IN_PROGRESS_ONLY)
    self.assertEmpty(results)

    results = self.db.ReadHuntFlows(
        hunt_id,
        0,
        10,
        filter_condition=db.HuntFlowsCondition.COMPLETED_FLOWS_ONLY)
    self.assertLen(results, 1)

  def testFlowStateUpdateUsingReturnProcessedFlow(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)
    hunt_id = hunt_obj.hunt_id

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_id)

    flow_obj = self.db.ReadFlowForProcessing(client_id, flow_id,
                                             rdfvalue.Duration("1m"))
    self.assertEqual(flow_obj.flow_state, rdf_flow_objects.Flow.FlowState.UNSET)

    flow_obj.flow_state = rdf_flow_objects.Flow.FlowState.ERROR
    self.db.ReturnProcessedFlow(flow_obj)

    results = self.db.ReadHuntFlows(
        hunt_id,
        0,
        10,
        filter_condition=db.HuntFlowsCondition.FAILED_FLOWS_ONLY)
    self.assertLen(results, 1)
