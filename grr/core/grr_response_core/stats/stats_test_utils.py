#!/usr/bin/env python
"""Common tests for stats-collector implementations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import time

from absl.testing import absltest
import builtins
from future.utils import with_metaclass
import mock


from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.stats import stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_utils

_INF = float("inf")


def FakeStatsContext(fake_stats_collector):
  """Stubs out the stats-collector singleton with the given fake object."""
  return mock.patch.object(stats_collector_instance, "_stats_singleton",
                           fake_stats_collector)


# pytype: disable=ignored-abstractmethod
class StatsCollectorTest(with_metaclass(abc.ABCMeta, absltest.TestCase)):
  """Stats collection tests.

  Each test method has uniquely-named metrics to accommodate implementations
  that do not support re-definition of metrics.
  """

  def setUp(self):
    super(StatsCollectorTest, self).setUp()

    self._mock_time = 100.0
    time_patcher = mock.patch.object(time, "time", lambda: self._mock_time)
    time_patcher.start()
    self.addCleanup(time_patcher.stop)

  @abc.abstractmethod
  def _CreateStatsCollector(self, metadata_list):
    """Creates a new stats collector with the given metadata."""
    # Return a mock stats collector to satisfy type-checking (pytype).
    return mock.Mock(spec_set=stats_collector.StatsCollector)

  def _Sleep(self, n):
    """Simulates sleeping for a given number of seconds."""
    self._mock_time += n

  def testSimpleCounter(self):
    counter_name = "testSimpleCounter_counter"

    collector = self._CreateStatsCollector(
        [stats_utils.CreateCounterMetadata(counter_name)])

    self.assertEqual(0, collector.GetMetricValue(counter_name))

    for _ in builtins.range(5):
      collector.IncrementCounter(counter_name)
    self.assertEqual(5, collector.GetMetricValue(counter_name))

    collector.IncrementCounter(counter_name, 2)
    self.assertEqual(7, collector.GetMetricValue(counter_name))

  def testDecrementingCounterRaises(self):
    counter_name = "testDecrementingCounterRaises_counter"

    collector = self._CreateStatsCollector(
        [stats_utils.CreateCounterMetadata(counter_name)])

    with self.assertRaises(ValueError):
      collector.IncrementCounter(counter_name, -1)

  def testCounterWithFields(self):
    counter_name = "testCounterWithFields_counter"

    collector = self._CreateStatsCollector([
        stats_utils.CreateCounterMetadata(
            counter_name, fields=[("dimension", str)])
    ])

    # Test that default values for any fields values are 0."
    self.assertEqual(0, collector.GetMetricValue(counter_name, fields=["a"]))
    self.assertEqual(0, collector.GetMetricValue(counter_name, fields=["b"]))

    for _ in builtins.range(5):
      collector.IncrementCounter(counter_name, fields=["dimension_value_1"])
    self.assertEqual(
        5, collector.GetMetricValue(counter_name, fields=["dimension_value_1"]))

    collector.IncrementCounter(counter_name, 2, fields=["dimension_value_1"])
    self.assertEqual(
        7, collector.GetMetricValue(counter_name, fields=["dimension_value_1"]))

    collector.IncrementCounter(counter_name, 2, fields=["dimension_value_2"])
    self.assertEqual(
        2, collector.GetMetricValue(counter_name, fields=["dimension_value_2"]))
    # Check that previously set values with other fields are not affected.
    self.assertEqual(
        7, collector.GetMetricValue(counter_name, fields=["dimension_value_1"]))

  def testSimpleGauge(self):
    int_gauge_name = "testSimpleGauge_int_gauge"
    string_gauge_name = "testSimpleGauge_string_gauge"

    collector = self._CreateStatsCollector([
        stats_utils.CreateGaugeMetadata(int_gauge_name, int),
        stats_utils.CreateGaugeMetadata(string_gauge_name, str)
    ])

    self.assertEqual(0, collector.GetMetricValue(int_gauge_name))
    self.assertEqual("", collector.GetMetricValue(string_gauge_name))

    collector.SetGaugeValue(int_gauge_name, 42)
    collector.SetGaugeValue(string_gauge_name, "some")

    self.assertEqual(42, collector.GetMetricValue(int_gauge_name))
    self.assertEqual("some", collector.GetMetricValue(string_gauge_name))

    # At least default Python type checking is enforced in gauges:
    # we can't assign string to int
    with self.assertRaises(ValueError):
      collector.SetGaugeValue(int_gauge_name, "some")
    # but we can assign int to string
    collector.SetGaugeValue(string_gauge_name, 42)

  def testGaugeWithFields(self):
    int_gauge_name = "testGaugeWithFields_int_gauge"

    collector = self._CreateStatsCollector([
        stats_utils.CreateGaugeMetadata(
            int_gauge_name, int, fields=[("dimension", str)])
    ])

    self.assertEqual(
        0, collector.GetMetricValue(
            int_gauge_name, fields=["dimension_value_1"]))
    self.assertEqual(
        0, collector.GetMetricValue(
            int_gauge_name, fields=["dimesnioN_value_2"]))

    collector.SetGaugeValue(int_gauge_name, 1, fields=["dimension_value_1"])
    collector.SetGaugeValue(int_gauge_name, 2, fields=["dimension_value_2"])

    self.assertEqual(
        1, collector.GetMetricValue(
            int_gauge_name, fields=["dimension_value_1"]))
    self.assertEqual(
        2, collector.GetMetricValue(
            int_gauge_name, fields=["dimension_value_2"]))

  def testGaugeWithCallback(self):
    int_gauge_name = "testGaugeWithCallback_int_gauge"
    string_gauge_name = "testGaugeWithCallback_string_gauge"

    collector = self._CreateStatsCollector([
        stats_utils.CreateGaugeMetadata(int_gauge_name, int),
        stats_utils.CreateGaugeMetadata(string_gauge_name, str)
    ])

    self.assertEqual(0, collector.GetMetricValue(int_gauge_name))
    self.assertEqual("", collector.GetMetricValue(string_gauge_name))

    collector.SetGaugeCallback(int_gauge_name, lambda: 42)
    collector.SetGaugeCallback(string_gauge_name, lambda: "some")

    self.assertEqual(42, collector.GetMetricValue(int_gauge_name))
    self.assertEqual("some", collector.GetMetricValue(string_gauge_name))

  def testSimpleEventMetric(self):
    event_metric_name = "testSimpleEventMetric_event_metric"

    collector = self._CreateStatsCollector([
        stats_utils.CreateEventMetadata(
            event_metric_name, bins=[0.0, 0.1, 0.2]),
    ])

    data = collector.GetMetricValue(event_metric_name)
    self.assertAlmostEqual(0, data.sum)
    self.assertEqual(0, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 0, 0.2: 0}, data.bins_heights)

    collector.RecordEvent(event_metric_name, 0.15)
    data = collector.GetMetricValue(event_metric_name)
    self.assertAlmostEqual(0.15, data.sum)
    self.assertEqual(1, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 1, 0.2: 0}, data.bins_heights)

    collector.RecordEvent(event_metric_name, 0.5)
    data = collector.GetMetricValue(event_metric_name)
    self.assertAlmostEqual(0.65, data.sum)
    self.assertEqual(2, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 1, 0.2: 1}, data.bins_heights)

    collector.RecordEvent(event_metric_name, -0.1)
    data = collector.GetMetricValue(event_metric_name)
    self.assertAlmostEqual(0.55, data.sum)
    self.assertEqual(3, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 1, 0.0: 0, 0.1: 1, 0.2: 1}, data.bins_heights)

  def testEventMetricWithFields(self):
    event_metric_name = "testEventMetricWithFields_event_metric"

    collector = self._CreateStatsCollector([
        stats_utils.CreateEventMetadata(
            event_metric_name,
            bins=[0.0, 0.1, 0.2],
            fields=[("dimension", str)])
    ])

    data = collector.GetMetricValue(
        event_metric_name, fields=["dimension_value_1"])
    self.assertAlmostEqual(0, data.sum)
    self.assertEqual(0, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 0, 0.2: 0}, data.bins_heights)

    collector.RecordEvent(event_metric_name, 0.15, fields=["dimension_value_1"])
    collector.RecordEvent(event_metric_name, 0.25, fields=["dimension_value_2"])

    data = collector.GetMetricValue(
        event_metric_name, fields=["dimension_value_1"])
    self.assertAlmostEqual(0.15, data.sum)
    self.assertEqual(1, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 1, 0.2: 0}, data.bins_heights)

    data = collector.GetMetricValue(
        event_metric_name, fields=["dimension_value_2"])
    self.assertAlmostEqual(0.25, data.sum)
    self.assertEqual(1, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 0, 0.2: 1}, data.bins_heights)

  def testRaisesOnImproperFieldsUsage1(self):
    counter_name = "testRaisesOnImproperFieldsUsage1_counter"
    int_gauge_name = "testRaisesOnImproperFieldsUsage1_int_gauge"
    event_metric_name = "testRaisesOnImproperFieldsUsage1_event_metric"

    collector = self._CreateStatsCollector([
        stats_utils.CreateCounterMetadata(counter_name),
        stats_utils.CreateGaugeMetadata(int_gauge_name, int),
        stats_utils.CreateEventMetadata(event_metric_name)
    ])

    # Check for counters
    with self.assertRaises(ValueError):
      collector.GetMetricValue(counter_name, fields=["a"])

    # Check for gauges
    with self.assertRaises(ValueError):
      collector.GetMetricValue(int_gauge_name, fields=["a"])

    # Check for event metrics
    self.assertRaises(
        ValueError,
        collector.GetMetricValue,
        event_metric_name,
        fields=["a", "b"])

  def testRaisesOnImproperFieldsUsage2(self):
    counter_name = "testRaisesOnImproperFieldsUsage2_counter"
    int_gauge_name = "testRaisesOnImproperFieldsUsage2_int_gauge"
    event_metric_name = "testRaisesOnImproperFieldsUsage2_event_metric"

    collector = self._CreateStatsCollector([
        stats_utils.CreateCounterMetadata(
            counter_name, fields=[("dimension", str)]),
        stats_utils.CreateGaugeMetadata(
            int_gauge_name, int, fields=[("dimension", str)]),
        stats_utils.CreateEventMetadata(
            event_metric_name, fields=[("dimension", str)])
    ])

    # Check for counters
    self.assertRaises(ValueError, collector.GetMetricValue, counter_name)
    self.assertRaises(
        ValueError, collector.GetMetricValue, counter_name, fields=["a", "b"])

    # Check for gauges
    self.assertRaises(ValueError, collector.GetMetricValue, int_gauge_name)
    self.assertRaises(
        ValueError, collector.GetMetricValue, int_gauge_name, fields=["a", "b"])

    # Check for event metrics
    self.assertRaises(ValueError, collector.GetMetricValue, event_metric_name)
    self.assertRaises(
        ValueError,
        collector.GetMetricValue,
        event_metric_name,
        fields=["a", "b"])

  def testGetAllMetricsMetadataWorksCorrectlyOnSimpleMetrics(self):
    counter_name = "testGAMM_SimpleMetrics_counter"
    int_gauge_name = "testGAMM_SimpleMetrics_int_gauge"
    event_metric_name = "testGAMM_SimpleMetrics_event_metric"

    collector = self._CreateStatsCollector([
        stats_utils.CreateCounterMetadata(counter_name),
        stats_utils.CreateGaugeMetadata(
            int_gauge_name, int, fields=[("dimension", str)]),
        stats_utils.CreateEventMetadata(event_metric_name)
    ])

    metrics = collector.GetAllMetricsMetadata()
    self.assertEqual(metrics[counter_name].metric_type,
                     rdf_stats.MetricMetadata.MetricType.COUNTER)
    self.assertFalse(metrics[counter_name].fields_defs)

    self.assertEqual(metrics[int_gauge_name].metric_type,
                     rdf_stats.MetricMetadata.MetricType.GAUGE)
    self.assertEqual(metrics[int_gauge_name].fields_defs, [
        rdf_stats.MetricFieldDefinition(
            field_name="dimension",
            field_type=rdf_stats.MetricFieldDefinition.FieldType.STR)
    ])

    self.assertEqual(metrics[event_metric_name].metric_type,
                     rdf_stats.MetricMetadata.MetricType.EVENT)
    self.assertFalse(metrics[event_metric_name].fields_defs)

  def testGetMetricFieldsWorksCorrectly(self):
    counter_name = "testGetMetricFieldsWorksCorrectly_counter"
    int_gauge_name = "testGetMetricFieldsWorksCorrectly_int_gauge"
    event_metric_name = "testGetMetricFieldsWorksCorrectly_event_metric"

    collector = self._CreateStatsCollector([
        stats_utils.CreateCounterMetadata(
            counter_name, fields=[("dimension1", str), ("dimension2", str)]),
        stats_utils.CreateGaugeMetadata(
            int_gauge_name, int, fields=[("dimension", str)]),
        stats_utils.CreateEventMetadata(
            event_metric_name, fields=[("dimension", str)]),
    ])

    collector.IncrementCounter(counter_name, fields=["b", "b"])
    collector.IncrementCounter(counter_name, fields=["a", "c"])

    collector.SetGaugeValue(int_gauge_name, 20, fields=["a"])
    collector.SetGaugeValue(int_gauge_name, 30, fields=["b"])

    collector.RecordEvent(event_metric_name, 0.1, fields=["a"])
    collector.RecordEvent(event_metric_name, 0.1, fields=["b"])

    fields = sorted(collector.GetMetricFields(counter_name), key=lambda t: t[0])
    self.assertEqual([("a", "c"), ("b", "b")], fields)

    fields = sorted(
        collector.GetMetricFields(int_gauge_name), key=lambda t: t[0])
    self.assertEqual([("a",), ("b",)], fields)

    fields = sorted(
        collector.GetMetricFields(event_metric_name), key=lambda t: t[0])
    self.assertEqual([("a",), ("b",)], fields)

  def testCountingDecorator(self):
    """Test _Function call counting."""
    counter_name = "testCountingDecorator_counter"

    collector = self._CreateStatsCollector(
        [stats_utils.CreateCounterMetadata(counter_name)])

    @stats_utils.Counted(counter_name)
    def CountedFunc():
      pass

    with FakeStatsContext(collector):
      for _ in builtins.range(10):
        CountedFunc()

    self.assertEqual(collector.GetMetricValue(counter_name), 10)

  def testMaps(self):
    """Test binned timings."""
    event_metric_name = "testMaps_event_metric"

    collector = self._CreateStatsCollector([
        stats_utils.CreateEventMetadata(
            event_metric_name, bins=[0.0, 0.1, 0.2])
    ])

    @stats_utils.Timed(event_metric_name)
    def TimedFunc(n):
      self._Sleep(n)

    with FakeStatsContext(collector):
      m = collector.GetMetricValue(event_metric_name)
      self.assertEqual(m.bins_heights[0.0], 0)
      self.assertEqual(m.bins_heights[0.1], 0)
      self.assertEqual(m.bins_heights[0.2], 0)

      for _ in builtins.range(3):
        TimedFunc(0)

      m = collector.GetMetricValue(event_metric_name)
      self.assertEqual(m.bins_heights[0.0], 3)
      self.assertEqual(m.bins_heights[0.1], 0)
      self.assertEqual(m.bins_heights[0.2], 0)

      TimedFunc(0.11)
      m = collector.GetMetricValue(event_metric_name)

      self.assertEqual(m.bins_heights[0.0], 3)
      self.assertEqual(m.bins_heights[0.1], 1)
      self.assertEqual(m.bins_heights[0.2], 0)

  def testCombiningDecorators(self):
    """Test combining decorators."""
    counter_name = "testCombiningDecorators_counter"
    event_metric_name = "testCombiningDecorators_event_metric"

    collector = self._CreateStatsCollector([
        stats_utils.CreateCounterMetadata(counter_name),
        stats_utils.CreateEventMetadata(
            event_metric_name, bins=[0.0, 0.1, 0.2])
    ])

    @stats_utils.Timed(event_metric_name)
    @stats_utils.Counted(counter_name)
    def OverdecoratedFunc(n):
      self._Sleep(n)

    with FakeStatsContext(collector):
      OverdecoratedFunc(0.02)

    # Check if all vars get updated
    m = collector.GetMetricValue(event_metric_name)
    self.assertEqual(m.bins_heights[0.0], 1)
    self.assertEqual(m.bins_heights[0.1], 0)
    self.assertEqual(m.bins_heights[0.2], 0)

    self.assertEqual(collector.GetMetricValue(counter_name), 1)

  def testExceptionHandling(self):
    """Test decorators when exceptions are thrown."""
    counter_name = "testExceptionHandling_counter"
    event_metric_name = "testExceptionHandling_event_metric"

    collector = self._CreateStatsCollector([
        stats_utils.CreateCounterMetadata(counter_name),
        stats_utils.CreateEventMetadata(
            event_metric_name, bins=[0.0, 0.1, 0.2])
    ])

    @stats_utils.Timed(event_metric_name)
    @stats_utils.Counted(counter_name)
    def RaiseFunc(n):
      self._Sleep(n)
      raise Exception()

    with FakeStatsContext(collector):
      self.assertRaises(Exception, RaiseFunc, 0.11)

    # Check if all vars get updated
    m = collector.GetMetricValue(event_metric_name)
    self.assertEqual(m.bins_heights[0.0], 0)
    self.assertEqual(m.bins_heights[0.1], 1)
    self.assertEqual(m.bins_heights[0.2], 0)

    self.assertEqual(collector.GetMetricValue(counter_name), 1)

  def testMultipleFuncs(self):
    """Tests if multiple decorators produce aggregate stats."""
    counter_name = "testMultipleFuncs_counter"
    event_metric_name = "testMultipleFuncs_event_metric"

    collector = self._CreateStatsCollector([
        stats_utils.CreateCounterMetadata(counter_name),
        stats_utils.CreateEventMetadata(event_metric_name, bins=[0, 1, 2])
    ])

    @stats_utils.Counted(counter_name)
    def Func1(n):
      self._Sleep(n)

    @stats_utils.Counted(counter_name)
    def Func2(n):
      self._Sleep(n)

    @stats_utils.Timed(event_metric_name)
    def Func3(n):
      self._Sleep(n)

    @stats_utils.Timed(event_metric_name)
    def Func4(n):
      self._Sleep(n)

    with FakeStatsContext(collector):
      Func1(0)
      Func2(0)
      self.assertEqual(collector.GetMetricValue(counter_name), 2)

      Func3(0)
      Func4(1)
      m = collector.GetMetricValue(event_metric_name)
      self.assertEqual(m.bins_heights[0.0], 1)
      self.assertEqual(m.bins_heights[1], 1)
      self.assertEqual(m.bins_heights[2], 0)
