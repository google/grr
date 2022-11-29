#!/usr/bin/env python
"""Unittest for GRRafana HTTP server."""
import copy
from unittest import mock

from absl import app
from absl.testing import absltest
from werkzeug import test as werkzeug_test
from werkzeug import wrappers as werkzeug_wrappers

from google.protobuf import timestamp_pb2

from grr_response_server import data_store
from grr_response_server import fleetspeak_connector
from grr_response_server.bin import grrafana
from grr_response_server.fleet_utils import FleetStats

from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2
from fleetspeak.src.server.proto.fleetspeak_server import resource_pb2

_TEST_CLIENT_ID_1 = "C.0000000000000001"
_TEST_CLIENT_ID_2 = "C.0000000000000002"
_START_RANGE_TIMESTAMP = "2020-08-13T14:20:17.158Z"
_END_RANGE_TIMESTAMP = "2020-08-18T17:15:58.761Z"
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
_TEST_CLIENT_BREAKDOWN_STATS = FleetStats(
    day_buckets=grrafana._FLEET_BREAKDOWN_DAY_BUCKETS,
    label_counts={
        1: {
            "foo-label": {
                "bar-os": 3,
                "baz-os": 4
            },
            "bar-label": {
                "bar-os": 5,
                "foo-os": 1
            }
        },
        7: {
            "foo-label": {
                "bar-os": 6,
                "baz-os": 5
            },
            "bar-label": {
                "bar-os": 5,
                "foo-os": 2
            }
        },
        14: {
            "foo-label": {
                "bar-os": 6,
                "baz-os": 5
            },
            "bar-label": {
                "bar-os": 5,
                "foo-os": 2
            },
            "baz-label": {
                "bar-os": 1
            }
        },
        30: {
            "foo-label": {
                "bar-os": 6,
                "baz-os": 5
            },
            "bar-label": {
                "bar-os": 5,
                "foo-os": 2
            },
            "baz-label": {
                "bar-os": 3,
                "foo-os": 1
            }
        }
    },
    total_counts={
        1: {
            "bar-os": 8,
            "baz-os": 4,
            "foo-os": 1
        },
        7: {
            "bar-os": 11,
            "baz-os": 5,
            "foo-os": 2
        },
        14: {
            "bar-os": 12,
            "baz-os": 5,
            "foo-os": 2
        },
        30: {
            "bar-os": 14,
            "baz-os": 5,
            "foo-os": 3
        }
    })
_TEST_VALID_RUD_QUERY = {
    "app": "dashboard",
    "requestId": "Q119",
    "timezone": "browser",
    "panelId": 2,
    "dashboardId": 77,
    "range": {
        "from": _START_RANGE_TIMESTAMP,
        "to": _END_RANGE_TIMESTAMP,
        "raw": {
            "from": _START_RANGE_TIMESTAMP,
            "to": _END_RANGE_TIMESTAMP
        }
    },
    "timeInfo": "",
    "interval": "10m",
    "intervalMs": 600000,
    "targets": [{
        "data": None,
        "target": "Max User CPU Rate",
        "refId": "A",
        "hide": False,
        "type": "timeseries"
    }, {
        "data": None,
        "target": "Mean System CPU Rate",
        "refId": "A",
        "hide": False,
        "type": "timeseries"
    }],
    "maxDataPoints": 800,
    "scopedVars": {
        "ClientID": {
            "text": _TEST_CLIENT_ID_1,
            "value": _TEST_CLIENT_ID_1
        },
        "__interval": {
            "text": "10m",
            "value": "10m"
        },
        "__interval_ms": {
            "text": "600000",
            "value": 600000
        }
    },
    "startTime": 1598782453496,
    "rangeRaw": {
        "from": _START_RANGE_TIMESTAMP,
        "to": _END_RANGE_TIMESTAMP
    },
    "adhocFilters": []
}
_TEST_VALID_CLIENT_STATS_QUERY = {
    "app": "dashboard",
    "requestId": "Q1",
    "timezone": "browser",
    "panelId": 12345,
    "dashboardId": 1,
    "range": {
        "from": "2020-10-21T04:29:36.806Z",
        "to": "2020-10-21T10:29:36.806Z",
        "raw": {
            "from": "now-6h",
            "to": "now"
        }
    },
    "timeInfo": "",
    "interval": "15s",
    "intervalMs": 15000,
    "targets": [{
        "data": "",
        "refId": "A",
        "target": "OS Platform Breakdown - 7 Day Active",
        "type": "timeseries",
        "datasource": "JSON"
    }],
    "maxDataPoints": 1700,
    "scopedVars": {
        "__interval": {
            "text": "15s",
            "value": "15s"
        },
        "__interval_ms": {
            "text": "15000",
            "value": 15000
        }
    },
    "startTime": 1603276176806,
    "rangeRaw": {
        "from": "now-6h",
        "to": "now"
    },
    "adhocFilters": [],
    "endTime": 1603276176858
}
_TEST_INVALID_TARGET_QUERY = copy.deepcopy(_TEST_VALID_RUD_QUERY)
_TEST_INVALID_TARGET_QUERY["targets"][0]["target"] = "unavailable_metric"


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


def _MockDatastoreReturningPlatformFleetStats(client_fleet_stats):
  client_fleet_stats.Validate()
  rel_db = mock.MagicMock()
  rel_db.CountClientPlatformsByLabel.return_value = client_fleet_stats
  return rel_db


class GrrafanaTest(absltest.TestCase):
  """Test the GRRafana HTTP server."""

  def setUp(self):
    super().setUp()
    self.client = werkzeug_test.Client(
        application=grrafana.Grrafana(),
        response_wrapper=werkzeug_wrappers.Response)

  def testRoot(self):
    response = self.client.get("/")
    self.assertEqual(200, response.status_code)

  def testSearchMetrics(self):
    response = self.client.post(
        "/search", json={
            "type": "timeseries",
            "target": ""
        })
    self.assertEqual(200, response.status_code)

    expected_res = [
        "Mean User CPU Rate", "Max User CPU Rate", "Mean System CPU Rate",
        "Max System CPU Rate", "Mean Resident Memory MB",
        "Max Resident Memory MB"
    ]
    expected_res.extend([
        f"OS Platform Breakdown - {n_days} Day Active"
        for n_days in grrafana._FLEET_BREAKDOWN_DAY_BUCKETS
    ])
    expected_res.extend([
        f"OS Release Version Breakdown - {n_days} Day Active"
        for n_days in grrafana._FLEET_BREAKDOWN_DAY_BUCKETS
    ])
    expected_res.extend([
        f"Client Version Strings - {n_days} Day Active"
        for n_days in grrafana._FLEET_BREAKDOWN_DAY_BUCKETS
    ])
    self.assertListEqual(response.json, expected_res)

  def testClientResourceUsageMetricQuery(self):
    conn = _MockConnReturningRecords([
        _TEST_CLIENT_RESOURCE_USAGE_RECORD_1,
        _TEST_CLIENT_RESOURCE_USAGE_RECORD_2
    ])
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      valid_response = self.client.post("/query", json=_TEST_VALID_RUD_QUERY)
      self.assertEqual(200, valid_response.status_code)
      self.assertEqual(valid_response.json, [{
          "target":
              "Max User CPU Rate",
          "datapoints": [[4.999776840209961, 1597328417823],
                         [4.999615669250488, 1597328419403]]
      }, {
          "target":
              "Mean System CPU Rate",
          "datapoints": [[0.31883034110069275, 1597328417823],
                         [0.07246342301368713, 1597328419403]]
      }])

  def testQueryInvalidRequest(self):
    conn = _MockConnReturningRecords([
        _TEST_CLIENT_RESOURCE_USAGE_RECORD_1,
        _TEST_CLIENT_RESOURCE_USAGE_RECORD_2
    ])
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      with self.assertRaises(KeyError):
        self.client.post("/query", json=_TEST_INVALID_TARGET_QUERY)

  def testClientsStatisticsMetric(self):
    rel_db = _MockDatastoreReturningPlatformFleetStats(
        _TEST_CLIENT_BREAKDOWN_STATS)
    with mock.patch.object(data_store, "REL_DB", rel_db):
      valid_response = self.client.post(
          "/query", json=_TEST_VALID_CLIENT_STATS_QUERY)
      self.assertEqual(200, valid_response.status_code)
      expected_res = [{
          "columns": [{
              "text": "Label",
              "type": "string"
          }, {
              "text": "Value",
              "type": "number"
          }],
          "rows": [["bar-os", 11], ["baz-os", 5], ["foo-os", 2]],
          "type": "table"
      }]
      self.assertEqual(valid_response.json, expected_res)


class TimeToProtoTimestampTest(absltest.TestCase):
  """Tests the conversion between Grafana and proto timestamps."""

  def testTimeToProtoTimestamp(self):
    self.assertEqual(
        grrafana.TimeToProtoTimestamp(_START_RANGE_TIMESTAMP),
        timestamp_pb2.Timestamp(seconds=1597328417, nanos=(158 * 1000000)))
    self.assertEqual(
        grrafana.TimeToProtoTimestamp(_END_RANGE_TIMESTAMP),
        timestamp_pb2.Timestamp(seconds=1597770958, nanos=(761 * 1000000)))


def main(argv):
  absltest.main(argv)


if __name__ == "__main__":
  app.run(main)
