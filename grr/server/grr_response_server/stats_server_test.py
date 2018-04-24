#!/usr/bin/env python
"""Test for the stats server implementation."""


import json


from grr.lib import flags
from grr.lib import stats
from grr.server.grr_response_server import stats_server

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
    self.assertEqual(
        set(varz_json["api_method_latency"]["value"].keys()),
        set(["sum", "bins_heights", "counter"]))

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
    self.assertEqual(varz_json["api_method_latency"]["value"].keys(),
                     ["Foo:http:SUCCESS"])
    self.assertEqual(
        set(varz_json["api_method_latency"]["value"]["Foo:http:SUCCESS"]
            .keys()), set(["sum", "bins_heights", "counter"]))


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
