#!/usr/bin/env python
from unittest import mock

from absl.testing import absltest

from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import metrics
from grr_response_proto.api import stats_pb2
from grr_response_server.gui import admin_ui_metrics
from grr_response_server.gui import api_test_lib
from grr_response_server.gui.api_plugins import stats
from grr.test_lib import stats_test_lib
from grr.test_lib import testing_startup


class StatsTest(
    stats_test_lib.StatsCollectorTestMixin,
    api_test_lib.ApiCallHandlerTest,
):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  def setUp(self):
    super().setUp()
    self.handler = stats.ApiIncrementCounterMetricHandler()

  @mock.patch.object(
      admin_ui_metrics,
      "API_INCREASE_ALLOWLIST",
      frozenset(["bananas_de_pijamas_counter"]),
  )
  def testIncreasesExistingMetric(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()
    ):
      counter = metrics.Counter(
          "bananas_de_pijamas_counter", fields=[("name", str), ("number", int)]
      )

    args = stats_pb2.ApiIncrementCounterMetricArgs(
        metric_name="bananas_de_pijamas_counter",
        field_values=[
            stats_pb2.FieldValue(
                field_type=stats_pb2.FieldValue.STRING, string_value="b"
            ),
            stats_pb2.FieldValue(
                field_type=stats_pb2.FieldValue.NUMBER, number_value=2
            ),
        ],
    )

    self.assertEqual(0, counter.GetValue(fields=["b", 1]))
    self.assertEqual(0, counter.GetValue(fields=["b", 2]))

    self.handler.Handle(args, context=self.context)

    self.assertEqual(0, counter.GetValue(fields=["b", 1]))
    self.assertEqual(1, counter.GetValue(fields=["b", 2]))

  @mock.patch.object(
      admin_ui_metrics,
      "API_INCREASE_ALLOWLIST",
      frozenset(["nothing_allowlisted"]),
  )
  def testRaisesNotAllowlisted(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()
    ):
      metrics.Counter(
          "bananas_de_pijamas_counter", fields=[("name", str), ("number", int)]
      )

    args = stats_pb2.ApiIncrementCounterMetricArgs(
        metric_name="invalid_counter_does_not_exist",
        field_values=[
            stats_pb2.FieldValue(
                field_type=stats_pb2.FieldValue.STRING, string_value="b"
            ),
            stats_pb2.FieldValue(
                field_type=stats_pb2.FieldValue.NUMBER, number_value=2
            ),
        ],
    )

    with self.assertRaises(ValueError):
      self.handler.Handle(args, context=self.context)

  @mock.patch.object(
      admin_ui_metrics,
      "API_INCREASE_ALLOWLIST",
      frozenset(
          ["bananas_de_pijamas_counter", "invalid_counter_does_not_exist"]
      ),
  )
  def testRaisesWithInvalidMetric(self):
    with self.SetUpStatsCollector(
        default_stats_collector.DefaultStatsCollector()
    ):
      metrics.Counter(
          "bananas_de_pijamas_counter", fields=[("name", str), ("number", int)]
      )

    args = stats_pb2.ApiIncrementCounterMetricArgs(
        metric_name="invalid_counter_does_not_exist",
        field_values=[
            stats_pb2.FieldValue(
                field_type=stats_pb2.FieldValue.STRING, string_value="b"
            ),
            stats_pb2.FieldValue(
                field_type=stats_pb2.FieldValue.NUMBER, number_value=2
            ),
        ],
    )

    with self.assertRaises(KeyError):
      self.handler.Handle(args, context=self.context)


if __name__ == "__main__":
  absltest.main()
