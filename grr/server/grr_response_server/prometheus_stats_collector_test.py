#!/usr/bin/env python
from collections.abc import Sequence

from absl import app

from grr_response_core.stats import stats_test_utils
from grr_response_server import prometheus_stats_collector
from grr.test_lib import test_lib


class PrometheusStatsCollectorTest(stats_test_utils.StatsCollectorTest):

  def _CreateStatsCollector(
      self,
  ) -> prometheus_stats_collector.PrometheusStatsCollector:
    return prometheus_stats_collector.PrometheusStatsCollector()


def main(argv: Sequence[str]) -> None:
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
