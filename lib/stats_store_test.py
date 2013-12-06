#!/usr/bin/env python
"""Tests for the stats_store classes."""



# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import data_store
from grr.lib import flags
from grr.lib import stats
from grr.lib import stats_store
from grr.lib import test_lib


class StatsStoreTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(StatsStoreTest, self).setUp()
    self.process_id = "some_pid"
    self.stats_store = stats_store.StatsStore(token=self.token)

  def testCountersAreWrittenToDataStore(self):
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.IncrementCounter("counter")

    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42,
                                sync=True)

    row = data_store.DB.ResolveRegex("aff4:/stats_store/some_pid", ".*",
                                     token=self.token)
    counter = [x for x in row if x[0] == "aff4:stats_store/counter"]
    self.assertTrue(counter)
    self.assertEqual(counter[0], ("aff4:stats_store/counter", 1, 42))

  def testStringGaugeValuesAreWrittenToDataStore(self):
    stats.STATS.RegisterGaugeMetric("str_gauge", str)
    stats.STATS.SetGaugeValue("str_gauge", "some_value")

    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42,
                                sync=True)

    row = data_store.DB.ResolveRegex("aff4:/stats_store/some_pid", ".*",
                                     token=self.token)
    counter = [x for x in row if x[0] == "aff4:stats_store/str_gauge"]
    self.assertTrue(counter)
    self.assertEqual(counter[0],
                     ("aff4:stats_store/str_gauge", "some_value", 42))

  def testIntGaugeValuesAreWrittenToDataStore(self):
    stats.STATS.RegisterGaugeMetric("int_gauge", int)
    stats.STATS.SetGaugeValue("int_gauge", 4242)

    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42,
                                sync=True)

    row = data_store.DB.ResolveRegex("aff4:/stats_store/some_pid", ".*",
                                     token=self.token)
    counter = [x for x in row if x[0] == "aff4:stats_store/int_gauge"]
    self.assertTrue(counter)
    self.assertEqual(counter[0], ("aff4:stats_store/int_gauge", 4242, 42))

  def testLaterValuesDoNotOverridePrevious(self):
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42,
                                sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=43,
                                sync=True)

    row = data_store.DB.ResolveRegex("aff4:/stats_store/some_pid", ".*",
                                     token=self.token)
    counters = [x for x in row if x[0] == "aff4:stats_store/counter"]
    self.assertEqual(len(counters), 2)
    counters = sorted(counters, key=lambda x: x[2])
    self.assertEqual(counters[0], ("aff4:stats_store/counter", 1, 42))
    self.assertEqual(counters[1], ("aff4:stats_store/counter", 2, 43))

  def testValuesAreFetchedCorrectly(self):
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.RegisterGaugeMetric("int_gauge", int)
    stats.STATS.SetGaugeValue("int_gauge", 4242)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42,
                                sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=43,
                                sync=True)

    stats_history = self.stats_store.ReadStats(
        process_id=self.process_id,
        timestamp=self.stats_store.ALL_TIMESTAMPS)
    self.assertEqual(stats_history["counter"], [(1, 42), (2, 43)])
    self.assertEqual(stats_history["int_gauge"], [(4242, 42), (4242, 43)])

  def testFetchedValuesCanBeLimitedByTimeRange(self):
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.RegisterGaugeMetric("int_gauge", int)
    stats.STATS.SetGaugeValue("int_gauge", 4242)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42,
                                sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=43,
                                sync=True)

    stats_history = self.stats_store.ReadStats(process_id=self.process_id,
                                               timestamp=(0, 42))
    self.assertEqual(stats_history["counter"], [(1, 42)])
    self.assertEqual(stats_history["int_gauge"], [(4242, 42)])

  def testFetchedValuesCanBeLimitedByName(self):
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.RegisterGaugeMetric("int_gauge", int)
    stats.STATS.SetGaugeValue("int_gauge", 4242)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42,
                                sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=43,
                                sync=True)

    stats_history = self.stats_store.ReadStats(process_id=self.process_id,
                                               predicate_regex="counter")
    self.assertEqual(stats_history["counter"], [(1, 42), (2, 43)])
    self.assertTrue("int_gauge" not in stats_history)

  def testDeleteStatsInTimeRangeWorksCorrectly(self):
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.RegisterGaugeMetric("int_gauge", int)
    stats.STATS.SetGaugeValue("int_gauge", 4242)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42,
                                sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=44,
                                sync=True)

    self.stats_store.DeleteStats(process_id=self.process_id, timestamp=(0, 43),
                                 sync=True)

    stats_history = self.stats_store.ReadStats(process_id=self.process_id)
    self.assertEqual(stats_history["counter"], [(2, 44)])
    self.assertEqual(stats_history["int_gauge"], [(4242, 44)])

  def testReturnsListOfAllUsedProcessIds(self):
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.RegisterGaugeMetric("int_gauge", int)

    self.stats_store.WriteStats(process_id="pid1", sync=True)
    self.stats_store.WriteStats(process_id="pid2", sync=True)

    self.assertEqual(sorted(self.stats_store.ListUsedProcessIds()),
                     ["pid1", "pid2"])

  def testMultiReadStatsWorksCorrectly(self):
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id="pid1", timestamp=42, sync=True)
    self.stats_store.WriteStats(process_id="pid2", timestamp=42, sync=True)
    self.stats_store.WriteStats(process_id="pid2", timestamp=43, sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id="pid1", timestamp=43, sync=True)

    results = self.stats_store.MultiReadStats()
    self.assertEqual(sorted(results.keys()), ["pid1", "pid2"])
    self.assertEqual(results["pid1"]["counter"], [(1, 42), (2, 43)])
    self.assertEqual(results["pid2"]["counter"], [(1, 42), (1, 43)])

  def testMultiReadStatsLimitsResultsByTimeRange(self):
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id="pid1", timestamp=42, sync=True)
    self.stats_store.WriteStats(process_id="pid2", timestamp=42, sync=True)
    self.stats_store.WriteStats(process_id="pid2", timestamp=44, sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id="pid1", timestamp=44, sync=True)

    results = self.stats_store.MultiReadStats(
        timestamp=(43, 100))
    self.assertEqual(sorted(results.keys()), ["pid1", "pid2"])
    self.assertEqual(results["pid1"]["counter"], [(2, 44)])
    self.assertEqual(results["pid2"]["counter"], [(1, 44)])

  def testRemoveEmptyProcessIds(self):
    stats.STATS.RegisterCounterMetric("counter")
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42,
                                sync=True)
    self.stats_store.DeleteStats(process_id=self.process_id, sync=True)
    self.stats_store.RemoveEmptyProcessIds()
    self.assertEqual(self.stats_store.ListUsedProcessIds(), [])


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
