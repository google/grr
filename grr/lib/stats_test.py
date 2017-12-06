#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""Tests for the stats classes."""

import time


from grr.lib import flags
from grr.lib import stats
from grr.test_lib import test_lib


class StatsTests(test_lib.GRRBaseTest):
  """Stats collection tests."""

  def Sleep(self, n):
    self.mock_time += n

  def setUp(self):
    super(StatsTests, self).setUp()

    self.mock_time = 100.0
    self.time_orig = time.time
    time.time = lambda: self.mock_time

  def tearDown(self):
    super(StatsTests, self).tearDown()
    time.time = self.time_orig

  def testSimpleCounter(self):
    stats.STATS.RegisterCounterMetric("test_counter")

    self.assertEqual(0, stats.STATS.GetMetricValue("test_counter"))

    for _ in range(5):
      stats.STATS.IncrementCounter("test_counter")
    self.assertEqual(5, stats.STATS.GetMetricValue("test_counter"))

    stats.STATS.IncrementCounter("test_counter", 2)
    self.assertEqual(7, stats.STATS.GetMetricValue("test_counter"))

  def testDecrementingCounterRaises(self):
    stats.STATS.RegisterCounterMetric("test_counter")
    self.assertRaises(ValueError, stats.STATS.IncrementCounter, "test_counter",
                      -1)

  def testCounterWithFields(self):
    stats.STATS.RegisterCounterMetric("test_counter", [("dimension", str)])

    # Test that default values for any fields values are 0."
    self.assertEqual(0, stats.STATS.GetMetricValue(
        "test_counter", fields=["a"]))
    self.assertEqual(0, stats.STATS.GetMetricValue(
        "test_counter", fields=["b"]))

    for _ in range(5):
      stats.STATS.IncrementCounter("test_counter", fields=["dimension_value_1"])
    self.assertEqual(5,
                     stats.STATS.GetMetricValue(
                         "test_counter", fields=["dimension_value_1"]))

    stats.STATS.IncrementCounter(
        "test_counter", 2, fields=["dimension_value_1"])
    self.assertEqual(7,
                     stats.STATS.GetMetricValue(
                         "test_counter", fields=["dimension_value_1"]))

    stats.STATS.IncrementCounter(
        "test_counter", 2, fields=["dimension_value_2"])
    self.assertEqual(2,
                     stats.STATS.GetMetricValue(
                         "test_counter", fields=["dimension_value_2"]))
    # Check that previously set values with other fields are not affected.
    self.assertEqual(7,
                     stats.STATS.GetMetricValue(
                         "test_counter", fields=["dimension_value_1"]))

  def testSimpleGauge(self):
    stats.STATS.RegisterGaugeMetric("test_int_gauge", int)
    stats.STATS.RegisterGaugeMetric("test_string_gauge", str)

    self.assertEqual(0, stats.STATS.GetMetricValue("test_int_gauge"))
    self.assertEqual("", stats.STATS.GetMetricValue("test_string_gauge"))

    stats.STATS.SetGaugeValue("test_int_gauge", 42)
    stats.STATS.SetGaugeValue("test_string_gauge", "some")

    self.assertEqual(42, stats.STATS.GetMetricValue("test_int_gauge"))
    self.assertEqual("some", stats.STATS.GetMetricValue("test_string_gauge"))

    # At least default Python type checking is enfored in gauges:
    # we can't assign string to int
    self.assertRaises(ValueError, stats.STATS.SetGaugeValue, "test_int_gauge",
                      "some")
    # but we can assign int to string
    stats.STATS.SetGaugeValue("test_string_gauge", 42)

  def testGaugeWithFields(self):
    stats.STATS.RegisterGaugeMetric(
        "test_int_gauge", int, fields=[("dimension", str)])

    self.assertEqual(0,
                     stats.STATS.GetMetricValue(
                         "test_int_gauge", fields=["dimension_value_1"]))
    self.assertEqual(0,
                     stats.STATS.GetMetricValue(
                         "test_int_gauge", fields=["dimesnioN_value_2"]))

    stats.STATS.SetGaugeValue("test_int_gauge", 1, fields=["dimension_value_1"])
    stats.STATS.SetGaugeValue("test_int_gauge", 2, fields=["dimension_value_2"])

    self.assertEqual(1,
                     stats.STATS.GetMetricValue(
                         "test_int_gauge", fields=["dimension_value_1"]))
    self.assertEqual(2,
                     stats.STATS.GetMetricValue(
                         "test_int_gauge", fields=["dimension_value_2"]))

  def testGaugeWithCallback(self):
    stats.STATS.RegisterGaugeMetric("test_int_gauge", int)
    stats.STATS.RegisterGaugeMetric("test_string_gauge", str)

    self.assertEqual(0, stats.STATS.GetMetricValue("test_int_gauge"))
    self.assertEqual("", stats.STATS.GetMetricValue("test_string_gauge"))

    stats.STATS.SetGaugeCallback("test_int_gauge", lambda: 42)
    stats.STATS.SetGaugeCallback("test_string_gauge", lambda: "some")

    self.assertEqual(42, stats.STATS.GetMetricValue("test_int_gauge"))
    self.assertEqual("some", stats.STATS.GetMetricValue("test_string_gauge"))

  def testSimpleEventMetric(self):
    inf = float("inf")

    stats.STATS.RegisterEventMetric("test_event_metric", bins=[0.0, 0.1, 0.2])

    data = stats.STATS.GetMetricValue("test_event_metric")
    self.assertAlmostEqual(0, data.sum)
    self.assertEqual(0, data.count)
    self.assertEqual([-inf, 0.0, 0.1, 0.2], data.bins)
    self.assertEqual({-inf: 0, 0.0: 0, 0.1: 0, 0.2: 0}, data.bins_heights)

    stats.STATS.RecordEvent("test_event_metric", 0.15)
    data = stats.STATS.GetMetricValue("test_event_metric")
    self.assertAlmostEqual(0.15, data.sum)
    self.assertEqual(1, data.count)
    self.assertEqual([-inf, 0.0, 0.1, 0.2], data.bins)
    self.assertEqual({-inf: 0, 0.0: 0, 0.1: 1, 0.2: 0}, data.bins_heights)

    stats.STATS.RecordEvent("test_event_metric", 0.5)
    data = stats.STATS.GetMetricValue("test_event_metric")
    self.assertAlmostEqual(0.65, data.sum)
    self.assertEqual(2, data.count)
    self.assertEqual([-inf, 0.0, 0.1, 0.2], data.bins)
    self.assertEqual({-inf: 0, 0.0: 0, 0.1: 1, 0.2: 1}, data.bins_heights)

    stats.STATS.RecordEvent("test_event_metric", -0.1)
    data = stats.STATS.GetMetricValue("test_event_metric")
    self.assertAlmostEqual(0.55, data.sum)
    self.assertEqual(3, data.count)
    self.assertEqual([-inf, 0.0, 0.1, 0.2], data.bins)
    self.assertEqual({-inf: 1, 0.0: 0, 0.1: 1, 0.2: 1}, data.bins_heights)

  def testEventMetricWithFields(self):
    inf = float("inf")

    stats.STATS.RegisterEventMetric(
        "test_event_metric", bins=[0.0, 0.1, 0.2], fields=[("dimension", str)])

    data = stats.STATS.GetMetricValue(
        "test_event_metric", fields=["dimension_value_1"])
    self.assertAlmostEqual(0, data.sum)
    self.assertEqual(0, data.count)
    self.assertEqual([-inf, 0.0, 0.1, 0.2], data.bins)
    self.assertEqual({-inf: 0, 0.0: 0, 0.1: 0, 0.2: 0}, data.bins_heights)

    stats.STATS.RecordEvent(
        "test_event_metric", 0.15, fields=["dimension_value_1"])
    stats.STATS.RecordEvent(
        "test_event_metric", 0.25, fields=["dimension_value_2"])

    data = stats.STATS.GetMetricValue(
        "test_event_metric", fields=["dimension_value_1"])
    self.assertAlmostEqual(0.15, data.sum)
    self.assertEqual(1, data.count)
    self.assertEqual([-inf, 0.0, 0.1, 0.2], data.bins)
    self.assertEqual({-inf: 0, 0.0: 0, 0.1: 1, 0.2: 0}, data.bins_heights)

    data = stats.STATS.GetMetricValue(
        "test_event_metric", fields=["dimension_value_2"])
    self.assertAlmostEqual(0.25, data.sum)
    self.assertEqual(1, data.count)
    self.assertEqual([-inf, 0.0, 0.1, 0.2], data.bins)
    self.assertEqual({-inf: 0, 0.0: 0, 0.1: 0, 0.2: 1}, data.bins_heights)

  def testRaisesOnImproperFieldsUsage1(self):
    # Check for counters
    stats.STATS.RegisterCounterMetric("test_counter")
    self.assertRaises(
        ValueError, stats.STATS.GetMetricValue, "test_counter", fields=["a"])

    # Check for gauges
    stats.STATS.RegisterGaugeMetric("test_int_gauge", int)
    self.assertRaises(
        ValueError, stats.STATS.GetMetricValue, "test_int_gauge", fields=["a"])

    # Check for event metrics
    stats.STATS.RegisterEventMetric("test_event_metric")
    self.assertRaises(
        ValueError,
        stats.STATS.GetMetricValue,
        "test_event_metric",
        fields=["a", "b"])

  def testRaisesOnImproperFieldsUsage2(self):
    # Check for counters
    stats.STATS.RegisterCounterMetric(
        "test_counter", fields=[("dimension", str)])
    self.assertRaises(ValueError, stats.STATS.GetMetricValue, "test_counter")
    self.assertRaises(
        ValueError,
        stats.STATS.GetMetricValue,
        "test_counter",
        fields=["a", "b"])

    # Check for gauges
    stats.STATS.RegisterGaugeMetric(
        "test_int_gauge", int, fields=[("dimension", str)])
    self.assertRaises(ValueError, stats.STATS.GetMetricValue, "test_int_gauge")
    self.assertRaises(
        ValueError,
        stats.STATS.GetMetricValue,
        "test_int_gauge",
        fields=["a", "b"])

    # Check for event metrics
    stats.STATS.RegisterEventMetric(
        "test_event_metric", fields=[("dimension", str)])
    self.assertRaises(ValueError, stats.STATS.GetMetricValue,
                      "test_event_metric")
    self.assertRaises(
        ValueError,
        stats.STATS.GetMetricValue,
        "test_event_metric",
        fields=["a", "b"])

  def testGetAllMetricsMetadataWorksCorrectlyOnSimpleMetrics(self):
    stats.STATS.RegisterCounterMetric("test_counter")
    stats.STATS.RegisterGaugeMetric(
        "test_int_gauge", int, fields=[("dimension", str)])
    stats.STATS.RegisterEventMetric("test_event_metric")

    metrics = stats.STATS.GetAllMetricsMetadata()
    self.assertEqual(metrics["test_counter"].metric_type,
                     stats.MetricType.COUNTER)
    self.assertFalse(metrics["test_counter"].fields_defs)

    self.assertEqual(metrics["test_int_gauge"].metric_type,
                     stats.MetricType.GAUGE)
    self.assertEqual(metrics["test_int_gauge"].fields_defs, [
        stats.MetricFieldDefinition(
            field_name="dimension",
            field_type=stats.MetricFieldDefinition.FieldType.STR)
    ])

    self.assertEqual(metrics["test_event_metric"].metric_type,
                     stats.MetricType.EVENT)
    self.assertFalse(metrics["test_event_metric"].fields_defs)

  def testGetMetricFieldsWorksCorrectly(self):
    stats.STATS.RegisterCounterMetric(
        "test_counter", fields=[("dimension1", str), ("dimension2", str)])
    stats.STATS.RegisterGaugeMetric(
        "test_int_gauge", int, fields=[("dimension", str)])
    stats.STATS.RegisterEventMetric(
        "test_event_metric", fields=[("dimension", str)])

    stats.STATS.IncrementCounter("test_counter", fields=["b", "b"])
    stats.STATS.IncrementCounter("test_counter", fields=["a", "c"])

    stats.STATS.SetGaugeValue("test_int_gauge", 20, fields=["a"])
    stats.STATS.SetGaugeValue("test_int_gauge", 30, fields=["b"])

    stats.STATS.RecordEvent("test_event_metric", 0.1, fields=["a"])
    stats.STATS.RecordEvent("test_event_metric", 0.1, fields=["b"])

    fields = sorted(
        stats.STATS.GetMetricFields("test_counter"), key=lambda t: t[0])
    self.assertEqual([("a", "c"), ("b", "b")], fields)

    fields = sorted(
        stats.STATS.GetMetricFields("test_int_gauge"), key=lambda t: t[0])
    self.assertEqual([("a",), ("b",)], fields)

    fields = sorted(
        stats.STATS.GetMetricFields("test_event_metric"), key=lambda t: t[0])
    self.assertEqual([("a",), ("b",)], fields)

  @stats.Counted("test_counter")
  def CountedFunc(self):
    pass

  def testCountingDecorator(self):
    """Test function call counting."""
    stats.STATS.RegisterCounterMetric("test_counter")

    for _ in range(10):
      self.CountedFunc()

    self.assertEqual(stats.STATS.GetMetricValue("test_counter"), 10)

  @stats.Timed("test_timed")
  def TimedFunc(self, n):
    self.Sleep(n)

  def testMaps(self):
    """Test binned timings."""
    stats.STATS.RegisterEventMetric("test_timed", bins=[0.0, 0.1, 0.2])

    m = stats.STATS.GetMetricValue("test_timed")
    self.assertEqual(m.bins_heights[0.0], 0)
    self.assertEqual(m.bins_heights[0.1], 0)
    self.assertEqual(m.bins_heights[0.2], 0)

    for _ in range(3):
      self.TimedFunc(0)

    m = stats.STATS.GetMetricValue("test_timed")
    self.assertEqual(m.bins_heights[0.0], 3)
    self.assertEqual(m.bins_heights[0.1], 0)
    self.assertEqual(m.bins_heights[0.2], 0)

    self.TimedFunc(0.11)
    m = stats.STATS.GetMetricValue("test_timed")

    self.assertEqual(m.bins_heights[0.0], 3)
    self.assertEqual(m.bins_heights[0.1], 1)
    self.assertEqual(m.bins_heights[0.2], 0)

  @stats.Timed("test_timed")
  @stats.Counted("test_counter")
  def OverdecoratedFunc(self, n):
    self.Sleep(n)

  def testCombiningDecorators(self):
    """Test combining decorators."""
    stats.STATS.RegisterCounterMetric("test_counter")
    stats.STATS.RegisterEventMetric("test_timed", bins=[0.0, 0.1, 0.2])

    self.OverdecoratedFunc(0.02)

    # Check if all vars get updated
    m = stats.STATS.GetMetricValue("test_timed")
    self.assertEqual(m.bins_heights[0.0], 1)
    self.assertEqual(m.bins_heights[0.1], 0)
    self.assertEqual(m.bins_heights[0.2], 0)

    self.assertEqual(stats.STATS.GetMetricValue("test_counter"), 1)

  @stats.Timed("test_timed")
  @stats.Counted("test_counter")
  def RaiseFunc(self, n):
    self.Sleep(n)
    raise Exception()

  def testExceptionHandling(self):
    """Test decorators when exceptions are thrown."""
    stats.STATS.RegisterCounterMetric("test_counter")
    stats.STATS.RegisterEventMetric("test_timed", bins=[0.0, 0.1, 0.2])

    self.assertRaises(Exception, self.RaiseFunc, 0.11)

    # Check if all vars get updated
    m = stats.STATS.GetMetricValue("test_timed")
    self.assertEqual(m.bins_heights[0.0], 0)
    self.assertEqual(m.bins_heights[0.1], 1)
    self.assertEqual(m.bins_heights[0.2], 0)

    self.assertEqual(stats.STATS.GetMetricValue("test_counter"), 1)

  @stats.Counted("test_multiple_count")
  def Func1(self, n):
    self.Sleep(n)

  @stats.Counted("test_multiple_count")
  def Func2(self, n):
    self.Sleep(n)

  @stats.Timed("test_multiple_timing")
  def Func3(self, n):
    self.Sleep(n)

  @stats.Timed("test_multiple_timing")
  def Func4(self, n):
    self.Sleep(n)

  def testMultipleFuncs(self):
    """Tests if multiple decorators produce aggregate stats."""
    stats.STATS.RegisterCounterMetric("test_multiple_count")
    stats.STATS.RegisterEventMetric("test_multiple_timing", bins=[0, 1, 2])

    self.Func1(0)
    self.Func2(0)
    self.assertEqual(stats.STATS.GetMetricValue("test_multiple_count"), 2)

    self.Func3(0)
    self.Func4(1)
    m = stats.STATS.GetMetricValue("test_multiple_timing")
    self.assertEqual(m.bins_heights[0.0], 1)
    self.assertEqual(m.bins_heights[1], 1)
    self.assertEqual(m.bins_heights[2], 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
