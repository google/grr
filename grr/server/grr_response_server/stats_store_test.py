#!/usr/bin/env python
"""Tests for the stats_store classes."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_test_utils
from grr_response_core.stats import stats_utils
from grr_response_server import aff4
from grr_response_server import stats_store
from grr_response_server import timeseries
from grr_response_server.aff4_objects import stats_store as aff4_stats_store
from grr.test_lib import db_test_lib
from grr.test_lib import test_lib

# Metrics used for testing.
_SINGLE_DIM_COUNTER = "single_dim_counter"
_COUNTER_WITH_ONE_FIELD = "counter_with_one_field"
_COUNTER_WITH_TWO_FIELDS = "counter_with_two_fields"
_EVENT_METRIC = "events"


def _CreateFakeStatsCollector():
  """Returns a stats-collector for use by tests in this file."""
  return default_stats_collector.DefaultStatsCollector([
      stats_utils.CreateCounterMetadata(_SINGLE_DIM_COUNTER),
      stats_utils.CreateCounterMetadata(
          _COUNTER_WITH_ONE_FIELD, fields=[("field1", str)]),
      stats_utils.CreateCounterMetadata(
          _COUNTER_WITH_TWO_FIELDS, fields=[("field1", str), ("field2", int)]),
      stats_utils.CreateEventMetadata(_EVENT_METRIC),
  ])


@db_test_lib.DualDBTest
class StatsStoreTest(test_lib.GRRBaseTest):

  def setUp(self):
    super(StatsStoreTest, self).setUp()

    config_overrider = test_lib.ConfigOverrider({
        "Database.useForReads.stats": True,
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

    fake_stats_context = stats_test_utils.FakeStatsContext(
        _CreateFakeStatsCollector())
    fake_stats_context.start()
    self.addCleanup(fake_stats_context.stop)

  def testReadStats(self):
    with test_lib.FakeTime(rdfvalue.RDFDatetime(1000)):
      stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
      stats_collector_instance.Get().IncrementCounter(
          _COUNTER_WITH_ONE_FIELD, fields=["fieldval1"])
      stats_collector_instance.Get().IncrementCounter(
          _COUNTER_WITH_TWO_FIELDS, fields=["fieldval2", 3])
      stats_store._WriteStats(process_id="fake_process_id")

    with test_lib.FakeTime(rdfvalue.RDFDatetime(2000)):
      stats_collector_instance.Get().IncrementCounter(
          _COUNTER_WITH_TWO_FIELDS, fields=["fieldval2", 3])
      stats_collector_instance.Get().IncrementCounter(
          _COUNTER_WITH_TWO_FIELDS, fields=["fieldval2", 4])
      stats_store._WriteStats(process_id="fake_process_id")

    expected_single_dim_results = {
        "fake_process_id": {
            _SINGLE_DIM_COUNTER: [(1, 1000), (1, 2000)]
        }
    }
    expected_multi_dim1_results = {
        "fake_process_id": {
            _COUNTER_WITH_ONE_FIELD: {
                "fieldval1": [(1, 1000), (1, 2000)]
            }
        }
    }
    expected_multi_dim2_results = {
        "fake_process_id": {
            _COUNTER_WITH_TWO_FIELDS: {
                "fieldval2": {
                    3: [(1, 1000), (2, 2000)],
                    4: [(1, 2000)]
                }
            }
        }
    }

    self.assertDictEqual(
        stats_store.ReadStats("f", _SINGLE_DIM_COUNTER),
        expected_single_dim_results)
    self.assertDictEqual(
        stats_store.ReadStats("fake", _COUNTER_WITH_ONE_FIELD),
        expected_multi_dim1_results)
    self.assertEqual(
        stats_store.ReadStats("fake_process_id", _COUNTER_WITH_TWO_FIELDS),
        expected_multi_dim2_results)

  @db_test_lib.LegacyDataStoreOnly
  def testDeleteStatsFromLegacyDB(self):
    with test_lib.ConfigOverrider({"StatsStore.stats_ttl_hours": 1}):
      timestamp1 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(1)
      timestamp2 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3600)
      timestamp3 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(4800)
      with test_lib.FakeTime(timestamp1):
        stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
        stats_store._WriteStats(process_id="fake_process_id")
        expected_results = {
            "fake_process_id": {
                _SINGLE_DIM_COUNTER: [(1, timestamp1)]
            }
        }
        self.assertDictEqual(
            stats_store.ReadStats("f", _SINGLE_DIM_COUNTER), expected_results)
      with test_lib.FakeTime(timestamp2):
        stats_store._WriteStats(process_id="fake_process_id")
        expected_results = {
            "fake_process_id": {
                _SINGLE_DIM_COUNTER: [(1, timestamp1), (1, timestamp2)]
            }
        }
        self.assertDictEqual(
            stats_store.ReadStats("f", _SINGLE_DIM_COUNTER), expected_results)
      with test_lib.FakeTime(timestamp3):
        stats_store._DeleteStatsFromLegacyDB("fake_process_id")
        # timestamp1 is older than 1h, so it should get deleted.
        expected_results = {
            "fake_process_id": {
                _SINGLE_DIM_COUNTER: [(1, timestamp2)]
            }
        }
        self.assertDictEqual(
            stats_store.ReadStats("f", _SINGLE_DIM_COUNTER), expected_results)


class StatsStoreDataQueryTest(test_lib.GRRBaseTest):
  """Tests for StatsStoreDataQuery class."""

  def setUp(self):
    super(StatsStoreDataQueryTest, self).setUp()
    self.process_id = "some_pid"
    self.stats_store = aff4.FACTORY.Create(
        None, aff4_stats_store.StatsStore, mode="w", token=self.token)
    fake_stats_context = stats_test_utils.FakeStatsContext(
        _CreateFakeStatsCollector())
    fake_stats_context.start()
    self.addCleanup(fake_stats_context.stop)

  def testUsingInCallNarrowsQuerySpace(self):
    # Create sample data.
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    stats_collector_instance.Get().IncrementCounter(
        _COUNTER_WITH_ONE_FIELD, fields=["http"])
    stats_collector_instance.Get().IncrementCounter(
        _COUNTER_WITH_ONE_FIELD, fields=["rpc"])

    # Write to data store.
    self.stats_store.WriteStats(process_id=self.process_id, timestamp=42)

    # Read them back and apply queries with In() and InAll() calls.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In(_SINGLE_DIM_COUNTER).SeriesCount(), 1)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In(_COUNTER_WITH_ONE_FIELD).InAll().SeriesCount(), 2)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(
        query.In(_COUNTER_WITH_ONE_FIELD).In("http").SeriesCount(), 1)

  def testInCallAcceptsRegularExpressions(self):
    # Initialize and write test data.
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))

    stats_data = self.stats_store.MultiReadStats(process_ids=["pid1", "pid2"])

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid1").In(_SINGLE_DIM_COUNTER).SeriesCount(), 1)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid2").In(_SINGLE_DIM_COUNTER).SeriesCount(), 1)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid.*").In(_SINGLE_DIM_COUNTER).SeriesCount(), 2)

  def testInTimeRangeLimitsQueriesByTime(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100))

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(140))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Check that InTimeRange works as expected.
    query = stats_store.StatsStoreDataQuery(stats_data)
    ts = query.In(_SINGLE_DIM_COUNTER).TakeValue().InTimeRange(
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(80),
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(120)).ts

    self.assertListEqual(ts.data, [[2, 100 * 1e6]])

  def testInTimeRangeRaisesIfAppliedBeforeTakeMethod(self):
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(RuntimeError):
      query.In(_SINGLE_DIM_COUNTER).InTimeRange(
          rdfvalue.RDFDatetime.FromSecondsSinceEpoch(80),
          rdfvalue.RDFDatetime.FromSecondsSinceEpoch(120))

  def testTakeValueUsesPlainValuesToBuildTimeSeries(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    ts = query.In(_SINGLE_DIM_COUNTER).TakeValue().ts
    self.assertListEqual(ts.data, [[1, 42 * 1e6], [2, 100 * 1e6]])

  def testTakeValueRaisesIfDistributionIsEncountered(self):
    # Write test data.
    stats_collector_instance.Get().RecordEvent(_EVENT_METRIC, 42)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(ValueError):
      query.In(_EVENT_METRIC).TakeValue()

  def testTakeDistributionCountUsesDistributionCountsToBuildTimeSeries(self):
    # Write test data.
    stats_collector_instance.Get().RecordEvent(_EVENT_METRIC, 42)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    stats_collector_instance.Get().RecordEvent(_EVENT_METRIC, 43)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In(_EVENT_METRIC).TakeDistributionCount().ts
    self.assertListEqual(ts.data, [[1, 42 * 1e6], [2, 100 * 1e6]])

  def testTakeDistributionCountRaisesIfPlainValueIsEncountered(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(ValueError):
      query.In(_SINGLE_DIM_COUNTER).TakeDistributionCount()

  def testTakeDistributionSumUsesDistributionSumsToBuildTimeSeries(self):
    # Write test data.
    stats_collector_instance.Get().RecordEvent(_EVENT_METRIC, 42)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    stats_collector_instance.Get().RecordEvent(_EVENT_METRIC, 43)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In(_EVENT_METRIC).TakeDistributionSum().ts
    self.assertListEqual(ts.data, [[42, 42 * 1e6], [85, 100 * 1e6]])

  def testTakeDistributionSumRaisesIfPlainValueIsEncountered(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(ValueError):
      query.In(_SINGLE_DIM_COUNTER).TakeDistributionSum()

  def testNormalize(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(15))

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(45))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In(_SINGLE_DIM_COUNTER).TakeValue().Normalize(
        rdfvalue.Duration("30s"), 0, rdfvalue.Duration("1m")).ts
    self.assertListEqual(ts.data, [[1.5, 0 * 1e6], [3.0, 30 * 1e6]])

  def testNormalizeFillsGapsInTimeSeries(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(120))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In(_SINGLE_DIM_COUNTER).TakeValue().Normalize(
        rdfvalue.Duration("30s"), 0, rdfvalue.Duration("130s")).ts

    self.assertListEqual(ts.data, [[1.0, 0], [None, 30 * 1e6], [None, 60 * 1e6],
                                   [None, 90 * 1e6], [2.0, 120 * 1e6]])

  def testNormalizeRaisesIfAppliedBeforeTakeMethod(self):
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(RuntimeError):
      query.In(_SINGLE_DIM_COUNTER).Normalize(15, 0, 60)

  def testAggregateViaSumAggregatesMultipleTimeSeriesIntoOne(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))

    stats_data = self.stats_store.MultiReadStats(process_ids=["pid1", "pid2"])
    query = stats_store.StatsStoreDataQuery(stats_data)

    ts = query.In("pid.*").In(_SINGLE_DIM_COUNTER).TakeValue().Normalize(
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

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(30))

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
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

      ts = query.In(_SINGLE_DIM_COUNTER).TakeValue().ts

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
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
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
    self.assertEqual(query.In("pid1").In(_SINGLE_DIM_COUNTER).SeriesCount(), 1)

    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In("pid.*").In(_SINGLE_DIM_COUNTER).SeriesCount(), 2)

  def testRate(self):
    # Write test data.
    for i in range(5):
      for _ in range(i):
        stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)

      self.stats_store.WriteStats(
          process_id=self.process_id,
          timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10 * i))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    ts = query.In(_SINGLE_DIM_COUNTER).TakeValue().Normalize(
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
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))

    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id=self.process_id,
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    ts = query.In(_SINGLE_DIM_COUNTER).TakeValue().Scale(3).ts

    self.assertListEqual(ts.data, [[3, 42 * 1e6], [6, 100 * 1e6]])

  def testMeanReturnsZeroIfQueryHasNoTimeSeries(self):
    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertEqual(query.In(_SINGLE_DIM_COUNTER).TakeValue().Mean(), 0)

  def testMeanRaisesIfCalledOnMultipleTimeSeries(self):
    # Write test data.
    stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
    self.stats_store.WriteStats(
        process_id="pid1",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0))
    self.stats_store.WriteStats(
        process_id="pid2",
        timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(90))

    stats_data = self.stats_store.MultiReadStats(process_ids=["pid1", "pid2"])
    query = stats_store.StatsStoreDataQuery(stats_data)
    with self.assertRaises(RuntimeError):
      query.In("pid.*").In(_SINGLE_DIM_COUNTER).TakeValue().Mean()

  def testMeanReducesTimeSerieToSingleNumber(self):
    # Write test data.
    for i in range(5):
      stats_collector_instance.Get().IncrementCounter(_SINGLE_DIM_COUNTER)
      self.stats_store.WriteStats(
          process_id=self.process_id,
          timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10 * i))

    # Read data back.
    stats_data = self.stats_store.ReadStats(process_id=self.process_id)

    # Get time series generated with TakeValue().
    query = stats_store.StatsStoreDataQuery(stats_data)
    self.assertAlmostEqual(query.In(_SINGLE_DIM_COUNTER).TakeValue().Mean(), 3)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
