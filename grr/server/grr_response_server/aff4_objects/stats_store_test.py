#!/usr/bin/env python
"""Tests for AFF4 stats_store classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future.utils import iterkeys

from grr_response_core.lib import flags
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_test_utils
from grr_response_core.stats import stats_utils
from grr_response_server import aff4
from grr_response_server.aff4_objects import stats_store
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib


class StatsStoreTest(aff4_test_lib.AFF4ObjectTest):

  def setUp(self):
    super(StatsStoreTest, self).setUp()

    self.process_id = "some_pid"
    self.stats_store = aff4.FACTORY.Create(
        None, stats_store.StatsStore, mode="w", token=self.token)
    fake_stats_collector = default_stats_collector.DefaultStatsCollector([
        stats_utils.CreateCounterMetadata("counter"),
        stats_utils.CreateCounterMetadata(
            "counter_with_fields", fields=[("source", str)]),
        stats_utils.CreateEventMetadata("events"),
        stats_utils.CreateEventMetadata(
            "events_with_fields", fields=[("source", str)]),
        stats_utils.CreateGaugeMetadata("int_gauge", int),
        stats_utils.CreateGaugeMetadata("str_gauge", str),
        stats_utils.CreateGaugeMetadata(
            "str_gauge_with_fields", str, fields=[("task", int)])
    ])
    fake_stats_context = stats_test_utils.FakeStatsContext(fake_stats_collector)
    fake_stats_context.start()
    self.addCleanup(fake_stats_context.stop)

  def testValuesAreFetchedCorrectly(self):
    stats_collector_instance.Get().SetGaugeValue("int_gauge", 4242)

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42)

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=43)

    stats_history = self.stats_store.ReadStats(
        process_id=self.process_id, timestamp=self.stats_store.ALL_TIMESTAMPS)
    self.assertEqual(stats_history["counter"], [(1, 42), (2, 43)])
    self.assertEqual(stats_history["int_gauge"], [(4242, 42), (4242, 43)])

  def testFetchedValuesCanBeLimitedByTimeRange(self):
    stats_collector_instance.Get().SetGaugeValue("int_gauge", 4242)

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42)

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=43)

    stats_history = self.stats_store.ReadStats(
        process_id=self.process_id, timestamp=(0, 42))
    self.assertEqual(stats_history["counter"], [(1, 42)])
    self.assertEqual(stats_history["int_gauge"], [(4242, 42)])

  def testFetchedValuesCanBeLimitedByName(self):
    stats_collector_instance.Get().SetGaugeValue("int_gauge", 4242)

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42)

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=43)

    stats_history = self.stats_store.ReadStats(
        process_id=self.process_id, metric_name="counter")
    self.assertEqual(stats_history["counter"], [(1, 42), (2, 43)])
    self.assertNotIn("int_gauge", stats_history)

  def testDeleteStatsInTimeRangeWorksCorrectly(self):
    stats_collector_instance.Get().SetGaugeValue("int_gauge", 4242)

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42)

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=44)

    self.stats_store.DeleteStats(process_id=self.process_id, timestamp=(0, 43))

    stats_history = self.stats_store.ReadStats(process_id=self.process_id)
    self.assertEqual(stats_history["counter"], [(2, 44)])
    self.assertEqual(stats_history["int_gauge"], [(4242, 44)])

  def testDeleteStatsInTimeRangeWorksCorrectlyWithFields(self):
    stats_collector_instance.Get().IncrementCounter(
        "counter_with_fields", fields=["http"])
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42)

    stats_collector_instance.Get().IncrementCounter(
        "counter_with_fields", fields=["http"])
    stats_collector_instance.Get().IncrementCounter(
        "counter_with_fields", fields=["rpc"])
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=44)

    self.stats_store.DeleteStats(process_id=self.process_id, timestamp=(0, 43))

    stats_history = self.stats_store.ReadStats(process_id=self.process_id)

    self.assertEqual(stats_history["counter_with_fields"]["http"], [(2, 44)])
    self.assertEqual(stats_history["counter_with_fields"]["rpc"], [(1, 44)])

  def testReturnsListOfAllUsedProcessIds(self):
    self.stats_store.WriteStats(process_id="pid1")
    self.stats_store.WriteStats(process_id="pid2")

    self.assertEqual(
        sorted(self.stats_store.ListUsedProcessIds()), ["pid1", "pid2"])

  def testMultiReadStatsWorksCorrectly(self):
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id="pid1", timestamp=42)
    self.stats_store.WriteStats(process_id="pid2", timestamp=42)
    self.stats_store.WriteStats(process_id="pid2", timestamp=43)

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id="pid1", timestamp=43)

    results = self.stats_store.MultiReadStats()
    self.assertEqual(sorted(iterkeys(results)), ["pid1", "pid2"])
    self.assertEqual(results["pid1"]["counter"], [(1, 42), (2, 43)])
    self.assertEqual(results["pid2"]["counter"], [(1, 42), (1, 43)])

  def testMultiReadStatsLimitsResultsByTimeRange(self):
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id="pid1", timestamp=42)
    self.stats_store.WriteStats(process_id="pid2", timestamp=42)
    self.stats_store.WriteStats(process_id="pid2", timestamp=44)

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(process_id="pid1", timestamp=44)

    results = self.stats_store.MultiReadStats(timestamp=(43, 100))
    self.assertEqual(sorted(iterkeys(results)), ["pid1", "pid2"])
    self.assertEqual(results["pid1"]["counter"], [(2, 44)])
    self.assertEqual(results["pid2"]["counter"], [(1, 44)])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
