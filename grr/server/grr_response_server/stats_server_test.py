#!/usr/bin/env python
# Lint as: python3
"""Test for the stats server implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io

from absl import app
import mock
import portpicker
import prometheus_client
import prometheus_client.parser as prometheus_parser
import requests

from grr_response_core.stats import metrics
from grr_response_server import base_stats_server_test
from grr_response_server import prometheus_stats_collector
from grr_response_server import stats_server
from grr.test_lib import stats_test_lib
from grr.test_lib import test_lib


class StatsServerTest(base_stats_server_test.StatsServerTestMixin,
                      stats_test_lib.StatsCollectorTestMixin,
                      test_lib.GRRBaseTest):

  def setUpStatsServer(self, port):
    return stats_server.StatsServer(port)

  def testPrometheusIntegration(self):
    registry = prometheus_client.CollectorRegistry(auto_describe=True)
    collector = prometheus_stats_collector.PrometheusStatsCollector(
        registry=registry)

    with self.SetUpStatsCollector(collector):
      counter = metrics.Counter("foobars")
    counter.Increment(42)

    port = portpicker.pick_unused_port()

    with mock.patch.object(stats_server.StatsServerHandler, "registry",
                           registry):
      server = stats_server.StatsServer(port)
      server.Start()
      self.addCleanup(server.Stop)
      res = requests.get("http://localhost:{}/metrics".format(port))

    text_fd = io.StringIO(res.text)
    families = prometheus_parser.text_fd_to_metric_families(text_fd)
    families = {family.name: family for family in families}

    self.assertIn("foobars", families)
    self.assertEqual(families["foobars"].samples[0].value, 42)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
