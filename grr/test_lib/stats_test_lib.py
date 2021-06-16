#!/usr/bin/env python
"""Classes for stats-related testing."""

import contextlib
from unittest import mock

from grr_response_core.lib.util import precondition
from grr_response_core.stats import metrics
from grr_response_core.stats import stats_collector_instance


class StatsDeltaAssertionContext(object):
  """A context manager to check the stats variable changes."""

  def __init__(self, test, delta, metric, fields=None):
    precondition.AssertType(metric, metrics.AbstractMetric)
    self.test = test
    self.metric = metric
    self.fields = fields
    self.delta = delta

  def __enter__(self):
    self.prev_count = self.metric.GetValue(fields=self.fields)
    # Handle the case when we're dealing with distributions.
    if hasattr(self.prev_count, "count"):
      self.prev_count = self.prev_count.count

  def __exit__(self, unused_type, unused_value, unused_traceback):
    new_count = self.metric.GetValue(fields=self.fields)
    if hasattr(new_count, "count"):
      new_count = new_count.count

    actual = new_count - self.prev_count

    self.test.assertEqual(
        actual, self.delta,
        "%s (fields=%s) expected to change with delta=%d, but changed by %d. "
        "Metric has field values %s." %
        (self.metric.name, self.fields, self.delta, actual,
         self.metric.GetFields()))


class StatsTestMixin(object):
  """Mixin for stats-related assertions."""

  # pylint: disable=invalid-name
  def assertStatsCounterDelta(self, delta, metric, fields=None):
    return StatsDeltaAssertionContext(self, delta, metric, fields=fields)

  # pylint: enable=invalid-name


class StatsCollectorTestMixin(object):
  """Mixin for setting up a StatsCollector with metrics."""

  @contextlib.contextmanager
  def SetUpStatsCollector(self, collector):
    patcher = mock.patch.multiple(
        stats_collector_instance, _metadatas=[], _stats_singleton=None)
    patcher.start()
    self.addCleanup(patcher.stop)
    yield
    stats_collector_instance.Set(collector)
    self.collector = stats_collector_instance.Get()
