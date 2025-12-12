#!/usr/bin/env python
"""Unittest for GRRafana HTTP server."""

import copy
from unittest import mock

from absl.testing import absltest
from werkzeug import test as werkzeug_test
from werkzeug import wrappers as werkzeug_wrappers

from google.protobuf import timestamp_pb2
from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_server import fleetspeak_connector
from grr_response_server.bin import grrafana
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2
from fleetspeak.src.server.proto.fleetspeak_server import resource_pb2

_TEST_CLIENT_ID_1 = "C.0000000000000001"
_TEST_CLIENT_ID_2 = "C.0000000000000002"
_START_RANGE_TIMESTAMP = "2020-08-13T14:20:17.158Z"
_END_RANGE_TIMESTAMP = "2020-08-18T17:15:58.761Z"
_TEST_CLIENT_RESOURCE_USAGE_RECORD_1 = {
    "scope": "system",
    "pid": 2714460,
    "process_start_time": {"seconds": 1597327815, "nanos": 817468715},
    "client_timestamp": {"seconds": 1597328416, "nanos": 821525280},
    "server_timestamp": {"seconds": 1597328417, "nanos": 823124057},
    "mean_user_cpu_rate": 0.31883034110069275,
    "max_user_cpu_rate": 4.999776840209961,
    "mean_system_cpu_rate": 0.31883034110069275,
    "max_system_cpu_rate": 4.999776840209961,
    "mean_resident_memory_mib": 20,
    "max_resident_memory_mib": 20,
}
_TEST_CLIENT_RESOURCE_USAGE_RECORD_2 = {
    "scope": "GRR",
    "pid": 2714474,
    "process_start_time": {"seconds": 1597327815, "nanos": 818657389},
    "client_timestamp": {"seconds": 1597328418, "nanos": 402023428},
    "server_timestamp": {"seconds": 1597328419, "nanos": 403123025},
    "mean_user_cpu_rate": 0.492735356092453,
    "max_user_cpu_rate": 4.999615669250488,
    "mean_system_cpu_rate": 0.07246342301368713,
    "max_system_cpu_rate": 0.3333326578140259,
    "mean_resident_memory_mib": 59,
    "max_resident_memory_mib": 59,
}

_TEST_VALID_RUD_QUERY = {
    "app": "dashboard",
    "requestId": "Q119",
    "timezone": "browser",
    "panelId": 2,
    "dashboardId": 77,
    "range": {
        "from": _START_RANGE_TIMESTAMP,
        "to": _END_RANGE_TIMESTAMP,
        "raw": {"from": _START_RANGE_TIMESTAMP, "to": _END_RANGE_TIMESTAMP},
    },
    "timeInfo": "",
    "interval": "10m",
    "intervalMs": 600000,
    "targets": [
        {
            "data": None,
            "target": "Max User CPU Rate",
            "refId": "A",
            "hide": False,
            "type": "timeseries",
        },
        {
            "data": None,
            "target": "Mean System CPU Rate",
            "refId": "A",
            "hide": False,
            "type": "timeseries",
        },
    ],
    "maxDataPoints": 800,
    "scopedVars": {
        "ClientID": {"text": _TEST_CLIENT_ID_1, "value": _TEST_CLIENT_ID_1},
        "__interval": {"text": "10m", "value": "10m"},
        "__interval_ms": {"text": "600000", "value": 600000},
    },
    "startTime": 1598782453496,
    "rangeRaw": {"from": _START_RANGE_TIMESTAMP, "to": _END_RANGE_TIMESTAMP},
    "adhocFilters": [],
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
            max_resident_memory_mib=record["max_resident_memory_mib"],
        )
    )
  conn.outgoing.FetchClientResourceUsageRecords.return_value = (
      admin_pb2.FetchClientResourceUsageRecordsResponse(records=records)
  )
  return conn


class GrrafanaTest(absltest.TestCase):
  """Test the GRRafana HTTP server."""

  @classmethod
  def setUpClass(cls):
    super().setUpClass()

    # TODO: Remove once the "default" instance is actually default.
    try:
      instance = stats_collector_instance.Get()
      cls.addClassCleanup(lambda: stats_collector_instance.Set(instance))
    except stats_collector_instance.StatsNotInitializedError:
      pass
    stats_collector_instance.Set(
        default_stats_collector.DefaultStatsCollector()
    )

  def setUp(self):
    super().setUp()
    self.client = werkzeug_test.Client(
        application=grrafana.Grrafana(),
        response_wrapper=werkzeug_wrappers.Response,
    )

  def testRoot(self):
    response = self.client.get("/")
    self.assertEqual(200, response.status_code)

  def testSearchMetrics(self):
    response = self.client.post(
        "/search", json={"type": "timeseries", "target": ""}
    )
    self.assertEqual(200, response.status_code)

    expected_res = [
        "Mean User CPU Rate",
        "Max User CPU Rate",
        "Mean System CPU Rate",
        "Max System CPU Rate",
        "Mean Resident Memory MB",
        "Max Resident Memory MB",
    ]
    self.assertListEqual(response.json, expected_res)

  def testClientResourceUsageMetricQuery(self):
    conn = _MockConnReturningRecords([
        _TEST_CLIENT_RESOURCE_USAGE_RECORD_1,
        _TEST_CLIENT_RESOURCE_USAGE_RECORD_2,
    ])
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      valid_response = self.client.post("/query", json=_TEST_VALID_RUD_QUERY)
      self.assertEqual(200, valid_response.status_code)
      self.assertEqual(
          valid_response.json,
          [
              {
                  "target": "Max User CPU Rate",
                  "datapoints": [
                      [4.999776840209961, 1597328417823],
                      [4.999615669250488, 1597328419403],
                  ],
              },
              {
                  "target": "Mean System CPU Rate",
                  "datapoints": [
                      [0.31883034110069275, 1597328417823],
                      [0.07246342301368713, 1597328419403],
                  ],
              },
          ],
      )

  def testQueryInvalidRequest(self):
    conn = _MockConnReturningRecords([
        _TEST_CLIENT_RESOURCE_USAGE_RECORD_1,
        _TEST_CLIENT_RESOURCE_USAGE_RECORD_2,
    ])
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      with self.assertRaises(KeyError):
        self.client.post("/query", json=_TEST_INVALID_TARGET_QUERY)


class TimeToProtoTimestampTest(absltest.TestCase):
  """Tests the conversion between Grafana and proto timestamps."""

  def testTimeToProtoTimestamp(self):
    self.assertEqual(
        grrafana.TimeToProtoTimestamp(_START_RANGE_TIMESTAMP),
        timestamp_pb2.Timestamp(seconds=1597328417, nanos=(158 * 1000000)),
    )
    self.assertEqual(
        grrafana.TimeToProtoTimestamp(_END_RANGE_TIMESTAMP),
        timestamp_pb2.Timestamp(seconds=1597770958, nanos=(761 * 1000000)),
    )


if __name__ == "__main__":
  absltest.main()
