#!/usr/bin/env python
"""Test for the stats server implementation."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io


from absl import app
import mock
import prometheus_client
import prometheus_client.parser as prometheus_parser

from grr_response_core.stats import stats_utils
from grr_response_server import base_stats_server_test
from grr_response_server import prometheus_stats_collector
from grr_response_server import stats_server
from grr.test_lib import test_lib


class StatsServerTest(base_stats_server_test.StatsServerTestMixin,
                      test_lib.GRRBaseTest):

  def setUpStatsServer(self, port):
    return stats_server.StatsServer(port)

  def testPrometheusIntegration(self):
    registry = prometheus_client.CollectorRegistry(auto_describe=True)

    metadatas = [stats_utils.CreateCounterMetadata("foobars")]
    collector = prometheus_stats_collector.PrometheusStatsCollector(
        metadatas, registry=registry)
    collector.IncrementCounter("foobars", 42)

    handler = stats_server.StatsServerHandler(
        mock.MagicMock(), mock.MagicMock(), mock.MagicMock())
    handler.registry = registry
    handler.path = "/metrics"
    handler.headers = {}
    handler.wfile = io.BytesIO()

    handler.do_GET()
    handler.wfile.seek(0)

    families = prometheus_parser.text_fd_to_metric_families(handler.wfile)
    families = {family.name: family for family in families}

    self.assertIn("foobars", families)
    self.assertEqual(families["foobars"].samples[0].value, 42)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
