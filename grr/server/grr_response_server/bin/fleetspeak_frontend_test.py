#!/usr/bin/env python
"""Unittest for GRR<->Fleetspeak server side glue code."""

import itertools
import mock

from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2
from fleetspeak.src.server.grpcservice.client import client as fs_client

from grr.lib import communicator
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr_response_proto import jobs_pb2
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import fleetspeak_connector
from grr.server.grr_response_server import fleetspeak_utils
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import queue_manager
from grr.server.grr_response_server.bin import fleetspeak_frontend as fs_frontend_tool
from grr.server.grr_response_server.flows.general import processes as flow_processes
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import frontend_test_lib
from grr.test_lib import test_lib


class _FakeGRPCServiceClient(fs_client.ServiceClient):

  class _FakeConnection(object):

    def __init__(self, send_callback=lambda _: None):
      self._send_callback = send_callback

    def InsertMessage(self, message, timeout=None):
      del timeout
      self._send_callback(message)

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


def SetAFF4FSEnabledFlag(grr_id, token):
  with aff4.FACTORY.Create(
      grr_id, aff4.AFF4Object.classes["VFSGRRClient"], mode="w",
      token=token) as client:
    client.Set(client.Schema.FLEETSPEAK_ENABLED, rdfvalue.RDFBool(True))


@db_test_lib.DualDBTest
class FleetspeakGRRFEServerTest(frontend_test_lib.FrontEndServerTest):
  """Tests the Fleetspeak based GRRFEServer."""

  def testReceiveMessagesFleetspeak(self):
    service_name = "GRR"
    fake_service_client = _FakeGRPCServiceClient(service_name)

    fleetspeak_connector.Reset()
    fleetspeak_connector.Init(service_client=fake_service_client)

    fsd = fs_frontend_tool.GRRFSServer()

    grr_client_nr = 0xab
    grr_client_id_urn = self.SetupClient(grr_client_nr)

    flow_obj = self.FlowSetup(flow_test_lib.FlowOrderTest.__name__,
                              grr_client_id_urn)

    num_msgs = 9

    session_id = flow_obj.session_id
    messages = [
        rdf_flows.GrrMessage(
            request_id=1,
            response_id=i,
            session_id=session_id,
            payload=rdfvalue.RDFInteger(i)) for i in xrange(1, num_msgs + 1)
    ]

    fs_client_id = "\x10\x00\x00\x00\x00\x00\x00\xab"
    # fs_client_id should be equivalent to grr_client_id_urn
    self.assertEqual(
        fs_client_id,
        fleetspeak_utils.GRRIDToFleetspeakID(grr_client_id_urn.Basename()))

    fs_messages = [
        fs_common_pb2.Message(
            message_type="GrrMessage",
            source=fs_common_pb2.Address(
                client_id=fs_client_id, service_name=service_name))
        for _ in xrange(num_msgs)
    ]
    for fs_message, message in itertools.izip(fs_messages, messages):
      fs_message.data.Pack(message.AsPrimitiveProto())

    for msg in fs_messages:
      fsd.Process(msg, None)

    # Make sure the task is still on the client queue
    manager = queue_manager.QueueManager(token=self.token)
    tasks_on_client_queue = manager.Query(grr_client_id_urn, 100)
    self.assertEqual(len(tasks_on_client_queue), 1)

    want_messages = [message.Copy() for message in messages]
    for want_message in want_messages:
      # This is filled in by the frontend as soon as it gets the message.
      want_message.auth_state = (
          rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)
      want_message.source = grr_client_id_urn

    stored_messages = data_store.DB.ReadResponsesForRequestId(session_id, 1)

    self.assertEqual(len(stored_messages), len(want_messages))

    stored_messages.sort(key=lambda m: m.response_id)
    # Check that messages were stored correctly
    for stored_message, want_message in itertools.izip(stored_messages,
                                                       want_messages):
      stored_message.timestamp = None
      self.assertRDFValuesEqual(stored_message, want_message)

  def testReceiveMessageListFleetspeak(self):
    service_name = "GRR"
    fake_service_client = _FakeGRPCServiceClient(service_name)

    fleetspeak_connector.Reset()
    fleetspeak_connector.Init(service_client=fake_service_client)

    fsd = fs_frontend_tool.GRRFSServer()

    grr_client_nr = 0xab
    grr_client_id_urn = self.SetupClient(grr_client_nr)

    flow_obj = self.FlowSetup(flow_test_lib.FlowOrderTest.__name__,
                              grr_client_id_urn)

    num_msgs = 9

    session_id = flow_obj.session_id
    messages = [
        rdf_flows.GrrMessage(
            request_id=1,
            response_id=i,
            session_id=session_id,
            payload=rdfvalue.RDFInteger(i)) for i in xrange(1, num_msgs + 1)
    ]

    fs_client_id = "\x10\x00\x00\x00\x00\x00\x00\xab"
    # fs_client_id should be equivalent to grr_client_id_urn
    self.assertEqual(
        fs_client_id,
        fleetspeak_utils.GRRIDToFleetspeakID(grr_client_id_urn.Basename()))

    message_list = rdf_flows.PackedMessageList()
    communicator.Communicator.EncodeMessageList(
        rdf_flows.MessageList(job=messages), message_list)

    fs_message = fs_common_pb2.Message(
        message_type="MessageList",
        source=fs_common_pb2.Address(
            client_id=fs_client_id, service_name=service_name))
    fs_message.data.Pack(message_list.AsPrimitiveProto())
    fsd.Process(fs_message, None)

    # Make sure the task is still on the client queue
    manager = queue_manager.QueueManager(token=self.token)
    tasks_on_client_queue = manager.Query(grr_client_id_urn, 100)
    self.assertEqual(len(tasks_on_client_queue), 1)

    want_messages = [message.Copy() for message in messages]
    for want_message in want_messages:
      # This is filled in by the frontend as soon as it gets the message.
      want_message.auth_state = (
          rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)
      want_message.source = grr_client_id_urn

    stored_messages = data_store.DB.ReadResponsesForRequestId(session_id, 1)

    self.assertEqual(len(stored_messages), len(want_messages))

    stored_messages.sort(key=lambda m: m.response_id)
    # Check that messages were stored correctly
    for stored_message, want_message in itertools.izip(stored_messages,
                                                       want_messages):
      stored_message.timestamp = None
      self.assertRDFValuesEqual(stored_message, want_message)

  def testPingIsRecorded(self):
    service_name = "GRR"
    fake_service_client = _FakeGRPCServiceClient(service_name)

    fleetspeak_connector.Reset()
    fleetspeak_connector.Init(service_client=fake_service_client)

    fsd = fs_frontend_tool.GRRFSServer()

    grr_client_nr = 0xab
    grr_client = self.SetupTestClientObject(grr_client_nr)
    self.SetupClient(grr_client_nr)

    messages = [
        rdf_flows.GrrMessage(
            request_id=1,
            response_id=1,
            session_id="F:123456",
            payload=rdfvalue.RDFInteger(1))
    ]

    fs_client_id = "\x10\x00\x00\x00\x00\x00\x00\xab"
    # fs_client_id should be equivalent to grr_client_id_urn
    self.assertEqual(fs_client_id,
                     fleetspeak_utils.GRRIDToFleetspeakID(grr_client.client_id))

    message_list = rdf_flows.PackedMessageList()
    communicator.Communicator.EncodeMessageList(
        rdf_flows.MessageList(job=messages), message_list)

    fs_message = fs_common_pb2.Message(
        message_type="MessageList",
        source=fs_common_pb2.Address(
            client_id=fs_client_id, service_name=service_name))
    fs_message.data.Pack(message_list.AsPrimitiveProto())

    fake_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42)
    with test_lib.FakeTime(fake_time):
      fsd.Process(fs_message, None)

    md = data_store.REL_DB.ReadClientMetadata(grr_client.client_id)
    self.assertEqual(md.ping, fake_time)

    with aff4.FACTORY.Open(grr_client.client_id) as client:
      self.assertEqual(client.Get(client.Schema.PING), fake_time)


@db_test_lib.DualDBTest
class ListProcessesFleetspeakTest(flow_test_lib.FlowTestsBaseclass):
  """Test the process listing flow w/ Fleetspeak."""

  def setUp(self):
    super(ListProcessesFleetspeakTest, self).setUp()

    self.client_id = self.SetupClient(0)
    SetAFF4FSEnabledFlag(self.client_id, token=self.token)
    data_store.REL_DB.WriteClientMetadata(
        self.client_id.Basename(), fleetspeak_enabled=True)

  def testProcessListingOnlyFleetspeak(self):
    """Test that the ListProcesses flow works with Fleetspeak."""
    client_mock = action_mocks.ListProcessesMock([
        rdf_client.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe=r"c:\windows\cmd.exe",
            ctime=1333718907167083L)
    ])
    client_mock.mock_task_queue = []

    def SendCallback(fs_msg):
      pb_msg = jobs_pb2.GrrMessage()
      fs_msg.data.Unpack(pb_msg)
      msg = rdf_flows.GrrMessage.FromSerializedString(
          pb_msg.SerializeToString())
      client_mock.mock_task_queue.append(msg)

    service_name = "GRR"
    fake_service_client = _FakeGRPCServiceClient(
        service_name, send_callback=SendCallback)

    fleetspeak_connector.Reset()
    fleetspeak_connector.Init(service_client=fake_service_client)

    with mock.patch.object(
        fake_service_client.outgoing,
        "InsertMessage",
        wraps=fake_service_client.outgoing.InsertMessage):
      flow_urn = flow.GRRFlow.StartFlow(
          client_id=self.client_id,
          flow_name=flow_processes.ListProcesses.__name__,
          token=self.token)
      session_id = flow_test_lib.TestFlowHelper(
          flow_urn, client_mock, client_id=self.client_id, token=self.token)

      fleetspeak_connector.CONN.outgoing.InsertMessage.assert_called()

    # Check the output collection
    processes = flow.GRRFlow.ResultCollectionForFID(session_id)

    self.assertEqual(len(processes), 1)
    process, = processes

    self.assertEqual(process.ctime, 1333718907167083L)
    self.assertEqual(process.cmdline, ["cmd.exe"])


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
