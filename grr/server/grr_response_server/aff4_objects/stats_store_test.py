#!/usr/bin/env python
"""Tests for the stats_store classes."""
from __future__ import absolute_import
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iterkeys

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_test_utils
from grr_response_core.stats import stats_utils
from grr_response_server import aff4
from grr_response_server import timeseries
from grr_response_server.aff4_objects import stats_store
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib


def _CreateFakeStatsCollector():
  """Returns a stats-collector for use by tests in this file."""
  return default_stats_collector.DefaultStatsCollector([
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


class StatsStoreTest(aff4_test_lib.AFF4ObjectTest):

  def setUp(self):
    super(StatsStoreTest, self).setUp()

    self.process_id = "some_pid"
    self.stats_store = aff4.FACTORY.Create(
        None, stats_store.StatsStore, mode="w", token=self.token)
    fake_stats_context = stats_test_utils.FakeStatsContext(
        _CreateFakeStatsCollector())
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
    self.assertTrue("int_gauge" not in stats_history)

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

  def testReadMetadataReturnsAllUsedMetadata(self):
    # Check that there are no metadata for registered metrics.
    metadata = self.stats_store.ReadMetadata(
        process_id=self.process_id).AsDict()
    self.assertFalse("counter" in metadata)
    self.assertFalse("counter_with_fields" in metadata)
    self.assertFalse("events" in metadata)
    self.assertFalse("events_with_fields" in metadata)
    self.assertFalse("str_gauge" in metadata)
    self.assertFalse("str_gauge_with_fields" in metadata)

    # Write stats to the data store. Metadata should be
    # written as well.
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42)

    # Check that metadata were written into the store.
    metadata = self.stats_store.ReadMetadata(
        process_id=self.process_id).AsDict()

    # Field definitions used in assertions below.
    source_field_def = rdf_stats.MetricFieldDefinition(
        field_name="source",
        field_type=rdf_stats.MetricFieldDefinition.FieldType.STR)
    task_field_def = rdf_stats.MetricFieldDefinition(
        field_name="task",
        field_type=rdf_stats.MetricFieldDefinition.FieldType.INT)

    self.assertTrue("counter" in metadata)
    self.assertEqual(metadata["counter"].varname, "counter")
    self.assertEqual(metadata["counter"].metric_type,
                     rdf_stats.MetricMetadata.MetricType.COUNTER)
    self.assertEqual(metadata["counter"].value_type,
                     rdf_stats.MetricMetadata.ValueType.INT)
    self.assertListEqual(list(metadata["counter"].fields_defs), [])

    self.assertTrue("counter_with_fields" in metadata)
    self.assertEqual(metadata["counter_with_fields"].varname,
                     "counter_with_fields")
    self.assertEqual(metadata["counter_with_fields"].metric_type,
                     rdf_stats.MetricMetadata.MetricType.COUNTER)
    self.assertEqual(metadata["counter_with_fields"].value_type,
                     rdf_stats.MetricMetadata.ValueType.INT)
    self.assertListEqual(
        list(metadata["counter_with_fields"].fields_defs), [source_field_def])

    self.assertTrue("events" in metadata)
    self.assertEqual(metadata["events"].varname, "events")
    self.assertEqual(metadata["events"].metric_type,
                     rdf_stats.MetricMetadata.MetricType.EVENT)
    self.assertEqual(metadata["events"].value_type,
                     rdf_stats.MetricMetadata.ValueType.DISTRIBUTION)
    self.assertListEqual(list(metadata["events"].fields_defs), [])

    self.assertTrue("events_with_fields" in metadata)
    self.assertEqual(metadata["events_with_fields"].varname,
                     "events_with_fields")
    self.assertEqual(metadata["events_with_fields"].metric_type,
                     rdf_stats.MetricMetadata.MetricType.EVENT)
    self.assertEqual(metadata["events_with_fields"].value_type,
                     rdf_stats.MetricMetadata.ValueType.DISTRIBUTION)
    self.assertListEqual(
        list(metadata["events_with_fields"].fields_defs), [source_field_def])

    self.assertTrue("str_gauge" in metadata)
    self.assertEqual(metadata["str_gauge"].varname, "str_gauge")
    self.assertEqual(metadata["str_gauge"].metric_type,
                     rdf_stats.MetricMetadata.MetricType.GAUGE)
    self.assertEqual(metadata["str_gauge"].value_type,
                     rdf_stats.MetricMetadata.ValueType.STR)
    self.assertListEqual(list(metadata["str_gauge"].fields_defs), [])

    self.assertTrue("str_gauge_with_fields" in metadata)
    self.assertEqual(metadata["str_gauge_with_fields"].varname,
                     "str_gauge_with_fields")
    self.assertEqual(metadata["str_gauge_with_fields"].metric_type,
                     rdf_stats.MetricMetadata.MetricType.GAUGE)
    self.assertEqual(metadata["str_gauge_with_fields"].value_type,
                     rdf_stats.MetricMetadata.ValueType.STR)
    self.assertListEqual(
        list(metadata["str_gauge_with_fields"].fields_defs), [task_field_def])

  def testMultiReadMetadataReturnsAllUsedMetadata(self):
    # Check that there are no metadata for registered metrics.
    metadata_by_id = self.stats_store.MultiReadMetadata(
        process_ids=["pid1", "pid2"])
    self.assertFalse("counter" in metadata_by_id["pid1"].AsDict())
    self.assertFalse("counter" in metadata_by_id["pid2"].AsDict())

    # Write stats to the data store. Metadata should be
    # written as well.
    self.stats_store.WriteStats(process_id="pid1", timestamp=42)

    # Now metadata should be found only for the pid1.
    metadata_by_id = self.stats_store.MultiReadMetadata(
        process_ids=["pid1", "pid2"])
    self.assertTrue("counter" in metadata_by_id["pid1"].AsDict())
    self.assertFalse("counter" in metadata_by_id["pid2"].AsDict())

    # Write stats for the pid2 and check again.
    self.stats_store.WriteStats(process_id="pid2", timestamp=42)

    metadata_by_id = self.stats_store.MultiReadMetadata(
        process_ids=["pid1", "pid2"])
    self.assertTrue("counter" in metadata_by_id["pid1"].AsDict())
    self.assertTrue("counter" in metadata_by_id["pid2"].AsDict())


class StatsStoreDataQueryTest(aff4_test_lib.AFF4ObjectTest):
  """Tests for StatsStoreDataQuery class."""

  def setUp(self):
    super(StatsStoreDataQueryTest, self).setUp()
    self.process_id = "some_pid"
    self.stats_store = aff4.FACTORY.Create(
        None, stats_store.StatsStore, mode="w", token=self.token)
    fake_stats_context = stats_test_utils.FakeStatsContext(
        _CreateFakeStatsCollector())
    fake_stats_context.start()
    self.addCleanup(fake_stats_context.stop)

  def testUsingInCallNarrowsQuerySpace(self):
    # Create sample data.
    stats_collector_instance.Get().IncrementCounter("counter")
    stats_collector_instance.Get().IncrementCounter(
        "counter_with_fields", fields=["http"])
    stats_collector_instance.Get().IncrementCounter(
        "counter_with_fields", fields=["rpc"])

    # Write to data store.
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42)

    # Read them back and apply queries with In() and InAll() calls.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("counter").SeriesCount(), 1)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("counter_with_fields").InAll().SeriesCount(), 2)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(
        query.In("counter_with_fields").In("http").SeriesCount(), 1)

  def testInCallAcceptsRegularExpressions(self):
    # Initialize and write test data.
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))

    stats_data = self.stats_store.MultiReadStats(process_ids=["pid1", "pid2"])

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid1").In("counter").SeriesCount(), 1)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid2").In("counter").SeriesCount(), 1)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid.*").In("counter").SeriesCount(), 2)

  def testInTimeRangeLimitsQueriesByTime(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(140))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Check that InTimeRange works as expected.
    query = stats_store.StatsStoreDataQuery(stats_data)
    ts = query.In("counter").TakeValue().InTimeRange(
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(80),
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(120)).ts

    self.assertListEqual(ts.data, [[2, 100 * 1e6]])

  def testInTimeRangeRaisesIfAppliedBeforeTakeMethod(self):
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(RuntimeError):
      query.In("counter").InTimeRange(
          rdfvalue.RDFDatetime.FromSecondsSinceEpoch(80),
          rdfvalue.RDFDatetime.FromSecondsSinceEpoch(120))

  def testTakeValueUsesPlainValuesToBuildTimeSeries(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    ts = query.In("counter").TakeValue().ts
    self.assertListEqual(ts.data, [[1, 42 * 1e6], [2, 100 * 1e6]])

  def testTakeValueRaisesIfDistributionIsEncountered(self):
    # Write test data.
    stats_collector_instance.Get().RecordEvent("events", 42)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(ValueError):
      query.In("events").TakeValue()

  def testTakeDistributionCountUsesDistributionCountsToBuildTimeSeries(self):
    # Write test data.
    stats_collector_instance.Get().RecordEvent("events", 42)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    stats_collector_instance.Get().RecordEvent("events", 43)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In("events").TakeDistributionCount().ts
    self.assertListEqual(ts.data, [[1, 42 * 1e6], [2, 100 * 1e6]])

  def testTakeDistributionCountRaisesIfPlainValueIsEncountered(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(ValueError):
      query.In("counter").TakeDistributionCount()

  def testTakeDistributionSumUsesDistributionSumsToBuildTimeSeries(self):
    # Write test data.
    stats_collector_instance.Get().RecordEvent("events", 42)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    stats_collector_instance.Get().RecordEvent("events", 43)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In("events").TakeDistributionSum().ts
    self.assertListEqual(ts.data, [[42, 42 * 1e6], [85, 100 * 1e6]])

  def testTakeDistributionSumRaisesIfPlainValueIsEncountered(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(ValueError):
      query.In("counter").TakeDistributionSum()

  def testNormalize(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(15))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(45))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In("counter").TakeValue().Normalize(
        rdfvalue.Duration("30s"), 0, rdfvalue.Duration("1m")).ts
    self.assertListEqual(ts.data, [[1.5, 0 * 1e6], [3.0, 30 * 1e6]])

  def testNormalizeFillsGapsInTimeSeries(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(120))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In("counter").TakeValue().Normalize(
        rdfvalue.Duration("30s"), 0, rdfvalue.Duration("130s")).ts

    self.assertListEqual(ts.data, [[1.0, 0], [None, 30 * 1e6], [None, 60 * 1e6],
                                   [None, 90 * 1e6], [2.0, 120 * 1e6]])

  def testNormalizeRaisesIfAppliedBeforeTakeMethod(self):
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(RuntimeError):
      query.In("counter").Normalize(15, 0, 60)

  def testAggregateViaSumAggregatesMultipleTimeSeriesIntoOne(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))

    stats_data = self.stats_store.MultiReadStats(process_ids=["pid1", "pid2"])
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In("pid.*").In("counter").TakeValue().Normalize(
        rdfvalue.Duration("30s"),
        0,
        rdfvalue.Duration("2m"),
        mode=timeseries.NORMALIZE_MODE_COUNTER).AggregateViaSum().ts

    # We expect 2 time series in the query:
    # 1970-01-01 00:00:00    1
    # 1970-01-01 00:00:30    1
    # 1970-01-01 00:01:00    1
    # 1970-01-01 00:01:30    3
    #
    # and:
    # 1970-01-01 00:00:00    2
    # 1970-01-01 00:00:30    2
    # 1970-01-01 00:01:00    2
    # 1970-01-01 00:01:30    3
    #
    # Therefore we expect the sum to look like:
    # 1970-01-01 00:00:00    3
    # 1970-01-01 00:00:30    3
    # 1970-01-01 00:01:00    3
    # 1970-01-01 00:01:30    6
    self.assertAlmostEqual(ts.data[0][0], 3)
    self.assertAlmostEqual(ts.data[1][0], 3)
    self.assertAlmostEqual(ts.data[2][0], 3)
    self.assertAlmostEqual(ts.data[3][0], 6)
    self.assertListEqual([t for _, t in ts.data],
                         [0.0 * 1e6, 30.0 * 1e6, 60.0 * 1e6, 90.0 * 1e6])

  def testMakeIncreasingHandlesValuesResets(self):
    # Write test data.
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(30))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(60))

    # Simulate process restart by reseting the stats-collector.
    with stats_test_utils.FakeStatsContext(_CreateFakeStatsCollector()):
      self.stats_store.WriteStats(
          process_id="pid1",
          timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))

      # We've reset the counter on 60th second, so we get following time series:
      # 1970-01-01 00:00:00    0
      # 1970-01-01 00:00:30    1
      # 1970-01-01 00:01:00    2
      # 1970-01-01 00:01:30    0
      stats_data = self.stats_store.ReadStats(process_id="pid1")
      query = stats_store.StatsStoreDataQuery(stats_data)

      ts = query.In("counter").TakeValue().ts

      self.assertAlmostEqual(ts.data[0][0], 0)
      self.assertAlmostEqual(ts.data[1][0], 1)
      self.assertAlmostEqual(ts.data[2][0], 2)
      self.assertAlmostEqual(ts.data[3][0], 0)

      # EnsureIsIncremental detects the reset and increments values that follow
      # the reset point:
      # 1970-01-01 00:00:00    0
      # 1970-01-01 00:00:30    1
      # 1970-01-01 00:01:00    2
      # 1970-01-01 00:01:30    2
      ts = query.MakeIncreasing().ts

      self.assertAlmostEqual(ts.data[0][0], 0)
      self.assertAlmostEqual(ts.data[1][0], 1)
      self.assertAlmostEqual(ts.data[2][0], 2)
      self.assertAlmostEqual(ts.data[3][0], 2)

  def testSeriesCountReturnsNumberOfDataSeriesInCurrentQuery(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))

    stats_data = self.stats_store.MultiReadStats(process_ids=["pid1", "pid2"])

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid.*").SeriesCount(), 2)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid1").In("counter").SeriesCount(), 1)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid.*").In("counter").SeriesCount(), 2)

  def testRate(self):
    # Write test data.
    for i in range(5):
      for _ in range(i):
        stats_collector_instance.Get().IncrementCounter("counter")

      self.stats_store.WriteStats(
          process_id=self.process_id,
          timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10 * i))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    ts = query.In("counter").TakeValue().Normalize(
        rdfvalue.Duration("10s"), 0, rdfvalue.Duration("50s")).Rate().ts

    # We expect following time serie:
    # 1970-01-01 00:00:00    0
    # 1970-01-01 00:00:10    1
    # 1970-01-01 00:00:20    3
    # 1970-01-01 00:00:30    6
    # 1970-01-01 00:00:40    10
    #
    # Therefore we expect the following after applying Rate():
    # 1970-01-01 00:00:00    0
    # 1970-01-01 00:00:10    0.1
    # 1970-01-01 00:00:20    0.2
    # 1970-01-01 00:00:30    0.3
    # 1970-01-01 00:00:40    0.4
    self.assertListEqual(ts.data,
                         [[0.1, 0], [0.2, 10 * 1e6],
                          [0.30000000000000004, 20 * 1e6], [0.4, 30 * 1e6]])

  def testScaleAppliesScaleFunctionToSingleTimeSerie(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    ts = query.In("counter").TakeValue().Scale(3).ts

    self.assertListEqual(ts.data, [[3, 42 * 1e6], [6, 100 * 1e6]])

  def testMeanReturnsZeroIfQueryHasNoTimeSeries(self):
    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("counter").TakeValue().Mean(), 0)

  def testMeanRaisesIfCalledOnMultipleTimeSeries(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))

    stats_data = self.stats_store.MultiReadStats(process_ids=["pid1", "pid2"])
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(RuntimeError):
      query.In("pid.*").In("counter").TakeValue().Mean()

  def testMeanReducesTimeSerieToSingleNumber(self):
    # Write test data.
    for i in range(5):
      stats_collector_instance.Get().IncrementCounter("counter")
      self.stats_store.WriteStats(
          process_id=self.process_id,
          timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10 * i))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertAlmostEqual(query.In("counter").TakeValue().Mean(), 3)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
