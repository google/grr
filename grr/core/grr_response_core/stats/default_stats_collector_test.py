#!/usr/bin/env python
"""Tests for the DefaultStatsCollector."""

from collections.abc import Sequence

from absl import app

from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_test_utils
from grr.test_lib import test_lib


class DefaultStatsCollectorTest(stats_test_utils.StatsCollectorTest):

  def _CreateStatsCollector(
      self,
  ) -> default_stats_collector.DefaultStatsCollector:
    return default_stats_collector.DefaultStatsCollector()


def main(argv: Sequence[str]) -> None:
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
