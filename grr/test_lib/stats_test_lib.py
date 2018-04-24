#!/usr/bin/env python
"""Classes for stats-related testing."""

import mock

from grr.lib import stats


class StatsDeltaAssertionContext(object):
  """A context manager to check the stats variable changes."""

  def __init__(self, test, delta, varname, fields=None):
    self.test = test
    self.varname = varname
    self.fields = fields
    self.delta = delta

  def __enter__(self):
    self.prev_count = stats.STATS.GetMetricValue(
        self.varname, fields=self.fields)
    # Handle the case when we're dealing with distributions.
    if hasattr(self.prev_count, "count"):
      self.prev_count = self.prev_count.count

  def __exit__(self, unused_type, unused_value, unused_traceback):
    new_count = stats.STATS.GetMetricValue(
        varname=self.varname, fields=self.fields)
    if hasattr(new_count, "count"):
      new_count = new_count.count

    self.test.assertEqual(
        new_count - self.prev_count, self.delta,
        "%s (fields=%s) expected to change with delta=%d" %
        (self.varname, self.fields, self.delta))


class StatsTestMixin(object):
  """Mixing for stats-related assertions."""

  def setUp(self):  # pylint: disable=invalid-name
    super(StatsTestMixin, self).setUp()
    self._stats_patcher = mock.patch.object(stats, "STATS",
                                            stats.StatsCollector())
    self._stats_patcher.start()

  def tearDown(self):  # pylint: disable=invalid-name
    self._stats_patcher.stop()
    super(StatsTestMixin, self).tearDown()

  # pylint: disable=invalid-name
  def assertStatsCounterDelta(self, delta, varname, fields=None):
    return StatsDeltaAssertionContext(self, delta, varname, fields=fields)

  # pylint: enable=invalid-name
