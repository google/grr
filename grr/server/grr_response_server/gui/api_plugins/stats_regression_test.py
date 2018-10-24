#!/usr/bin/env python
"""This module contains regression tests for stats API handlers."""
from __future__ import absolute_import
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_test_utils
from grr_response_core.stats import stats_utils
from grr_response_server import aff4
from grr_response_server.aff4_objects import stats_store as aff4_stats_store
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import stats as stats_plugin
from grr_response_server.gui.api_plugins.report_plugins import report_plugins_test_mocks

from grr.test_lib import test_lib

# TODO(user): Implement unit tests in addition to regression tests.


class ApiListStatsStoreMetricsMetadataHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "ListStatsStoreMetricsMetadata"
  handler = stats_plugin.ApiListStatsStoreMetricsMetadataHandler

  def Run(self):
    stats_collector = default_stats_collector.DefaultStatsCollector([
        stats_utils.CreateCounterMetadata(
            "sample_counter", docstring="Sample counter metric."),
        stats_utils.CreateGaugeMetadata(
            "sample_gauge_value", str, docstring="Sample gauge metric."),
        stats_utils.CreateEventMetadata(
            "sample_event", docstring="Sample event metric."),
    ])

    with stats_test_utils.FakeStatsContext(stats_collector):
      with aff4.FACTORY.Create(
          None, aff4_stats_store.StatsStore, mode="w",
          token=self.token) as stats_store:
        stats_store.WriteStats(process_id="worker_1")

    self.Check(
        "ListStatsStoreMetricsMetadata",
        args=stats_plugin.ApiListStatsStoreMetricsMetadataArgs(
            component="WORKER"))


class ApiGetStatsStoreMetricHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "GetStatsStoreMetric"
  handler = stats_plugin.ApiGetStatsStoreMetricHandler

  def Run(self):
    stats_collector = default_stats_collector.DefaultStatsCollector([
        stats_utils.CreateCounterMetadata(
            "sample_counter", docstring="Sample counter metric."),
        stats_utils.CreateGaugeMetadata(
            "sample_gauge_value", float, docstring="Sample gauge metric."),
        stats_utils.CreateEventMetadata(
            "sample_event", docstring="Sample event metric."),
    ])

    with stats_test_utils.FakeStatsContext(stats_collector):
      for i in range(10):
        with test_lib.FakeTime(42 + i * 60):
          stats_collector.IncrementCounter("sample_counter")
          stats_collector.SetGaugeValue("sample_gauge_value", i * 0.5)
          stats_collector.RecordEvent("sample_event", 0.42 + 0.5 * i)

          with aff4.FACTORY.Create(
              None, aff4_stats_store.StatsStore, mode="w",
              token=self.token) as stats_store:
            stats_store.WriteStats(process_id="worker_1")

    self.Check(
        "GetStatsStoreMetric",
        args=stats_plugin.ApiGetStatsStoreMetricArgs(
            component="WORKER",
            metric_name="sample_counter",
            start=42000000,
            end=3600000000))
    self.Check(
        "GetStatsStoreMetric",
        args=stats_plugin.ApiGetStatsStoreMetricArgs(
            component="WORKER",
            metric_name="sample_counter",
            start=42000000,
            end=3600000000,
            rate="1m"))

    self.Check(
        "GetStatsStoreMetric",
        args=stats_plugin.ApiGetStatsStoreMetricArgs(
            component="WORKER",
            metric_name="sample_gauge_value",
            start=42000000,
            end=3600000000))

    self.Check(
        "GetStatsStoreMetric",
        args=stats_plugin.ApiGetStatsStoreMetricArgs(
            component="WORKER",
            metric_name="sample_event",
            start=42000000,
            end=3600000000))
    self.Check(
        "GetStatsStoreMetric",
        args=stats_plugin.ApiGetStatsStoreMetricArgs(
            component="WORKER",
            metric_name="sample_event",
            start=42000000,
            end=3600000000,
            distribution_handling_mode="DH_COUNT"))


class ApiListReportsHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "ListReports"
  handler = stats_plugin.ApiListReportsHandler

  def Run(self):
    with report_plugins_test_mocks.MockedReportPlugins():
      self.Check("ListReports")


class ApiGetReportRegressionTest(api_regression_test_lib.ApiRegressionTest):

  api_method = "GetReport"
  handler = stats_plugin.ApiGetReportHandler

  def Run(self):
    with report_plugins_test_mocks.MockedReportPlugins():
      self.Check(
          "GetReport",
          args=stats_plugin.ApiGetReportArgs(
              name="BarReportPlugin",
              start_time=rdfvalue.RDFDatetime.FromHumanReadable("2012/12/14")
              .AsMicrosecondsSinceEpoch(),
              duration="4d"))


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
