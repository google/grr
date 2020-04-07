#!/usr/bin/env python
# Lint as: python3
"""Tests for the metrics interface for stats collection."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl.testing import absltest

import mock

from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import metrics
from grr_response_core.stats import stats_collector_instance
from grr.test_lib import stats_test_lib


class MetricsTest(stats_test_lib.StatsTestMixin,
                  stats_test_lib.StatsCollectorTestMixin, absltest.TestCase):

  def testCounterRegistration(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      metrics.Counter("cfoo")
    self.assertIsNotNone(self.collector.GetMetricMetadata("cfoo"))

  def testGaugeRegistration(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      metrics.Gauge("gfoo", int)
    self.assertIsNotNone(self.collector.GetMetricMetadata("gfoo"))

  def testEventRegistration(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      metrics.Event("efoo")
    self.assertIsNotNone(self.collector.GetMetricMetadata("efoo"))

  def testCounterIncrement(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      counter = metrics.Counter("cfoo", fields=[("bar", str)])
    with self.assertStatsCounterDelta(1, counter, fields=["baz"]):
      counter.Increment(fields=["baz"])

  def testGetValue(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      counter = metrics.Counter("cfoo", fields=[("bar", str)])
    self.assertEqual(counter.GetValue(["baz"]), 0)
    counter.Increment(fields=["baz"])
    self.assertEqual(counter.GetValue(["baz"]), 1)

  def testGetFields(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      counter = metrics.Counter("cfoo", fields=[("bar", str)])
    self.assertEmpty(counter.GetFields())
    counter.Increment(fields=["baz"])
    counter.Increment(fields=["bazz"])
    self.assertCountEqual(counter.GetFields(), [("baz",), ("bazz",)])

  def testCountedDecoratorIncrement(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      counter = metrics.Counter("cfoo", fields=[("bar", str)])

    @counter.Counted(fields=["baz"])
    def Foo():
      pass

    with self.assertStatsCounterDelta(1, counter, fields=["baz"]):
      Foo()

  def testSuccessesCountedDecoratorIncrement(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      counter = metrics.Counter("cfoo", fields=[("bar", str)])

    @counter.SuccessesCounted(fields=["baz"])
    def Foo():
      pass

    with self.assertStatsCounterDelta(1, counter, fields=["baz"]):
      Foo()

  def testErrorsCountedDecoratorIncrement(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      counter = metrics.Counter("cfoo", fields=[("bar", str)])

    @counter.ErrorsCounted(fields=["baz"])
    def Foo():
      raise ValueError()

    with self.assertStatsCounterDelta(1, counter, fields=["baz"]):
      with self.assertRaises(ValueError):
        Foo()

  def testSetGaugeValue(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      gauge = metrics.Gauge("gfoo", int, fields=[("bar", str)])
    with self.assertStatsCounterDelta(42, gauge, fields=["baz"]):
      gauge.SetValue(42, fields=["baz"])

  def testRecordEvent(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      event = metrics.Event("efoo", fields=[("bar", str)])
    with self.assertStatsCounterDelta(1, event, fields=["baz"]):
      event.RecordEvent(42, fields=["baz"])

  def testTimedDecorator(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()):
      event = metrics.Event("efoo", fields=[("bar", str)])

    @event.Timed(fields=["baz"])
    def Foo():
      pass

    with self.assertStatsCounterDelta(1, event, fields=["baz"]):
      Foo()

  def testMetricCanBeRegisteredAfterStatsCollectorHasBeenSetUp(self):
    with mock.patch.multiple(
        stats_collector_instance, _metadatas=[], _stats_singleton=None):
      stats_collector_instance.Set(
          default_stats_collector.DefaultStatsCollector())
      counter = metrics.Counter("cfoo")
      counter.Increment(1)


if __name__ == "__main__":
  absltest.main()
