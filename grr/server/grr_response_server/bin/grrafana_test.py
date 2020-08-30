#!/usr/bin/env python
# Lint as: python3
"""Unittest for GRRafana HTTP server."""
from absl.testing import absltest
from absl import app, flags
import mock

from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2

from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server.bin import grrafana
from grr_response_server import server_startup

from werkzeug import serving as werkzeug_serving
from werkzeug import test as werkzeug_test

_TEST_CLIENT_IDS = ["C.0000000000000001", "C.0000000000000002"]


def _MockConnReturningClients(grr_ids):
  client_1 = admin_pb2.Client(
      client_id=fleetspeak_utils.GRRIDToFleetspeakID(grr_ids[0]))
  client_2 = admin_pb2.Client(
      client_id=fleetspeak_utils.GRRIDToFleetspeakID(grr_ids[1]))
  conn = mock.MagicMock()
  conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
      clients=[client_1, client_2])
  return conn


class GrrafanaTest(absltest.TestCase):
  """Test the GRRafana HTTP server."""

  def setUp(self):
    super(GrrafanaTest, self).setUp()
    self.client = werkzeug_test.Client(application=grrafana.Grrafana(),
                                      response_wrapper=grrafana.JSONResponse)
  def testRoot(self):
    response = self.client.get("/")
    self.assertEqual(200, response.status_code)

  def testSearchMetrics(self):
    response = self.client.post("/search", json={'type': 'timeseries', 'target': ''})
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
