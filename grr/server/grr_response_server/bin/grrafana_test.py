#!/usr/bin/env python
# Lint as: python3
"""Unittest for GRRafana HTTP server."""
from absl.testing import absltest
from absl import app
import mock

from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2, resource_pb2

from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server.bin import grrafana

from werkzeug import serving as werkzeug_serving
from werkzeug import test as werkzeug_test

_TEST_CLIENT_ID_1 = "C.0000000000000001"
_TEST_CLIENT_ID_2 = "C.0000000000000002"
_TEST_CLIENT_RESOURCE_USAGE_RECORD_1 = {
    "scope": "system",
    "pid": 2714460,
    "process_start_time": {
        "seconds": 1597327815,
        "nanos": 817468715
    },
    "client_timestamp": {
        "seconds": 1597328416,
        "nanos": 821525280
    },
    "server_timestamp": {
        "seconds": 1597328417,
        "nanos": 823124057
    },
    "mean_user_cpu_rate": 0.31883034110069275,
    "max_user_cpu_rate": 4.999776840209961,
    "mean_system_cpu_rate": 0.31883034110069275,
    "max_system_cpu_rate": 4.999776840209961,
    "mean_resident_memory_mib": 20,
    "max_resident_memory_mib": 20
}
_TEST_CLIENT_RESOURCE_USAGE_RECORD_2 = {
    "scope": "GRR",
    "pid": 2714474,
    "process_start_time": {
        "seconds": 1597327815,
        "nanos": 818657389
    },
    "client_timestamp": {
        "seconds": 1597328418,
        "nanos": 402023428
    },
    "server_timestamp": {
        "seconds": 1597328419,
        "nanos": 403123025
    },
    "mean_user_cpu_rate": 0.492735356092453,
    "max_user_cpu_rate": 4.999615669250488,
    "mean_system_cpu_rate": 0.07246342301368713,
    "max_system_cpu_rate": 0.3333326578140259,
    "mean_resident_memory_mib": 59,
    "max_resident_memory_mib": 59
}


def _MockConnReturningClients(grr_ids):
  clients = []
  for grr_id in grr_ids:
    client = admin_pb2.Client(
        client_id=fleetspeak_utils.GRRIDToFleetspeakID(grr_id))
    clients.append(client)
  conn = mock.MagicMock()
  conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
      clients=clients)
  return conn


def _MockConnReturningRecords(client_ruds):
  conn = mock.MagicMock()
  records = []
  for record in client_ruds:
    records.append(
        resource_pb2.ClientResourceUsageRecord(
            scope=record["scope"],
            pid=record["pid"],
            process_start_time=record["process_start_time"],
            client_timestamp=record["client_timestamp"],
            server_timestamp=record["server_timestamp"],
            mean_user_cpu_rate=record["mean_user_cpu_rate"],
            max_user_cpu_rate=record["max_user_cpu_rate"],
            mean_system_cpu_rate=record["mean_system_cpu_rate"],
            max_system_cpu_rate=record["max_system_cpu_rate"],
            mean_resident_memory_mib=record["mean_resident_memory_mib"],
            max_resident_memory_mib=record["max_resident_memory_mib"]))
  conn.outgoing.FetchClientResourceUsageRecords.return_value = admin_pb2.FetchClientResourceUsageRecordsResponse(
      records=records)
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
    self.assertEqual(200, response.status_code)
    self.assertListEqual(response.json, [
        "mean_user_cpu_rate",
        "max_user_cpu_rate",
        "mean_system_cpu_rate",
        "max_system_cpu_rate",
        "mean_resident_memory_mib",
        "max_resident_memory_mib",
    ])

  def testSearchClientIds(self):
    conn = _MockConnReturningClients([_TEST_CLIENT_ID_1, _TEST_CLIENT_ID_2])
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      response = self.client.post("/search", json={'target': 'some_query'})
      self.assertEqual(200, response.status_code)
      self.assertListEqual(response.json,
                       ["C.0000000000000001", "C.0000000000000002"])

  def testQuery(self):
    conn = _MockConnReturningRecords([_TEST_CLIENT_RESOURCE_USAGE_RECORD_1, _TEST_CLIENT_RESOURCE_USAGE_RECORD_2])
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      response = self.client.post(
          "/query",
          json={
              'app': 'dashboard',
              'requestId': 'Q119',
              'timezone': 'browser',
              'panelId': 2,
              'dashboardId': 77,
              'range': {
                  'from': '2020-08-13T14:20:17.000Z',
                  'to': '2020-08-18T17:15:58.000Z',
                  'raw': {
                      'from': '2020-08-13T14:20:17.000Z',
                      'to': '2020-08-18T17:15:58.000Z'
                  }
              },
              'timeInfo': '',
              'interval': '10m',
              'intervalMs': 600000,
              'targets': [{
                  'data': None,
                  'target': 'max_user_cpu_rate',
                  'refId': 'A',
                  'hide': False,
                  'type': 'timeseries'
              }, {
                  'data': None,
                  'target': 'mean_system_cpu_rate',
                  'refId': 'A',
                  'hide': False,
                  'type': 'timeseries'
              }],
              'maxDataPoints': 800,
              'scopedVars': {
                  'hellovar': {
                      'text': _TEST_CLIENT_ID_1,
                      'value': _TEST_CLIENT_ID_1
                  },
                  '__interval': {
                      'text': '10m',
                      'value': '10m'
                  },
                  '__interval_ms': {
                      'text': '600000',
                      'value': 600000
                  }
              },
              'startTime': 1598782453496,
              'rangeRaw': {
                  'from': '2020-08-13T14:20:17.000Z',
                  'to': '2020-08-18T17:15:58.000Z'
              },
              'adhocFilters': []
          })
      self.assertEqual(200, response.status_code)
      self.assertEqual(response.json, [{
          "target":
              "max_user_cpu_rate",
          "datapoints": [[4.999776840209961, 1597328417000],
                         [4.999615669250488, 1597328419000]]
      }, {
          "target":
              "mean_system_cpu_rate",
          "datapoints": [[0.31883034110069275, 1597328417000],
                         [0.07246342301368713, 1597328419000]]
      }])


def main(argv):
  absltest.main(argv)


if __name__ == "__main__":
  app.run(main)
