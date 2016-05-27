#!/usr/bin/env python
"""Tests for the stats_store classes."""



from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import test_lib
from grr.lib import timeseries

from grr.lib.aff4_objects import stats_store


class StatsStoreTest(test_lib.AFF4ObjectTest):

  def setUp(self):
    super(StatsStoreTest, self).setUp()

    self.process_id = "some_pid"
    self.stats_store = aff4.FACTORY.Create(None,
                                           stats_store.StatsStore,
                                           mode="w",
                                           token=self.token)

  def testCountersAreWrittenToDataStore(self):
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.IncrementCounter("counter")

    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    row = data_store.DB.ResolvePrefix("aff4:/stats_store/some_pid",
                                      "",
                                      token=self.token)
    counter = [x for x in row if x[0] == "aff4:stats_store/counter"]
    self.assertTrue(counter)

    stored_value = stats_store.StatsStoreValue(
        value_type=stats.MetricMetadata.ValueType.INT,
        int_value=1)
    self.assertEqual(counter[0], ("aff4:stats_store/counter",
                                  stored_value.SerializeToString(), 42))

  def testCountersWithFieldsAreWrittenToDataStore(self):
    stats.STATS.RegisterCounterMetric("counter", fields=[("source", str)])
    stats.STATS.IncrementCounter("counter", fields=["http"])
    stats.STATS.IncrementCounter("counter", delta=2, fields=["rpc"])

    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    row = data_store.DB.ResolvePrefix("aff4:/stats_store/some_pid",
                                      "",
                                      token=self.token)
    # Check that no plain counter is written.
    values = [stats_store.StatsStoreValue(x[1]) for x in row
              if x[0] == "aff4:stats_store/counter"]
    self.assertEqual(len(values), 2)

    http_field_value = stats_store.StatsStoreFieldValue(
        field_type=stats.MetricFieldDefinition.FieldType.STR,
        str_value="http")
    rpc_field_value = stats_store.StatsStoreFieldValue(
        field_type=stats.MetricFieldDefinition.FieldType.STR,
        str_value="rpc")

    # Check that counter with source=http is written.
    http_counter = [x for x in values if x.fields_values == [http_field_value]]
    self.assertTrue(http_counter)
    self.assertEqual(http_counter[0].value_type,
                     stats.MetricMetadata.ValueType.INT)
    self.assertEqual(http_counter[0].int_value, 1)

    # Check that counter with source=rpc is written.
    rpc_counter = [x for x in values if x.fields_values == [rpc_field_value]]
    self.assertTrue(rpc_counter)
    self.assertEqual(rpc_counter[0].value_type,
                     stats.MetricMetadata.ValueType.INT)
    self.assertEqual(rpc_counter[0].int_value, 2)

  def testEventMetricsAreWrittenToDataStore(self):
    stats.STATS.RegisterEventMetric("foo_event")
    stats.STATS.RecordEvent("foo_event", 5)
    stats.STATS.RecordEvent("foo_event", 15)

    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    row = data_store.DB.ResolvePrefix("aff4:/stats_store/some_pid",
                                      "",
                                      token=self.token)
    values = [stats_store.StatsStoreValue(x[1]) for x in row
              if x[0] == "aff4:stats_store/foo_event"]
    self.assertEqual(len(values), 1)

    stored_value = values[0]
    self.assertEqual(stored_value.value_type,
                     stats.MetricMetadata.ValueType.DISTRIBUTION)
    self.assertEqual(stored_value.distribution_value.count, 2)
    self.assertEqual(stored_value.distribution_value.sum, 20)

  def testEventMetricsWithFieldsAreWrittenToDataStore(self):
    stats.STATS.RegisterEventMetric("foo_event", fields=[("source", str)])
    stats.STATS.RecordEvent("foo_event", 5, fields=["http"])
    stats.STATS.RecordEvent("foo_event", 15, fields=["rpc"])

    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    row = data_store.DB.ResolvePrefix("aff4:/stats_store/some_pid",
                                      "",
                                      token=self.token)

    values = [stats_store.StatsStoreValue(x[1]) for x in row
              if x[0] == "aff4:stats_store/foo_event"]
    self.assertEqual(len(values), 2)

    http_field_value = stats_store.StatsStoreFieldValue(
        field_type=stats.MetricFieldDefinition.FieldType.STR,
        str_value="http")
    rpc_field_value = stats_store.StatsStoreFieldValue(
        field_type=stats.MetricFieldDefinition.FieldType.STR,
        str_value="rpc")

    # Check that distribution with source=http is written.
    http_events = [x for x in values if x.fields_values == [http_field_value]]
    self.assertTrue(http_events)
    self.assertEqual(http_events[0].value_type,
                     stats.MetricMetadata.ValueType.DISTRIBUTION)
    self.assertEqual(http_events[0].distribution_value.count, 1)
    self.assertEqual(http_events[0].distribution_value.sum, 5)

    # Check that distribution with source=rpc is written.
    rpc_events = [x for x in values if x.fields_values == [rpc_field_value]]
    self.assertTrue(rpc_events)
    self.assertEqual(rpc_events[0].value_type,
                     stats.MetricMetadata.ValueType.DISTRIBUTION)
    self.assertEqual(rpc_events[0].distribution_value.count, 1)
    self.assertEqual(rpc_events[0].distribution_value.sum, 15)

  def testStringGaugeValuesAreWrittenToDataStore(self):
    stats.STATS.RegisterGaugeMetric("str_gauge", str)
    stats.STATS.SetGaugeValue("str_gauge", "some_value")

    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    row = data_store.DB.ResolvePrefix("aff4:/stats_store/some_pid",
                                      "",
                                      token=self.token)
    counter = [x for x in row if x[0] == "aff4:stats_store/str_gauge"]
    self.assertTrue(counter)

    stored_value = stats_store.StatsStoreValue(
        value_type=stats.MetricMetadata.ValueType.STR,
        str_value="some_value")
    self.assertEqual(counter[0], ("aff4:stats_store/str_gauge",
                                  stored_value.SerializeToString(), 42))

  def testIntGaugeValuesAreWrittenToDataStore(self):
    stats.STATS.RegisterGaugeMetric("int_gauge", int)
    stats.STATS.SetGaugeValue("int_gauge", 4242)

    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    row = data_store.DB.ResolvePrefix("aff4:/stats_store/some_pid",
                                      "",
                                      token=self.token)
    counter = [x for x in row if x[0] == "aff4:stats_store/int_gauge"]
    self.assertTrue(counter)

    stored_value = stats_store.StatsStoreValue(
        value_type=stats.MetricMetadata.ValueType.INT,
        int_value=4242)
    self.assertEqual(counter[0], ("aff4:stats_store/int_gauge",
                                  stored_value.SerializeToString(), 42))

  def testLaterValuesDoNotOverridePrevious(self):
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=43,
                                sync=True)

    row = data_store.DB.ResolvePrefix("aff4:/stats_store/some_pid",
                                      "",
                                      token=self.token)
    counters = [x for x in row if x[0] == "aff4:stats_store/counter"]
    self.assertEqual(len(counters), 2)
    counters = sorted(counters, key=lambda x: x[2])

    stored_value = stats_store.StatsStoreValue(
        value_type=stats.MetricMetadata.ValueType.INT,
        int_value=1)
    self.assertEqual(counters[0], ("aff4:stats_store/counter",
                                   stored_value.SerializeToString(), 42))
    stored_value = stats_store.StatsStoreValue(
        value_type=stats.MetricMetadata.ValueType.INT,
        int_value=2)
    self.assertEqual(counters[1], ("aff4:stats_store/counter",
                                   stored_value.SerializeToString(), 43))

  def testValuesAreFetchedCorrectly(self):
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.RegisterGaugeMetric("int_gauge", int)
    stats.STATS.SetGaugeValue("int_gauge", 4242)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=43,
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
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=43,
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
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=43,
                                sync=True)

    stats_history = self.stats_store.ReadStats(process_id=self.process_id,
                                               metric_name="counter")
    self.assertEqual(stats_history["counter"], [(1, 42), (2, 43)])
    self.assertTrue("int_gauge" not in stats_history)

  def testDeleteStatsInTimeRangeWorksCorrectly(self):
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.RegisterGaugeMetric("int_gauge", int)
    stats.STATS.SetGaugeValue("int_gauge", 4242)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=44,
                                sync=True)

    self.stats_store.DeleteStats(process_id=self.process_id,
                                 timestamp=(0, 43),
                                 sync=True)

    stats_history = self.stats_store.ReadStats(process_id=self.process_id)
    self.assertEqual(stats_history["counter"], [(2, 44)])
    self.assertEqual(stats_history["int_gauge"], [(4242, 44)])

  def testDeleteStatsInTimeRangeWorksCorrectlyWithFields(self):
    stats.STATS.RegisterCounterMetric("counter", fields=[("source", str)])

    stats.STATS.IncrementCounter("counter", fields=["http"])
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    stats.STATS.IncrementCounter("counter", fields=["http"])
    stats.STATS.IncrementCounter("counter", fields=["rpc"])
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=44,
                                sync=True)

    self.stats_store.DeleteStats(process_id=self.process_id,
                                 timestamp=(0, 43),
                                 sync=True)

    stats_history = self.stats_store.ReadStats(process_id=self.process_id)

    self.assertEqual(stats_history["counter"]["http"], [(2, 44)])
    self.assertEqual(stats_history["counter"]["rpc"], [(1, 44)])

  def testReturnsListOfAllUsedProcessIds(self):
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.RegisterGaugeMetric("int_gauge", int)

    self.stats_store.WriteStats(process_id="pid1", sync=True)
    self.stats_store.WriteStats(process_id="pid2", sync=True)

    self.assertEqual(
        sorted(self.stats_store.ListUsedProcessIds()), ["pid1", "pid2"])

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

    results = self.stats_store.MultiReadStats(timestamp=(43, 100))
    self.assertEqual(sorted(results.keys()), ["pid1", "pid2"])
    self.assertEqual(results["pid1"]["counter"], [(2, 44)])
    self.assertEqual(results["pid2"]["counter"], [(1, 44)])

  def testReadMetadataReturnsAllUsedMetadata(self):
    # Register metrics
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.RegisterCounterMetric("counter_with_fields",
                                      fields=[("source", str)])

    stats.STATS.RegisterEventMetric("events")
    stats.STATS.RegisterEventMetric("events_with_fields",
                                    fields=[("source", str)])

    stats.STATS.RegisterGaugeMetric("str_gauge", str)
    stats.STATS.RegisterGaugeMetric("str_gauge_with_fields",
                                    str,
                                    fields=[("task", int)])

    # Check that there are no metadata for registered metrics.
    metadata = self.stats_store.ReadMetadata(process_id=self.process_id)
    self.assertFalse("counter" in metadata)
    self.assertFalse("counter_with_fields" in metadata)
    self.assertFalse("events" in metadata)
    self.assertFalse("events_with_fields" in metadata)
    self.assertFalse("str_gauge" in metadata)
    self.assertFalse("str_gauge_with_fields" in metadata)

    # Write stats to the data store. Metadata should be
    # written as well.
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

    # Check that metadata were written into the store.
    metadata = self.stats_store.ReadMetadata(process_id=self.process_id)

    # Field definitions used in assertions below.
    source_field_def = stats.MetricFieldDefinition(
        field_name="source",
        field_type=stats.MetricFieldDefinition.FieldType.STR)
    task_field_def = stats.MetricFieldDefinition(
        field_name="task",
        field_type=stats.MetricFieldDefinition.FieldType.INT)

    self.assertTrue("counter" in metadata)
    self.assertEqual(metadata["counter"].varname, "counter")
    self.assertEqual(metadata["counter"].metric_type, stats.MetricType.COUNTER)
    self.assertEqual(metadata["counter"].value_type,
                     stats.MetricMetadata.ValueType.INT)
    self.assertListEqual(list(metadata["counter"].fields_defs), [])

    self.assertTrue("counter_with_fields" in metadata)
    self.assertEqual(metadata["counter_with_fields"].varname,
                     "counter_with_fields")
    self.assertEqual(metadata["counter_with_fields"].metric_type,
                     stats.MetricType.COUNTER)
    self.assertEqual(metadata["counter_with_fields"].value_type,
                     stats.MetricMetadata.ValueType.INT)
    self.assertListEqual(
        list(metadata["counter_with_fields"].fields_defs), [source_field_def])

    self.assertTrue("events" in metadata)
    self.assertEqual(metadata["events"].varname, "events")
    self.assertEqual(metadata["events"].metric_type, stats.MetricType.EVENT)
    self.assertEqual(metadata["events"].value_type,
                     stats.MetricMetadata.ValueType.DISTRIBUTION)
    self.assertListEqual(list(metadata["events"].fields_defs), [])

    self.assertTrue("events_with_fields" in metadata)
    self.assertEqual(metadata["events_with_fields"].varname,
                     "events_with_fields")
    self.assertEqual(metadata["events_with_fields"].metric_type,
                     stats.MetricType.EVENT)
    self.assertEqual(metadata["events_with_fields"].value_type,
                     stats.MetricMetadata.ValueType.DISTRIBUTION)
    self.assertListEqual(
        list(metadata["events_with_fields"].fields_defs), [source_field_def])

    self.assertTrue("str_gauge" in metadata)
    self.assertEqual(metadata["str_gauge"].varname, "str_gauge")
    self.assertEqual(metadata["str_gauge"].metric_type, stats.MetricType.GAUGE)
    self.assertEqual(metadata["str_gauge"].value_type,
                     stats.MetricMetadata.ValueType.STR)
    self.assertListEqual(list(metadata["str_gauge"].fields_defs), [])

    self.assertTrue("str_gauge_with_fields" in metadata)
    self.assertEqual(metadata["str_gauge_with_fields"].varname,
                     "str_gauge_with_fields")
    self.assertEqual(metadata["str_gauge_with_fields"].metric_type,
                     stats.MetricType.GAUGE)
    self.assertEqual(metadata["str_gauge_with_fields"].value_type,
                     stats.MetricMetadata.ValueType.STR)
    self.assertListEqual(
        list(metadata["str_gauge_with_fields"].fields_defs), [task_field_def])

  def testMultiReadMetadataReturnsAllUsedMetadata(self):
    stats.STATS.RegisterCounterMetric("counter")

    # Check that there are no metadata for registered metrics.
    metadata_by_id = self.stats_store.MultiReadMetadata(
        process_ids=["pid1", "pid2"])
    self.assertFalse("counter" in metadata_by_id["pid1"])
    self.assertFalse("counter" in metadata_by_id["pid2"])

    # Write stats to the data store. Metadata should be
    # written as well.
    self.stats_store.WriteStats(process_id="pid1", timestamp=42, sync=True)

    # Now metadata should be found only for the pid1.
    metadata_by_id = self.stats_store.MultiReadMetadata(
        process_ids=["pid1", "pid2"])
    self.assertTrue("counter" in metadata_by_id["pid1"])
    self.assertFalse("counter" in metadata_by_id["pid2"])

    # Write stats for the pid2 and check again.
    self.stats_store.WriteStats(process_id="pid2", timestamp=42, sync=True)

    metadata_by_id = self.stats_store.MultiReadMetadata(
        process_ids=["pid1", "pid2"])
    self.assertTrue("counter" in metadata_by_id["pid1"])
    self.assertTrue("counter" in metadata_by_id["pid2"])


class StatsStoreDataQueryTest(test_lib.AFF4ObjectTest):
  """Tests for StatsStoreDataQuery class."""

  def setUp(self):
    super(StatsStoreDataQueryTest, self).setUp()
    self.process_id = "some_pid"
    self.stats_store = aff4.FACTORY.Create(None,
                                           stats_store.StatsStore,
                                           mode="w",
                                           token=self.token)

  def testUsingInCallNarrowsQuerySpace(self):
    # Create sample data.
    stats.STATS.RegisterCounterMetric("counter")
    stats.STATS.RegisterCounterMetric("counter_with_fields",
                                      fields=[("source", str)])

    stats.STATS.IncrementCounter("counter")
    stats.STATS.IncrementCounter("counter_with_fields", fields=["http"])
    stats.STATS.IncrementCounter("counter_with_fields", fields=["rpc"])

    # Write to data store.
    self.stats_store.WriteStats(process_id=self.process_id,
                                timestamp=42,
                                sync=True)

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
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(0),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(90),
        sync=True)
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(90),
        sync=True)

    stats_data = self.stats_store.MultiReadStats(process_ids=["pid1", "pid2"])

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid1").In("counter").SeriesCount(), 1)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid2").In("counter").SeriesCount(), 1)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid.*").In("counter").SeriesCount(), 2)

  def testInTimeRangeLimitsQueriesByTime(self):
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(100),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(140),
        sync=True)

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Check that InTimeRange works as expected.
    query = stats_store.StatsStoreDataQuery(stats_data)
    ts = query.In("counter").TakeValue().InTimeRange(
        rdfvalue.RDFDatetime().FromSecondsFromEpoch(80),
        rdfvalue.RDFDatetime().FromSecondsFromEpoch(120)).ts

    self.assertListEqual(ts.data, [[2, 100 * 1e6]])

  def testInTimeRangeRaisesIfAppliedBeforeTakeMethod(self):
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertRaises(RuntimeError, query.In("counter").InTimeRange,
                      rdfvalue.RDFDatetime().FromSecondsFromEpoch(80),
                      rdfvalue.RDFDatetime().FromSecondsFromEpoch(120))

  def testTakeValueUsesPlainValuesToBuildTimeSeries(self):
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(100),
        sync=True)

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    ts = query.In("counter").TakeValue().ts
    self.assertListEqual(ts.data, [[1, 42 * 1e6], [2, 100 * 1e6]])

  def testTakeValueRaisesIfDistributionIsEncountered(self):
    # Initialize and write test data.
    stats.STATS.RegisterEventMetric("events")

    stats.STATS.RecordEvent("events", 42)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42),
        sync=True)

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertRaises(ValueError, query.In("events").TakeValue)

  def testTakeDistributionCountUsesDistributionCountsToBuildTimeSeries(self):
    # Initialize and write test data.
    stats.STATS.RegisterEventMetric("events")

    stats.STATS.RecordEvent("events", 42)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42),
        sync=True)

    stats.STATS.RecordEvent("events", 43)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(100),
        sync=True)

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In("events").TakeDistributionCount().ts
    self.assertListEqual(ts.data, [[1, 42 * 1e6], [2, 100 * 1e6]])

  def testTakeDistributionCountRaisesIfPlainValueIsEncountered(self):
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42),
        sync=True)

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertRaises(ValueError, query.In("counter").TakeDistributionCount)

  def testTakeDistributionSumUsesDistributionSumsToBuildTimeSeries(self):
    # Initialize and write test data.
    stats.STATS.RegisterEventMetric("events")

    stats.STATS.RecordEvent("events", 42)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42),
        sync=True)

    stats.STATS.RecordEvent("events", 43)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(100),
        sync=True)

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In("events").TakeDistributionSum().ts
    self.assertListEqual(ts.data, [[42, 42 * 1e6], [85, 100 * 1e6]])

  def testTakeDistributionSumRaisesIfPlainValueIsEncountered(self):
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42),
        sync=True)

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertRaises(ValueError, query.In("counter").TakeDistributionSum)

  def testNormalize(self):
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(0),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(15),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(45),
        sync=True)

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In("counter").TakeValue().Normalize(
        rdfvalue.Duration("30s"), 0, rdfvalue.Duration("1m")).ts
    self.assertListEqual(ts.data, [[1.5, 0 * 1e6], [3.0, 30 * 1e6]])

  def testNormalizeFillsGapsInTimeSeries(self):
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(0),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(120),
        sync=True)

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
    self.assertRaises(RuntimeError, query.In("counter").Normalize, 15, 0, 60)

  def testAggregateViaSumAggregatesMultipleTimeSeriesIntoOne(self):
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(0),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(0),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(90),
        sync=True)
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(90),
        sync=True)

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
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(0),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(30),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(60),
        sync=True)

    stats.STATS.RegisterCounterMetric("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(90),
        sync=True)

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
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(0),
        sync=True)
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(90),
        sync=True)

    stats_data = self.stats_store.MultiReadStats(process_ids=["pid1", "pid2"])

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid.*").SeriesCount(), 2)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid1").In("counter").SeriesCount(), 1)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid.*").In("counter").SeriesCount(), 2)

  def testRate(self):
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    for i in range(5):
      for _ in range(i):
        stats.STATS.IncrementCounter("counter")

      self.stats_store.WriteStats(
          process_id=self.process_id,
          timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(10 * i),
          sync=True)

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
    self.assertListEqual(ts.data, [[0.1, 0], [0.2, 10 * 1e6],
                                   [0.30000000000000004, 20 * 1e6], [0.4,
                                                                     30 * 1e6]])

  def testScaleAppliesScaleFunctionToSingleTimeSerie(self):
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(42),
        sync=True)

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(100),
        sync=True)

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
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    stats.STATS.IncrementCounter("counter")
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(0),
        sync=True)
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(90),
        sync=True)

    stats_data = self.stats_store.MultiReadStats(process_ids=["pid1", "pid2"])
    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertRaises(RuntimeError,
                      query.In("pid.*").In("counter").TakeValue().Mean)

  def testMeanReducesTimeSerieToSingleNumber(self):
    # Initialize and write test data.
    stats.STATS.RegisterCounterMetric("counter")

    for i in range(5):
      stats.STATS.IncrementCounter("counter")
      self.stats_store.WriteStats(
          process_id=self.process_id,
          timestamp=rdfvalue.RDFDatetime().FromSecondsFromEpoch(10 * i),
          sync=True)

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertAlmostEqual(query.In("counter").TakeValue().Mean(), 3)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
