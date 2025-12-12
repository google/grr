#!/usr/bin/env python
"""Tests for frontend server, client communicator, and the GRRHTTPClient."""

import random
import sys
from unittest import mock
import zlib

from absl import app
from absl.testing import absltest

from google.protobuf import wrappers_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import flows_pb2
from grr_response_server import data_store
from grr_response_server import frontend_lib
from grr_response_server import sinks
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import administrative
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.sinks import test_lib as sinks_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr_response_proto import rrg_pb2


MESSAGE_EXPIRY_TIME = 100


def ReceiveMessages(client_id, messages):
  server = TestServer()
  server.ReceiveMessages(client_id, messages)


def TestServer():
  return frontend_lib.FrontEndServer(message_expiry_time=MESSAGE_EXPIRY_TIME)


class GRRFEServerTestRelational(flow_test_lib.FlowTestsBaseclass):
  """Tests the GRRFEServer with relational flows enabled."""

  def _FlowSetup(self, client_id, flow_id):
    rdf_flow = flows_pb2.Flow(
        flow_class_name=administrative.OnlineNotification.__name__,
        client_id=client_id,
        flow_id=flow_id,
    )
    data_store.REL_DB.WriteFlowObject(rdf_flow)

    req = flows_pb2.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1
    )

    data_store.REL_DB.WriteFlowRequests([req])

    return rdf_flow, req

  def testReceiveMessages(self):
    """Tests receiving messages."""
    client_id = "C.1234567890123456"
    flow_id = "12345678"
    data_store.REL_DB.WriteClientMetadata(client_id)
    before_flow_create = data_store.REL_DB.Now()
    _, req = self._FlowSetup(client_id, flow_id)
    after_flow_create = data_store.REL_DB.Now()

    session_id = "%s/%s" % (client_id, flow_id)
    messages = [
        rdf_flows.GrrMessage(
            request_id=1,
            response_id=i,
            session_id=session_id,
            auth_state="AUTHENTICATED",
            payload=rdfvalue.RDFInteger(i),
        )
        for i in range(1, 10)
    ]

    ReceiveMessages(client_id, messages)
    received = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
        client_id, flow_id
    )
    self.assertLen(received, 1)
    received_request = received[0][0]
    self.assertEqual(received_request.client_id, req.client_id)
    self.assertEqual(received_request.flow_id, req.flow_id)
    self.assertEqual(received_request.request_id, req.request_id)
    self.assertBetween(
        received_request.timestamp, before_flow_create, after_flow_create
    )
    self.assertLen(received[0][1], 9)

  def testBlobHandlerMessagesAreHandledOnTheFrontend(self):
    client_id = "C.1234567890123456"
    data_store.REL_DB.WriteClientMetadata(client_id)

    # Check that the worker queue is empty.
    self.assertEmpty(data_store.REL_DB.ReadMessageHandlerRequests())

    data = b"foo"
    data_blob = rdf_protodict.DataBlob(
        data=zlib.compress(data),
        compression=rdf_protodict.DataBlob.CompressionType.ZCOMPRESSION,
    )
    messages = [
        rdf_flows.GrrMessage(
            source=client_id,
            session_id=str(rdfvalue.SessionID(flow_name="TransferStore")),
            payload=data_blob,
            auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED,
        )
    ]
    ReceiveMessages(client_id, messages)

    # Check that the worker queue is still empty.
    self.assertEmpty(data_store.REL_DB.ReadMessageHandlerRequests())

    # Check that the blob was written to the blob store.
    self.assertTrue(
        data_store.BLOBS.CheckBlobExists(models_blobs.BlobID.Of(data))
    )

  def testCrashReport(self):
    client_id = "C.1234567890123456"
    flow_id = "12345678"
    data_store.REL_DB.WriteClientMetadata(client_id)
    self._FlowSetup(client_id, flow_id)

    # Make sure the event handler is present.
    self.assertTrue(administrative.ClientCrashHandler)

    session_id = rdfvalue.FlowSessionID(f"{client_id}/{flow_id}")
    status = rdf_flows.GrrStatus(
        status=rdf_flows.GrrStatus.ReturnedStatus.CLIENT_KILLED
    )
    messages = [
        rdf_flows.GrrMessage(
            source=client_id,
            request_id=1,
            response_id=1,
            session_id=session_id,
            payload=status,
            auth_state="AUTHENTICATED",
            type=rdf_flows.GrrMessage.Type.STATUS,
        )
    ]

    ReceiveMessages(client_id, messages)

    crash_details_rel = data_store.REL_DB.ReadClientCrashInfo(client_id)
    self.assertTrue(crash_details_rel)
    self.assertEqual(crash_details_rel.session_id, session_id)

  def testReceiveStatusMessage(self):
    client_id = "C.1234567890123456"
    flow_id = "12345678"
    data_store.REL_DB.WriteClientMetadata(client_id)
    self._FlowSetup(client_id, flow_id)

    session_id = rdfvalue.FlowSessionID(f"{client_id}/{flow_id}")
    status = rdf_flows.GrrStatus(status=rdf_flows.GrrStatus.ReturnedStatus.OK)
    status.cpu_time_used.deprecated_user_cpu_time = 1.1
    status.cpu_time_used.deprecated_system_cpu_time = 2.2

    messages = [
        rdf_flows.GrrMessage(
            source=client_id,
            request_id=1,
            response_id=1,
            session_id=session_id,
            payload=status,
            auth_state="AUTHENTICATED",
            type=rdf_flows.GrrMessage.Type.STATUS,
        )
    ]

    ReceiveMessages(client_id, messages)

    received = data_store.REL_DB.ReadAllFlowRequestsAndResponses(
        client_id, flow_id
    )
    self.assertLen(received, 1)
    self.assertNotEqual(received[0][1][1], status)
    self.assertAlmostEqual(received[0][1][1].cpu_time_used.user_cpu_time, 1.1)
    self.assertFalse(received[0][1][1].cpu_time_used.deprecated_user_cpu_time)
    self.assertAlmostEqual(received[0][1][1].cpu_time_used.system_cpu_time, 2.2)
    self.assertFalse(received[0][1][1].cpu_time_used.deprecated_system_cpu_time)


class FrontEndServerTest(absltest.TestCase):

  def setUp(self):
    super().setUp()

    self.server = frontend_lib.FrontEndServer()

  @db_test_lib.WithDatabase
  def testReceiveRRGResponseStatusOK(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    flow_request = flows_pb2.FlowRequest()
    flow_request.client_id = client_id
    flow_request.flow_id = flow_id
    flow_request.request_id = 1337
    db.WriteFlowRequests([flow_request])

    response = rrg_pb2.Response()
    response.flow_id = int(flow_id, 16)
    response.request_id = 1337
    response.response_id = 42
    response.status.network_bytes_sent = 4 * 1024 * 1024

    self.server.ReceiveRRGResponse(client_id, response)

    flow_responses = db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(flow_responses, 1)

    flow_response = flow_responses[0][1][response.response_id]
    self.assertIsInstance(flow_response, flows_pb2.FlowStatus)
    self.assertEqual(flow_response.client_id, client_id)
    self.assertEqual(flow_response.flow_id, flow_id)
    self.assertEqual(flow_response.request_id, 1337)
    self.assertEqual(flow_response.response_id, 42)

    self.assertEqual(
        flow_response.status,
        rdf_flow_objects.FlowStatus.Status.OK,
    )
    self.assertEqual(flow_response.network_bytes_sent, 4 * 1024 * 1024)

  @db_test_lib.WithDatabase
  def testReceiveRRGResponseStatusError(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    flow_request = flows_pb2.FlowRequest()
    flow_request.client_id = client_id
    flow_request.flow_id = flow_id
    flow_request.request_id = 1337
    db.WriteFlowRequests([flow_request])

    response = rrg_pb2.Response()
    response.flow_id = int(flow_id, 16)
    response.request_id = 1337
    response.response_id = 42
    response.status.error.type = rrg_pb2.Status.Error.UNSUPPORTED_ACTION
    response.status.error.message = "foobar"

    self.server.ReceiveRRGResponse(client_id, response)

    flow_responses = db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(flow_responses, 1)

    flow_response = flow_responses[0][1][response.response_id]
    self.assertIsInstance(flow_response, flows_pb2.FlowStatus)
    self.assertEqual(flow_response.client_id, client_id)
    self.assertEqual(flow_response.flow_id, flow_id)
    self.assertEqual(flow_response.request_id, 1337)
    self.assertEqual(flow_response.response_id, 42)

    self.assertEqual(
        flow_response.status,
        rdf_flow_objects.FlowStatus.Status.ERROR,
    )
    self.assertEqual(flow_response.error_message, "foobar")

  @db_test_lib.WithDatabase
  def testReceiveRRGResponseResult(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    flow_request = flows_pb2.FlowRequest()
    flow_request.client_id = client_id
    flow_request.flow_id = flow_id
    flow_request.request_id = 1337
    db.WriteFlowRequests([flow_request])

    response = rrg_pb2.Response()
    response.flow_id = int(flow_id, 16)
    response.request_id = 1337
    response.response_id = 42
    response.result.Pack(wrappers_pb2.StringValue(value="foobar"))

    self.server.ReceiveRRGResponse(client_id, response)

    flow_responses = db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(flow_responses, 1)

    flow_response = flow_responses[0][1][response.response_id]
    self.assertIsInstance(flow_response, flows_pb2.FlowResponse)
    self.assertEqual(flow_response.client_id, client_id)
    self.assertEqual(flow_response.flow_id, flow_id)
    self.assertEqual(flow_response.request_id, 1337)
    self.assertEqual(flow_response.response_id, 42)

    string = wrappers_pb2.StringValue()
    string.ParseFromString(flow_response.any_payload.value)
    self.assertEqual(string.value, "foobar")

  @db_test_lib.WithDatabase
  def testReceiveRRGResponseLog(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    flow_request = flows_pb2.FlowRequest()
    flow_request.client_id = client_id
    flow_request.flow_id = flow_id
    flow_request.request_id = 1337
    db.WriteFlowRequests([flow_request])

    response = rrg_pb2.Response()
    response.flow_id = int(flow_id, 16)
    response.request_id = 1337
    response.log.level = rrg_pb2.Log.Level.INFO
    response.log.timestamp.GetCurrentTime()
    response.log.message = "lorem ipsum dolor sit amet"

    self.server.ReceiveRRGResponse(client_id, response)

    logs = db.ReadFlowRRGLogs(client_id, flow_id, offset=0, count=1024)
    self.assertLen(logs, 1)
    self.assertEqual(logs[0].level, rrg_pb2.Log.Level.INFO)
    self.assertEqual(logs[0].message, "lorem ipsum dolor sit amet")
    self.assertGreater(logs[0].timestamp.seconds, 0)

  @db_test_lib.WithDatabase
  def testReceiveRRGResponseUnexpected(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)

    flow_request = flows_pb2.FlowRequest()
    flow_request.client_id = client_id
    flow_request.flow_id = flow_id
    flow_request.request_id = 1337
    db.WriteFlowRequests([flow_request])

    response = rrg_pb2.Response()
    response.flow_id = int(flow_id, 16)
    response.request_id = 1337
    response.response_id = 42

    with self.assertRaisesRegex(ValueError, "Unexpected response"):
      self.server.ReceiveRRGResponse(client_id, response)

  @db_test_lib.WithDatabase
  def testReceiveRRGResponsesMany(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)
    request_id = random.randint(0, sys.maxsize)

    flow_request = flows_pb2.FlowRequest()
    flow_request.client_id = client_id
    flow_request.flow_id = flow_id
    flow_request.request_id = request_id
    db.WriteFlowRequests([flow_request])

    response_1 = rrg_pb2.Response()
    response_1.flow_id = int(flow_id, 16)
    response_1.request_id = request_id
    response_1.response_id = 1
    response_1.result.Pack(wrappers_pb2.StringValue(value="foo"))

    response_2 = rrg_pb2.Response()
    response_2.flow_id = int(flow_id, 16)
    response_2.request_id = request_id
    response_2.response_id = 2
    response_2.result.Pack(wrappers_pb2.StringValue(value="bar"))

    self.server.ReceiveRRGResponses(client_id, [response_1, response_2])

    flow_responses = db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(flow_responses, 1)

    flow_response_1 = flow_responses[0][1][response_1.response_id]
    self.assertIsInstance(flow_response_1, flows_pb2.FlowResponse)
    self.assertEqual(flow_response_1.client_id, client_id)
    self.assertEqual(flow_response_1.flow_id, flow_id)
    self.assertEqual(flow_response_1.request_id, request_id)
    self.assertEqual(flow_response_1.response_id, 1)

    string_1 = wrappers_pb2.StringValue()
    string_1.ParseFromString(flow_response_1.any_payload.value)
    self.assertEqual(string_1.value, "foo")

    flow_response_2 = flow_responses[0][1][response_2.response_id]
    self.assertIsInstance(flow_response_2, flows_pb2.FlowResponse)
    self.assertEqual(flow_response_2.client_id, client_id)
    self.assertEqual(flow_response_2.flow_id, flow_id)
    self.assertEqual(flow_response_2.request_id, request_id)
    self.assertEqual(flow_response_2.response_id, 2)

    string_2 = wrappers_pb2.StringValue()
    string_2.ParseFromString(flow_response_2.any_payload.value)
    self.assertEqual(string_2.value, "bar")

  @db_test_lib.WithDatabase
  def testReceiveRRGResponsesEmpty(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    # Should not raise.
    self.server.ReceiveRRGResponses(client_id, [])

  def testReceiveRRGParcelOK(self):
    client_id = "C.1234567890ABCDEF"

    sink = sinks_test_lib.FakeSink()

    with mock.patch.object(sinks, "REGISTRY", {rrg_pb2.STARTUP: sink}):
      parcel = rrg_pb2.Parcel()
      parcel.sink = rrg_pb2.STARTUP
      parcel.payload.value = b"FOO"
      self.server.ReceiveRRGParcel(client_id, parcel)

      parcel = rrg_pb2.Parcel()
      parcel.sink = rrg_pb2.STARTUP
      parcel.payload.value = b"BAR"
      self.server.ReceiveRRGParcel(client_id, parcel)

    parcels = sink.Parcels(client_id)
    self.assertLen(parcels, 2)
    self.assertEqual(parcels[0].payload.value, b"FOO")
    self.assertEqual(parcels[1].payload.value, b"BAR")

  def testReceiveRRGParcelError(self):
    class FakeSink(sinks.Sink):

      # TODO: Add the `@override` annotation [1] once we are can
      # use Python 3.12 features.
      #
      # [1]: https://peps.python.org/pep-0698/
      def Accept(self, client_id: str, parcel: rrg_pb2.Parcel) -> None:
        del client_id, parcel  # Unused.
        raise RuntimeError()

    with mock.patch.object(sinks, "REGISTRY", {rrg_pb2.STARTUP: FakeSink()}):
      parcel = rrg_pb2.Parcel()
      parcel.sink = rrg_pb2.STARTUP
      parcel.payload.value = b"FOO"
      # Should not raise.
      self.server.ReceiveRRGParcel("C.1234567890ABCDEF", parcel)

  def testReceiveRRGParcelsMany(self):
    client_id = "C.1234567890ABCDEF"

    fake_blob_sink = sinks_test_lib.FakeSink()
    fake_startup_sink = sinks_test_lib.FakeSink()

    fake_registry = {
        rrg_pb2.BLOB: fake_blob_sink,
        rrg_pb2.STARTUP: fake_startup_sink,
    }
    with mock.patch.object(sinks, "REGISTRY", fake_registry):
      parcel_1 = rrg_pb2.Parcel()
      parcel_1.sink = rrg_pb2.BLOB
      parcel_1.payload.value = b"BLOB_1"

      parcel_2 = rrg_pb2.Parcel()
      parcel_2.sink = rrg_pb2.STARTUP
      parcel_2.payload.value = b"STARTUP_2"

      parcel_3 = rrg_pb2.Parcel()
      parcel_3.sink = rrg_pb2.BLOB
      parcel_3.payload.value = b"BLOB_3"

      self.server.ReceiveRRGParcels(client_id, [parcel_1, parcel_2, parcel_3])

    blob_parcels = fake_blob_sink.Parcels(client_id)
    self.assertLen(blob_parcels, 2)
    self.assertEqual(blob_parcels[0].payload.value, b"BLOB_1")
    self.assertEqual(blob_parcels[1].payload.value, b"BLOB_3")

    startup_parcels = fake_startup_sink.Parcels(client_id)
    self.assertLen(startup_parcels, 1)
    self.assertEqual(startup_parcels[0].payload.value, b"STARTUP_2")

  def testReceiveRRGParcelsEmpty(self):
    client_id = "C.1234567890ABCDEF"

    # Should not raise.
    self.server.ReceiveRRGParcels(client_id, [])


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  app.run(main)
