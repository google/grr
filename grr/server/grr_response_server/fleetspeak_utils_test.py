#!/usr/bin/env python
"""Tests for fleetspeak_utils module."""

from unittest import mock

from absl import app

from google.protobuf import timestamp_pb2
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_proto import jobs_pb2
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr.test_lib import test_lib
from fleetspeak.src.common.proto.fleetspeak import common_pb2
from fleetspeak.src.common.proto.fleetspeak import system_pb2 as fs_system_pb2
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2
from fleetspeak.src.server.proto.fleetspeak_server import resource_pb2


_TEST_CLIENT_ID = "C.0000000000000001"


def _MockConnReturningClient(grr_id, labels):
  client = admin_pb2.Client(
      client_id=fleetspeak_utils.GRRIDToFleetspeakID(grr_id),
      labels=[common_pb2.Label(service_name=k, label=v) for k, v in labels],
  )
  conn = mock.MagicMock()
  conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse(
      clients=[client]
  )
  return conn


class FleetspeakUtilsTest(test_lib.GRRBaseTest):

  def testGetLabelsFromFleetspeak_NoPrefix(self):
    conn = _MockConnReturningClient(
        _TEST_CLIENT_ID,
        [
            ("client", "foo-1"),
            ("client", "bar-2"),
            ("service-1", "foo-3"),
            ("service-1", "foo-4"),
            ("client", "foo-5"),
        ],
    )

    with test_lib.ConfigOverrider({
        "Server.fleetspeak_label_map": ["foo-5:baz-5"],
    }):
      with mock.patch.object(fleetspeak_connector, "CONN", conn):
        fleetspeak_connector.Init(conn)
        self.assertListEqual(
            fleetspeak_utils.GetLabelsFromFleetspeak(_TEST_CLIENT_ID),
            ["foo-1", "bar-2", "baz-5"],
        )

  def testGetLabelsFromFleetspeak_Prefix(self):
    conn = _MockConnReturningClient(
        _TEST_CLIENT_ID,
        [
            ("client", "foo-1"),
            ("client", "bar-2"),
            ("service-1", "foo-3"),
            ("service-1", "foo-4"),
            ("client", "foo-5"),
        ],
    )

    with test_lib.ConfigOverrider({
        "Server.fleetspeak_label_prefix": "foo",
        "Server.fleetspeak_label_map": ["foo-5: baz-5"],
    }):
      with mock.patch.object(fleetspeak_connector, "CONN", conn):
        fleetspeak_connector.Init(conn)
        self.assertListEqual(
            fleetspeak_utils.GetLabelsFromFleetspeak(_TEST_CLIENT_ID),
            ["foo-1", "baz-5"],
        )

  def testGetLabelsFromFleetspeak_NoLabels(self):
    conn = _MockConnReturningClient(_TEST_CLIENT_ID, [("service-1", "foo-3")])
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      fleetspeak_connector.Init(conn)
      self.assertEmpty(
          fleetspeak_utils.GetLabelsFromFleetspeak(_TEST_CLIENT_ID)
      )

  def testGetLabelsFromFleetspeak_UnknownClient(self):
    conn = mock.MagicMock()
    conn.outgoing.ListClients.return_value = admin_pb2.ListClientsResponse()
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      fleetspeak_connector.Init(conn)
      self.assertEmpty(
          fleetspeak_utils.GetLabelsFromFleetspeak(_TEST_CLIENT_ID)
      )

  @mock.patch.object(fleetspeak_connector, "CONN")
  def testSendGrrMessage(self, mock_conn):
    client_id = "C.0123456789abcdef"
    flow_id = "01234567"
    grr_message = rdf_flows.GrrMessage(
        session_id="%s/%s" % (client_id, flow_id),
        name="TestClientAction",
        request_id=1,
    )
    fleetspeak_utils.SendGrrMessageThroughFleetspeak(client_id, grr_message, [])
    mock_conn.outgoing.InsertMessage.assert_called_once()
    insert_args, _ = mock_conn.outgoing.InsertMessage.call_args
    fs_message = insert_args[0]
    expected_annotations = common_pb2.Annotations(
        entries=[
            common_pb2.Annotations.Entry(key="flow_id", value=flow_id),
            common_pb2.Annotations.Entry(key="request_id", value="1"),
        ]
    )
    unpacked_message = rdf_flows.GrrMessage.protobuf()
    fs_message.data.Unpack(unpacked_message)
    self.assertEqual(fs_message.annotations, expected_annotations)
    self.assertEqual(grr_message.AsPrimitiveProto(), unpacked_message)

  @mock.patch.object(fleetspeak_connector, "CONN")
  def testSendGrrMessageProto(self, mock_conn):
    client_id = "C.0123456789abcdef"
    flow_id = "01234567"
    grr_message = jobs_pb2.GrrMessage(
        session_id="%s/%s" % (client_id, flow_id),
        name="TestClientAction",
        request_id=1,
    )
    fleetspeak_utils.SendGrrMessageProtoThroughFleetspeak(
        client_id, grr_message, []
    )
    mock_conn.outgoing.InsertMessage.assert_called_once()
    insert_args, _ = mock_conn.outgoing.InsertMessage.call_args
    fs_message = insert_args[0]
    expected_annotations = common_pb2.Annotations(
        entries=[
            common_pb2.Annotations.Entry(key="flow_id", value=flow_id),
            common_pb2.Annotations.Entry(key="request_id", value="1"),
        ]
    )
    unpacked_message = jobs_pb2.GrrMessage()
    fs_message.data.Unpack(unpacked_message)
    self.assertEqual(fs_message.annotations, expected_annotations)
    self.assertEqual(grr_message, unpacked_message)

  @mock.patch.object(fleetspeak_connector, "CONN")
  def testKillFleetspeak(self, mock_conn):
    fleetspeak_utils.KillFleetspeak("C.1000000000000000", True)
    mock_conn.outgoing.InsertMessage.assert_called_once()
    insert_args, _ = mock_conn.outgoing.InsertMessage.call_args
    fs_message = insert_args[0]
    self.assertEqual(fs_message.message_type, "Die")
    self.assertEqual(
        fs_message.destination.client_id, b"\x10\x00\x00\x00\x00\x00\x00\x00"
    )
    self.assertEqual(fs_message.destination.service_name, "system")
    die_req = fs_system_pb2.DieRequest()
    fs_message.data.Unpack(die_req)
    self.assertTrue(die_req.force)

  @mock.patch.object(fleetspeak_connector, "CONN")
  def testRestartFleetspeakGrrService(self, mock_conn):
    fleetspeak_utils.RestartFleetspeakGrrService("C.2000000000000000")
    mock_conn.outgoing.InsertMessage.assert_called_once()
    insert_args, _ = mock_conn.outgoing.InsertMessage.call_args
    fs_message = insert_args[0]
    self.assertEqual(fs_message.message_type, "RestartService")
    self.assertEqual(
        fs_message.destination.client_id, b"\x20\x00\x00\x00\x00\x00\x00\x00"
    )
    self.assertEqual(fs_message.destination.service_name, "system")
    restart_req = fs_system_pb2.RestartServiceRequest()
    fs_message.data.Unpack(restart_req)
    self.assertEqual(restart_req.name, "GRR")

  @mock.patch.object(fleetspeak_connector, "CONN")
  def testDeleteFleetspeakPendingMessages(self, mock_conn):
    fleetspeak_utils.DeleteFleetspeakPendingMessages("C.1000000000000000")

    mock_conn.outgoing.DeletePendingMessages.assert_called_once()
    delete_args, _ = mock_conn.outgoing.DeletePendingMessages.call_args

    delete_req = delete_args[0]
    self.assertSameElements(
        delete_req.client_ids, [b"\x10\x00\x00\x00\x00\x00\x00\x00"]
    )

  def testGetFleetspeakPendingMessageCount(self):
    conn = mock.MagicMock()
    conn.outgoing.GetPendingMessageCount.return_value = (
        admin_pb2.GetPendingMessageCountResponse(count=42)
    )
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      count = fleetspeak_utils.GetFleetspeakPendingMessageCount(
          "C.1000000000000000"
      )
      self.assertEqual(count, 42)
      get_args, _ = conn.outgoing.GetPendingMessageCount.call_args
      get_req = get_args[0]
      self.assertSameElements(
          get_req.client_ids, [b"\x10\x00\x00\x00\x00\x00\x00\x00"]
      )

  def testGetFleetspeakPendingMessages(self):
    conn = mock.MagicMock()
    proto_response = admin_pb2.GetPendingMessagesResponse(
        messages=[common_pb2.Message(message_id=b"foo")]
    )
    conn.outgoing.GetPendingMessages.return_value = proto_response
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      result = fleetspeak_utils.GetFleetspeakPendingMessages(
          "C.1000000000000000", 1, 2, True
      )
      self.assertEqual(result, proto_response)
      get_args, _ = conn.outgoing.GetPendingMessages.call_args
      get_req = get_args[0]
      self.assertSameElements(
          get_req.client_ids, [b"\x10\x00\x00\x00\x00\x00\x00\x00"]
      )
      self.assertEqual(get_req.offset, 1)
      self.assertEqual(get_req.limit, 2)
      self.assertEqual(get_req.want_data, True)

  def testFetchClientResourceUsageRecords(self):
    conn = mock.MagicMock()
    conn.outgoing.FetchClientResourceUsageRecords.return_value = (
        admin_pb2.FetchClientResourceUsageRecordsResponse(
            records=[
                {"mean_user_cpu_rate": 1, "max_system_cpu_rate": 2},
                {"mean_user_cpu_rate": 4, "max_system_cpu_rate": 8},
            ]
        )
    )
    with mock.patch.object(fleetspeak_connector, "CONN", conn):
      expected_records_list = [
          resource_pb2.ClientResourceUsageRecord(
              mean_user_cpu_rate=1, max_system_cpu_rate=2
          ),
          resource_pb2.ClientResourceUsageRecord(
              mean_user_cpu_rate=4, max_system_cpu_rate=8
          ),
      ]
      arbitrary_date = timestamp_pb2.Timestamp(seconds=1, nanos=1)
      self.assertListEqual(
          fleetspeak_utils.FetchClientResourceUsageRecords(
              client_id=_TEST_CLIENT_ID,
              start_range=arbitrary_date,
              end_range=arbitrary_date,
          ),
          expected_records_list,
      )
      conn.outgoing.FetchClientResourceUsageRecords.assert_called_once()
      args, _ = conn.outgoing.FetchClientResourceUsageRecords.call_args
      self.assertEqual(
          args[0],
          admin_pb2.FetchClientResourceUsageRecordsRequest(
              client_id=fleetspeak_utils.GRRIDToFleetspeakID(_TEST_CLIENT_ID),
              start_timestamp=arbitrary_date,
              end_timestamp=arbitrary_date,
          ),
      )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
