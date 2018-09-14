#!/usr/bin/env python
"""Test for the stats server implementation."""
from __future__ import unicode_literals

import json


from future.utils import iterkeys

from grr_response_core.lib import flags
from grr_response_core.lib import stats
from grr_response_server import stats_server

from grr.test_lib import test_lib


class StatsServerTest(test_lib.GRRBaseTest):
  """Tests the authentication package of the data server."""

  def testEventMetricGetsRendered(self):
    stats.STATS.RegisterEventMetric("api_method_latency")
    stats.STATS.RecordEvent("api_method_latency", 15)

    varz_json = json.loads(stats_server.BuildVarzJsonString())
    self.assertEqual(varz_json["api_method_latency"]["info"],
                     {"metric_type": "EVENT",
                      "value_type": "DISTRIBUTION"})
    self.assertItemsEqual(
        iterkeys(varz_json["api_method_latency"]["value"]),
        ["sum", "bins_heights", "counter"])

  def testMetricWithMultipleFieldsGetsRendered(self):
    stats.STATS.RegisterEventMetric(
        "api_method_latency",
        fields=[("method_name", str), ("protocol", str), ("status", str)])
    stats.STATS.RecordEvent(
        "api_method_latency", 15, fields=["Foo", "http", "SUCCESS"])

    varz_json = json.loads(stats_server.BuildVarzJsonString())
    self.assertEqual(varz_json["api_method_latency"]["info"], {
        "metric_type":
            "EVENT",
        "value_type":
            "DISTRIBUTION",
        "fields_defs": [["method_name", "STR"], ["protocol", "STR"],
                        ["status", "STR"]]
    })

    api_method_latency_value = varz_json["api_method_latency"]["value"]
    self.assertEqual(
        list(iterkeys(api_method_latency_value)), ["Foo:http:SUCCESS"])
    self.assertItemsEqual(
        iterkeys(api_method_latency_value["Foo:http:SUCCESS"]),
        ["sum", "bins_heights", "counter"])


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
