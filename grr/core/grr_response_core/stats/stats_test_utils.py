#!/usr/bin/env python
"""Common tests for stats-collector implementations."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc
import time

from absl.testing import absltest

from future.builtins import range
from future.builtins import str
from future.utils import with_metaclass
import mock

from grr_response_core.lib.rdfvalues import stats as rdf_stats
from grr_response_core.stats import metrics
from grr.test_lib import stats_test_lib

_INF = float("inf")


class StatsCollectorTest(
    with_metaclass(abc.ABCMeta, stats_test_lib.StatsCollectorTestMixin,
                   absltest.TestCase)):
  """Stats collection tests.

  Each test method has uniquely-named metrics to accommodate implementations
  that do not support re-definition of metrics.

  For Events, the exact boundaries of Distribution bins are not tested. For
  these histogram metrics, it is acceptable that different implementations have
  slightly different behavior, e.g. one uses lower or equal while another uses
  strictly lower for bounds of bins. This allows integration with third-party
  metric libraries.
  """

  def setUp(self):
    super(StatsCollectorTest, self).setUp()

    self._mock_time = 100.0
    time_patcher = mock.patch.object(time, "time", lambda: self._mock_time)
    time_patcher.start()
    self.addCleanup(time_patcher.stop)

  @abc.abstractmethod
  def _CreateStatsCollector(self):
    """Creates a new stats collector."""

  def _Sleep(self, n):
    """Simulates sleeping for a given number of seconds."""
    self._mock_time += n

  def testSimpleCounter(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter("testSimpleCounter_counter")

    self.assertEqual(0, counter.GetValue())

    for _ in range(5):
      counter.Increment()
    self.assertEqual(5, counter.GetValue())

    counter.Increment(2)
    self.assertEqual(7, counter.GetValue())

  def testDecrementingCounterRaises(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter("testDecrementingCounterRaises_counter")

    with self.assertRaises(ValueError):
      counter.Increment(-1)

  def testCounterWithFields(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter(
          "testCounterWithFields_counter", fields=[("dimension", str)])

    # Test that default values for any fields values are 0."
    self.assertEqual(0, counter.GetValue(fields=["a"]))
    self.assertEqual(0, counter.GetValue(fields=["b"]))

    for _ in range(5):
      counter.Increment(fields=["dimension_value_1"])
    self.assertEqual(5, counter.GetValue(fields=["dimension_value_1"]))

    counter.Increment(2, fields=["dimension_value_1"])
    self.assertEqual(7, counter.GetValue(fields=["dimension_value_1"]))

    counter.Increment(2, fields=["dimension_value_2"])
    self.assertEqual(2, counter.GetValue(fields=["dimension_value_2"]))
    # Check that previously set values with other fields are not affected.
    self.assertEqual(7, counter.GetValue(fields=["dimension_value_1"]))

  def testSimpleGauge(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      int_gauge = metrics.Gauge("testSimpleGauge_int_gauge", int)
      float_gauge = metrics.Gauge("testSimpleGauge_float_gauge", float)

    self.assertEqual(0, int_gauge.GetValue())
    self.assertEqual(0.0, float_gauge.GetValue())
    int_gauge.SetValue(42)
    float_gauge.SetValue(42.3)

    self.assertEqual(42, int_gauge.GetValue())
    self.assertAlmostEqual(42.3, float_gauge.GetValue())

    # At least default Python type checking is enforced in gauges:
    # we can't assign string to int
    with self.assertRaises(ValueError):
      int_gauge.SetValue("some")

  def testGaugeWithFields(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      int_gauge = metrics.Gauge(
          "testGaugeWithFields_int_gauge", int, fields=[("dimension", str)])

    self.assertEqual(0, int_gauge.GetValue(fields=["dimension_value_1"]))
    self.assertEqual(0, int_gauge.GetValue(fields=["dimesnioN_value_2"]))

    int_gauge.SetValue(1, fields=["dimension_value_1"])
    int_gauge.SetValue(2, fields=["dimension_value_2"])

    self.assertEqual(1, int_gauge.GetValue(fields=["dimension_value_1"]))
    self.assertEqual(2, int_gauge.GetValue(fields=["dimension_value_2"]))

  def testGaugeWithCallback(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      int_gauge = metrics.Gauge("testGaugeWithCallback_int_gauge", int)
      float_gauge = metrics.Gauge("testGaugeWithCallback_float_gauge", float)

    self.assertEqual(0, int_gauge.GetValue())
    self.assertEqual(0.0, float_gauge.GetValue())

    int_gauge.SetCallback(lambda: 42)
    float_gauge.SetCallback(lambda: 42.3)

    self.assertEqual(42, int_gauge.GetValue())
    self.assertAlmostEqual(42.3, float_gauge.GetValue())

  def testSimpleEventMetric(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      event_metric = metrics.Event(
          "testSimpleEventMetric_event_metric", bins=[0.0, 0.1, 0.2])

    data = event_metric.GetValue()
    self.assertAlmostEqual(0, data.sum)
    self.assertEqual(0, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 0, 0.2: 0}, data.bins_heights)

    event_metric.RecordEvent(0.15)
    data = event_metric.GetValue()
    self.assertAlmostEqual(0.15, data.sum)
    self.assertEqual(1, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 1, 0.2: 0}, data.bins_heights)

    event_metric.RecordEvent(0.5)
    data = event_metric.GetValue()
    self.assertAlmostEqual(0.65, data.sum)
    self.assertEqual(2, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 1, 0.2: 1}, data.bins_heights)

    event_metric.RecordEvent(-0.1)
    data = event_metric.GetValue()
    self.assertAlmostEqual(0.55, data.sum)
    self.assertEqual(3, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 1, 0.0: 0, 0.1: 1, 0.2: 1}, data.bins_heights)

  def testEventMetricWithFields(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      event_metric = metrics.Event(
          "testEventMetricWithFields_event_metric",
          bins=[0.0, 0.1, 0.2],
          fields=[("dimension", str)])

    data = event_metric.GetValue(fields=["dimension_value_1"])
    self.assertAlmostEqual(0, data.sum)
    self.assertEqual(0, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 0, 0.2: 0}, data.bins_heights)

    event_metric.RecordEvent(0.15, fields=["dimension_value_1"])
    event_metric.RecordEvent(0.25, fields=["dimension_value_2"])

    data = event_metric.GetValue(fields=["dimension_value_1"])
    self.assertAlmostEqual(0.15, data.sum)
    self.assertEqual(1, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 1, 0.2: 0}, data.bins_heights)

    data = event_metric.GetValue(fields=["dimension_value_2"])
    self.assertAlmostEqual(0.25, data.sum)
    self.assertEqual(1, data.count)
    self.assertEqual([-_INF, 0.0, 0.1, 0.2], list(data.bins))
    self.assertEqual({-_INF: 0, 0.0: 0, 0.1: 0, 0.2: 1}, data.bins_heights)

  def testRaisesOnImproperFieldsUsage1(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter("testRaisesOnImproperFieldsUsage1_counter")
      int_gauge = metrics.Gauge("testRaisesOnImproperFieldsUsage1_int_gauge",
                                int)
      event_metric = metrics.Event(
          "testRaisesOnImproperFieldsUsage1_event_metric")

    # Check for counters
    with self.assertRaises(ValueError):
      counter.GetValue(fields=["a"])

    # Check for gauges
    with self.assertRaises(ValueError):
      int_gauge.GetValue(fields=["a"])

    # Check for event metrics
    with self.assertRaises(ValueError):
      event_metric.GetValue(fields=["a", "b"])

  def testRaisesOnImproperFieldsUsage2(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter(
          "testRaisesOnImproperFieldsUsage2_counter",
          fields=[("dimension", str)])
      int_gauge = metrics.Gauge(
          "testRaisesOnImproperFieldsUsage2_int_gauge",
          int,
          fields=[("dimension", str)])
      event_metric = metrics.Event(
          "testRaisesOnImproperFieldsUsage2_event_metric",
          fields=[("dimension", str)])

    # Check for counters
    with self.assertRaises(ValueError):
      counter.GetValue()
    with self.assertRaises(ValueError):
      counter.GetValue(fields=["a", "b"])

    # Check for gauges
    with self.assertRaises(ValueError):
      int_gauge.GetValue()
    with self.assertRaises(ValueError):
      int_gauge.GetValue(fields=["a", "b"])

    # Check for event metrics
    with self.assertRaises(ValueError):
      event_metric.GetValue()
    with self.assertRaises(ValueError):
      event_metric.GetValue(fields=["a", "b"])

  def testGetAllMetricsMetadataWorksCorrectlyOnSimpleMetrics(self):
    counter_name = "testGAMM_SimpleMetrics_counter"
    int_gauge_name = "testGAMM_SimpleMetrics_int_gauge"
    event_metric_name = "testGAMM_SimpleMetrics_event_metric"

    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      metrics.Counter(counter_name)
      metrics.Gauge(int_gauge_name, int, fields=[("dimension", str)])
      metrics.Event(event_metric_name)

    metadatas = self.collector.GetAllMetricsMetadata()
    self.assertEqual(metadatas[counter_name].metric_type,
                     rdf_stats.MetricMetadata.MetricType.COUNTER)
    self.assertFalse(metadatas[counter_name].fields_defs)

    self.assertEqual(metadatas[int_gauge_name].metric_type,
                     rdf_stats.MetricMetadata.MetricType.GAUGE)
    self.assertEqual(metadatas[int_gauge_name].fields_defs, [
        rdf_stats.MetricFieldDefinition(
            field_name="dimension",
            field_type=rdf_stats.MetricFieldDefinition.FieldType.STR)
    ])

    self.assertEqual(metadatas[event_metric_name].metric_type,
                     rdf_stats.MetricMetadata.MetricType.EVENT)
    self.assertFalse(metadatas[event_metric_name].fields_defs)

  def testGetMetricFieldsWorksCorrectly(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter(
          "testGetMetricFieldsWorksCorrectly_counter",
          fields=[("dimension1", str), ("dimension2", str)])
      int_gauge = metrics.Gauge(
          "testGetMetricFieldsWorksCorrectly_int_gauge",
          int,
          fields=[("dimension", str)])
      event_metric = metrics.Event(
          "testGetMetricFieldsWorksCorrectly_event_metric",
          fields=[("dimension", str)])

    counter.Increment(fields=["b", "b"])
    counter.Increment(fields=["a", "c"])
    self.assertCountEqual([("a", "c"), ("b", "b")], counter.GetFields())

    int_gauge.SetValue(20, fields=["a"])
    int_gauge.SetValue(30, fields=["b"])
    self.assertCountEqual([("a",), ("b",)], int_gauge.GetFields())

    event_metric.RecordEvent(0.1, fields=["a"])
    event_metric.RecordEvent(0.1, fields=["b"])
    self.assertCountEqual([("a",), ("b",)], event_metric.GetFields())

  def testCountingDecorator(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter("testCountingDecorator_counter")

    @counter.Counted()
    def CountedFunc():
      pass

    for _ in range(10):
      CountedFunc()

    self.assertEqual(counter.GetValue(), 10)

  def testSuccessesCountingDecorator(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter("testCountingDecorator_successes_counter")

    @counter.SuccessesCounted()
    def CountedFunc(should_raise):
      if should_raise:
        raise RuntimeError("foo")

    for i in range(10):
      if i % 2 == 0:
        with self.assertRaises(RuntimeError):
          CountedFunc(True)
      else:
        CountedFunc(False)

    # Failing calls shouldn't increment the counter.
    self.assertEqual(counter.GetValue(), 5)

  def testErrorsCountingDecorator(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter("testCountingDecorator_errors_counter")

    @counter.SuccessesCounted()
    def CountedFunc(should_raise):
      if should_raise:
        raise RuntimeError("foo")

    for i in range(10):
      if i % 2 == 0:
        with self.assertRaises(RuntimeError):
          CountedFunc(True)
      else:
        CountedFunc(False)

    # Non-failing calls shouldn't increment the counter.
    self.assertEqual(counter.GetValue(), 5)

  def testBinnedTimings(self):
    event_metric_name = "testMaps_event_metric"

    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      event_metric = metrics.Event(event_metric_name, bins=[0, 0.1, 0.2])

    @event_metric.Timed()
    def TimedFunc(n):
      self._Sleep(n)

    m = event_metric.GetValue()
    self.assertEqual(m.bins_heights, {-_INF: 0, 0: 0, 0.1: 0, 0.2: 0})

    for _ in range(3):
      TimedFunc(0.01)

    m = event_metric.GetValue()
    self.assertEqual(m.bins_heights, {-_INF: 0, 0: 3, 0.1: 0, 0.2: 0})

    TimedFunc(0.11)
    m = event_metric.GetValue()
    self.assertEqual(m.bins_heights, {-_INF: 0, 0: 3, 0.1: 1, 0.2: 0})

  def testCombiningDecorators(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter("testCombiningDecorators_counter")
      event_metric = metrics.Event(
          "testCombiningDecorators_event_metric", bins=[0.0, 0.1, 0.2])

    @event_metric.Timed()
    @counter.Counted()
    def OverdecoratedFunc(n):
      self._Sleep(n)

    OverdecoratedFunc(0.02)

    # Check if all vars get updated
    m = event_metric.GetValue()
    self.assertEqual(m.bins_heights, {-_INF: 0, 0: 1, 0.1: 0, 0.2: 0})

    self.assertEqual(counter.GetValue(), 1)

  def testExceptionHandling(self):
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter("testExceptionHandling_counter")
      event_metric = metrics.Event(
          "testExceptionHandling_event_metric", bins=[0, 0.1, 0.2])

    @event_metric.Timed()
    @counter.Counted()
    def RaiseFunc(n):
      self._Sleep(n)
      raise Exception()

    with self.assertRaises(Exception):
      RaiseFunc(0.11)

    # Check if all vars get updated
    m = event_metric.GetValue()
    self.assertEqual(m.bins_heights, {-_INF: 0, 0: 0, 0.1: 1, 0.2: 0})

    self.assertEqual(counter.GetValue(), 1)

  def testMultipleFuncs(self):
    """Tests if multiple decorators produce aggregate stats."""
    with self.SetUpStatsCollector(self._CreateStatsCollector()):
      counter = metrics.Counter("testMultipleFuncs_counter")
      event_metric = metrics.Event(
          "testMultipleFuncs_event_metric", bins=[0, 1, 2])

    @counter.Counted()
    def Func1(n):
      self._Sleep(n)

    @counter.Counted()
    def Func2(n):
      self._Sleep(n)

    @event_metric.Timed()
    def Func3(n):
      self._Sleep(n)

    @event_metric.Timed()
    def Func4(n):
      self._Sleep(n)

    Func1(0.1)
    Func2(0.1)
    self.assertEqual(counter.GetValue(), 2)

    Func3(0.1)
    Func4(1.1)
    m = event_metric.GetValue()
    self.assertEqual(m.bins_heights, {-_INF: 0, 0: 1, 1: 1, 2: 0})
