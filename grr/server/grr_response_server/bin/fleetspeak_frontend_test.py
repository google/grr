#!/usr/bin/env python
"""Unittest for GRR<->Fleetspeak server side glue code."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from future.builtins import range
import mock

from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2
from fleetspeak.src.server.grpcservice.client import client as fs_client
from fleetspeak.src.server.proto.fleetspeak_server import admin_pb2 as fs_admin_pb2

from grr_response_core.lib import communicator
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_proto import jobs_pb2
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import fleetspeak_connector
from grr_response_server import fleetspeak_utils
from grr_response_server.bin import fleetspeak_frontend as fs_frontend_tool
from grr_response_server.flows.general import processes as flow_processes
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import action_mocks
from grr.test_lib import fleetspeak_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

FS_SERVICE_NAME = "GRR"


class _FakeGRPCServiceClient(fs_client.ServiceClient):

  class _FakeConnection(object):

    def __init__(self, send_callback=lambda _: None):
      self._send_callback = send_callback

    def InsertMessage(self, message, timeout=None):
      del timeout
      self._send_callback(message)

    def ListClients(self, request):
      clients = []
      for client_id in request.client_ids:
        clients.append(
            fs_admin_pb2.Client(
                client_id=client_id,
                labels=[
                    fs_common_pb2.Label(
                        service_name="client", label="alphabet"),
                    fs_common_pb2.Label(
                        service_name="client", label="alphabet-google-corp"),
                    fs_common_pb2.Label(service_name="client", label="linux"),
                ]))
      return fs_admin_pb2.ListClientsResponse(clients=clients)

  def __init__(self, service_name, send_callback=lambda _: None):
    super(_FakeGRPCServiceClient, self).__init__(service_name)
    self._process = None
    self._send_callback = send_callback
    self.outgoing = self._FakeConnection(send_callback)

  def Listen(self, process):
    self._process = process

  def Send(self, message):
    self._send_callback(message)

  def MockIncomingFSMessage(self, message):
    self._process(message)

  def MockIncomingFSMessages(self, messages):
    for message in messages:
      self.MockIncomingFSMessage(message)


class FleetspeakGRRFEServerTest(flow_test_lib.FlowTestsBaseclass):
  """Tests the Fleetspeak based GRRFEServer."""

  def setUp(self):
    super(FleetspeakGRRFEServerTest, self).setUp()
    fake_conn = _FakeGRPCServiceClient(FS_SERVICE_NAME)
    conn_overrider = fleetspeak_test_lib.ConnectionOverrider(fake_conn)
    conn_overrider.Start()
    self.addCleanup(conn_overrider.Stop)

  def testReceiveMessages(self):
    fs_server = fs_frontend_tool.GRRFSServer()
    client_id = "C.1234567890123456"
    flow_id = "12345678"
    data_store.REL_DB.WriteClientMetadata(client_id, fleetspeak_enabled=True)

    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id=flow_id,
        create_time=rdfvalue.RDFDatetime.Now())
    data_store.REL_DB.WriteFlowObject(rdf_flow)

    flow_request = rdf_flow_objects.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1)

    data_store.REL_DB.WriteFlowRequests([flow_request])
    session_id = "%s/%s" % (client_id, flow_id)
    fs_client_id = fleetspeak_utils.GRRIDToFleetspeakID(client_id)
    fs_messages = []
    for i in range(1, 10):
      grr_message = rdf_flows.GrrMessage(
          request_id=1,
          response_id=i + 1,
          session_id=session_id,
          payload=rdfvalue.RDFInteger(i))
      fs_message = fs_common_pb2.Message(
          message_type="GrrMessage",
          source=fs_common_pb2.Address(
              client_id=fs_client_id, service_name=FS_SERVICE_NAME))
      fs_message.data.Pack(grr_message.AsPrimitiveProto())
      fs_messages.append(fs_message)

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(123)):
      for fs_message in fs_messages:
        fs_server.Process(fs_message, None)

    # Ensure the last-ping timestamp gets updated.
    client_data = data_store.REL_DB.MultiReadClientMetadata([client_id])
    self.assertEqual(client_data[client_id].ping,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(123))

    flow_data = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
        client_id, flow_id)
    self.assertLen(flow_data, 1)
    stored_flow_request, flow_responses = flow_data[0]
    self.assertEqual(stored_flow_request, flow_request)
    self.assertLen(flow_responses, 9)

  def testReceiveMessageList(self):

    fs_server = fs_frontend_tool.GRRFSServer()
    client_id = "C.1234567890123456"
    flow_id = "12345678"
    data_store.REL_DB.WriteClientMetadata(client_id, fleetspeak_enabled=True)

    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id=flow_id,
        create_time=rdfvalue.RDFDatetime.Now())
    data_store.REL_DB.WriteFlowObject(rdf_flow)

    flow_request = rdf_flow_objects.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1)

    data_store.REL_DB.WriteFlowRequests([flow_request])
    session_id = "%s/%s" % (client_id, flow_id)
    fs_client_id = fleetspeak_utils.GRRIDToFleetspeakID(client_id)
    grr_messages = []
    for i in range(1, 10):
      grr_message = rdf_flows.GrrMessage(
          request_id=1,
          response_id=i + 1,
          session_id=session_id,
          payload=rdfvalue.RDFInteger(i))
      grr_messages.append(grr_message)
    packed_messages = rdf_flows.PackedMessageList()
    communicator.Communicator.EncodeMessageList(
        rdf_flows.MessageList(job=grr_messages), packed_messages)
    fs_message = fs_common_pb2.Message(
        message_type="MessageList",
        source=fs_common_pb2.Address(
            client_id=fs_client_id, service_name=FS_SERVICE_NAME))
    fs_message.data.Pack(packed_messages.AsPrimitiveProto())

    with test_lib.FakeTime(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(123)):
      fs_server.Process(fs_message, None)

    # Ensure the last-ping timestamp gets updated.
    client_data = data_store.REL_DB.MultiReadClientMetadata([client_id])
    self.assertEqual(client_data[client_id].ping,
                     rdfvalue.RDFDatetime.FromSecondsSinceEpoch(123))

    flow_data = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
        client_id, flow_id)
    self.assertLen(flow_data, 1)
    stored_flow_request, flow_responses = flow_data[0]
    self.assertEqual(stored_flow_request, flow_request)
    self.assertLen(flow_responses, 9)

  def testWriteLastPingForNewClients(self):

    fs_server = fs_frontend_tool.GRRFSServer()
    client_id = "C.1234567890123456"
    flow_id = "12345678"
    session_id = "%s/%s" % (client_id, flow_id)
    fs_client_id = fleetspeak_utils.GRRIDToFleetspeakID(client_id)

    grr_message = rdf_flows.GrrMessage(
        request_id=1,
        response_id=1,
        session_id=session_id,
        payload=rdfvalue.RDFInteger(1))
    fs_message = fs_common_pb2.Message(
        message_type="GrrMessage",
        source=fs_common_pb2.Address(
            client_id=fs_client_id, service_name=FS_SERVICE_NAME))
    fs_message.data.Pack(grr_message.AsPrimitiveProto())
    fake_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(123)

    with mock.patch.object(
        events.Events, "PublishEvent",
        wraps=events.Events.PublishEvent) as publish_event_fn:
      with mock.patch.object(
          data_store.REL_DB,
          "WriteClientMetadata",
          wraps=data_store.REL_DB.WriteClientMetadata) as write_metadata_fn:
        with test_lib.FakeTime(fake_time):
          fs_server.Process(fs_message, None)
        self.assertEqual(write_metadata_fn.call_count, 1)
        client_data = data_store.REL_DB.MultiReadClientMetadata([client_id])
        self.assertEqual(client_data[client_id].ping, fake_time)
        # TODO(user): publish_event_fn.assert_any_call(
        #     "ClientEnrollment", mock.ANY, token=mock.ANY) doesn't work here
        # for some reason.
        triggered_events = []
        for call_args, _ in publish_event_fn.call_args_list:
          if call_args:
            triggered_events.append(call_args[0])
        self.assertIn("ClientEnrollment", triggered_events)


class ListProcessesFleetspeakTest(flow_test_lib.FlowTestsBaseclass):
  """Test the process listing flow w/ Fleetspeak."""

  def setUp(self):
    super(ListProcessesFleetspeakTest, self).setUp()

    self.client_id = self.SetupClient(0)
    data_store.REL_DB.WriteClientMetadata(
        self.client_id, fleetspeak_enabled=True)

  def testProcessListingOnlyFleetspeak(self):
    """Test that the ListProcesses flow works with Fleetspeak."""
    client_mock = action_mocks.ListProcessesMock([
        rdf_client.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe=r"c:\windows\cmd.exe",
            ctime=1333718907167083)
    ])
    client_mock.mock_task_queue = []

    def SendCallback(fs_msg):
      pb_msg = jobs_pb2.GrrMessage()
      fs_msg.data.Unpack(pb_msg)
      msg = rdf_flows.GrrMessage.FromSerializedString(
          pb_msg.SerializeToString())
      client_mock.mock_task_queue.append(msg)

    fake_conn = _FakeGRPCServiceClient(
        FS_SERVICE_NAME, send_callback=SendCallback)

    with fleetspeak_test_lib.ConnectionOverrider(fake_conn):
      with mock.patch.object(
          fake_conn.outgoing,
          "InsertMessage",
          wraps=fake_conn.outgoing.InsertMessage):
        session_id = flow_test_lib.TestFlowHelper(
            flow_processes.ListProcesses.__name__,
            client_mock,
            client_id=self.client_id,
            token=self.token)

        fleetspeak_connector.CONN.outgoing.InsertMessage.assert_called()

      # Check the output collection
      processes = flow_test_lib.GetFlowResults(self.client_id, session_id)
      self.assertLen(processes, 1)
      process, = processes

      self.assertEqual(process.ctime, 1333718907167083)
      self.assertEqual(process.cmdline, ["cmd.exe"])


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
