#!/usr/bin/env python
# Lint as: python3
"""Unittest for GRRafana HTTP server."""
from absl.testing import absltest
from absl import app

from grr_response_server import fleetspeak_connector
from grr_response_server.bin import grrafana
from grr_response_server import server_startup

from werkzeug import serving as werkzeug_serving
from werkzeug import test as werkzeug_test


class GrrafanaTest(absltest.TestCase):
  """Test the GRRafana HTTP server."""

  def testRoot(self):
    client = werkzeug_test.Client(grrafana.Grrafana(), grrafana.JSONResponse)
    response = client.get('/')
    self.assertEqual(200, response.status_code)

  def testSearchMetrics(self):
    client = werkzeug_test.Client(application=grrafana.Grrafana(),
                                  response_wrapper=grrafana.JSONResponse)
    response = client.post("/search", json={'type': 'timeseries', 'target': ''})
    self.assertEqual(response.json, [
        "mean_user_cpu_rate",
        "max_user_cpu_rate",
        "mean_system_cpu_rate",
        "max_system_cpu_rate",
        "mean_resident_memory_mib",
        "max_resident_memory_mib",
    ])


def main(argv):
  absltest.main(argv)


if __name__ == "__main__":
  app.run(main)
