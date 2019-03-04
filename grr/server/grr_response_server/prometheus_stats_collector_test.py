#!/usr/bin/env python
"""Tests for PrometheusStatsCollector."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app

from grr_response_core.stats import stats_test_utils
from grr_response_server import prometheus_stats_collector
from grr.test_lib import test_lib


class PrometheusStatsCollectorTest(stats_test_utils.StatsCollectorTest):

  def _CreateStatsCollector(self, metadata_list):
    return prometheus_stats_collector.PrometheusStatsCollector(metadata_list)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
