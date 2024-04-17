#!/usr/bin/env python
"""Unittest for GRR<->Fleetspeak server side glue code."""

from unittest import mock

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_proto import flows_pb2
from grr_response_server import communicator
from grr_response_server import data_store
from grr_response_server import events
from grr_response_server import fleetspeak_utils
from grr_response_server.bin import fleetspeak_frontend_server
from grr_response_server.flows.general import processes as flow_processes
from grr_response_server.models import clients
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2

FS_SERVICE_NAME = "GRR"


class FleetspeakGRRFEServerTest(flow_test_lib.FlowTestsBaseclass):
  """Tests the Fleetspeak based GRRFEServer."""

  def testReceiveMessages(self):
    now = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(123)

    fs_server = fleetspeak_frontend_server.GRRFSServer()
    client_id = "C.1234567890123456"
    flow_id = "12345678"
    data_store.REL_DB.WriteClientMetadata(
        client_id,
        last_ping=now
        - fleetspeak_frontend_server.MIN_DELAY_BETWEEN_METADATA_UPDATES
        - rdfvalue.Duration("1s"),
    )

    flow = flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
    data_store.REL_DB.WriteFlowObject(flow)

    flow_request = flows_pb2.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1
    )

    before_write = data_store.REL_DB.Now()
    data_store.REL_DB.WriteFlowRequests([flow_request])
    after_write = data_store.REL_DB.Now()
    session_id = "%s/%s" % (client_id, flow_id)
    fs_client_id = fleetspeak_utils.GRRIDToFleetspeakID(client_id)
    fs_messages = []
    for i in range(1, 10):
      grr_message = rdf_flows.GrrMessage(
          request_id=1,
          response_id=i + 1,
          session_id=session_id,
          payload=rdfvalue.RDFInteger(i),
      )
      fs_message = fs_common_pb2.Message(
          message_type="GrrMessage",
          source=fs_common_pb2.Address(
              client_id=fs_client_id, service_name=FS_SERVICE_NAME
          ),
      )
      fs_message.data.Pack(grr_message.AsPrimitiveProto())
      fs_message.validation_info.tags["foo"] = "bar"
      fs_messages.append(fs_message)

    with test_lib.FakeTime(now):
      for fs_message in fs_messages:
        fs_server.Process(fs_message, None)

    # Ensure the last-ping timestamp gets updated.
    client_data = data_store.REL_DB.ReadClientMetadata(client_id)
    self.assertEqual(client_data.ping, now)
    self.assertEqual(
        clients.FleetspeakValidationInfoToDict(
            client_data.last_fleetspeak_validation_info
        ),
        {"foo": "bar"},
    )

    flow_data = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
        client_id, flow_id
    )
    self.assertLen(flow_data, 1)
    stored_flow_request, flow_responses = flow_data[0]
    self.assertEqual(stored_flow_request.client_id, flow_request.client_id)
    self.assertEqual(stored_flow_request.flow_id, flow_request.flow_id)
    self.assertEqual(stored_flow_request.request_id, flow_request.request_id)
    self.assertBetween(stored_flow_request.timestamp, before_write, after_write)
    self.assertLen(flow_responses, 9)

  def testReceiveMessageList(self):
    now = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(123)
    fs_server = fleetspeak_frontend_server.GRRFSServer()
    client_id = "C.1234567890123456"
    flow_id = "12345678"
    data_store.REL_DB.WriteClientMetadata(
        client_id,
        last_ping=now
        - fleetspeak_frontend_server.MIN_DELAY_BETWEEN_METADATA_UPDATES
        - rdfvalue.Duration("1s"),
    )

    flow = flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
    data_store.REL_DB.WriteFlowObject(flow)

    flow_request = flows_pb2.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1
    )
    before_write = data_store.REL_DB.Now()
    data_store.REL_DB.WriteFlowRequests([flow_request])
    after_write = data_store.REL_DB.Now()

    session_id = "%s/%s" % (client_id, flow_id)
    fs_client_id = fleetspeak_utils.GRRIDToFleetspeakID(client_id)
    grr_messages = []
    for i in range(1, 10):
      grr_message = rdf_flows.GrrMessage(
          request_id=1,
          response_id=i + 1,
          session_id=session_id,
          payload=rdfvalue.RDFInteger(i),
      )
      grr_messages.append(grr_message)
    packed_messages = rdf_flows.PackedMessageList()
    communicator.Communicator.EncodeMessageList(
        rdf_flows.MessageList(job=grr_messages), packed_messages
    )
    fs_message = fs_common_pb2.Message(
        message_type="MessageList",
        source=fs_common_pb2.Address(
            client_id=fs_client_id, service_name=FS_SERVICE_NAME
        ),
    )
    fs_message.data.Pack(packed_messages.AsPrimitiveProto())
    fs_message.validation_info.tags["foo"] = "bar"

    with test_lib.FakeTime(now):
      fs_server.Process(fs_message, None)

    # Ensure the last-ping timestamp gets updated.
    client_data = data_store.REL_DB.ReadClientMetadata(client_id)
    self.assertEqual(client_data.ping, now)
    self.assertEqual(
        clients.FleetspeakValidationInfoToDict(
            client_data.last_fleetspeak_validation_info
        ),
        {"foo": "bar"},
    )

    flow_data = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
        client_id, flow_id
    )
    self.assertLen(flow_data, 1)
    stored_flow_request, flow_responses = flow_data[0]
    self.assertEqual(stored_flow_request.client_id, flow_request.client_id)
    self.assertEqual(stored_flow_request.flow_id, flow_request.flow_id)
    self.assertEqual(stored_flow_request.request_id, flow_request.request_id)
    self.assertBetween(stored_flow_request.timestamp, before_write, after_write)
    self.assertLen(flow_responses, 9)

  def testMetadataDoesNotGetUpdatedIfPreviousUpdateIsTooRecent(self):
    fs_server = fleetspeak_frontend_server.GRRFSServer()
    client_id = "C.1234567890123456"
    flow_id = "12345678"
    now = rdfvalue.RDFDatetime.Now()
    data_store.REL_DB.WriteClientMetadata(client_id, last_ping=now)

    flow = flows_pb2.Flow(
        client_id=client_id,
        flow_id=flow_id,
    )
    data_store.REL_DB.WriteFlowObject(flow)
    flow_request = flows_pb2.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1
    )
    data_store.REL_DB.WriteFlowRequests([flow_request])
    session_id = "%s/%s" % (client_id, flow_id)
    grr_message = rdf_flows.GrrMessage(
        request_id=1,
        response_id=1,
        session_id=session_id,
        payload=rdfvalue.RDFInteger(0),
    )
    fs_client_id = fleetspeak_utils.GRRIDToFleetspeakID(client_id)
    fs_message = fs_common_pb2.Message(
        message_type="GrrMessage",
        source=fs_common_pb2.Address(
            client_id=fs_client_id, service_name=FS_SERVICE_NAME
        ),
    )
    fs_message.data.Pack(grr_message.AsPrimitiveProto())
    fs_server.Process(fs_message, None)

    # Ensure the last-ping timestamp doesn't get updated.
    client_data = data_store.REL_DB.ReadClientMetadata(client_id)
    self.assertEqual(client_data.ping, int(now))

  def testMetadataGetsUpdatedIfPreviousUpdateIsOldEnough(self):
    fs_server = fleetspeak_frontend_server.GRRFSServer()
    client_id = "C.1234567890123456"
    flow_id = "12345678"
    past = (
        rdfvalue.RDFDatetime.Now()
        - fleetspeak_frontend_server.MIN_DELAY_BETWEEN_METADATA_UPDATES
        - rdfvalue.Duration("1s")
    )
    data_store.REL_DB.WriteClientMetadata(client_id, last_ping=past)

    flow = flows_pb2.Flow(
        client_id=client_id,
        flow_id=flow_id,
    )
    data_store.REL_DB.WriteFlowObject(flow)
    flow_request = flows_pb2.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1
    )
    data_store.REL_DB.WriteFlowRequests([flow_request])
    session_id = "%s/%s" % (client_id, flow_id)
    grr_message = rdf_flows.GrrMessage(
        request_id=1,
        response_id=1,
        session_id=session_id,
        payload=rdfvalue.RDFInteger(0),
    )
    fs_client_id = fleetspeak_utils.GRRIDToFleetspeakID(client_id)
    fs_message = fs_common_pb2.Message(
        message_type="GrrMessage",
        source=fs_common_pb2.Address(
            client_id=fs_client_id, service_name=FS_SERVICE_NAME
        ),
    )
    fs_message.data.Pack(grr_message.AsPrimitiveProto())
    fs_server.Process(fs_message, None)

    # Ensure the last-ping timestamp does get updated.
    client_data = data_store.REL_DB.ReadClientMetadata(client_id)
    self.assertNotEqual(client_data.ping, int(past))

  def testWriteLastPingForNewClients(self):
    fs_server = fleetspeak_frontend_server.GRRFSServer()
    client_id = "C.1234567890123456"
    flow_id = "12345678"
    session_id = "%s/%s" % (client_id, flow_id)
    fs_client_id = fleetspeak_utils.GRRIDToFleetspeakID(client_id)

    grr_message = rdf_flows.GrrMessage(
        request_id=1,
        response_id=1,
        session_id=session_id,
        payload=rdfvalue.RDFInteger(1),
    )
    fs_message = fs_common_pb2.Message(
        message_type="GrrMessage",
        source=fs_common_pb2.Address(
            client_id=fs_client_id, service_name=FS_SERVICE_NAME
        ),
    )
    fs_message.data.Pack(grr_message.AsPrimitiveProto())
    fake_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(123)

    with mock.patch.object(
        events.Events, "PublishEvent", wraps=events.Events.PublishEvent
    ) as publish_event_fn:
      with mock.patch.object(
          data_store.REL_DB,
          "WriteClientMetadata",
          wraps=data_store.REL_DB.WriteClientMetadata,
      ) as write_metadata_fn:
        with test_lib.FakeTime(fake_time):
          fs_server.Process(fs_message, None)
        self.assertEqual(write_metadata_fn.call_count, 1)
        client_data = data_store.REL_DB.ReadClientMetadata(client_id)
        self.assertEqual(client_data.ping, fake_time)
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

  def testProcessListingOnlyFleetspeak(self):
    """Test that the ListProcesses flow works with Fleetspeak."""
    client_id = self.SetupClient(0)
    data_store.REL_DB.WriteClientMetadata(client_id)

    client_mock = action_mocks.ListProcessesMock([
        rdf_client.Process(
            pid=2,
            ppid=1,
            cmdline=["cmd.exe"],
            exe=r"c:\windows\cmd.exe",
            ctime=1333718907167083,
        )
    ])

    flow_id = flow_test_lib.TestFlowHelper(
        flow_processes.ListProcesses.__name__,
        client_mock,
        client_id=client_id,
        creator=self.test_username,
    )

    processes = flow_test_lib.GetFlowResults(client_id, flow_id)
    self.assertLen(processes, 1)
    (process,) = processes

    self.assertEqual(process.ctime, 1333718907167083)
    self.assertEqual(process.cmdline, ["cmd.exe"])


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
