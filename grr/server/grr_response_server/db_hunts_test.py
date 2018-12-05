#!/usr/bin/env python
"""Tests for the hunt database api."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
import sys

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.util import compatibility
from grr_response_server import db
from grr_response_server import flow
from grr_response_server import hunt
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import objects as rdf_objects


class DatabaseTestHuntMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of hunts.
  """

  def _SetupHuntClientAndFlow(self,
                              client_id=None,
                              hunt_id=None,
                              **additional_flow_args):
    client_id = self.InitializeClient(client_id=client_id)
    flow_id = flow.RandomFlowId()
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
    hunt_obj = rdf_hunt_objects.Hunt(hunt_id=hunt.RandomHuntId())
    self.db.WriteHuntObject(hunt_obj)

    read_hunt_obj = self.db.ReadHuntObject(hunt_obj.hunt_id)
    # Last update time is set automatically when the object is written.
    # Setting it on hunt_obj to make sure it doesn't influence the equality
    # check.
    hunt_obj.last_update_time = read_hunt_obj.last_update_time
    self.assertEqual(hunt_obj, read_hunt_obj)

  def testHuntObjectCanBeOverwritten(self):
    hunt_id = hunt.RandomHuntId()

    hunt_obj = rdf_hunt_objects.Hunt(hunt_id=hunt_id, description="foo")
    self.db.WriteHuntObject(hunt_obj)

    read_hunt_obj = self.db.ReadHuntObject(hunt_obj.hunt_id)
    self.assertEqual(read_hunt_obj.description, "foo")

    hunt_obj = rdf_hunt_objects.Hunt(hunt_id=hunt_id, description="bar")
    self.db.WriteHuntObject(hunt_obj)

    read_hunt_obj = self.db.ReadHuntObject(hunt_obj.hunt_id)
    self.assertEqual(read_hunt_obj.description, "bar")

  def testReadingNonExistentHuntObjectRaises(self):
    with self.assertRaises(db.UnknownHuntError):
      self.db.ReadHuntObject(hunt.RandomHuntId())

  def testReadAllHuntObjectsReturnsEmptyListWhenNoHunts(self):
    self.assertEqual(self.db.ReadAllHuntObjects(), [])

  def testReadAllHuntObjectsReturnsAllWrittenObjects(self):
    hunt_obj_1 = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj_1)

    hunt_obj_2 = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="bar")
    self.db.WriteHuntObject(hunt_obj_2)

    read_hunt_objs = self.db.ReadAllHuntObjects()
    self.assertLen(read_hunt_objs, 2)
    self.assertCountEqual(["foo", "bar"],
                          [h.description for h in read_hunt_objs])

  def testReadHuntLogEntriesReturnsEntryFromSingleHuntFlow(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(
        client_id="C.12345678901234AA", hunt_id=hunt_obj.hunt_id)
    self.db.WriteFlowLogEntries(client_id, flow_id,
                                [rdf_flow_objects.FlowLogEntry(message="blah")])

    hunt_log_entries = self.db.ReadHuntLogEntries(hunt_obj.hunt_id, 0, 10)
    self.assertLen(hunt_log_entries, 1)
    self.assertIsInstance(hunt_log_entries[0], rdf_flow_objects.FlowLogEntry)
    self.assertEqual(hunt_log_entries[0].hunt_id, hunt_obj.hunt_id)
    self.assertEqual(hunt_log_entries[0].client_id, client_id)
    self.assertEqual(hunt_log_entries[0].flow_id, flow_id)
    self.assertEqual(hunt_log_entries[0].message, "blah")

  def _WriteHuntLogEntries(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          client_id="C.12345678901234A%d" % i, hunt_id=hunt_obj.hunt_id)
      self.db.WriteFlowLogEntries(
          client_id, flow_id,
          [rdf_flow_objects.FlowLogEntry(message="blah%d" % i)])

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
    for (client_id, flow_id), results in sample_results.items():
      self._WriteFlowResults(
          client_id,
          flow_id,
          multiple_timestamps=True,
          sample_results=results,
      )

  def _SampleSingleTypeHuntResults(self, client_id=None, count=10):
    client_id = client_id or "C.1234567890123456"
    return [
        rdf_flow_objects.FlowResult(
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
                                count_per_type=5,
                                timestamp_start=10):
    client_id = client_id or "C.1234567890123456"
    return [
        rdf_flow_objects.FlowResult(
            tag="tag_%d" % i,
            payload=rdf_client.ClientSummary(
                client_id=client_id,
                system_manufacturer="manufacturer_%d" % i,
                install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                    timestamp_start + i))) for i in range(count_per_type)
    ] + [
        rdf_flow_objects.FlowResult(
            tag="tag_%d" % i,
            payload=rdf_client.ClientCrash(
                client_id=client_id,
                timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                    timestamp_start + i))) for i in range(count_per_type)
    ]

  def testReadHuntResultsReadsSingleResultOfSingleType(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(count=1)
    self._WriteHuntResults({(client_id, flow_id): sample_results})

    results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 10)
    self.assertLen(results, 1)
    self.assertEqual(results[0].hunt_id, hunt_obj.hunt_id)
    self.assertEqual(results[0].payload, sample_results[0].payload)

  def testReadHuntResultsReadsMultipleResultOfSingleType(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults(count=10)
    self._WriteHuntResults({(client_id, flow_id): sample_results})

    results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 1000)
    self.assertLen(results, 10)
    for i in range(10):
      self.assertEqual(results[i].hunt_id, hunt_obj.hunt_id)
      self.assertEqual(results[i].payload, sample_results[i].payload)

  def testReadHuntResultsReadsMultipleResultOfMultipleTypes(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id_1, flow_id_1 = self._SetupHuntClientAndFlow(
        hunt_id=hunt_obj.hunt_id)
    sample_results_1 = self._SampleTwoTypeHuntResults(client_id=client_id_1)
    self._WriteHuntResults({(client_id_1, flow_id_1): sample_results_1})

    client_id_2, flow_id_2 = self._SetupHuntClientAndFlow(
        hunt_id=hunt_obj.hunt_id)
    sample_results_2 = self._SampleTwoTypeHuntResults(client_id=client_id_1)
    self._WriteHuntResults({(client_id_2, flow_id_2): sample_results_2})

    sample_results = sample_results_1 + sample_results_2
    results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 1000)
    self.assertLen(results, len(sample_results))
    self.assertEqual([i.payload for i in results],
                     [i.payload for i in sample_results])

  def testReadHuntResultsCorrectlyAppliedOffsetAndCountFilters(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    sample_results = []
    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          hunt_id=hunt_obj.hunt_id)
      results = self._SampleSingleTypeHuntResults(client_id=client_id, count=1)
      sample_results.extend(results)
      self._WriteHuntResults({(client_id, flow_id): results})

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
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults()
    self._WriteHuntResults({(client_id, flow_id): sample_results})

    results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 100, with_tag="blah")
    self.assertFalse(results)

    results = self.db.ReadHuntResults(hunt_obj.hunt_id, 0, 100, with_tag="tag")
    self.assertFalse(results)

    results = self.db.ReadHuntResults(
        hunt_obj.hunt_id, 0, 100, with_tag="tag_1")
    self.assertEqual([i.payload for i in results],
                     [i.payload for i in sample_results if i.tag == "tag_1"])

  def testReadHuntResultsCorrectlyAppliesWithTypeFilter(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    sample_results = []
    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          hunt_id=hunt_obj.hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id, count_per_type=1)
      sample_results.extend(results)
      self._WriteHuntResults({(client_id, flow_id): results})

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
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults()
    self._WriteHuntResults({(client_id, flow_id): sample_results})

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
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    sample_results = []
    for i in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          hunt_id=hunt_obj.hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id, count_per_type=5)
      sample_results.extend(results)
      self._WriteHuntResults({(client_id, flow_id): results})

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
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults()
    self._WriteHuntResults({(client_id, flow_id): sample_results})

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
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults()
    self._WriteHuntResults({(client_id, flow_id): sample_results})

    num_results = self.db.CountHuntResults(hunt_obj.hunt_id)
    self.assertEqual(num_results, len(sample_results))

  def testCountHuntResultsCorrectlyAppliesWithTagFilter(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    client_id, flow_id = self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults()
    self._WriteHuntResults({(client_id, flow_id): sample_results})

    num_results = self.db.CountHuntResults(hunt_obj.hunt_id, with_tag="blah")
    self.assertEqual(num_results, 0)

    num_results = self.db.CountHuntResults(hunt_obj.hunt_id, with_tag="tag_1")
    self.assertEqual(num_results, 1)

  def testCountHuntResultsCorrectlyAppliesWithTypeFilter(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    sample_results = []
    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          hunt_id=hunt_obj.hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id, count_per_type=1)
      sample_results.extend(results)
      self._WriteHuntResults({(client_id, flow_id): results})

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
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    sample_results = []
    for _ in range(10):
      client_id, flow_id = self._SetupHuntClientAndFlow(
          hunt_id=hunt_obj.hunt_id)
      results = self._SampleTwoTypeHuntResults(
          client_id=client_id, count_per_type=5)
      sample_results.extend(results)
      self._WriteHuntResults({(client_id, flow_id): results})

    num_results = self.db.CountHuntResults(
        hunt_obj.hunt_id,
        with_tag="tag_1",
        with_type=compatibility.GetName(rdf_client.ClientSummary))
    self.assertEqual(num_results, 10)

  def testReadHuntFlowsReturnsEmptyListWhenNoFlows(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    self.assertEmpty(self.db.ReadHuntFlows(hunt_obj.hunt_id, 0, 10))

  def testReadHuntFlowsReturnsAllHuntFlowsWhenNoFilterCondition(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
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
        client_crash_info=rdf_client.ClientCrash(), hunt_id=hunt_obj.hunt_id)
    client_id, flow_with_results_id = self._SetupHuntClientAndFlow(
        hunt_id=hunt_obj.hunt_id)
    sample_results = self._SampleSingleTypeHuntResults()
    self._WriteHuntResults({(client_id, flow_with_results_id): sample_results})

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
        db.HuntFlowsCondition.FLOWS_WITH_RESULTS_ONLY: [flow_with_results_id],
    }

  def testReadHuntFlowsAppliesFilterConditionCorrectly(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    expectations = self._BuildFilterConditionExpectations(hunt_obj)
    for filter_condition, expected in expectations.items():
      results = self.db.ReadHuntFlows(
          hunt_obj.hunt_id, 0, 10, filter_condition=filter_condition)
      results_ids = [r.flow_id for r in results]
      self.assertCountEqual(
          results_ids, expected, "Result items do not match for "
          "(filter_condition=%d): %s vs %s" % (filter_condition, expected,
                                               results_ids))

  def testReadHuntFlowsCorrectlyAppliesOffsetAndCountFilters(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    expectations = self._BuildFilterConditionExpectations(hunt_obj)
    for filter_condition, _ in expectations.items():
      full_results = self.db.ReadHuntFlows(
          hunt_obj.hunt_id, 0, sys.maxsize, filter_condition=filter_condition)
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

  def testCountHuntFlowsReturnsEmptyListWhenNoFlows(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    self.assertEqual(self.db.CountHuntFlows(hunt_obj.hunt_id), 0)

  def testCountHuntFlowsReturnsAllHuntFlowsWhenNoFilterCondition(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)
    self._SetupHuntClientAndFlow(hunt_id=hunt_obj.hunt_id)

    self.assertEqual(self.db.CountHuntFlows(hunt_obj.hunt_id), 2)

  def testCountHuntFlowsAppliesFilterConditionCorrectly(self):
    hunt_obj = rdf_hunt_objects.Hunt(
        hunt_id=hunt.RandomHuntId(), description="foo")
    self.db.WriteHuntObject(hunt_obj)

    expectations = self._BuildFilterConditionExpectations(hunt_obj)
    for filter_condition, expected in expectations.items():
      result = self.db.CountHuntFlows(
          hunt_obj.hunt_id, filter_condition=filter_condition)
      self.assertEqual(
          result, len(expected), "Result count does not match for "
          "(filter_condition=%d): %d vs %d" % (filter_condition, len(expected),
                                               result))
