#!/usr/bin/env python
"""Tests for the DefaultStatsCollector."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_test_utils
from grr.test_lib import test_lib


class DefaultStatsCollectorTest(stats_test_utils.StatsCollectorTest):

  def _CreateStatsCollector(self, metadata_list):
    return default_stats_collector.DefaultStatsCollector(metadata_list)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
