#!/usr/bin/env python
"""This module contains regression tests for stats API handlers."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from builtins import range  # pylint: disable=redefined-builtin
from future.utils import itervalues

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_core.stats import stats_test_utils
from grr_response_core.stats import stats_utils
from grr_response_server import stats_store
from grr_response_server.gui import api_regression_http
from grr_response_server.gui import api_regression_test_lib
from grr_response_server.gui.api_plugins import stats as stats_plugin
from grr_response_server.gui.api_plugins.report_plugins import report_plugins_test_mocks


from grr.test_lib import test_lib

# TODO(user): Implement unit tests in addition to regression tests.


# Test metrics used in this test.
_TEST_COUNTER = "sample_counter"
_TEST_GAUGE_METRIC = "sample_gauge_value"
_TEST_EVENT_METRIC = "sample_event"


class ApiListStatsStoreMetricsMetadataHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "ListStatsStoreMetricsMetadata"
  handler = stats_plugin.ApiListStatsStoreMetricsMetadataHandler

  def _PostProcessApiResult(self, api_result):
    """Processes results of the API call before comparing with golden data.

    The ListStatsStoreMetricsMetadata API method returns all registered
    metrics, including non-test metrics that are used by server code that runs
    during the test. This method filters out all the non-test metrics, leaving
    only the ones that are relevant to this test.

    Args:
      api_result: An object representing the result returned by the API. For the
        HTTP API, this will be a list of dicts representing a JSON response.
    """
    test_metrics = {_TEST_COUNTER, _TEST_GAUGE_METRIC, _TEST_EVENT_METRIC}
    if self.api_version == 1:
      filtered_typed_data = [
          item for item in api_result["response"]["items"]
          if item["value"]["varname"]["value"] in test_metrics
      ]
      filtered_untyped_data = [
          item for item in api_result["type_stripped_response"]["items"]
          if item["varname"] in test_metrics
      ]
      api_result["response"]["items"] = filtered_typed_data
      api_result["type_stripped_response"]["items"] = filtered_untyped_data
    else:
      filtered_untyped_data = [
          item for item in api_result["response"]["items"]
          if item["varname"] in test_metrics
      ]
      api_result["response"]["items"] = filtered_untyped_data

  def Run(self):
    # We have to include all server metadata in the test context since server
    # code that uses the metrics runs within the context.
    non_test_metadata = list(
        itervalues(stats_collector_instance.Get().GetAllMetricsMetadata()))
    test_metadata = non_test_metadata + [
        stats_utils.CreateCounterMetadata(
            _TEST_COUNTER, docstring="Sample counter metric."),
        stats_utils.CreateGaugeMetadata(
            _TEST_GAUGE_METRIC, str, docstring="Sample gauge metric."),
        stats_utils.CreateEventMetadata(
            _TEST_EVENT_METRIC, docstring="Sample event metric."),
    ]
    stats_collector = default_stats_collector.DefaultStatsCollector(
        test_metadata)
    with stats_test_utils.FakeStatsContext(stats_collector):
      # We use mixins to run the same tests against multiple APIs.
      # Result-filtering is only needed for HTTP API tests.
      if isinstance(self, api_regression_http.HttpApiRegressionTestMixinBase):
        api_post_process_fn = self._PostProcessApiResult
      else:
        api_post_process_fn = None

      self.Check(
          "ListStatsStoreMetricsMetadata",
          args=stats_plugin.ApiListStatsStoreMetricsMetadataArgs(
              component="WORKER"),
          api_post_process_fn=api_post_process_fn)


class ApiGetStatsStoreMetricHandlerRegressionTest(
    api_regression_test_lib.ApiRegressionTest):

  api_method = "GetStatsStoreMetric"
  handler = stats_plugin.ApiGetStatsStoreMetricHandler

  def Run(self):
    with test_lib.ConfigOverrider({"Database.useForReads.stats": True}):
      real_metric_metadata = list(
          itervalues(stats_collector_instance.Get().GetAllMetricsMetadata()))
      test_metadata = real_metric_metadata + [
          stats_utils.CreateCounterMetadata(
              _TEST_COUNTER, docstring="Sample counter metric."),
          stats_utils.CreateGaugeMetadata(
              _TEST_GAUGE_METRIC, float, docstring="Sample gauge metric."),
          stats_utils.CreateEventMetadata(
              _TEST_EVENT_METRIC, docstring="Sample event metric."),
      ]
      stats_collector = default_stats_collector.DefaultStatsCollector(
          test_metadata)
      with stats_test_utils.FakeStatsContext(stats_collector):
        for i in range(10):
          with test_lib.FakeTime(42 + i * 60):
            stats_collector.IncrementCounter(_TEST_COUNTER)
            stats_collector.SetGaugeValue(_TEST_GAUGE_METRIC, i * 0.5)
            stats_collector.RecordEvent(_TEST_EVENT_METRIC, 0.42 + 0.5 * i)
            stats_store._WriteStats(process_id="worker_1")

        range_start = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42)
        range_end = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(3600)

        self.Check(
            "GetStatsStoreMetric",
            args=stats_plugin.ApiGetStatsStoreMetricArgs(
                component="WORKER",
                metric_name=_TEST_COUNTER,
                start=range_start,
                end=range_end))
        self.Check(
            "GetStatsStoreMetric",
            args=stats_plugin.ApiGetStatsStoreMetricArgs(
                component="WORKER",
                metric_name=_TEST_COUNTER,
                start=range_start,
                end=range_end,
                rate="1m"))

        self.Check(
            "GetStatsStoreMetric",
            args=stats_plugin.ApiGetStatsStoreMetricArgs(
                component="WORKER",
                metric_name=_TEST_GAUGE_METRIC,
                start=range_start,
                end=range_end))

        self.Check(
            "GetStatsStoreMetric",
            args=stats_plugin.ApiGetStatsStoreMetricArgs(
                component="WORKER",
                metric_name=_TEST_EVENT_METRIC,
                start=range_start,
                end=range_end))
        self.Check(
            "GetStatsStoreMetric",
            args=stats_plugin.ApiGetStatsStoreMetricArgs(
                component="WORKER",
                metric_name=_TEST_EVENT_METRIC,
                start=range_start,
                end=range_end,
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
