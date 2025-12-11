#!/usr/bin/env python
"""Unittest for GRR<->Fleetspeak server side glue code."""
import random
import sys
from unittest import mock

from absl import app

from google.protobuf import any_pb2
from google.protobuf import wrappers_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import communicator
from grr_response_server import data_store
from grr_response_server import fleetspeak
from grr_response_server import fleetspeak_utils
from grr_response_server import sinks
from grr_response_server.bin import fleetspeak_frontend_server
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import processes as flow_processes
from grr_response_server.models import clients as models_clients
from grr_response_server.sinks import test_lib as sinks_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2
from grr_response_proto import rrg_pb2

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
        models_clients.FleetspeakValidationInfoToDict(
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
        models_clients.FleetspeakValidationInfoToDict(
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
        data_store.REL_DB,
        "WriteClientMetadata",
        wraps=data_store.REL_DB.WriteClientMetadata,
    ) as write_metadata_fn:
      with test_lib.FakeTime(fake_time):
        fs_server.Process(fs_message, None)
      self.assertEqual(write_metadata_fn.call_count, 1)
      client_data = data_store.REL_DB.ReadClientMetadata(client_id)
      self.assertEqual(client_data.ping, fake_time)

  @db_test_lib.WithDatabase
  def testProcess_EnrollmentValidationTags(self, db: abstract_db.Database):
    client_id = "C.0123456789abcdef"

    message = fs_common_pb2.Message()
    message.source.client_id = fleetspeak_utils.GRRIDToFleetspeakID(client_id)
    message.validation_info.tags["tag-1"] = "value-1"
    message.validation_info.tags["tag-2"] = "value-2"

    server = fleetspeak_frontend_server.GRRFSServer()
    server.Process(message, context=None)

    metadata = db.ReadClientMetadata(client_id)
    fleetspeak_validation_tags = metadata.last_fleetspeak_validation_info.tags
    fleetspeak_validation_tags.sort(key=lambda _: _.key)
    self.assertEqual(fleetspeak_validation_tags[0].key, "tag-1")
    self.assertEqual(fleetspeak_validation_tags[0].value, "value-1")
    self.assertEqual(fleetspeak_validation_tags[1].key, "tag-2")
    self.assertEqual(fleetspeak_validation_tags[1].value, "value-2")

  @db_test_lib.WithDatabase
  def testProcessBatch_NoClientMetadata(self, db: abstract_db.Database):
    client_id = "C.0123456789abcdef"

    batch = fleetspeak.MessageBatch(
        client_id=client_id,
        service="GRR-batched",
        message_type="rrg.Parcel",
        messages=[],
        validation_info_tags={
            "tag-1": "value-1",
            "tag-2": "value-2",
        },
    )

    time_before = db.Now()

    server = fleetspeak_frontend_server.GRRFSServer()
    server.ProcessBatch(batch)

    time_after = db.Now()

    # There was no metadata before, processing the batch should create one.
    metadata = db.ReadClientMetadata(client_id)
    self.assertBetween(metadata.ping, time_before, time_after)
    self.assertBetween(metadata.first_seen, time_before, time_after)

    validation_info_tags = metadata.last_fleetspeak_validation_info.tags
    validation_info_tags.sort(key=lambda _: _.key)
    self.assertLen(validation_info_tags, 2)
    self.assertEqual(validation_info_tags[0].key, "tag-1")
    self.assertEqual(validation_info_tags[0].value, "value-1")
    self.assertEqual(validation_info_tags[1].key, "tag-2")
    self.assertEqual(validation_info_tags[1].value, "value-2")

  @db_test_lib.WithDatabase
  def testProcessBatch_StaleClientMetadata(self, db: abstract_db.Database):
    client_id = "C.0123456789abcdef"

    db.WriteClientMetadata(
        client_id,
        last_ping=db.Now(),
    )

    time_before = db.Now()

    batch = fleetspeak.MessageBatch(
        client_id=client_id,
        service="GRR-batched",
        message_type="rrg.Parcel",
        messages=[],
        validation_info_tags={},
    )

    server = fleetspeak_frontend_server.GRRFSServer()
    server.ProcessBatch(batch)

    # There was a metadata entry before that is fresh, processing the batch
    # should not override it.
    #
    # We are working with an assumption here that writing the metadata and then
    # processing the batch is quicker than the delay we require between updates.
    # This theoretically might not be true but should never happen in practice.
    metadata = db.ReadClientMetadata(client_id)
    self.assertLess(metadata.ping, time_before)

  @db_test_lib.WithDatabase
  def testProcessBatch_FreshClientMetadata(self, db: abstract_db.Database):
    client_id = "C.0123456789abcdef"

    db.WriteClientMetadata(
        client_id,
        last_ping=db.Now() - rdfvalue.Duration.From(12, rdfvalue.WEEKS),
        fleetspeak_validation_info={
            "tag-1": "value-1-old",
            "tag-2": "value-2-old",
        },
    )

    time_before = db.Now()

    batch = fleetspeak.MessageBatch(
        client_id=client_id,
        service="GRR-batched",
        message_type="rrg.Parcel",
        messages=[],
        validation_info_tags={
            "tag-1": "value-1-new",
            "tag-2": "value-2-new",
        },
    )

    server = fleetspeak_frontend_server.GRRFSServer()
    server.ProcessBatch(batch)

    # There was a metadata entry before, but it was 2 weeks old. Processing the
    # batch should update it.
    metadata = db.ReadClientMetadata(client_id)
    self.assertGreater(metadata.ping, time_before)

    validation_info_tags = metadata.last_fleetspeak_validation_info.tags
    validation_info_tags.sort(key=lambda _: _.key)
    self.assertLen(validation_info_tags, 2)
    self.assertEqual(validation_info_tags[0].key, "tag-1")
    self.assertEqual(validation_info_tags[0].value, "value-1-new")
    self.assertEqual(validation_info_tags[1].key, "tag-2")
    self.assertEqual(validation_info_tags[1].value, "value-2-new")

  @db_test_lib.WithDatabase
  def testProcessBatch_GrrMessage(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)
    request_id = random.randint(0, sys.maxsize)

    flow_obj = flows_pb2.Flow(
        client_id=client_id,
        flow_id=flow_id,
    )
    db.WriteFlowObject(flow_obj)

    flow_request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
    )
    db.WriteFlowRequests([flow_request])

    grr_message_1 = jobs_pb2.GrrMessage()
    grr_message_1.session_id = f"{client_id}/{flow_id}"
    grr_message_1.request_id = request_id
    grr_message_1.response_id = 1
    grr_message_1.args_rdf_name = rdfvalue.RDFString.__name__
    grr_message_1.args = rdfvalue.RDFString("foo").SerializeToBytes()
    grr_message_any_1 = any_pb2.Any()
    grr_message_any_1.Pack(grr_message_1)

    grr_message_2 = jobs_pb2.GrrMessage()
    grr_message_2.session_id = f"{client_id}/{flow_id}"
    grr_message_2.request_id = request_id
    grr_message_2.response_id = 2
    grr_message_2.args_rdf_name = rdfvalue.RDFString.__name__
    grr_message_2.args = rdfvalue.RDFString("bar").SerializeToBytes()
    grr_message_any_2 = any_pb2.Any()
    grr_message_any_2.Pack(grr_message_2)

    batch = fleetspeak.MessageBatch(
        client_id=client_id,
        service="GRR-batched",
        message_type="GrrMessage",
        messages=[
            grr_message_any_1,
            grr_message_any_2,
        ],
        validation_info_tags={},
    )

    server = fleetspeak_frontend_server.GRRFSServer()
    server.ProcessBatch(batch)

    flow_requests_and_responses = db.ReadAllFlowRequestsAndResponses(
        client_id=client_id,
        flow_id=flow_id,
    )

    self.assertLen(flow_requests_and_responses, 1)
    _, flow_responses = flow_requests_and_responses[0]
    self.assertLen(flow_responses, 2)

    self.assertEqual(flow_responses[1].response_id, 1)
    string = wrappers_pb2.StringValue()
    self.assertTrue(flow_responses[1].payload.Unpack(string))
    self.assertEqual(string.value, "foo")

    self.assertEqual(flow_responses[2].response_id, 2)
    string = wrappers_pb2.StringValue()
    self.assertTrue(flow_responses[2].payload.Unpack(string))
    self.assertEqual(string.value, "bar")

  @db_test_lib.WithDatabase
  def testProcessBatch_MessageList(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)
    request_id = random.randint(0, sys.maxsize)

    flow_obj = flows_pb2.Flow(
        client_id=client_id,
        flow_id=flow_id,
    )
    db.WriteFlowObject(flow_obj)

    flow_request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
    )
    db.WriteFlowRequests([flow_request])

    message_list_1 = jobs_pb2.MessageList()
    message_list_2 = jobs_pb2.MessageList()

    grr_message_1 = message_list_1.job.add()
    grr_message_1.session_id = f"{client_id}/{flow_id}"
    grr_message_1.request_id = request_id
    grr_message_1.response_id = 1
    grr_message_1.args_rdf_name = rdfvalue.RDFString.__name__
    grr_message_1.args = rdfvalue.RDFString("foo").SerializeToBytes()

    grr_message_2 = message_list_1.job.add()
    grr_message_2.session_id = f"{client_id}/{flow_id}"
    grr_message_2.request_id = request_id
    grr_message_2.response_id = 2
    grr_message_2.args_rdf_name = rdfvalue.RDFString.__name__
    grr_message_2.args = rdfvalue.RDFString("bar").SerializeToBytes()

    grr_message_3 = message_list_2.job.add()
    grr_message_3.session_id = f"{client_id}/{flow_id}"
    grr_message_3.request_id = request_id
    grr_message_3.response_id = 3
    grr_message_3.args_rdf_name = rdfvalue.RDFString.__name__
    grr_message_3.args = rdfvalue.RDFString("quux").SerializeToBytes()

    packed_message_list_1 = jobs_pb2.PackedMessageList()
    packed_message_list_1.message_list = message_list_1.SerializeToString()
    packed_message_list_any_1 = any_pb2.Any()
    packed_message_list_any_1.Pack(packed_message_list_1)

    packed_message_list_2 = jobs_pb2.PackedMessageList()
    packed_message_list_2.message_list = message_list_2.SerializeToString()
    packed_message_list_any_2 = any_pb2.Any()
    packed_message_list_any_2.Pack(packed_message_list_2)

    batch = fleetspeak.MessageBatch(
        client_id=client_id,
        service="GRR-batched",
        message_type="MessageList",
        messages=[
            packed_message_list_any_1,
            packed_message_list_any_2,
        ],
        validation_info_tags={},
    )

    server = fleetspeak_frontend_server.GRRFSServer()
    server.ProcessBatch(batch)

    flow_requests_and_responses = db.ReadAllFlowRequestsAndResponses(
        client_id=client_id,
        flow_id=flow_id,
    )

    self.assertLen(flow_requests_and_responses, 1)
    _, flow_responses = flow_requests_and_responses[0]
    self.assertLen(flow_responses, 3)

    self.assertEqual(flow_responses[1].response_id, 1)
    string = wrappers_pb2.StringValue()
    self.assertTrue(flow_responses[1].payload.Unpack(string))
    self.assertEqual(string.value, "foo")

    self.assertEqual(flow_responses[2].response_id, 2)
    string = wrappers_pb2.StringValue()
    self.assertTrue(flow_responses[2].payload.Unpack(string))
    self.assertEqual(string.value, "bar")

    self.assertEqual(flow_responses[3].response_id, 3)
    string = wrappers_pb2.StringValue()
    self.assertTrue(flow_responses[3].payload.Unpack(string))
    self.assertEqual(string.value, "quux")

  @db_test_lib.WithDatabase
  def testProcessBatch_RRGResponse(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)
    request_id = random.randint(0, sys.maxsize)

    flow_obj = flows_pb2.Flow(
        client_id=client_id,
        flow_id=flow_id,
    )
    db.WriteFlowObject(flow_obj)

    flow_request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
    )
    db.WriteFlowRequests([flow_request])

    rrg_response_1 = rrg_pb2.Response()
    rrg_response_1.flow_id = int(flow_id, 16)
    rrg_response_1.request_id = request_id
    rrg_response_1.response_id = 1
    rrg_response_1.result.Pack(wrappers_pb2.StringValue(value="foo"))
    rrg_response_any_1 = any_pb2.Any()
    rrg_response_any_1.Pack(rrg_response_1)

    rrg_response_2 = rrg_pb2.Response()
    rrg_response_2.flow_id = int(flow_id, 16)
    rrg_response_2.request_id = request_id
    rrg_response_2.response_id = 2
    rrg_response_2.result.Pack(wrappers_pb2.StringValue(value="bar"))
    rrg_response_any_2 = any_pb2.Any()
    rrg_response_any_2.Pack(rrg_response_2)

    batch = fleetspeak.MessageBatch(
        client_id=client_id,
        service="GRR-batched",
        message_type="rrg.Response",
        messages=[
            rrg_response_any_1,
            rrg_response_any_2,
        ],
        validation_info_tags={},
    )

    server = fleetspeak_frontend_server.GRRFSServer()
    server.ProcessBatch(batch)

    flow_requests_and_responses = db.ReadAllFlowRequestsAndResponses(
        client_id=client_id,
        flow_id=flow_id,
    )

    self.assertLen(flow_requests_and_responses, 1)
    _, flow_responses = flow_requests_and_responses[0]

    self.assertEqual(flow_responses[1].response_id, 1)
    string = wrappers_pb2.StringValue()
    self.assertTrue(flow_responses[1].any_payload.Unpack(string))
    self.assertEqual(string.value, "foo")

    self.assertEqual(flow_responses[2].response_id, 2)
    string = wrappers_pb2.StringValue()
    self.assertTrue(flow_responses[2].any_payload.Unpack(string))
    self.assertEqual(string.value, "bar")

  @db_test_lib.WithDatabase
  def testProcessBatch_RRGParcel(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)
    flow_id = db_test_utils.InitializeFlow(db, client_id)
    request_id = random.randint(0, sys.maxsize)

    flow_obj = flows_pb2.Flow(
        client_id=client_id,
        flow_id=flow_id,
    )
    db.WriteFlowObject(flow_obj)

    flow_request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
    )
    db.WriteFlowRequests([flow_request])

    rrg_parcel_1 = rrg_pb2.Parcel()
    rrg_parcel_1.sink = rrg_pb2.STARTUP
    rrg_parcel_1.payload.Pack(wrappers_pb2.StringValue(value="foo"))
    rrg_parcel_any_1 = any_pb2.Any()
    rrg_parcel_any_1.Pack(rrg_parcel_1)

    rrg_parcel_2 = rrg_pb2.Parcel()
    rrg_parcel_2.sink = rrg_pb2.STARTUP
    rrg_parcel_2.payload.Pack(wrappers_pb2.StringValue(value="bar"))
    rrg_parcel_any_2 = any_pb2.Any()
    rrg_parcel_any_2.Pack(rrg_parcel_2)

    batch = fleetspeak.MessageBatch(
        client_id=client_id,
        service="GRR-batched",
        message_type="rrg.Parcel",
        messages=[
            rrg_parcel_any_1,
            rrg_parcel_any_2,
        ],
        validation_info_tags={},
    )

    sink = sinks_test_lib.FakeSink()

    with mock.patch.object(sinks, "REGISTRY", {rrg_pb2.STARTUP: sink}):
      server = fleetspeak_frontend_server.GRRFSServer()
      server.ProcessBatch(batch)

    parcels = sink.Parcels(client_id)
    self.assertLen(parcels, 2)

    string = wrappers_pb2.StringValue()
    self.assertTrue(parcels[0].payload.Unpack(string))
    self.assertEqual(string.value, "foo")

    string = wrappers_pb2.StringValue()
    self.assertTrue(parcels[1].payload.Unpack(string))
    self.assertEqual(string.value, "bar")

  @db_test_lib.WithDatabase
  def testProcessBatch_UnknownType(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeClient(db)

    batch = fleetspeak.MessageBatch(
        client_id=client_id,
        service="GRR-batched",
        message_type="rrg.NotExisting",
        messages=[],
        validation_info_tags={},
    )

    server = fleetspeak_frontend_server.GRRFSServer()
    server.ProcessBatch(batch)  # Should not raise.


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

    flow_id = flow_test_lib.StartAndRunFlow(
        flow_processes.ListProcesses,
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
