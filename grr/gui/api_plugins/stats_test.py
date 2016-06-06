#!/usr/bin/env python
"""This module contains tests for stats API handlers."""



from grr.gui import api_test_lib

from grr.lib import aff4
from grr.lib import flags
from grr.lib import stats
from grr.lib import test_lib
from grr.lib import utils

from grr.lib.aff4_objects import stats_store as aff4_stats_store

# TODO(user): Implement unit tests in addition to regression tests.


class ApiListStatsStoreMetricsMetadataHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):

  handler = "ApiListStatsStoreMetricsMetadataHandler"

  def Run(self):
    stats_collector = stats.StatsCollector()

    stats_collector.RegisterCounterMetric("sample_counter",
                                          docstring="Sample counter metric.")

    stats_collector.RegisterGaugeMetric("sample_gauge_value",
                                        str,
                                        docstring="Sample gauge metric.")

    stats_collector.RegisterEventMetric("sample_event",
                                        docstring="Sample event metric.")

    with utils.Stubber(stats, "STATS", stats_collector):
      with aff4.FACTORY.Create(None,
                               aff4_stats_store.StatsStore,
                               mode="w",
                               token=self.token) as stats_store:
        stats_store.WriteStats(process_id="worker_1", sync=True)

    self.Check("GET", "/api/stats/store/WORKER/metadata")


class ApiGetStatsStoreMetricHandlerRegressionTest(
    api_test_lib.ApiCallHandlerRegressionTest):

  handler = "ApiGetStatsStoreMetricHandler"

  def Run(self):
    stats_collector = stats.StatsCollector()

    stats_collector.RegisterCounterMetric("sample_counter",
                                          docstring="Sample counter metric.")

    stats_collector.RegisterGaugeMetric("sample_gauge_value",
                                        float,
                                        docstring="Sample gauge metric.")

    stats_collector.RegisterEventMetric("sample_event",
                                        docstring="Sample event metric.")

    with utils.Stubber(stats, "STATS", stats_collector):
      for i in range(10):
        with test_lib.FakeTime(42 + i * 60):
          stats_collector.IncrementCounter("sample_counter")
          stats_collector.SetGaugeValue("sample_gauge_value", i * 0.5)
          stats_collector.RecordEvent("sample_event", 0.42 + 0.5 * i)

          with aff4.FACTORY.Create(None,
                                   aff4_stats_store.StatsStore,
                                   mode="w",
                                   token=self.token) as stats_store:
            stats_store.WriteStats(process_id="worker_1", sync=True)

    self.Check("GET", "/api/stats/store/WORKER/metrics/sample_counter?"
               "start=42000000&end=3600000000")
    self.Check("GET", "/api/stats/store/WORKER/metrics/sample_counter?"
               "start=42000000&end=3600000000&rate=1m")

    self.Check("GET", "/api/stats/store/WORKER/metrics/sample_gauge_value?"
               "start=42000000&end=3600000000")

    self.Check("GET", "/api/stats/store/WORKER/metrics/sample_event?"
               "start=42000000&end=3600000000")
    self.Check("GET", "/api/stats/store/WORKER/metrics/sample_event?"
               "start=42000000&end=3600000000&"
               "distribution_handling_mode=DH_COUNT")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
