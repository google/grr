#!/usr/bin/env python
"""Classes for stats-related testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.stats import stats_collector_instance


class StatsDeltaAssertionContext(object):
  """A context manager to check the stats variable changes."""

  def __init__(self, test, delta, varname, fields=None):
    self.test = test
    self.varname = varname
    self.fields = fields
    self.delta = delta

  def __enter__(self):
    self.prev_count = stats_collector_instance.Get().GetMetricValue(
        self.varname, fields=self.fields)
    # Handle the case when we're dealing with distributions.
    if hasattr(self.prev_count, "count"):
      self.prev_count = self.prev_count.count

  def __exit__(self, unused_type, unused_value, unused_traceback):
    new_count = stats_collector_instance.Get().GetMetricValue(
        self.varname, fields=self.fields)
    if hasattr(new_count, "count"):
      new_count = new_count.count

    actual = new_count - self.prev_count
    self.test.assertEqual(
        actual, self.delta,
        "%s (fields=%s) expected to change with delta=%d, but changed by %d" %
        (self.varname, self.fields, self.delta, actual))


class StatsTestMixin(object):
  """Mixin for stats-related assertions."""

  # pylint: disable=invalid-name
  def assertStatsCounterDelta(self, delta, varname, fields=None):
    return StatsDeltaAssertionContext(self, delta, varname, fields=fields)

  # pylint: enable=invalid-name
