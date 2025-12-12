#!/usr/bin/env python
"""Tests for the flow database api."""

from collections.abc import Sequence
import queue
import random
import threading
import time
from typing import Optional, Union
from unittest import mock

from google.protobuf import any_pb2
from google.protobuf import timestamp_pb2
from google.protobuf import wrappers_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import flow
from grr_response_server.databases import db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows import file
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr.test_lib import test_lib
from grr_response_proto import rrg_pb2


class DatabaseTestFlowMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of flows.
  """

  def testFlowWritingUnknownClient(self):
    flow_id = "1234ABCD"
    client_id = "C.1234567890123456"

    flow_obj = flows_pb2.Flow(client_id=client_id, flow_id=flow_id)

    with self.assertRaises(db.UnknownClientError):
      self.db.WriteFlowObject(flow_obj)

  def testFlowWriting(self):
    flow_id = "1234ABCD"
    client_id = "C.1234567890123456"

    self.db.WriteClientMetadata(client_id)

    flow_obj = flows_pb2.Flow(
        client_id=client_id,
        flow_id=flow_id,
        long_flow_id=f"{client_id}/{flow_id}",
        next_request_to_process=4,
        creator="foo",
        flow_class_name="bar",
    )
    flow_obj.cpu_time_used.user_cpu_time = 123
    flow_obj.cpu_time_used.system_cpu_time = 456
    flow_obj.network_bytes_sent = 789
    self.db.WriteFlowObject(flow_obj)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)

    # Last update and creation times have changed, everything else should be
    # equal.
    read_flow.ClearField("create_time")
    read_flow.ClearField("last_update_time")

    self.assertEqual(read_flow, flow_obj)

    # Invalid flow id or client id raises.
    with self.assertRaises(db.UnknownFlowError):
      self.db.ReadFlowObject(client_id, "1234AAAA")

    with self.assertRaises(db.UnknownFlowError):
      self.db.ReadFlowObject("C.1234567890000000", flow_id)

  def testFlowOverwrite(self):
    flow_id = "1234ABCD"
    client_id = "C.1234567890123456"

    self.db.WriteClientMetadata(client_id)

    flow_obj = flows_pb2.Flow(
        client_id=client_id,
        flow_id=flow_id,
        long_flow_id=f"{client_id}/{flow_id}",
        next_request_to_process=4,
        creator="foo",
        flow_class_name="bar",
    )
    flow_obj.cpu_time_used.user_cpu_time = 123
    flow_obj.cpu_time_used.system_cpu_time = 456
    flow_obj.network_bytes_sent = 789
    self.db.WriteFlowObject(flow_obj)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)

    # Last update and creation times have changed, everything else should be
    # equal.
    read_flow.ClearField("create_time")
    read_flow.ClearField("last_update_time")

    self.assertEqual(read_flow, flow_obj)

    # Now change the flow object.
    flow_obj.next_request_to_process = 5

    self.db.WriteFlowObject(flow_obj)

    read_flow_after_update = self.db.ReadFlowObject(client_id, flow_id)

    self.assertEqual(read_flow_after_update.next_request_to_process, 5)

  def testFlowOverwriteFailsWithAllowUpdateFalse(self):
    flow_id = "1234ABCD"
    client_id = "C.1234567890123456"

    self.db.WriteClientMetadata(client_id)

    flow_obj = flows_pb2.Flow(
        client_id=client_id, flow_id=flow_id, next_request_to_process=4
    )
    self.db.WriteFlowObject(flow_obj, allow_update=False)

    # Now change the flow object.
    flow_obj.next_request_to_process = 5

    with self.assertRaises(db.FlowExistsError) as context:
      self.db.WriteFlowObject(flow_obj, allow_update=False)
    self.assertEqual(context.exception.client_id, client_id)
    self.assertEqual(context.exception.flow_id, flow_id)

    read_flow_after_update = self.db.ReadFlowObject(client_id, flow_id)

    self.assertEqual(read_flow_after_update.next_request_to_process, 4)

  def testFlowTimestamp(self):
    client_id = "C.0123456789012345"
    flow_id = "0F00B430"

    self.db.WriteClientMetadata(client_id)

    before_timestamp = self.db.Now().AsMicrosecondsSinceEpoch()

    flow_obj = flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
    self.db.WriteFlowObject(flow_obj)

    after_timestamp = self.db.Now().AsMicrosecondsSinceEpoch()

    flow_obj = self.db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertBetween(flow_obj.create_time, before_timestamp, after_timestamp)

  def testFlowTimestampWithMissingCreationTime(self):
    client_id = "C.0123456789012345"
    flow_id = "0F00B430"

    self.db.WriteClientMetadata(client_id)

    before_timestamp = self.db.Now().AsMicrosecondsSinceEpoch()

    flow_obj = flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
    self.db.WriteFlowObject(flow_obj)

    after_timestamp = self.db.Now().AsMicrosecondsSinceEpoch()

    flow_obj = self.db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertBetween(flow_obj.create_time, before_timestamp, after_timestamp)

  def testFlowNameWithMissingNameInProtobuf(self):
    client_id = "C.0123456789012345"
    flow_id = "0F00B430"

    self.db.WriteClientMetadata(client_id)

    flow_obj = flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
    flow_obj.flow_class_name = "Quux"
    self.db.WriteFlowObject(flow_obj)

    flow_obj.ClearField("flow_class_name")
    self.db.UpdateFlow(client_id=client_id, flow_id=flow_id, flow_obj=flow_obj)

    flow_obj = self.db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.flow_class_name, "Quux")

  def testFlowKeyMetadataUnchangable(self):
    client_id = "C.0123456789012345"
    flow_id = "0F00B430"

    self.db.WriteClientMetadata(client_id)

    flow_obj = flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
    flow_obj.long_flow_id = f"{client_id}/{flow_id}"
    self.db.WriteFlowObject(flow_obj)

    flow_obj.client_id = "C.0123456789ABCDEF"
    flow_obj.flow_id = "0B43F0000"
    flow_obj.long_flow_id = f"{flow_obj.client_id}/{flow_obj.flow_id}"
    self.db.UpdateFlow(client_id=client_id, flow_id=flow_id, flow_obj=flow_obj)

    flow_obj = self.db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.client_id, client_id)
    self.assertEqual(flow_obj.flow_id, flow_id)
    self.assertEqual(flow_obj.long_flow_id, f"{client_id}/{flow_id}")

  def testFlowParentMetadataUnchangable(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = "0F00B430"

    flow_obj = flows_pb2.Flow(client_id=client_id, flow_id=flow_id)

    parent_flow_id_1 = db_test_utils.InitializeFlow(self.db, client_id)
    parent_hunt_id_1 = db_test_utils.InitializeHunt(self.db)

    flow_obj.parent_flow_id = parent_flow_id_1
    flow_obj.parent_hunt_id = parent_hunt_id_1
    self.db.WriteFlowObject(flow_obj)

    parent_flow_id_2 = db_test_utils.InitializeFlow(self.db, client_id)
    parent_hunt_id_2 = db_test_utils.InitializeHunt(self.db)

    flow_obj.parent_flow_id = parent_flow_id_2
    flow_obj.parent_hunt_id = parent_hunt_id_2
    self.db.UpdateFlow(client_id=client_id, flow_id=flow_id, flow_obj=flow_obj)

    flow_obj = self.db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.parent_flow_id, parent_flow_id_1)
    self.assertEqual(flow_obj.parent_hunt_id, parent_hunt_id_1)

  def testFlowNameUnchangable(self):
    client_id = "C.0123456789012345"
    flow_id = "0F00B430"

    self.db.WriteClientMetadata(client_id)

    flow_obj = flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
    flow_obj.flow_class_name = "Quux"
    self.db.WriteFlowObject(flow_obj)

    flow_obj.flow_class_name = "Norf"
    self.db.UpdateFlow(client_id=client_id, flow_id=flow_id, flow_obj=flow_obj)

    flow_obj = self.db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.flow_class_name, "Quux")

  def testFlowCreatorUnchangable(self):
    client_id = "C.0123456789012345"
    flow_id = "0F00B430"

    self.db.WriteClientMetadata(client_id)

    flow_obj = flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
    flow_obj.creator = "norf"
    self.db.WriteFlowObject(flow_obj)

    flow_obj.creator = "thud"
    self.db.UpdateFlow(client_id=client_id, flow_id=flow_id, flow_obj=flow_obj)

    flow_obj = self.db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.creator, "norf")

  def testFlowCreatorUnsetInProtobuf(self):
    client_id = "C.0123456789012345"
    flow_id = "0F00B430"

    self.db.WriteClientMetadata(client_id)

    flow_obj = flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
    flow_obj.creator = "norf"
    self.db.WriteFlowObject(flow_obj)

    flow_obj.ClearField("creator")
    self.db.UpdateFlow(client_id=client_id, flow_id=flow_id, flow_obj=flow_obj)

    flow_obj = self.db.ReadFlowObject(client_id=client_id, flow_id=flow_id)
    self.assertEqual(flow_obj.creator, "norf")

  def testReadAllFlowObjects(self):
    client_id_1 = "C.1111111111111111"
    client_id_2 = "C.2222222222222222"

    self.db.WriteClientMetadata(client_id_1)
    self.db.WriteClientMetadata(client_id_2)

    # Write a flow and a child flow for client 1.
    flow1 = rdf_flow_objects.Flow(client_id=client_id_1, flow_id="000A0001")
    proto_flow = mig_flow_objects.ToProtoFlow(flow1)
    self.db.WriteFlowObject(proto_flow)
    flow2 = rdf_flow_objects.Flow(
        client_id=client_id_1, flow_id="000A0002", parent_flow_id="000A0001"
    )
    proto_flow = mig_flow_objects.ToProtoFlow(flow2)
    self.db.WriteFlowObject(proto_flow)

    # Same flow id for client 2.
    flow3 = rdf_flow_objects.Flow(client_id=client_id_2, flow_id="000A0001")
    proto_flow = mig_flow_objects.ToProtoFlow(flow3)
    self.db.WriteFlowObject(proto_flow)

    flows = self.db.ReadAllFlowObjects()
    self.assertCountEqual(
        [f.flow_id for f in flows], ["000A0001", "000A0002", "000A0001"]
    )

  def testReadAllFlowObjectsWithMinCreateTime(self):
    client_id_1 = "C.1111111111111111"
    self.db.WriteClientMetadata(client_id_1)

    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="0000001A")
    )

    timestamp = self.db.Now()

    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="0000001B")
    )

    flows = self.db.ReadAllFlowObjects(min_create_time=timestamp)
    self.assertEqual([f.flow_id for f in flows], ["0000001B"])

  def testReadAllFlowObjectsWithMaxCreateTime(self):
    client_id_1 = "C.1111111111111111"
    self.db.WriteClientMetadata(client_id_1)

    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="0000001A")
    )

    timestamp = self.db.Now()

    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="0000001B")
    )

    flows = self.db.ReadAllFlowObjects(max_create_time=timestamp)
    self.assertEqual([f.flow_id for f in flows], ["0000001A"])

  def testReadAllFlowObjectsWithClientID(self):
    client_id_1 = "C.1111111111111111"
    client_id_2 = "C.2222222222222222"
    self.db.WriteClientMetadata(client_id_1)
    self.db.WriteClientMetadata(client_id_2)

    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="0000001A")
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_2, flow_id="0000001B")
    )

    flows = self.db.ReadAllFlowObjects(client_id=client_id_1)
    self.assertEqual([f.flow_id for f in flows], ["0000001A"])

  def testReadAllFlowObjectsWitParentFlowID(self):
    client_id = db_test_utils.InitializeClient(self.db)

    parent_flow = rdf_flow_objects.Flow()
    parent_flow.client_id = client_id
    parent_flow.flow_id = "AAAAAAAA"
    proto_flow = mig_flow_objects.ToProtoFlow(parent_flow)
    self.db.WriteFlowObject(proto_flow)

    child_flow_1 = rdf_flow_objects.Flow()
    child_flow_1.client_id = client_id
    child_flow_1.flow_id = "CCCC1111"
    child_flow_1.parent_flow_id = "AAAAAAAA"
    proto_flow = mig_flow_objects.ToProtoFlow(child_flow_1)
    self.db.WriteFlowObject(proto_flow)

    child_flow_2 = rdf_flow_objects.Flow()
    child_flow_2.client_id = client_id
    child_flow_2.flow_id = "CCCC2222"
    child_flow_2.parent_flow_id = "AAAAAAAA"
    proto_flow = mig_flow_objects.ToProtoFlow(child_flow_2)
    self.db.WriteFlowObject(proto_flow)

    not_child_flow = rdf_flow_objects.Flow()
    not_child_flow.client_id = client_id
    not_child_flow.flow_id = "FFFFFFFF"
    proto_flow = mig_flow_objects.ToProtoFlow(not_child_flow)
    self.db.WriteFlowObject(proto_flow)

    result = self.db.ReadAllFlowObjects(
        client_id=client_id, parent_flow_id="AAAAAAAA", include_child_flows=True
    )

    result_flow_ids = set(_.flow_id for _ in result)
    self.assertIn("CCCC1111", result_flow_ids)
    self.assertIn("CCCC2222", result_flow_ids)
    self.assertNotIn("AAAAAAAA", result_flow_ids)
    self.assertNotIn("FFFFFFFF", result_flow_ids)

  def testReadAllFlowObjectsWithParentFlowIDWithoutChildren(self):
    client_id = db_test_utils.InitializeClient(self.db)

    parent_flow = rdf_flow_objects.Flow()
    parent_flow.client_id = client_id
    parent_flow.flow_id = "AAAAAAAA"
    proto_flow = mig_flow_objects.ToProtoFlow(parent_flow)
    self.db.WriteFlowObject(proto_flow)

    with self.assertRaises(ValueError):
      self.db.ReadAllFlowObjects(
          client_id=client_id,
          parent_flow_id="AAAAAAAAA",
          include_child_flows=False,
      )

  def testReadAllFlowObjectsWithoutChildren(self):
    client_id_1 = "C.1111111111111111"
    self.db.WriteClientMetadata(client_id_1)

    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="0000001A")
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(
            client_id=client_id_1, flow_id="0000001B", parent_flow_id="0000001A"
        )
    )

    flows = self.db.ReadAllFlowObjects(include_child_flows=False)
    self.assertEqual([f.flow_id for f in flows], ["0000001A"])

  def testReadAllFlowObjectsWithNotCreatedBy(self):
    client_id_1 = "C.1111111111111111"
    self.db.WriteClientMetadata(client_id_1)

    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="000A0001", creator="foo")
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="000A0002", creator="bar")
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="000A0003", creator="baz")
    )

    flows = self.db.ReadAllFlowObjects(not_created_by=frozenset(["baz", "foo"]))
    self.assertCountEqual([f.flow_id for f in flows], ["000A0002"])

  def testReadAllFlowObjectsWithAllConditions(self):
    client_id_1 = "C.1111111111111111"
    client_id_2 = "C.2222222222222222"
    self.db.WriteClientMetadata(client_id_1)
    self.db.WriteClientMetadata(client_id_2)

    min_timestamp = self.db.Now()

    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="0000000A", creator="bar")
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="0000000F", creator="foo")
    )

    max_timestamp = self.db.Now()

    self.db.WriteFlowObject(
        flows_pb2.Flow(
            client_id=client_id_1, flow_id="0000000B", parent_flow_id="0000000A"
        )
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="0000000C")
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_1, flow_id="0000000D")
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id_2, flow_id="0000000E")
    )

    flows = self.db.ReadAllFlowObjects(
        client_id=client_id_1,
        min_create_time=min_timestamp,
        max_create_time=max_timestamp,
        include_child_flows=False,
        not_created_by=frozenset(["baz", "foo"]),
    )
    self.assertEqual([f.flow_id for f in flows], ["0000000A"])

  def testUpdateUnknownFlow(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    crash_info = jobs_pb2.ClientCrash(crash_message="oh no")
    with self.assertRaises(db.UnknownFlowError):
      self.db.UpdateFlow(
          "C.1234567890AAAAAA", flow_id, client_crash_info=crash_info
      )

  def testFlowUpdateChangesAllFields(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    flow_obj = self.db.ReadFlowObject(client_id, flow_id)
    flow_obj.cpu_time_used.user_cpu_time = 0.5
    flow_obj.cpu_time_used.system_cpu_time = 1.5
    flow_obj.num_replies_sent = 10
    flow_obj.network_bytes_sent = 100

    self.db.UpdateFlow(client_id, flow_id, flow_obj=flow_obj)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)

    # Last update times will differ.
    read_flow.ClearField("last_update_time")
    flow_obj.ClearField("last_update_time")
    self.assertEqual(read_flow, flow_obj)

  def testFlowStateUpdate(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    # Check that just updating flow_state works fine.
    self.db.UpdateFlow(
        client_id, flow_id, flow_state=flows_pb2.Flow.FlowState.CRASHED
    )
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.flow_state, flows_pb2.Flow.FlowState.CRASHED)

    # TODO(user): remove an option to update the flow by updating flow_obj.
    # It makes the DB API unnecessary complicated.
    # Check that changing flow_state through flow_obj works too.
    read_flow.flow_state = flows_pb2.Flow.FlowState.RUNNING
    self.db.UpdateFlow(client_id, flow_id, flow_obj=read_flow)

    read_flow_2 = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow_2.flow_state, flows_pb2.Flow.FlowState.RUNNING)

  def testUpdatingFlowObjAndFlowStateInSingleUpdateRaises(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    with self.assertRaises(db.ConflictingUpdateFlowArgumentsError):
      self.db.UpdateFlow(
          client_id,
          flow_id,
          flow_obj=read_flow,
          flow_state=flows_pb2.Flow.FlowState.CRASHED,
      )

  def testCrashInfoUpdate(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    crash_info = jobs_pb2.ClientCrash(crash_message="oh no")
    self.db.UpdateFlow(client_id, flow_id, client_crash_info=crash_info)
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.client_crash_info, crash_info)

  def testProcessingInformationUpdate(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    now = self.db.Now()
    deadline = now + rdfvalue.Duration.From(6, rdfvalue.HOURS)
    self.db.UpdateFlow(
        client_id,
        flow_id,
        processing_on="Worker1",
        processing_since=now,
        processing_deadline=deadline,
    )
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.processing_on, "Worker1")
    self.assertEqual(read_flow.processing_since, now)
    self.assertEqual(read_flow.processing_deadline, deadline)

    # None can be used to clear some fields.
    self.db.UpdateFlow(client_id, flow_id, processing_on=None)
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertFalse(read_flow.HasField("processing_on"))

    self.db.UpdateFlow(client_id, flow_id, processing_since=None)
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertFalse(read_flow.HasField("processing_since"))

    self.db.UpdateFlow(client_id, flow_id, processing_deadline=None)
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertFalse(read_flow.HasField("processing_deadline"))

  def testUpdateFlowUpdateTime(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    pre_update_time = self.db.Now().AsMicrosecondsSinceEpoch()

    self.db.UpdateFlow(
        client_id,
        flow_id,
        flow_state=flows_pb2.Flow.FlowState.FINISHED,
    )

    post_update_time = self.db.Now().AsMicrosecondsSinceEpoch()

    flow_obj = self.db.ReadFlowObject(client_id, flow_id)
    self.assertBetween(
        flow_obj.last_update_time, pre_update_time, post_update_time
    )

  def testRequestWriting(self):
    client_id_1 = "C.1234567890123456"
    client_id_2 = "C.1234567890123457"
    flow_id_1 = "1234ABCD"
    flow_id_2 = "ABCD1234"

    with self.assertRaises(db.AtLeastOneUnknownFlowError):
      self.db.WriteFlowRequests(
          [flows_pb2.FlowRequest(client_id=client_id_1, flow_id=flow_id_1)]
      )
    for client_id in [client_id_1, client_id_2]:
      self.db.WriteClientMetadata(client_id)

    requests = []
    for flow_id in [flow_id_1, flow_id_2]:
      for client_id in [client_id_1, client_id_2]:
        self.db.WriteFlowObject(
            flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
        )

        for i in range(1, 4):
          requests.append(
              flows_pb2.FlowRequest(
                  client_id=client_id, flow_id=flow_id, request_id=i
              )
          )

    self.db.WriteFlowRequests(requests)

    for flow_id in [flow_id_1, flow_id_2]:
      for client_id in [client_id_1, client_id_2]:
        read = self.db.ReadAllFlowRequestsAndResponses(
            client_id=client_id, flow_id=flow_id
        )

        self.assertLen(read, 3)
        self.assertEqual(
            [req.request_id for (req, _) in read], list(range(1, 4))
        )
        for _, responses in read:
          self.assertEqual(responses, {})

  def _WriteRequestForProcessing(self, client_id, flow_id, request_id):
    req_func = mock.Mock()
    self.db.RegisterFlowProcessingHandler(req_func)
    self.addCleanup(self.db.UnregisterFlowProcessingHandler)

    marked_flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=3
    )

    # We write 2 requests, one after another:
    # First request is the request provided by the user. Second is
    # a special (i.e. marked) one.
    #
    # The marked request is guaranteed to trigger processing. This way
    # tests relying on flow processing callback being called (or not being
    # called) can avoid race conditions: flow processing callback is guaranteed
    # to be called for the marked request after it's either called or not called
    # for the  user-supplied request. Effectively, callback's invocation for
    # the marked requests acts as a checkpoint: after it we can make
    # assertions.
    request = flows_pb2.FlowRequest(
        flow_id=flow_id,
        client_id=client_id,
        request_id=request_id,
        needs_processing=True,
    )
    marked_request = flows_pb2.FlowRequest(
        flow_id=marked_flow_id,
        client_id=client_id,
        request_id=3,
        needs_processing=True,
    )

    self.db.WriteFlowRequests([request, marked_request])

    marked_found = False
    cur_time = rdfvalue.RDFDatetime.Now()
    while True:
      requests = []
      for call in req_func.call_args_list:
        requests.extend(call[0])

      if any(r.flow_id == marked_flow_id for r in requests):
        # Poll-based implementations (i.e. MySQL) give no guarantess
        # with regards to the order in which requests are going to be processed.
        # In such implementations when 2 requests are retrieved from the DB,
        # they're both going to be processed concurrently in parallel threads.
        # For such implementations we allow for additional 0.1 seconds to pass
        # after the marked flow processing request is processed to allow for
        # possible parallel processing to finish.
        if marked_found:
          return len([r for r in requests if r.flow_id != marked_flow_id])
        else:
          marked_found = True

      time.sleep(0.1)
      if rdfvalue.RDFDatetime.Now() - cur_time > rdfvalue.Duration.From(
          10, rdfvalue.SECONDS
      ):
        self.fail("Flow request was not processed in time.")

  def testRequestWritingHighIDDoesntTriggerFlowProcessing(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=3
    )

    requests_triggered = self._WriteRequestForProcessing(client_id, flow_id, 4)
    # Not the expected request.
    self.assertEqual(requests_triggered, 0)

  def testRequestWritingLowIDDoesntTriggerFlowProcessing(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=3
    )

    requests_triggered = self._WriteRequestForProcessing(client_id, flow_id, 2)
    # Not the expected request.
    self.assertEqual(requests_triggered, 0)

  def testRequestWritingExpectedIDTriggersFlowProcessing(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=3
    )

    requests_triggered = self._WriteRequestForProcessing(client_id, flow_id, 3)
    # This one is.
    self.assertEqual(requests_triggered, 1)

  def testFlowRequestsWithStartTimeAreCorrectlyDelayed(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=3
    )

    req_func = mock.Mock()
    self.db.RegisterFlowProcessingHandler(req_func)
    self.addCleanup(self.db.UnregisterFlowProcessingHandler)

    cur_time = rdfvalue.RDFDatetime.Now()
    request = flows_pb2.FlowRequest(
        flow_id=flow_id,
        client_id=client_id,
        request_id=3,
        start_time=int(cur_time + rdfvalue.Duration.From(2, rdfvalue.SECONDS)),
        needs_processing=True,
    )

    self.db.WriteFlowRequests([request])
    self.assertEqual(req_func.call_count, 0)

    while req_func.call_count == 0:
      time.sleep(0.1)
      if rdfvalue.RDFDatetime.Now() - cur_time > rdfvalue.Duration.From(
          10, rdfvalue.SECONDS
      ):
        self.fail("Flow request was not processed in time.")

    self.assertGreaterEqual(
        rdfvalue.RDFDatetime.Now() - cur_time,
        rdfvalue.Duration.From(2, rdfvalue.SECONDS),
    )

  def testDeleteFlowRequests(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    requests = []
    responses = []
    for request_id in range(1, 4):
      requests.append(
          flows_pb2.FlowRequest(
              client_id=client_id, flow_id=flow_id, request_id=request_id
          )
      )
      responses.append(
          flows_pb2.FlowResponse(
              client_id=client_id,
              flow_id=flow_id,
              request_id=request_id,
              response_id=1,
          )
      )

    self.db.WriteFlowRequests(requests)
    self.db.WriteFlowResponses(responses)

    request_list = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertCountEqual(
        [req.request_id for req, _ in request_list],
        [req.request_id for req in requests],
    )

    random.shuffle(requests)

    while requests:
      request = requests.pop()
      self.db.DeleteFlowRequests([request])
      request_list = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
      self.assertCountEqual(
          [req.request_id for req, _ in request_list],
          [req.request_id for req in requests],
      )

  def testResponsesForUnknownFlow(self):
    client_id = "C.1234567890123456"
    flow_id = "1234ABCD"

    # This will not raise but also not write anything.
    with test_lib.SuppressLogs():
      self.db.WriteFlowResponses([
          flows_pb2.FlowResponse(
              client_id=client_id, flow_id=flow_id, request_id=1, response_id=1
          )
      ])
    read = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertEqual(read, [])

  def testResponsesForUnknownRequest(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    request = flows_pb2.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1
    )
    self.db.WriteFlowRequests([request])

    # Write two responses at a time, one request exists, the other doesn't.
    with test_lib.SuppressLogs():
      self.db.WriteFlowResponses([
          flows_pb2.FlowResponse(
              client_id=client_id, flow_id=flow_id, request_id=1, response_id=1
          ),
          flows_pb2.FlowResponse(
              client_id=client_id, flow_id=flow_id, request_id=2, response_id=1
          ),
      ])

    # We should have one response in the db.
    read = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(read, 1)
    request, responses = read[0]
    self.assertLen(responses, 1)

  def testWriteResponsesConcurrent(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    request = flows_pb2.FlowRequest()
    request.client_id = client_id
    request.flow_id = flow_id
    request.request_id = 1
    request.next_state = "FOO"
    self.db.WriteFlowRequests([request])

    response = flows_pb2.FlowResponse()
    response.client_id = client_id
    response.flow_id = flow_id
    response.request_id = 1
    response.response_id = 1

    status = flows_pb2.FlowStatus()
    status.client_id = client_id
    status.flow_id = flow_id
    status.request_id = 1
    status.response_id = 2

    def ResponseThread():
      self.db.WriteFlowResponses([response])

    def StatusThread():
      self.db.WriteFlowResponses([status])

    response_thread = threading.Thread(target=ResponseThread)
    status_thread = threading.Thread(target=StatusThread)

    response_thread.start()
    status_thread.start()

    response_thread.join()
    status_thread.join()

    ready_requests = self.db.ReadFlowRequests(
        client_id=client_id,
        flow_id=flow_id,
    )
    self.assertIn(request.request_id, ready_requests)

    request, _ = ready_requests[request.request_id]
    self.assertTrue(request.needs_processing)

  def testStatusForUnknownRequest(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    request = flows_pb2.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1
    )
    self.db.WriteFlowRequests([request])

    # Write two status responses at a time, one for the request that exists, one
    # for a request that doesn't.
    with test_lib.SuppressLogs():
      self.db.WriteFlowResponses([
          flows_pb2.FlowStatus(
              client_id=client_id, flow_id=flow_id, request_id=1, response_id=1
          ),
          flows_pb2.FlowStatus(
              client_id=client_id, flow_id=flow_id, request_id=2, response_id=1
          ),
      ])

    # We should have one response in the db.
    read = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(read, 1)
    request, responses = read[0]
    self.assertLen(responses, 1)

    self.assertEqual(request.nr_responses_expected, 1)

  def testResponseWriting(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=1,
        needs_processing=False,
    )

    before_write = self.db.Now()
    self.db.WriteFlowRequests([request])
    after_write = self.db.Now()

    responses = [
        flows_pb2.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=i
        )
        for i in range(3)
    ]

    self.db.WriteFlowResponses(responses)

    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(all_requests, 1)

    read_request, read_responses = all_requests[0]
    self.assertEqual(read_request.client_id, request.client_id)
    self.assertEqual(read_request.flow_id, request.flow_id)
    self.assertEqual(read_request.request_id, request.request_id)
    self.assertEqual(read_request.needs_processing, request.needs_processing)
    self.assertBetween(read_request.timestamp, before_write, after_write)
    self.assertEqual(list(read_responses), [0, 1, 2])

    for response_id, response in read_responses.items():
      self.assertEqual(response.response_id, response_id)

  def testResponseWritingForDuplicateResponses(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=1,
        needs_processing=False,
    )

    before_write = self.db.Now()
    self.db.WriteFlowRequests([request])
    after_write = self.db.Now()

    responses = [
        flows_pb2.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=0
        ),
        flows_pb2.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=0
        ),
    ]

    self.db.WriteFlowResponses(responses)

    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(all_requests, 1)

    read_request, read_responses = all_requests[0]
    self.assertEqual(read_request.client_id, request.client_id)
    self.assertEqual(read_request.flow_id, request.flow_id)
    self.assertEqual(read_request.request_id, request.request_id)
    self.assertEqual(read_request.needs_processing, request.needs_processing)
    self.assertBetween(read_request.timestamp, before_write, after_write)
    self.assertEqual(list(read_responses), [0])

    for response_id, response in read_responses.items():
      self.assertEqual(response.response_id, response_id)

  def testCompletingMultipleRequests(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    requests = []
    responses = []
    for i in range(5):
      requests.append(
          flows_pb2.FlowRequest(
              client_id=client_id,
              flow_id=flow_id,
              request_id=i,
              needs_processing=False,
          )
      )
      responses.append(
          flows_pb2.FlowResponse(
              client_id=client_id, flow_id=flow_id, request_id=i, response_id=1
          )
      )
      responses.append(
          flows_pb2.FlowStatus(
              client_id=client_id, flow_id=flow_id, request_id=i, response_id=2
          )
      )

    self.db.WriteFlowRequests(requests)

    # Complete all requests at once.
    self.db.WriteFlowResponses(responses)

    read = self.db.ReadAllFlowRequestsAndResponses(
        client_id=client_id, flow_id=flow_id
    )
    self.assertEqual(len(read), 5)
    for req, _ in read:
      self.assertTrue(req.needs_processing)

  def testStatusMessagesCanBeWrittenAndRead(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=1,
        needs_processing=False,
    )
    self.db.WriteFlowRequests([request])

    responses = [
        flows_pb2.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=i
        )
        for i in range(3)
    ]
    # Also store an Iterator, why not.
    responses.append(
        flows_pb2.FlowIterator(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=3
        )
    )
    responses.append(
        flows_pb2.FlowStatus(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=4
        )
    )
    self.db.WriteFlowResponses(responses)

    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(all_requests, 1)

    _, read_responses = all_requests[0]
    self.assertEqual(list(read_responses), [0, 1, 2, 3, 4])
    for i in range(3):
      self.assertIsInstance(read_responses[i], flows_pb2.FlowResponse)
    self.assertIsInstance(read_responses[3], flows_pb2.FlowIterator)
    self.assertIsInstance(read_responses[4], flows_pb2.FlowStatus)

  def _ReadRequest(self, client_id, flow_id, request_id):
    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    for request, unused_responses in all_requests:
      if request.request_id == request_id:
        return request

  def _Responses(
      self, client_id, flow_id, request_id, num_responses
  ) -> list[flows_pb2.FlowResponse]:
    return [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_id,
            response_id=i,
        )
        for i in range(1, num_responses + 1)
    ]

  def _ResponsesAndStatus(
      self, client_id, flow_id, request_id, num_responses
  ) -> list[Union[flows_pb2.FlowResponse, flows_pb2.FlowStatus]]:
    return self._Responses(client_id, flow_id, request_id, num_responses) + [
        flows_pb2.FlowStatus(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_id,
            response_id=num_responses + 1,
        )
    ]

  def _WriteRequestAndCompleteResponses(
      self, client_id, flow_id, request_id, num_responses
  ):
    request = flows_pb2.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=request_id
    )
    self.db.WriteFlowRequests([request])

    return self._WriteCompleteResponses(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        num_responses=num_responses,
    )

  def _WriteCompleteResponses(
      self, client_id, flow_id, request_id, num_responses
  ):
    # Write <num_responses> responses and a status in random order.
    responses = self._ResponsesAndStatus(
        client_id, flow_id, request_id, num_responses
    )
    random.shuffle(responses)

    for response in responses:
      request = self._ReadRequest(client_id, flow_id, request_id)
      self.assertIsNotNone(request)
      # This is false up to the moment when we write the last response.
      self.assertFalse(request.needs_processing)

      self.db.WriteFlowResponses([response])

    # Now that we sent all responses, the request needs processing.
    request = self._ReadRequest(client_id, flow_id, request_id)
    self.assertTrue(request.needs_processing)
    self.assertEqual(request.nr_responses_expected, len(responses))

    # Flow processing request might have been generated.
    return len(self.db.ReadFlowProcessingRequests())

  def testResponsesForEarlierRequestDontTriggerFlowProcessing(self):
    # Write a flow that is waiting for request #2.
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )
    requests_triggered = self._WriteRequestAndCompleteResponses(
        client_id, flow_id, request_id=1, num_responses=3
    )

    # No flow processing request generated for request 1 (we are waiting
    # for #2).
    self.assertEqual(requests_triggered, 0)

  def testResponsesForEarlierIncrementalRequestDontTriggerFlowProcessing(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )
    request_id = 1

    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        next_state="Next",
        callback_state="Callback",
    )
    self.db.WriteFlowRequests([request])

    responses = self._Responses(client_id, flow_id, request_id, 1)
    self.db.WriteFlowResponses(responses)

    requests_to_process = self.db.ReadFlowProcessingRequests()
    self.assertEmpty(requests_to_process)

  def testResponsesForLaterRequestDontTriggerFlowProcessing(self):
    # Write a flow that is waiting for request #2.
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )
    requests_triggered = self._WriteRequestAndCompleteResponses(
        client_id, flow_id, request_id=3, num_responses=7
    )

    # No flow processing request generated for request 3 (we are waiting
    # for #2).
    self.assertEqual(requests_triggered, 0)

  def testResponsesForLaterIncrementalRequestDoNotTriggerIncrementalProcessing(
      self,
  ):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )
    request_id = 3

    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        next_state="Next",
        callback_state="Callback",
    )
    self.db.WriteFlowRequests([request])

    responses = self._Responses(client_id, flow_id, request_id, 1)
    self.db.WriteFlowResponses(responses)

    requests_to_process = self.db.ReadFlowProcessingRequests()
    self.assertEmpty(requests_to_process)

  def testResponsesForExpectedRequestTriggerFlowProcessing(self):
    # Write a flow that is waiting for request #2.
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )
    requests_triggered = self._WriteRequestAndCompleteResponses(
        client_id, flow_id, request_id=2, num_responses=5
    )

    # This one generates a request.
    self.assertEqual(requests_triggered, 1)

  def testResponsesForExpectedIncrementalRequestTriggerIncrementalProcessing(
      self,
  ):
    request_id = 2
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=request_id
    )

    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        next_state="Next",
        callback_state="Callback",
    )
    self.db.WriteFlowRequests([request])

    requests_to_process = self.db.ReadFlowProcessingRequests()
    self.assertEmpty(requests_to_process)

    responses = self._Responses(client_id, flow_id, request_id, 1)
    self.db.WriteFlowResponses(responses)

    requests_to_process = self.db.ReadFlowProcessingRequests()
    self.assertLen(requests_to_process, 1)

  def testCompletingRequestsWithResponsesTriggersDelayedProcessingCorrectly(
      self,
  ):
    # Pretend that the flow currently processes request #1.
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )

    start_time = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration.From(
        6, rdfvalue.SECONDS
    )

    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=2,
        nr_responses_expected=2,
        start_time=int(start_time),
        next_state="Foo",
        next_response_id=1,
        needs_processing=False,
    )

    responses = []
    responses.append(
        flows_pb2.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=2, response_id=0
        )
    )
    responses.append(
        flows_pb2.FlowStatus(
            client_id=client_id,
            flow_id=flow_id,
            request_id=2,
            response_id=2,
            status=rdf_flow_objects.FlowStatus.Status.OK,
        )
    )

    request_queue = queue.Queue()

    def Callback(request: flows_pb2.FlowProcessingRequest):
      self.db.AckFlowProcessingRequests([request])
      request_queue.put(request)

    self.db.RegisterFlowProcessingHandler(Callback)
    self.addCleanup(self.db.UnregisterFlowProcessingHandler)

    self.db.WriteFlowRequests([request])
    self.db.WriteFlowResponses(responses)

    # The request #2 shouldn't be processed within 3 seconds...
    try:
      request_queue.get(True, timeout=3)
      self.fail("Notification arrived too quickly")
    except queue.Empty:
      pass

    # ...but should be procssed within the next 10 seconds.
    try:
      request_queue.get(True, timeout=10)
    except queue.Empty:
      self.fail("Notification didn't arrive when it was expected to.")

  def testRewritingResponsesForRequestDoesNotTriggerAdditionalProcessing(self):
    # Write a flow that is waiting for request #2.
    client_id = db_test_utils.InitializeClient(self.db)
    marked_client_id = db_test_utils.InitializeClient(self.db)

    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )
    marked_flow_id = db_test_utils.InitializeFlow(
        self.db, marked_client_id, next_request_to_process=2
    )

    request = flows_pb2.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=2
    )
    self.db.WriteFlowRequests([request])

    marked_request = flows_pb2.FlowRequest(
        client_id=marked_client_id, flow_id=marked_flow_id, request_id=2
    )
    self.db.WriteFlowRequests([marked_request])

    # Generate responses together with a status message.
    responses = self._ResponsesAndStatus(client_id, flow_id, 2, 4)
    marked_responses = self._ResponsesAndStatus(
        marked_client_id, marked_flow_id, 2, 4
    )

    req_func = mock.Mock()
    self.db.RegisterFlowProcessingHandler(req_func)
    self.addCleanup(self.db.UnregisterFlowProcessingHandler)

    # Write responses. This should trigger flow request processing.
    self.db.WriteFlowResponses(responses)
    cur_time = rdfvalue.RDFDatetime.Now()
    while True:
      if req_func.call_count == 1:
        break
      time.sleep(0.1)
      if rdfvalue.RDFDatetime.Now() - cur_time > rdfvalue.Duration.From(
          10, rdfvalue.SECONDS
      ):
        self.fail("Flow request was not processed in time.")

    req_func.reset_mock()

    # Write responses again. No further processing of these should be triggered.
    self.db.WriteFlowResponses(responses)
    # Testing for a callback *not being* called is not entirely trivial. Waiting
    # for 1 (or 5, or 10) seconds is not acceptable (too slow). An approach used
    # here: we need to trigger certain event - a kind of a checkpoint that is
    # guaranteed to be triggered after the callback is called or is not called.
    #
    # Explicitly write marked_responses to trigger the flow processing handler.
    # After flow processing handler is triggered for marked_responses, we can
    # check that it wasn't triggered for responses.
    self.db.WriteFlowResponses(marked_responses)
    cur_time = rdfvalue.RDFDatetime.Now()
    marked_found = False
    while True:
      requests = []
      for call in req_func.call_args_list:
        requests.extend(call[0])

      if any(r.flow_id == marked_flow_id for r in requests):
        # Poll-based implementations (i.e. MySQL) give no guarantess
        # with regards to the order in which requests are going to be processed.
        # In such implementations when 2 requests are retrieved from the DB,
        # they're both going to be processed concurrently in parallel threads.
        # For such implementations we allow for additional 0.1 seconds to pass
        # after the marked flow processing request is processed to allow for
        # possible parallel processing to finish.
        if marked_found:
          self.assertEmpty([r for r in requests if r.flow_id != marked_flow_id])
          break
        else:
          marked_found = True

      time.sleep(0.1)
      if rdfvalue.RDFDatetime.Now() - cur_time > rdfvalue.Duration.From(
          10, rdfvalue.SECONDS
      ):
        self.fail("Flow request was not processed in time.")

  def testRewritingResponsesForIncrementalRequestsTriggersMoreProcessing(self):
    request_id = 2
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=request_id
    )

    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        next_state="Next",
        callback_state="Callback",
    )
    self.db.WriteFlowRequests([request])

    responses = self._Responses(client_id, flow_id, request_id, 1)

    self.db.WriteFlowResponses(responses)
    requests_to_process = self.db.ReadFlowProcessingRequests()
    self.assertLen(requests_to_process, 1)

    self.db.DeleteAllFlowProcessingRequests()
    requests_to_process = self.db.ReadFlowProcessingRequests()
    self.assertEmpty(requests_to_process)

    # Writing same responses second time triggers a processing requests.
    self.db.WriteFlowResponses(responses)
    requests_to_process = self.db.ReadFlowProcessingRequests()
    self.assertLen(requests_to_process, 1)

  def testLeaseFlowForProcessingRaisesIfParentHuntIsStoppedOrCompleted(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)
    self.db.UpdateHuntObject(
        hunt_id, hunt_state=hunts_pb2.Hunt.HuntState.STOPPED
    )

    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, parent_hunt_id=hunt_id
    )
    processing_time = rdfvalue.Duration.From(60, rdfvalue.SECONDS)

    with self.assertRaises(db.ParentHuntIsNotRunningError):
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

    self.db.UpdateHuntObject(
        hunt_id, hunt_state=hunts_pb2.Hunt.HuntState.COMPLETED
    )

    with self.assertRaises(db.ParentHuntIsNotRunningError):
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

    self.db.UpdateHuntObject(
        hunt_id, hunt_state=hunts_pb2.Hunt.HuntState.STARTED
    )

    # Should work again.
    self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

  def testLeaseFlowForProcessingThatIsAlreadyBeingProcessed(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    processing_time = rdfvalue.Duration.From(60, rdfvalue.SECONDS)

    flow_for_processing = self.db.LeaseFlowForProcessing(
        client_id, flow_id, processing_time
    )

    # Already marked as being processed.
    with self.assertRaises(ValueError):
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

    self.assertTrue(self.db.ReleaseProcessedFlow(flow_for_processing))

    # Should work again.
    self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

  def testLeaseFlowForProcessingAfterProcessingTimeExpiration(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    processing_time = rdfvalue.Duration.From(60, rdfvalue.SECONDS)
    now = rdfvalue.RDFDatetime.Now()

    with test_lib.FakeTime(now):
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

    # Already marked as being processed.
    with self.assertRaises(ValueError):
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

    after_deadline = (
        now + processing_time + rdfvalue.Duration.From(1, rdfvalue.SECONDS)
    )
    with test_lib.FakeTime(after_deadline):
      # Should work again.
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

  def testLeaseFlowForProcessingUpdatesHuntCounters(self):
    hunt_id = db_test_utils.InitializeHunt(self.db)

    processing_time = rdfvalue.Duration.From(60, rdfvalue.SECONDS)

    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, flow_id=hunt_id, parent_hunt_id=hunt_id
    )

    flow_for_processing = self.db.LeaseFlowForProcessing(
        client_id, flow_id, processing_time
    )
    flow_for_processing.num_replies_sent = 10

    client_summary_result = flows_pb2.FlowResult(
        client_id=client_id, flow_id=flow_id, hunt_id=hunt_id
    )
    client_summary_result.payload.Pack(
        jobs_pb2.ClientSummary(client_id=client_id)
    )
    sample_results = [client_summary_result] * 10
    self._WriteFlowResults(sample_results)

    self.assertTrue(self.db.ReleaseProcessedFlow(flow_for_processing))

    counters = self.db.ReadHuntCounters(hunt_id)
    self.assertEqual(counters.num_clients_with_results, 1)
    self.assertEqual(counters.num_results, 10)

  def testLeaseFlowForProcessingUpdatesFlowObjects(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    now = rdfvalue.RDFDatetime.Now()
    processing_time = rdfvalue.Duration.From(60, rdfvalue.SECONDS)
    processing_deadline = now + processing_time

    with test_lib.FakeTime(now):
      flow_for_processing = self.db.LeaseFlowForProcessing(
          client_id, flow_id, processing_time
      )

    self.assertEqual(flow_for_processing.processing_on, utils.ProcessIdString())
    # Using assertGreaterEqual and assertLess, as processing_since might come
    # from the commit timestamp and thus not be influenced by test_lib.FakeTime.
    self.assertGreaterEqual(flow_for_processing.processing_since, int(now))
    self.assertLess(
        flow_for_processing.processing_since, int(now + rdfvalue.Duration("5s"))
    )
    self.assertEqual(
        flow_for_processing.processing_deadline, int(processing_deadline)
    )

    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.processing_on, flow_for_processing.processing_on)
    self.assertEqual(
        read_flow.processing_since, flow_for_processing.processing_since
    )
    self.assertEqual(
        read_flow.processing_deadline,
        flow_for_processing.processing_deadline,
    )
    self.assertEqual(read_flow.num_replies_sent, 0)

    flow_for_processing.next_request_to_process = 5
    flow_for_processing.num_replies_sent = 10

    self.assertTrue(self.db.ReleaseProcessedFlow(flow_for_processing))
    # Check that returning the flow doesn't change the flow object.
    self.assertEqual(read_flow.processing_on, flow_for_processing.processing_on)
    self.assertEqual(
        read_flow.processing_since, flow_for_processing.processing_since
    )
    self.assertEqual(
        read_flow.processing_deadline,
        flow_for_processing.processing_deadline,
    )

    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertFalse(read_flow.processing_on)
    self.assertFalse(read_flow.HasField("processing_since"))
    self.assertFalse(read_flow.HasField("processing_deadline"))
    self.assertEqual(read_flow.next_request_to_process, 5)
    self.assertEqual(read_flow.num_replies_sent, 10)

  def testFlowLastUpdateTime(self):
    processing_time = rdfvalue.Duration.From(60, rdfvalue.SECONDS)

    t0 = self.db.Now().AsMicrosecondsSinceEpoch()
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    t1 = self.db.Now().AsMicrosecondsSinceEpoch()

    read_flow = self.db.ReadFlowObject(client_id, flow_id)

    self.assertBetween(read_flow.last_update_time, t0, t1)

    flow_for_processing = self.db.LeaseFlowForProcessing(
        client_id, flow_id, processing_time
    )
    self.assertBetween(flow_for_processing.last_update_time, t0, t1)

    t2 = self.db.Now().AsMicrosecondsSinceEpoch()
    self.db.ReleaseProcessedFlow(flow_for_processing)
    t3 = self.db.Now().AsMicrosecondsSinceEpoch()

    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertBetween(read_flow.last_update_time, t2, t3)

  def testReleaseProcessedFlow(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )

    processing_time = rdfvalue.Duration.From(60, rdfvalue.SECONDS)

    processed_flow = self.db.LeaseFlowForProcessing(
        client_id, flow_id, processing_time
    )

    # Let's say we processed one request on this flow.
    processed_flow.next_request_to_process = 2

    # There are some requests ready for processing but not #2.
    self.db.WriteFlowRequests([
        flows_pb2.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=1,
            needs_processing=True,
        ),
        flows_pb2.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=4,
            needs_processing=True,
        ),
    ])
    self.assertTrue(self.db.ReleaseProcessedFlow(processed_flow))

    processed_flow = self.db.LeaseFlowForProcessing(
        client_id, flow_id, processing_time
    )
    # And another one.
    processed_flow.next_request_to_process = 3

    # But in the meantime, request 3 is ready for processing.
    self.db.WriteFlowRequests([
        flows_pb2.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=3,
            needs_processing=True,
        )
    ])

    self.assertFalse(self.db.ReleaseProcessedFlow(processed_flow))

  def testReleaseProcessedFlowWithRequestScheduledInFuture(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )

    processing_time = rdfvalue.Duration.From(60, rdfvalue.SECONDS)

    processed_flow = self.db.LeaseFlowForProcessing(
        client_id, flow_id, processing_time
    )

    # Let's say we processed one request on this flow.
    processed_flow.next_request_to_process = 2

    # There is a request ready for processing but only in the future.
    # It shouldn't be returned as ready for processing.
    self.db.WriteFlowRequests([
        flows_pb2.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=2,
            start_time=int(
                rdfvalue.RDFDatetime.Now()
                + rdfvalue.Duration.From(60, rdfvalue.SECONDS)
            ),
            needs_processing=True,
        ),
    ])
    self.assertTrue(self.db.ReleaseProcessedFlow(processed_flow))

  def testReleaseProcessedFlowWithProcessedFlowRequest(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    flow_request = flows_pb2.FlowRequest()
    flow_request.client_id = client_id
    flow_request.flow_id = flow_id
    flow_request.request_id = 1
    flow_request.needs_processing = False
    self.db.WriteFlowRequests([flow_request])

    flow_obj = flows_pb2.Flow()
    flow_obj.client_id = client_id
    flow_obj.flow_id = flow_id
    flow_obj.next_request_to_process = 1
    self.assertTrue(self.db.ReleaseProcessedFlow(flow_obj))

  def testReadChildFlows(self):
    client_id = "C.1234567890123456"
    self.db.WriteClientMetadata(client_id)

    self.db.WriteFlowObject(
        flows_pb2.Flow(flow_id="00000001", client_id=client_id)
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(
            flow_id="00000002", client_id=client_id, parent_flow_id="00000001"
        )
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(
            flow_id="00000003", client_id=client_id, parent_flow_id="00000002"
        )
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(
            flow_id="00000004", client_id=client_id, parent_flow_id="00000001"
        )
    )

    # This one is completely unrelated (different client id).
    self.db.WriteClientMetadata("C.1234567890123457")
    self.db.WriteFlowObject(
        flows_pb2.Flow(flow_id="00000001", client_id="C.1234567890123457")
    )
    self.db.WriteFlowObject(
        flows_pb2.Flow(
            flow_id="00000002",
            client_id="C.1234567890123457",
            parent_flow_id="00000001",
        )
    )

    children = self.db.ReadChildFlowObjects(client_id, "00000001")

    self.assertLen(children, 2)
    for c in children:
      self.assertEqual(c.parent_flow_id, "00000001")

    children = self.db.ReadChildFlowObjects(client_id, "00000002")
    self.assertLen(children, 1)
    self.assertEqual(children[0].parent_flow_id, "00000002")
    self.assertEqual(children[0].flow_id, "00000003")

    children = self.db.ReadChildFlowObjects(client_id, "00000003")
    self.assertEmpty(children)

  def _WriteRequestAndResponses(self, client_id, flow_id):
    self.db.WriteFlowObject(
        flows_pb2.Flow(client_id=client_id, flow_id=flow_id)
    )

    for request_id in range(1, 4):
      request = flows_pb2.FlowRequest(
          client_id=client_id, flow_id=flow_id, request_id=request_id
      )
      self.db.WriteFlowRequests([request])

      for response_id in range(1, 3):
        response = flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_id,
            response_id=response_id,
        )
        self.db.WriteFlowResponses([response])

  def _CheckRequestsAndResponsesAreThere(self, client_id, flow_id):
    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(all_requests, 3)
    for _, responses in all_requests:
      self.assertLen(responses, 2)

  def testDeleteAllFlowRequestsAndResponses(self):
    client_id1 = "C.1234567890123456"
    client_id2 = "C.1234567890123457"
    flow_id1 = "1234ABCD"
    flow_id2 = "1234ABCE"

    self.db.WriteClientMetadata(client_id1)
    self.db.WriteClientMetadata(client_id2)

    self._WriteRequestAndResponses(client_id1, flow_id1)
    self._WriteRequestAndResponses(client_id1, flow_id2)
    self._WriteRequestAndResponses(client_id2, flow_id1)
    self._WriteRequestAndResponses(client_id2, flow_id2)

    self._CheckRequestsAndResponsesAreThere(client_id1, flow_id1)
    self._CheckRequestsAndResponsesAreThere(client_id1, flow_id2)
    self._CheckRequestsAndResponsesAreThere(client_id2, flow_id1)
    self._CheckRequestsAndResponsesAreThere(client_id2, flow_id2)

    self.db.DeleteAllFlowRequestsAndResponses(client_id1, flow_id2)

    self._CheckRequestsAndResponsesAreThere(client_id1, flow_id1)
    self._CheckRequestsAndResponsesAreThere(client_id2, flow_id1)
    self._CheckRequestsAndResponsesAreThere(client_id2, flow_id2)

    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id1, flow_id2)
    self.assertEqual(all_requests, [])

  def testReadFlowRequests_ReadsAllRequestsAndResponses(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )

    flow_requests = self.db.ReadFlowRequests(client_id, flow_id)
    self.assertEmpty(flow_requests)

    # Write some requests and responses.

    request_ids = [10, 1]  # Requests might not arrive in order.
    response_ids = [4, 1, 2]  # Responses might not arrive in order.

    requests = []
    for request_id in request_ids:
      requests.append(
          flows_pb2.FlowRequest(
              client_id=client_id,
              flow_id=flow_id,
              request_id=request_id,
              needs_processing=True,
              next_response_id=1,
          )
      )
    self.db.WriteFlowRequests(requests)

    responses = []
    # Responses for request with id 10.
    for response_id in response_ids:
      responses.append(
          flows_pb2.FlowResponse(
              client_id=client_id,
              flow_id=flow_id,
              request_id=10,
              response_id=response_id,
          )
      )
    before_write_ts = self.db.Now()
    self.db.WriteFlowResponses(responses)
    after_write_ts = self.db.Now()

    flow_requests = self.db.ReadFlowRequests(client_id, flow_id)
    self.assertLen(flow_requests, 2)

    self.assertEqual(set(flow_requests.keys()), set(request_ids))

    request_1, responses_1 = flow_requests[1]
    self.assertEqual(request_1.request_id, 1)
    self.assertEqual(request_1.flow_id, flow_id)
    self.assertEqual(request_1.client_id, client_id)
    self.assertEqual(request_1.needs_processing, True)
    self.assertEmpty(responses_1)

    request_10, responses_10 = flow_requests[10]
    self.assertEqual(request_10.request_id, 10)
    self.assertEqual(request_10.flow_id, flow_id)
    self.assertEqual(request_10.client_id, client_id)
    self.assertEqual(request_10.needs_processing, True)
    self.assertEqual(request_10.next_response_id, 1)
    self.assertLen(responses_10, 3)

    expected_responses = sorted(responses, key=lambda r: r.response_id)
    for response, expected in zip(responses_10, expected_responses):
      self.assertEqual(response.client_id, expected.client_id)
      self.assertEqual(response.flow_id, expected.flow_id)
      self.assertEqual(response.request_id, expected.request_id)
      self.assertEqual(response.response_id, expected.response_id)
      self.assertBetween(response.timestamp, before_write_ts, after_write_ts)

  def testReadFlowRequests_ReturnsOnlyResultsForGivenFlowAndClient(self):
    client_id_1 = db_test_utils.InitializeClient(self.db)
    flow_id_1 = db_test_utils.InitializeFlow(self.db, client_id_1)

    client_id_2 = db_test_utils.InitializeClient(self.db)
    flow_id_2 = db_test_utils.InitializeFlow(self.db, client_id_2)

    requests = []
    responses = []
    for client_id, flow_id in (
        (client_id_1, flow_id_1),
        (client_id_2, flow_id_2),
    ):
      requests.append(
          flows_pb2.FlowRequest(
              client_id=client_id,
              flow_id=flow_id,
              request_id=1,
          )
      )
      responses.append(
          flows_pb2.FlowResponse(
              client_id=client_id,
              flow_id=flow_id,
              request_id=1,
              response_id=2,
          )
      )
    self.db.WriteFlowRequests(requests)
    self.db.WriteFlowResponses(responses)

    flow_requests = self.db.ReadFlowRequests(client_id_1, flow_id_1)

    self.assertEqual(list(flow_requests), [1])
    request, responses = flow_requests[1]

    self.assertEqual(request.client_id, client_id_1)
    self.assertEqual(request.flow_id, flow_id_1)

    self.assertLen(responses, 1)
    self.assertEqual(responses[0].client_id, client_id_1)
    self.assertEqual(responses[0].flow_id, flow_id_1)
    self.assertEqual(responses[0].response_id, 2)

  def testUpdateIncrementalFlowRequests(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    requests = []
    for request_id in range(10):
      requests.append(
          flows_pb2.FlowRequest(
              client_id=client_id,
              flow_id=flow_id,
              request_id=request_id,
              next_state="Next",
              callback_state="Callback",
          )
      )
    self.db.WriteFlowRequests(requests)

    update_map = dict((i, i * 2) for i in range(10))
    self.db.UpdateIncrementalFlowRequests(client_id, flow_id, update_map)

    for request_id in range(10):
      r = self._ReadRequest(client_id, flow_id, request_id)
      self.assertEqual(r.next_response_id, request_id * 2)

  def testFlowProcessingRequestsQueue(self):
    client_id = db_test_utils.InitializeClient(self.db)

    flow_ids = []
    for _ in range(5):
      flow_id = db_test_utils.InitializeFlow(self.db, client_id)
      flow_ids.append(flow_id)

    request_queue = queue.Queue()

    def Callback(request: flows_pb2.FlowProcessingRequest):
      self.db.AckFlowProcessingRequests([request])
      request_queue.put(request)

    self.db.RegisterFlowProcessingHandler(Callback)
    self.addCleanup(self.db.UnregisterFlowProcessingHandler)

    requests = []
    for flow_id in flow_ids:
      requests.append(
          flows_pb2.FlowProcessingRequest(client_id=client_id, flow_id=flow_id)
      )

    pre_creation_time = self.db.Now()
    self.db.WriteFlowProcessingRequests(requests)
    post_creation_time = self.db.Now()

    got = []
    while len(got) < 5:
      try:
        l = request_queue.get(True, timeout=6)
        got.append(l)
      except queue.Empty:
        self.fail(
            "Timed out waiting for messages, expected 5, got %d" % len(got)
        )

    self.assertCountEqual(
        [r.client_id for r in requests], [g.client_id for g in got]
    )
    self.assertCountEqual(
        [r.flow_id for r in requests], [g.flow_id for g in got]
    )
    for g in got:
      self.assertBetween(
          int(g.creation_time), pre_creation_time, post_creation_time
      )

  def testFlowProcessingRequestsQueueWithDelay(self):
    client_id = db_test_utils.InitializeClient(self.db)

    flow_ids = []
    for _ in range(5):
      flow_id = db_test_utils.InitializeFlow(self.db, client_id)
      flow_ids.append(flow_id)

    request_queue = queue.Queue()

    def Callback(request: flows_pb2.FlowProcessingRequest):
      self.db.AckFlowProcessingRequests([request])
      request_queue.put(request)

    self.db.RegisterFlowProcessingHandler(Callback)
    self.addCleanup(self.db.UnregisterFlowProcessingHandler)

    now = rdfvalue.RDFDatetime.Now()
    delivery_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
        now.AsSecondsSinceEpoch() + 0.5
    )
    requests = []
    for flow_id in flow_ids:
      requests.append(
          flows_pb2.FlowProcessingRequest(
              client_id=client_id,
              flow_id=flow_id,
              delivery_time=int(delivery_time),
          )
      )

    pre_creation_time = self.db.Now()
    self.db.WriteFlowProcessingRequests(requests)
    post_creation_time = self.db.Now()

    got = []
    while len(got) < 5:
      try:
        l = request_queue.get(True, timeout=6)
        got.append(l)
      except queue.Empty:
        self.fail(
            "Timed out waiting for messages, expected 5, got %d" % len(got)
        )
      self.assertGreater(rdfvalue.RDFDatetime.Now(), l.delivery_time)

    self.assertCountEqual(
        [r.client_id for r in requests], [g.client_id for g in got]
    )
    self.assertCountEqual(
        [r.flow_id for r in requests], [g.flow_id for g in got]
    )
    for g in got:
      self.assertBetween(g.creation_time, pre_creation_time, post_creation_time)

    leftover = self.db.ReadFlowProcessingRequests()
    self.assertEmpty(leftover)

  def testFlowRequestsStartTimeIsRespectedWhenResponsesAreWritten(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    request_queue = queue.Queue()

    def Callback(request: flows_pb2.FlowProcessingRequest):
      self.db.AckFlowProcessingRequests([request])
      request_queue.put(request)

    self.db.RegisterFlowProcessingHandler(Callback)
    self.addCleanup(self.db.UnregisterFlowProcessingHandler)

    now = rdfvalue.RDFDatetime.Now()
    delivery_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
        now.AsSecondsSinceEpoch() + 5
    )
    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=1,
        start_time=int(delivery_time),
        nr_responses_expected=1,
        next_state="Foo",
        needs_processing=True,
    )
    self.db.WriteFlowRequests([request])

    payload_any = any_pb2.Any()
    payload_any.Pack(flows_pb2.FlowRequest())

    response = flows_pb2.FlowResponse(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request.request_id,
        response_id=0,
        # For the purpose of the test, the payload can be arbitrary,
        # using rdf_flow_objects.FlowRequest as a sample struct.
        payload=payload_any,
    )
    self.db.WriteFlowResponses([response])

    try:
      l = request_queue.get(True, timeout=3)
      self.fail("Expected to get no messages within 3 seconds, got 1")
    except queue.Empty:
      pass

    try:
      l = request_queue.get(True, timeout=10)
    except queue.Empty:
      self.fail("Timed out waiting for messages")

    self.assertGreater(rdfvalue.RDFDatetime.Now(), l.delivery_time)

  def testFlowProcessingRequestIsAlwaysWrittenIfStartTimeIsSpecified(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    fprs = self.db.ReadFlowProcessingRequests()
    self.assertEmpty(fprs)

    now = rdfvalue.RDFDatetime.Now()
    delivery_time = now + rdfvalue.Duration("5s")
    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        # Note that the request_id is different from the next_request_id
        # recorded in the flow object (with a freshly initialized flow that
        # will be 1). For flow requests with start_time set, we have to make
        # sure that a FlowProcessingRequest is written to the queue so that
        # the flow would "wake up" when needed - by that time the
        # next_request_id might be equivalent to the FlowRequest's request_id
        # and the state will get processed.
        request_id=42,
        start_time=int(delivery_time),
        nr_responses_expected=1,
        next_state="Foo",
        needs_processing=True,
    )
    self.db.WriteFlowRequests([request])

    fprs = self.db.ReadFlowProcessingRequests()
    self.assertLen(fprs, 1)

  def testFPRNotWrittenIfStartTimeNotSpecifiedAndIdDoesNotMatch(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    fprs = self.db.ReadFlowProcessingRequests()
    self.assertEmpty(fprs)

    request = flows_pb2.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=42,
        nr_responses_expected=1,
        next_state="Foo",
        needs_processing=True,
    )
    self.db.WriteFlowRequests([request])

    fprs = self.db.ReadFlowProcessingRequests()
    self.assertEmpty(fprs)

  def testIncrementalFlowProcessingRequests(self):
    pass

  def testAcknowledgingFlowProcessingRequestsWorks(self):
    client_id = db_test_utils.InitializeClient(self.db)

    flow_ids = []
    for _ in range(5):
      flow_id = db_test_utils.InitializeFlow(self.db, client_id)
      flow_ids.append(flow_id)
    flow_ids.sort()

    now = rdfvalue.RDFDatetime.Now()
    delivery_time = now + rdfvalue.Duration.From(10, rdfvalue.MINUTES)
    requests = []
    for flow_id in flow_ids:
      requests.append(
          flows_pb2.FlowProcessingRequest(
              client_id=client_id,
              flow_id=flow_id,
              delivery_time=int(delivery_time),
          )
      )

    self.db.WriteFlowProcessingRequests(requests)

    # We stored 5 FlowProcessingRequests, read them back and check they are all
    # there.
    stored_requests = self.db.ReadFlowProcessingRequests()
    stored_requests.sort(key=lambda r: r.flow_id)
    self.assertLen(stored_requests, 5)
    self.assertCountEqual([r.flow_id for r in stored_requests], flow_ids)

    # Now we ack requests 1 and 2. There should be three remaining in the db.
    self.db.AckFlowProcessingRequests(stored_requests[1:3])
    stored_requests = self.db.ReadFlowProcessingRequests()
    self.assertLen(stored_requests, 3)
    self.assertCountEqual(
        [r.flow_id for r in stored_requests],
        [flow_ids[0], flow_ids[3], flow_ids[4]],
    )

    # Make sure DeleteAllFlowProcessingRequests removes all requests.
    self.db.DeleteAllFlowProcessingRequests()
    self.assertEmpty(self.db.ReadFlowProcessingRequests())

    self.db.UnregisterFlowProcessingHandler()

  def _SampleResults(
      self, client_id: str, flow_id: str, hunt_id: Optional[str] = None
  ) -> Sequence[flows_pb2.FlowResult]:
    sample_results = []
    for i in range(10):
      r = flows_pb2.FlowResult(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_id,
          tag="tag_%d" % i,
      )
      r.payload.Pack(
          jobs_pb2.ClientSummary(
              client_id=client_id,
              system_manufacturer="manufacturer_%d" % i,
              install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      sample_results.append(r)

    return sample_results

  def _WriteFlowResults(self, sample_results=None, multiple_timestamps=False):

    if multiple_timestamps:
      for r in sample_results:
        self.db.WriteFlowResults([r])
    else:
      # Use random.shuffle to make sure we don't care about the order of
      # results here, as they all have the same timestamp.
      random.shuffle(sample_results)
      self.db.WriteFlowResults(sample_results)

    return sample_results

  def testWritesAndReadsSingleFlowResultOfSingleType(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_result = flows_pb2.FlowResult(client_id=client_id, flow_id=flow_id)
    sample_result.payload.Pack(jobs_pb2.ClientSummary(client_id=client_id))

    with test_lib.FakeTime(42):
      self.db.WriteFlowResults([sample_result])

    results = self.db.ReadFlowResults(client_id, flow_id, 0, 100)
    self.assertLen(results, 1)
    self.assertEqual(results[0].payload, sample_result.payload)
    self.assertEqual(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(results[0].timestamp),
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42),
    )

  def testWritesAndReadsRDFStringFlowResult(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    result = flows_pb2.FlowResult(client_id=client_id, flow_id=flow_id)
    result.payload.Pack(wrappers_pb2.StringValue(value="foobar"))
    self.db.WriteFlowResults([result])

    results = self.db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    r_payload = wrappers_pb2.StringValue()
    results[0].payload.Unpack(r_payload)
    self.assertEqual(r_payload, wrappers_pb2.StringValue(value="foobar"))

  def testWritesAndReadsRDFBytesFlowResult(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    result = flows_pb2.FlowResult(client_id=client_id, flow_id=flow_id)
    result.payload.Pack(wrappers_pb2.BytesValue(value=b"foobar"))
    self.db.WriteFlowResults([result])

    results = self.db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    r_payload = wrappers_pb2.BytesValue()
    results[0].payload.Unpack(r_payload)
    self.assertEqual(r_payload, wrappers_pb2.BytesValue(value=b"foobar"))

  def testWritesAndReadsRDFIntegerFlowResult(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    result = flows_pb2.FlowResult(client_id=client_id, flow_id=flow_id)
    result.payload.Pack(wrappers_pb2.Int64Value(value=42))
    self.db.WriteFlowResults([result])

    results = self.db.ReadFlowResults(client_id, flow_id, offset=0, count=1024)
    self.assertLen(results, 1)

    r_payload = wrappers_pb2.Int64Value()
    results[0].payload.Unpack(r_payload)
    self.assertEqual(r_payload, wrappers_pb2.Int64Value(value=42))

  def testReadResultsRestoresAllFlowResultsFields(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_result = flows_pb2.FlowResult(
        client_id=client_id, flow_id=flow_id, hunt_id="ABC123"
    )
    sample_result.payload.Pack(jobs_pb2.ClientSummary(client_id=client_id))

    with test_lib.FakeTime(42):
      self.db.WriteFlowResults([sample_result])

    results = self.db.ReadFlowResults(client_id, flow_id, 0, 100)
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id)
    self.assertEqual(results[0].flow_id, flow_id)
    self.assertEndsWith(results[0].hunt_id, "ABC123")  # Ignore leading 0s.
    self.assertEqual(results[0].payload, sample_result.payload)
    self.assertEqual(
        rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(results[0].timestamp),
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42),
    )

  def testWritesAndReadsMultipleFlowResultsOfSingleType(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id)
    )

    results = self.db.ReadFlowResults(client_id, flow_id, 0, 100)
    self.assertLen(results, len(sample_results))

    # All results were written with the same timestamp (as they were written
    # via a single WriteFlowResults call), so no assumptions about
    # the order are made.
    self.assertCountEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results],
    )

  def testWritesAndReadsMultipleFlowResultsWithDifferentTimestamps(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True
    )

    results = self.db.ReadFlowResults(client_id, flow_id, 0, 100)
    self.assertLen(results, len(sample_results))

    # Returned results have to be sorted by the timestamp in the ascending
    # order.
    self.assertEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results],
    )

  def testWritesAndReadsMultipleFlowResultsOfMultipleTypes(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_results = []
    for i in range(10):
      r = flows_pb2.FlowResult(client_id=client_id, flow_id=flow_id)
      r.payload.Pack(
          jobs_pb2.ClientSummary(
              client_id=client_id,
              install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      sample_results.append(r)

      r = flows_pb2.FlowResult(client_id=client_id, flow_id=flow_id)
      r.payload.Pack(
          jobs_pb2.ClientCrash(
              client_id=client_id,
              timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      sample_results.append(r)

      r = flows_pb2.FlowResult(client_id=client_id, flow_id=flow_id)
      r.payload.Pack(jobs_pb2.ClientInformation(client_version=i))
      sample_results.append(r)

    self._WriteFlowResults(sample_results)

    results = self.db.ReadFlowResults(client_id, flow_id, 0, 100)
    self.assertLen(results, len(sample_results))

    self.assertCountEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results],
    )

  def testReadFlowResultsCorrectlyAppliesOffsetAndCountFilters(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True
    )

    for l in range(1, 11):
      for i in range(10):
        results = self.db.ReadFlowResults(client_id, flow_id, i, l)
        expected = sample_results[i : i + l]

        result_payloads = [x.payload for x in results]
        expected_payloads = [x.payload for x in expected]
        self.assertEqual(
            result_payloads,
            expected_payloads,
            "Results differ from expected (from %d, size %d): %s vs %s"
            % (i, l, result_payloads, expected_payloads),
        )

  def testReadFlowResultsCorrectlyAppliesWithTagFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True
    )

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_tag="blah"
    )
    self.assertFalse(results)

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_tag="tag"
    )
    self.assertFalse(results)

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_tag="tag_1"
    )
    self.assertEqual([i.payload for i in results], [sample_results[1].payload])

  def testReadFlowResultsCorrectlyAppliesWithTypeFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_results_summary = []
    sample_results_crash = []
    for i in range(10):
      r = flows_pb2.FlowResult(client_id=client_id, flow_id=flow_id)
      r.payload.Pack(
          jobs_pb2.ClientSummary(
              client_id=client_id,
              install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      sample_results_summary.append(r)

      r = flows_pb2.FlowResult(client_id=client_id, flow_id=flow_id)
      r.payload.Pack(
          jobs_pb2.ClientCrash(
              client_id=client_id,
              timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      sample_results_crash.append(r)

    self.db.WriteFlowResults(sample_results_summary + sample_results_crash)

    results = self.db.ReadFlowResults(
        client_id,
        flow_id,
        0,
        100,
        with_type=rdf_client.ClientInformation.__name__,
    )
    self.assertFalse(results)

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_type=rdf_client.ClientSummary.__name__
    )
    self.assertCountEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results_summary],
    )

  def testReadFlowResultsCorrectlyAppliesWithProtoTypeUrlFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_results_summary = []
    sample_results_crash = []
    for i in range(10):
      r = flows_pb2.FlowResult(client_id=client_id, flow_id=flow_id)
      r.payload.Pack(
          jobs_pb2.ClientSummary(
              client_id=client_id,
              install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      sample_results_summary.append(r)

      r = flows_pb2.FlowResult(client_id=client_id, flow_id=flow_id)
      r.payload.Pack(
          jobs_pb2.ClientCrash(
              client_id=client_id,
              timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      sample_results_crash.append(r)

    self.db.WriteFlowResults(sample_results_summary + sample_results_crash)

    any_proto = any_pb2.Any()
    any_proto.Pack(jobs_pb2.ClientInformation())
    client_information_type_url = any_proto.type_url
    results = self.db.ReadFlowResults(
        client_id,
        flow_id,
        0,
        100,
        with_proto_type_url=client_information_type_url,
    )
    self.assertEmpty(results)

    any_proto.Pack(jobs_pb2.ClientSummary())
    client_summary_type_url = any_proto.type_url
    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_proto_type_url=client_summary_type_url
    )
    self.assertCountEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results_summary],
    )

  def testReadFlowResultsCorrectlyAppliesWithTypeAndProtoTypeUrlFilters(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    any_proto = any_pb2.Any()
    any_proto.Pack(jobs_pb2.ClientSummary())
    client_summary_type_url = any_proto.type_url

    with self.assertRaises(ValueError):
      self.db.ReadFlowResults(
          client_id,
          flow_id,
          0,
          100,
          with_type=rdf_client.ClientSummary.__name__,
          with_proto_type_url=client_summary_type_url,
      )

  def testReadFlowResultsCorrectlyAppliesWithSubstringFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True
    )

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_substring="blah"
    )
    self.assertFalse(results)

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_substring="manufacturer"
    )
    self.assertEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results],
    )

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_substring="manufacturer_1"
    )
    self.assertEqual([i.payload for i in results], [sample_results[1].payload])

  def testReadFlowResultsCorrectlyAppliesVariousCombinationsOfFilters(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True
    )

    tags = {None: list(sample_results), "tag_1": [sample_results[1]]}

    substrings = {
        None: list(sample_results),
        "manufacturer": list(sample_results),
        "manufacturer_1": [sample_results[1]],
    }

    types = {
        None: list(sample_results),
        jobs_pb2.ClientSummary.__name__: list(sample_results),
    }

    for tag_value, tag_expected in tags.items():
      for substring_value, substring_expected in substrings.items():
        for type_value, type_expected in types.items():
          expected = [
              r
              for r in tag_expected
              if r in substring_expected and r in type_expected
          ]
          results = self.db.ReadFlowResults(
              client_id,
              flow_id,
              0,
              100,
              with_tag=tag_value,
              with_type=type_value,
              with_substring=substring_value,
          )

          self.assertCountEqual(
              [i.payload for i in expected],
              [i.payload for i in results],
              "Result items do not match for "
              "(tag=%s, type=%s, substring=%s): %s vs %s"
              % (tag_value, type_value, substring_value, expected, results),
          )

  def testCountFlowResultsReturnsCorrectResultsCount(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True
    )

    num_results = self.db.CountFlowResults(client_id, flow_id)
    self.assertEqual(num_results, len(sample_results))

  def testCountFlowResultsCorrectlyAppliesWithTagFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True
    )

    num_results = self.db.CountFlowResults(client_id, flow_id, with_tag="blah")
    self.assertEqual(num_results, 0)

    num_results = self.db.CountFlowResults(client_id, flow_id, with_tag="tag_1")
    self.assertEqual(num_results, 1)

  def testCountFlowResultsCorrectlyAppliesWithTypeFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    client_summary_result = flows_pb2.FlowResult(
        client_id=client_id, flow_id=flow_id
    )
    client_summary_result.payload.Pack(
        jobs_pb2.ClientSummary(client_id=client_id)
    )

    client_crash_result = flows_pb2.FlowResult(
        client_id=client_id, flow_id=flow_id
    )
    client_crash_result.payload.Pack(jobs_pb2.ClientCrash(client_id=client_id))

    self._WriteFlowResults(sample_results=[client_summary_result] * 10)
    self._WriteFlowResults(sample_results=[client_crash_result] * 10)

    num_results = self.db.CountFlowResults(
        client_id, flow_id, with_type=rdf_client.ClientInformation.__name__
    )
    self.assertEqual(num_results, 0)

    num_results = self.db.CountFlowResults(
        client_id, flow_id, with_type=rdf_client.ClientSummary.__name__
    )
    self.assertEqual(num_results, 10)

    num_results = self.db.CountFlowResults(
        client_id, flow_id, with_type=rdf_client.ClientCrash.__name__
    )
    self.assertEqual(num_results, 10)

  def testCountFlowResultsCorrectlyAppliesWithTagAndWithTypeFilters(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True
    )

    num_results = self.db.CountFlowResults(
        client_id,
        flow_id,
        with_tag="tag_1",
        with_type=jobs_pb2.ClientSummary.__name__,
    )
    self.assertEqual(num_results, 1)

  def testCountFlowResultsByTypeReturnsCorrectNumbers(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    client_summary_result = flows_pb2.FlowResult(
        client_id=client_id, flow_id=flow_id
    )
    client_summary_result.payload.Pack(
        jobs_pb2.ClientSummary(client_id=client_id)
    )

    client_crash_result = flows_pb2.FlowResult(
        client_id=client_id, flow_id=flow_id
    )
    client_crash_result.payload.Pack(jobs_pb2.ClientCrash(client_id=client_id))

    sample_results = self._WriteFlowResults(
        sample_results=[client_summary_result] * 3
    )
    sample_results.extend(
        self._WriteFlowResults(sample_results=[client_crash_result] * 5)
    )

    counts_by_type = self.db.CountFlowResultsByType(client_id, flow_id)
    self.assertEqual(
        counts_by_type,
        {
            "ClientSummary": 3,
            "ClientCrash": 5,
        },
    )

  def testCountFlowResultsByProtoTypeUrlReturnsCorrectNumbers(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    client_summary_result = flows_pb2.FlowResult(
        client_id=client_id, flow_id=flow_id
    )
    client_summary_result.payload.Pack(
        jobs_pb2.ClientSummary(client_id=client_id)
    )

    client_crash_result = flows_pb2.FlowResult(
        client_id=client_id, flow_id=flow_id
    )
    client_crash_result.payload.Pack(jobs_pb2.ClientCrash(client_id=client_id))

    sample_results = self._WriteFlowResults(
        sample_results=[client_summary_result] * 3
    )
    sample_results.extend(
        self._WriteFlowResults(sample_results=[client_crash_result] * 5)
    )

    counts_by_type = self.db.CountFlowResultsByProtoTypeUrl(client_id, flow_id)
    any_proto = any_pb2.Any()
    any_proto.Pack(jobs_pb2.ClientSummary())
    client_summary_type_url = any_proto.type_url
    any_proto.Pack(jobs_pb2.ClientCrash())

    client_crash_type_url = any_proto.type_url
    self.assertEqual(
        counts_by_type,
        {
            client_summary_type_url: 3,
            client_crash_type_url: 5,
        },
    )

  def _CreateErrors(self, client_id, flow_id, hunt_id=None):
    sample_errors = []
    for i in range(10):
      e = flows_pb2.FlowError(
          client_id=client_id,
          flow_id=flow_id,
          hunt_id=hunt_id,
          tag="tag_%d" % i,
      )
      e.payload.Pack(
          jobs_pb2.ClientSummary(
              client_id=client_id,
              system_manufacturer="manufacturer_%d" % i,
              install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      sample_errors.append(e)

    return sample_errors

  def _WriteFlowErrors(self, sample_errors=None, multiple_timestamps=False):

    if multiple_timestamps:
      for r in sample_errors:
        self.db.WriteFlowErrors([r])
    else:
      # Use random.shuffle to make sure we don't care about the order of
      # errors here, as they all have the same timestamp.
      random.shuffle(sample_errors)
      self.db.WriteFlowErrors(sample_errors)

    return sample_errors

  def testWritesAndReadsSingleFlowErrorOfSingleType(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_error = flows_pb2.FlowError(client_id=client_id, flow_id=flow_id)
    sample_error.payload.Pack(jobs_pb2.ClientSummary(client_id=client_id))

    with test_lib.FakeTime(42):
      self.db.WriteFlowErrors([sample_error])

    errors = self.db.ReadFlowErrors(client_id, flow_id, 0, 100)
    self.assertLen(errors, 1)
    self.assertEqual(errors[0].payload, sample_error.payload)
    self.assertEqual(
        errors[0].timestamp,
        rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
            42
        ).AsMicrosecondsSinceEpoch(),
    )

  def testWritesAndReadsMultipleFlowErrorsOfSingleType(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_errors = self._WriteFlowErrors(
        self._CreateErrors(client_id, flow_id)
    )

    errors = self.db.ReadFlowErrors(client_id, flow_id, 0, 100)
    self.assertLen(errors, len(sample_errors))

    # All errors were written with the same timestamp (as they were written
    # via a single WriteFlowErrors call), so no assumptions about
    # the order are made.
    self.assertCountEqual(
        [i.payload for i in errors],
        [i.payload for i in sample_errors],
    )

  def testWritesAndReadsMultipleFlowErrorsWithDifferentTimestamps(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_errors = self._WriteFlowErrors(
        self._CreateErrors(client_id, flow_id), multiple_timestamps=True
    )

    errors = self.db.ReadFlowErrors(client_id, flow_id, 0, 100)
    self.assertLen(errors, len(sample_errors))

    # Returned errors have to be sorted by the timestamp in the ascending
    # order.
    self.assertEqual(
        [i.payload for i in errors],
        [i.payload for i in sample_errors],
    )

  def testWritesAndReadsMultipleFlowErrorsOfMultipleTypes(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    def SampleClientSummaryError(i):
      error = flows_pb2.FlowError(client_id=client_id, flow_id=flow_id)
      error.payload.Pack(
          jobs_pb2.ClientSummary(
              client_id=client_id,
              install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      return error

    sample_errors = self._WriteFlowErrors(
        sample_errors=[SampleClientSummaryError(i) for i in range(10)]
    )

    def SampleClientCrashError(i):
      error = flows_pb2.FlowError(client_id=client_id, flow_id=flow_id)
      error.payload.Pack(
          jobs_pb2.ClientCrash(
              client_id=client_id,
              timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      return error

    sample_errors.extend(
        self._WriteFlowErrors(
            sample_errors=[SampleClientCrashError(i) for i in range(10)]
        )
    )

    def SampleClientInformationError(i):
      error = flows_pb2.FlowError(client_id=client_id, flow_id=flow_id)
      error.payload.Pack(jobs_pb2.ClientInformation(client_version=i))
      return error

    sample_errors.extend(
        self._WriteFlowErrors(
            sample_errors=[SampleClientInformationError(i) for i in range(10)]
        )
    )

    errors = self.db.ReadFlowErrors(client_id, flow_id, 0, 100)
    self.assertLen(errors, len(sample_errors))

    self.assertCountEqual(
        [i.payload for i in errors],
        [i.payload for i in sample_errors],
    )

  def testReadFlowErrorsCorrectlyAppliesOffsetAndCountFilters(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_errors = self._WriteFlowErrors(
        self._CreateErrors(client_id, flow_id), multiple_timestamps=True
    )

    for l in range(1, 11):
      for i in range(10):
        errors = self.db.ReadFlowErrors(client_id, flow_id, i, l)
        expected = sample_errors[i : i + l]

        error_payloads = [x.payload for x in errors]
        expected_payloads = [x.payload for x in expected]
        self.assertEqual(
            error_payloads,
            expected_payloads,
            "Errors differ from expected (from %d, size %d): %s vs %s"
            % (i, l, error_payloads, expected_payloads),
        )

  def testReadFlowErrorsCorrectlyAppliesWithTagFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_errors = self._WriteFlowErrors(
        self._CreateErrors(client_id, flow_id), multiple_timestamps=True
    )

    errors = self.db.ReadFlowErrors(client_id, flow_id, 0, 100, with_tag="blah")
    self.assertFalse(errors)

    errors = self.db.ReadFlowErrors(client_id, flow_id, 0, 100, with_tag="tag")
    self.assertFalse(errors)

    errors = self.db.ReadFlowErrors(
        client_id, flow_id, 0, 100, with_tag="tag_1"
    )
    self.assertEqual([i.payload for i in errors], [sample_errors[1].payload])

  def testReadFlowErrorsCorrectlyAppliesWithTypeFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    def SampleClientSummaryError(i):
      error = flows_pb2.FlowError(client_id=client_id, flow_id=flow_id)
      error.payload.Pack(
          jobs_pb2.ClientSummary(
              client_id=client_id,
              install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      return error

    sample_errors = self._WriteFlowErrors(
        sample_errors=[SampleClientSummaryError(i) for i in range(10)]
    )

    def SampleClientCrashError(i):
      error = flows_pb2.FlowError(client_id=client_id, flow_id=flow_id)
      error.payload.Pack(
          jobs_pb2.ClientCrash(
              client_id=client_id,
              timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
                  10 + i
              ).AsMicrosecondsSinceEpoch(),
          )
      )
      return error

    sample_errors.extend(
        self._WriteFlowErrors(
            sample_errors=[SampleClientCrashError(i) for i in range(10)]
        )
    )

    errors = self.db.ReadFlowErrors(
        client_id,
        flow_id,
        0,
        100,
        with_type=rdf_client.ClientInformation.__name__,
    )
    self.assertFalse(errors)

    errors = self.db.ReadFlowErrors(
        client_id, flow_id, 0, 100, with_type=rdf_client.ClientSummary.__name__
    )
    self.assertCountEqual(
        [i.payload for i in errors],
        [i.payload for i in sample_errors[:10]],
    )

  def testReadFlowErrorsCorrectlyAppliesVariousCombinationsOfFilters(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_errors = self._WriteFlowErrors(
        self._CreateErrors(client_id, flow_id), multiple_timestamps=True
    )

    tags = {None: list(sample_errors), "tag_1": [sample_errors[1]]}

    types = {
        None: list(sample_errors),
        rdf_client.ClientSummary.__name__: list(sample_errors),
    }

    for tag_value, tag_expected in tags.items():
      for type_value, type_expected in types.items():
        expected = [r for r in tag_expected if r in type_expected]
        errors = self.db.ReadFlowErrors(
            client_id, flow_id, 0, 100, with_tag=tag_value, with_type=type_value
        )

        self.assertCountEqual(
            [i.payload for i in expected],
            [i.payload for i in errors],
            "Error items do not match for (tag=%s, type=%s): %s vs %s"
            % (tag_value, type_value, expected, errors),
        )

  def testCountFlowErrorsReturnsCorrectErrorsCount(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    sample_errors = self._WriteFlowErrors(
        self._CreateErrors(client_id, flow_id), multiple_timestamps=True
    )

    num_errors = self.db.CountFlowErrors(client_id, flow_id)
    self.assertEqual(num_errors, len(sample_errors))

  def testCountFlowErrorsCorrectlyAppliesWithTagFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    self._WriteFlowErrors(
        self._CreateErrors(client_id, flow_id), multiple_timestamps=True
    )

    num_errors = self.db.CountFlowErrors(client_id, flow_id, with_tag="blah")
    self.assertEqual(num_errors, 0)

    num_errors = self.db.CountFlowErrors(client_id, flow_id, with_tag="tag_1")
    self.assertEqual(num_errors, 1)

  def testCountFlowErrorsCorrectlyAppliesWithTypeFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    client_summary_error = flows_pb2.FlowError(
        client_id=client_id, flow_id=flow_id
    )
    client_summary_error.payload.Pack(
        jobs_pb2.ClientSummary(client_id=client_id)
    )

    client_crash_error = flows_pb2.FlowError(
        client_id=client_id, flow_id=flow_id
    )
    client_crash_error.payload.Pack(jobs_pb2.ClientCrash(client_id=client_id))

    self._WriteFlowErrors(sample_errors=[client_summary_error] * 10)
    self._WriteFlowErrors(sample_errors=[client_crash_error] * 10)

    num_errors = self.db.CountFlowErrors(
        client_id, flow_id, with_type=rdf_client.ClientInformation.__name__
    )
    self.assertEqual(num_errors, 0)

    num_errors = self.db.CountFlowErrors(
        client_id, flow_id, with_type=rdf_client.ClientSummary.__name__
    )
    self.assertEqual(num_errors, 10)

    num_errors = self.db.CountFlowErrors(
        client_id, flow_id, with_type=rdf_client.ClientCrash.__name__
    )
    self.assertEqual(num_errors, 10)

  def testCountFlowErrorsCorrectlyAppliesWithTagAndWithTypeFilters(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    self._WriteFlowErrors(
        self._CreateErrors(client_id, flow_id), multiple_timestamps=True
    )

    num_errors = self.db.CountFlowErrors(
        client_id,
        flow_id,
        with_tag="tag_1",
        with_type=rdf_client.ClientSummary.__name__,
    )
    self.assertEqual(num_errors, 1)

  def testCountFlowErrorsByTypeReturnsCorrectNumbers(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    client_summary_error = flows_pb2.FlowError(
        client_id=client_id, flow_id=flow_id
    )
    client_summary_error.payload.Pack(
        jobs_pb2.ClientSummary(client_id=client_id)
    )

    client_crash_error = flows_pb2.FlowError(
        client_id=client_id, flow_id=flow_id
    )
    client_crash_error.payload.Pack(jobs_pb2.ClientCrash(client_id=client_id))

    sample_errors = self._WriteFlowErrors(
        sample_errors=[client_summary_error] * 3
    )
    sample_errors.extend(
        self._WriteFlowErrors(sample_errors=[client_crash_error] * 5)
    )

    counts_by_type = self.db.CountFlowErrorsByType(client_id, flow_id)
    self.assertEqual(
        counts_by_type,
        {
            "ClientSummary": 3,
            "ClientCrash": 5,
        },
    )

  def testWritesAndReadsSingleFlowLogEntry(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    message = "blah: ٩(͡๏̯͡๏)۶"

    self.db.WriteFlowLogEntry(
        flows_pb2.FlowLogEntry(
            client_id=client_id, flow_id=flow_id, message=message
        )
    )

    entries = self.db.ReadFlowLogEntries(client_id, flow_id, 0, 100)
    self.assertLen(entries, 1)
    self.assertEqual(entries[0].message, message)

  def _WriteFlowLogEntries(self, client_id, flow_id):
    messages = ["blah_%d" % i for i in range(10)]
    for message in messages:
      self.db.WriteFlowLogEntry(
          flows_pb2.FlowLogEntry(
              client_id=client_id, flow_id=flow_id, message=message
          )
      )

    return messages

  def testWritesAndReadsMultipleFlowLogEntries(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    messages = self._WriteFlowLogEntries(client_id, flow_id)

    entries = self.db.ReadFlowLogEntries(client_id, flow_id, 0, 100)
    self.assertEqual([e.message for e in entries], messages)

  def testReadFlowLogEntriesCorrectlyAppliesOffsetAndCountFilters(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    messages = self._WriteFlowLogEntries(client_id, flow_id)

    for i in range(10):
      for size in range(1, 10):
        entries = self.db.ReadFlowLogEntries(client_id, flow_id, i, size)
        self.assertEqual([e.message for e in entries], messages[i : i + size])

  def testReadFlowLogEntriesCorrectlyAppliesWithSubstringFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    messages = self._WriteFlowLogEntries(client_id, flow_id)

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 0, 100, with_substring="foobar"
    )
    self.assertFalse(entries)

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 0, 100, with_substring="blah"
    )
    self.assertEqual([e.message for e in entries], messages)

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 0, 100, with_substring="blah_1"
    )
    self.assertEqual([e.message for e in entries], [messages[1]])

  def testReadFlowLogEntriesCorrectlyAppliesVariousCombinationsOfFilters(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    messages = self._WriteFlowLogEntries(client_id, flow_id)

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 0, 100, with_substring="foobar"
    )
    self.assertFalse(entries)

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 1, 2, with_substring="blah"
    )
    self.assertEqual([e.message for e in entries], [messages[1], messages[2]])

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 0, 1, with_substring="blah_1"
    )
    self.assertEqual([e.message for e in entries], [messages[1]])

  def testCountFlowLogEntriesReturnsCorrectFlowLogEntriesCount(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    messages = self._WriteFlowLogEntries(client_id, flow_id)

    num_entries = self.db.CountFlowLogEntries(client_id, flow_id)
    self.assertEqual(num_entries, len(messages))

  def testFlowLogsAndErrorsForUnknownFlowsRaise(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = flow.RandomFlowId()

    with self.assertRaises(db.UnknownFlowError) as context:
      self.db.WriteFlowLogEntry(
          flows_pb2.FlowLogEntry(
              client_id=client_id, flow_id=flow_id, message="test"
          )
      )

    self.assertEqual(context.exception.client_id, client_id)
    self.assertEqual(context.exception.flow_id, flow_id)

  def testWriteFlowRRGLogsUnknownClient(self):
    client_id = "C.0123456789ABCDEF"
    flow_id = "ABCDEF00"
    request_id = random.randint(0, 1024)

    with self.assertRaises(db.UnknownFlowError) as context:
      self.db.WriteFlowRRGLogs(
          client_id=client_id,
          flow_id=flow_id,
          request_id=request_id,
          logs={
              1: rrg_pb2.Log(message="lorem ipsum"),
          },
      )

    self.assertEqual(context.exception.client_id, client_id)
    self.assertEqual(context.exception.flow_id, flow_id)

  def testWriteFlowRRGLogsUnknownFlow(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = "ABCDEF00"
    request_id = random.randint(0, 1024)

    with self.assertRaises(db.UnknownFlowError) as context:
      self.db.WriteFlowRRGLogs(
          client_id=client_id,
          flow_id=flow_id,
          request_id=request_id,
          logs={
              1: rrg_pb2.Log(message="lorem ipsum"),
          },
      )

    self.assertEqual(context.exception.client_id, client_id)
    self.assertEqual(context.exception.flow_id, flow_id)

  def testWriteFlowRRGLogsEmpty(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    request_id = random.randint(0, 1024)

    self.db.WriteFlowRRGLogs(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        logs={},
    )

    logs = self.db.ReadFlowRRGLogs(client_id, flow_id, offset=0, count=128)
    self.assertEmpty(logs)

  def testWriteFlowRRGLogsSingle(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    request_id = random.randint(0, 1024)

    self.db.WriteFlowRRGLogs(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        logs={
            1: rrg_pb2.Log(
                level=rrg_pb2.Log.INFO,
                timestamp=timestamp_pb2.Timestamp(seconds=1337),
                message="lorem ipsum",
            ),
        },
    )

    logs = self.db.ReadFlowRRGLogs(client_id, flow_id, offset=0, count=128)
    self.assertLen(logs, 1)
    self.assertEqual(logs[0].level, rrg_pb2.Log.INFO)
    self.assertEqual(logs[0].timestamp.seconds, 1337)
    self.assertEqual(logs[0].message, "lorem ipsum")

  def testWriteFlowRRGLogsMultipleSameFlow(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    request_id = random.randint(0, 1024)

    self.db.WriteFlowRRGLogs(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        logs={
            1: rrg_pb2.Log(message="lorem ipsum"),
            2: rrg_pb2.Log(message="sit dolor amet"),
        },
    )
    self.db.WriteFlowRRGLogs(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        logs={
            3: rrg_pb2.Log(message="consectetur adipiscing elit"),
            4: rrg_pb2.Log(message="sed do eiusmod"),
        },
    )

    logs = self.db.ReadFlowRRGLogs(client_id, flow_id, offset=0, count=1024)
    self.assertLen(logs, 4)
    self.assertEqual(logs[0].message, "lorem ipsum")
    self.assertEqual(logs[1].message, "sit dolor amet")
    self.assertEqual(logs[2].message, "consectetur adipiscing elit")
    self.assertEqual(logs[3].message, "sed do eiusmod")

  def testWriteFlowRRGLogsMultipleDifferentFlows(self):
    client_id_1 = db_test_utils.InitializeClient(self.db)
    client_id_2 = db_test_utils.InitializeClient(self.db)

    flow_id_1_1 = db_test_utils.InitializeFlow(self.db, client_id_1)
    flow_id_1_2 = db_test_utils.InitializeFlow(self.db, client_id_1)
    flow_id_2_1 = db_test_utils.InitializeFlow(self.db, client_id_2)

    self.db.WriteFlowRRGLogs(
        client_id=client_id_1,
        flow_id=flow_id_1_1,
        request_id=random.randint(0, 1024),
        logs={
            1: rrg_pb2.Log(message="lorem ipsum"),
            2: rrg_pb2.Log(message="sit dolor amet"),
        },
    )
    self.db.WriteFlowRRGLogs(
        client_id=client_id_1,
        flow_id=flow_id_1_2,
        request_id=random.randint(0, 1024),
        logs={
            1: rrg_pb2.Log(message="consectetur adipiscing elit"),
        },
    )
    self.db.WriteFlowRRGLogs(
        client_id=client_id_2,
        flow_id=flow_id_2_1,
        request_id=random.randint(0, 1024),
        logs={
            1: rrg_pb2.Log(message="sed do eiusmod"),
        },
    )

    logs_1_1 = self.db.ReadFlowRRGLogs(
        client_id=client_id_1,
        flow_id=flow_id_1_1,
        offset=0,
        count=1024,
    )
    self.assertLen(logs_1_1, 2)
    self.assertEqual(logs_1_1[0].message, "lorem ipsum")
    self.assertEqual(logs_1_1[1].message, "sit dolor amet")

    logs_1_2 = self.db.ReadFlowRRGLogs(
        client_id=client_id_1,
        flow_id=flow_id_1_2,
        offset=0,
        count=1024,
    )
    self.assertLen(logs_1_2, 1)
    self.assertEqual(logs_1_2[0].message, "consectetur adipiscing elit")

    logs_2_1 = self.db.ReadFlowRRGLogs(
        client_id=client_id_2,
        flow_id=flow_id_2_1,
        offset=0,
        count=1024,
    )
    self.assertLen(logs_2_1, 1)
    self.assertEqual(logs_2_1[0].message, "sed do eiusmod")

  def testReadFlowRRGLogsOffset(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    request_id = random.randint(0, 1024)

    self.db.WriteFlowRRGLogs(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        logs={
            1: rrg_pb2.Log(message="lorem ipsum"),
            2: rrg_pb2.Log(message="sit dolor amet"),
            3: rrg_pb2.Log(message="consectetur adipiscing elit"),
            4: rrg_pb2.Log(message="sed do eiusmod"),
        },
    )

    logs = self.db.ReadFlowRRGLogs(client_id, flow_id, offset=2, count=1024)
    self.assertLen(logs, 2)
    self.assertEqual(logs[0].message, "consectetur adipiscing elit")
    self.assertEqual(logs[1].message, "sed do eiusmod")

  def testReadFlowRRGLogsCount(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    request_id = random.randint(0, 1024)

    self.db.WriteFlowRRGLogs(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        logs={
            1: rrg_pb2.Log(message="lorem ipsum"),
            2: rrg_pb2.Log(message="sit dolor amet"),
            3: rrg_pb2.Log(message="consectetur adipiscing elit"),
            4: rrg_pb2.Log(message="sed do eiusmod"),
        },
    )

    logs = self.db.ReadFlowRRGLogs(client_id, flow_id, offset=0, count=2)
    self.assertLen(logs, 2)
    self.assertEqual(logs[0].message, "lorem ipsum")
    self.assertEqual(logs[1].message, "sit dolor amet")

  def testReadFlowRRGLogsOffsetAndCount(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    request_id = random.randint(0, 1024)

    self.db.WriteFlowRRGLogs(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        logs={
            1: rrg_pb2.Log(message="lorem ipsum"),
            2: rrg_pb2.Log(message="sit dolor amet"),
            3: rrg_pb2.Log(message="consectetur adipiscing elit"),
            4: rrg_pb2.Log(message="sed do eiusmod"),
            5: rrg_pb2.Log(message="tempor incididunt ut"),
        },
    )

    logs = self.db.ReadFlowRRGLogs(client_id, flow_id, offset=1, count=3)
    self.assertLen(logs, 3)
    self.assertEqual(logs[0].message, "sit dolor amet")
    self.assertEqual(logs[1].message, "consectetur adipiscing elit")
    self.assertEqual(logs[2].message, "sed do eiusmod")

  def _WriteFlowOutputPluginLogEntries(
      self, client_id, flow_id, output_plugin_id
  ):
    entries = []
    for i in range(10):
      message = "blah_🚀_%d" % i
      enum = flows_pb2.FlowOutputPluginLogEntry.LogEntryType
      if i % 3 == 0:
        log_entry_type = enum.ERROR
      else:
        log_entry_type = enum.LOG

      entry = flows_pb2.FlowOutputPluginLogEntry(
          client_id=client_id,
          flow_id=flow_id,
          output_plugin_id=output_plugin_id,
          message=message,
          log_entry_type=log_entry_type,
      )
      entries.append(entry)

      self.db.WriteFlowOutputPluginLogEntry(entry)

    return entries

  def testWriteFlowOutputPluginLogEntryRaisesOnUnknownFlow(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = "ABCDEF48"

    entry = flows_pb2.FlowOutputPluginLogEntry()
    entry.client_id = client_id
    entry.flow_id = flow_id
    entry.output_plugin_id = "F00"
    entry.message = "Lorem ipsum."

    with self.assertRaises(db.AtLeastOneUnknownFlowError) as context:
      self.db.WriteFlowOutputPluginLogEntry(entry)

    self.assertEqual(context.exception.flow_keys, [(client_id, flow_id)])

  def testFlowOutputPluginLogEntriesCanBeWrittenAndThenRead(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    output_plugin_id = "1"

    written_entries = self._WriteFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id
    )
    read_entries = self.db.ReadFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id, 0, 100
    )

    self.assertLen(written_entries, len(read_entries))
    self.assertEqual(
        [e.message for e in written_entries], [e.message for e in read_entries]
    )
    got_ids = set(e.output_plugin_id for e in read_entries)
    self.assertEqual(got_ids, {"1"})

  def testReadAllFlowOutputPluginLogEntries(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    self._WriteFlowOutputPluginLogEntries(client_id, flow_id, "1")
    self._WriteFlowOutputPluginLogEntries(client_id, flow_id, "2")

    read_entries = self.db.ReadAllFlowOutputPluginLogEntries(
        client_id, flow_id, 0, 100
    )
    self.assertLen(read_entries, 20)
    got_ids = set(e.output_plugin_id for e in read_entries)
    self.assertEqual(got_ids, {"1", "2"})

  def testReadAllFlowOutputPluginLogEntriesWithTypeFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    self._WriteFlowOutputPluginLogEntries(client_id, flow_id, "1")
    self._WriteFlowOutputPluginLogEntries(client_id, flow_id, "2")

    log_entries = self.db.ReadAllFlowOutputPluginLogEntries(
        client_id,
        flow_id,
        0,
        100,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
    )
    self.assertLen(log_entries, 12)
    got_ids = set(e.output_plugin_id for e in log_entries)
    self.assertEqual(got_ids, {"1", "2"})

    error_entries = self.db.ReadAllFlowOutputPluginLogEntries(
        client_id,
        flow_id,
        0,
        100,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
    )
    self.assertLen(error_entries, 8)
    got_ids = set(e.output_plugin_id for e in error_entries)
    self.assertEqual(got_ids, {"1", "2"})

  def testFlowOutputPluginLogEntryWith1MbMessageCanBeWrittenAndThenRead(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    output_plugin_id = "1"

    entry = flows_pb2.FlowOutputPluginLogEntry(
        client_id=client_id,
        flow_id=flow_id,
        output_plugin_id=output_plugin_id,
        message="x" * 1024 * 1024,
        log_entry_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
    )

    self.db.WriteFlowOutputPluginLogEntry(entry)
    read_entries = self.db.ReadFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id, 0, 100
    )

    self.assertLen(read_entries, 1)
    self.assertEqual(read_entries[0].message, entry.message)
    self.assertEqual(read_entries[0].output_plugin_id, "1")

  def testWriteMultipleFlowOutputPluginLogEntries(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    output_plugin_id = "1"

    entries = []
    for i in range(10):
      message = f"blah_🚀_{i}"
      enum = flows_pb2.FlowOutputPluginLogEntry.LogEntryType
      if i % 3 == 0:
        log_entry_type = enum.ERROR
      else:
        log_entry_type = enum.LOG

      entry = flows_pb2.FlowOutputPluginLogEntry(
          client_id=client_id,
          flow_id=flow_id,
          output_plugin_id=output_plugin_id,
          message=message,
          log_entry_type=log_entry_type,
      )
      entries.append(entry)

    self.db.WriteMultipleFlowOutputPluginLogEntries(entries)

    read_entries = self.db.ReadFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id, 0, 100
    )
    self.assertLen(read_entries, 10)
    self.assertEqual(
        [e.message for e in entries], [e.message for e in read_entries]
    )
    got_ids = set(e.output_plugin_id for e in read_entries)
    self.assertEqual(got_ids, {"1"})

  def testFlowOutputPluginLogEntriesCanBeReadWithTypeFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    output_plugin_id = "1"

    self._WriteFlowOutputPluginLogEntries(client_id, flow_id, output_plugin_id)

    read_entries = self.db.ReadFlowOutputPluginLogEntries(
        client_id,
        flow_id,
        output_plugin_id,
        0,
        100,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
    )
    self.assertLen(read_entries, 4)
    got_ids = set(e.output_plugin_id for e in read_entries)
    self.assertEqual(got_ids, {"1"})

    read_entries = self.db.ReadFlowOutputPluginLogEntries(
        client_id,
        flow_id,
        output_plugin_id,
        0,
        100,
        with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
    )
    self.assertLen(read_entries, 6)
    got_ids = set(e.output_plugin_id for e in read_entries)
    self.assertEqual(got_ids, {"1"})

  def testReadFlowOutputPluginLogEntriesCorrectlyAppliesOffsetCounter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    output_plugin_id = "1"

    entries = self._WriteFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id
    )

    for l in range(1, 11):
      for i in range(10):
        results = self.db.ReadFlowOutputPluginLogEntries(
            client_id, flow_id, output_plugin_id, i, l
        )
        expected = entries[i : i + l]

        result_messages = [x.message for x in results]
        expected_messages = [x.message for x in expected]
        self.assertEqual(
            result_messages,
            expected_messages,
            "Results differ from expected (from %d, size %d): %s vs %s"
            % (i, l, result_messages, expected_messages),
        )

  def testReadFlowOutputPluginLogEntriesAppliesOffsetCounterWithType(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    output_plugin_id = "1"

    entries = self._WriteFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id
    )

    for l in range(1, 11):
      for i in range(10):
        for with_type in [
            flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
            flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
        ]:
          results = self.db.ReadFlowOutputPluginLogEntries(
              client_id, flow_id, output_plugin_id, i, l, with_type=with_type
          )
          expected = [e for e in entries if e.log_entry_type == with_type][
              i : i + l
          ]

          result_messages = [x.message for x in results]
          expected_messages = [x.message for x in expected]
          self.assertEqual(
              result_messages,
              expected_messages,
              "Results differ from expected (from %d, size %d): %s vs %s"
              % (i, l, result_messages, expected_messages),
          )

  def testFlowOutputPluginLogEntriesCanBeCountedPerPlugin(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    output_plugin_id_1 = "1"
    self._WriteFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id_1
    )

    output_plugin_id_2 = "2"
    self._WriteFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id_2
    )

    self.assertEqual(
        self.db.CountFlowOutputPluginLogEntries(
            client_id, flow_id, output_plugin_id_1
        ),
        10,
    )
    self.assertEqual(
        self.db.CountFlowOutputPluginLogEntries(
            client_id, flow_id, output_plugin_id_2
        ),
        10,
    )

  def testCountFlowOutputPluginLogEntriesRespectsWithTypeFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    output_plugin_id = "1"
    self._WriteFlowOutputPluginLogEntries(client_id, flow_id, output_plugin_id)

    self.assertEqual(
        self.db.CountFlowOutputPluginLogEntries(
            client_id,
            flow_id,
            output_plugin_id,
            with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
        ),
        6,
    )
    self.assertEqual(
        self.db.CountFlowOutputPluginLogEntries(
            client_id,
            flow_id,
            output_plugin_id,
            with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
        ),
        4,
    )

  def testCountAllFlowOutputPluginLogEntries(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)
    output_plugin_id_1 = "1"
    self._WriteFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id_1
    )

    output_plugin_id_2 = "2"
    self._WriteFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id_2
    )

    self.assertEqual(
        self.db.CountAllFlowOutputPluginLogEntries(client_id, flow_id),
        20,
    )

  def testCountAllFlowOutputPluginLogEntriesRespectsWithTypeFilter(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    output_plugin_id = "1"
    self._WriteFlowOutputPluginLogEntries(client_id, flow_id, output_plugin_id)

    self.assertEqual(
        self.db.CountAllFlowOutputPluginLogEntries(
            client_id,
            flow_id,
            with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
        ),
        6,
    )
    self.assertEqual(
        self.db.CountAllFlowOutputPluginLogEntries(
            client_id,
            flow_id,
            with_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ERROR,
        ),
        4,
    )

  def _SetupScheduledFlow(self, **kwargs):
    flow_args = flows_pb2.CollectFilesByKnownPathArgs()
    flow_args.collection_level = random.randint(0, 3)

    sf = flows_pb2.ScheduledFlow()
    sf.scheduled_flow_id = flow.RandomFlowId()
    sf.flow_name = file.CollectFilesByKnownPath.__name__
    sf.flow_args.Pack(flow_args)
    sf.runner_args.network_bytes_limit = random.randint(0, 10)
    sf.create_time = int(rdfvalue.RDFDatetime.Now())
    sf.MergeFrom(flows_pb2.ScheduledFlow(**kwargs))
    self.db.WriteScheduledFlow(sf)
    return sf

  def testListScheduledFlowsInitiallyEmpty(self):
    client_id = db_test_utils.InitializeClient(self.db)
    username = db_test_utils.InitializeUser(self.db)
    self.assertEmpty(self.db.ListScheduledFlows(client_id, username))

  def testWriteScheduledFlowPersistsAllFields(self):
    client_id = db_test_utils.InitializeClient(self.db)
    username = db_test_utils.InitializeUser(self.db)

    flow_args = flows_pb2.CollectFilesByKnownPathArgs()
    flow_args.paths.append("/baz")

    flow_args_any = any_pb2.Any()
    flow_args_any.Pack(flow_args)

    sf = self._SetupScheduledFlow(
        client_id=client_id,
        creator=username,
        scheduled_flow_id="1234123421342134",
        flow_name=file.CollectFilesByKnownPath.__name__,
        flow_args=flow_args_any,
        runner_args=flows_pb2.FlowRunnerArgs(network_bytes_limit=1024),
        create_time=int(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42)),
        error="foobazzle disintegrated",
    )

    results = self.db.ListScheduledFlows(client_id, username)
    self.assertEqual([sf], results)

    result = results[0]
    self.assertEqual(result.client_id, client_id)
    self.assertEqual(result.creator, username)
    self.assertEqual(result.scheduled_flow_id, "1234123421342134")
    self.assertEqual(result.flow_name, file.CollectFilesByKnownPath.__name__)
    self.assertEqual(result.runner_args.network_bytes_limit, 1024)
    self.assertEqual(
        result.create_time, int(rdfvalue.RDFDatetime.FromSecondsSinceEpoch(42))
    )
    self.assertEqual(result.error, "foobazzle disintegrated")

    flow_args = flows_pb2.CollectFilesByKnownPathArgs()
    result.flow_args.Unpack(flow_args)
    self.assertEqual(flow_args.paths, ["/baz"])

  def testWriteMultipleScheduledFlows(self):
    client_id = db_test_utils.InitializeClient(self.db)
    username = db_test_utils.InitializeUser(self.db)

    self._SetupScheduledFlow(client_id=client_id, creator=username)
    self._SetupScheduledFlow(client_id=client_id, creator=username)

    results = self.db.ListScheduledFlows(client_id, username)
    self.assertLen(results, 2)

    self.assertEqual(results[0].client_id, client_id)
    self.assertEqual(results[1].client_id, client_id)

    self.assertEqual(results[0].creator, username)
    self.assertEqual(results[1].creator, username)

  def testWriteScheduledFlowUpdatesExistingEntry(self):
    client_id = db_test_utils.InitializeClient(self.db)
    username = db_test_utils.InitializeUser(self.db)

    sf = self._SetupScheduledFlow(client_id=client_id, creator=username)
    sf = self._SetupScheduledFlow(
        client_id=client_id,
        creator=username,
        scheduled_flow_id=sf.scheduled_flow_id,
        error="foobar",
    )

    results = self.db.ListScheduledFlows(client_id, username)
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id)
    self.assertEqual(results[0].creator, username)
    self.assertEqual(results[0].scheduled_flow_id, sf.scheduled_flow_id)
    self.assertEqual(results[0].error, "foobar")

  def testListScheduledFlowsFiltersCorrectly(self):
    client_id1 = db_test_utils.InitializeClient(self.db, "C.0000000000000001")
    client_id2 = db_test_utils.InitializeClient(self.db, "C.0000000000000002")
    client_id3 = db_test_utils.InitializeClient(self.db, "C.0000000000000003")

    username1 = db_test_utils.InitializeUser(self.db)
    username2 = db_test_utils.InitializeUser(self.db)
    username3 = db_test_utils.InitializeUser(self.db)

    self._SetupScheduledFlow(client_id=client_id1, creator=username1)
    self._SetupScheduledFlow(client_id=client_id1, creator=username1)
    self._SetupScheduledFlow(client_id=client_id1, creator=username2)
    self._SetupScheduledFlow(client_id=client_id2, creator=username1)
    self._SetupScheduledFlow(client_id=client_id2, creator=username2)

    results = self.db.ListScheduledFlows(client_id1, username1)
    self.assertLen(results, 2)
    self.assertEqual(results[0].client_id, client_id1)
    self.assertEqual(results[0].creator, username1)
    self.assertEqual(results[1].client_id, client_id1)
    self.assertEqual(results[1].creator, username1)

    results = self.db.ListScheduledFlows(client_id1, username2)
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id1)
    self.assertEqual(results[0].creator, username2)

    results = self.db.ListScheduledFlows(client_id2, username1)
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id2)
    self.assertEqual(results[0].creator, username1)

    results = self.db.ListScheduledFlows(client_id2, username2)
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id2)
    self.assertEqual(results[0].creator, username2)

    self.assertEmpty(
        self.db.ListScheduledFlows("C.1234123412341234", username1)
    )
    self.assertEmpty(self.db.ListScheduledFlows(client_id1, "nonexistent"))
    self.assertEmpty(
        self.db.ListScheduledFlows("C.1234123412341234", "nonexistent")
    )
    self.assertEmpty(self.db.ListScheduledFlows(client_id3, username1))
    self.assertEmpty(self.db.ListScheduledFlows(client_id1, username3))

  def testWriteScheduledFlowRaisesForUnknownClient(self):
    username = db_test_utils.InitializeUser(self.db)

    with self.assertRaises(db.UnknownClientError):
      self._SetupScheduledFlow(client_id="C.1234123412341234", creator=username)

    self.assertEmpty(self.db.ListScheduledFlows("C.1234123412341234", username))

  def testWriteScheduledFlowRaisesForUnknownUser(self):
    client_id = db_test_utils.InitializeClient(self.db)

    with self.assertRaises(db.UnknownGRRUserError):
      self._SetupScheduledFlow(client_id=client_id, creator="nonexistent")

    self.assertEmpty(self.db.ListScheduledFlows(client_id, "nonexistent"))

  def testDeleteScheduledFlowRemovesScheduledFlow(self):
    client_id = db_test_utils.InitializeClient(self.db)
    username = db_test_utils.InitializeUser(self.db)

    sf = self._SetupScheduledFlow(client_id=client_id, creator=username)

    self.db.DeleteScheduledFlow(client_id, username, sf.scheduled_flow_id)

    self.assertEmpty(self.db.ListScheduledFlows(client_id, username))

  def testDeleteScheduledFlowDoesNotRemoveUnrelatedEntries(self):
    client_id1 = db_test_utils.InitializeClient(self.db)
    client_id2 = db_test_utils.InitializeClient(self.db)
    username1 = db_test_utils.InitializeUser(self.db)
    username2 = db_test_utils.InitializeUser(self.db)

    sf111 = self._SetupScheduledFlow(client_id=client_id1, creator=username1)
    self._SetupScheduledFlow(client_id=client_id1, creator=username1)
    self._SetupScheduledFlow(
        client_id=client_id2,
        creator=username1,
        scheduled_flow_id=sf111.scheduled_flow_id,
    )
    self._SetupScheduledFlow(
        client_id=client_id1,
        creator=username2,
        scheduled_flow_id=sf111.scheduled_flow_id,
    )

    self.db.DeleteScheduledFlow(client_id1, username1, sf111.scheduled_flow_id)

    results = self.db.ListScheduledFlows(client_id1, username1)
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id1)
    self.assertEqual(results[0].creator, username1)

    results = self.db.ListScheduledFlows(client_id2, username1)
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id2)
    self.assertEqual(results[0].creator, username1)

    results = self.db.ListScheduledFlows(client_id1, username2)
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id1)
    self.assertEqual(results[0].creator, username2)

  def testDeleteScheduledFlowRaisesForUnknownScheduledFlow(self):
    client_id = db_test_utils.InitializeClient(self.db)
    username = db_test_utils.InitializeUser(self.db)

    self._SetupScheduledFlow(
        scheduled_flow_id="1", client_id=client_id, creator=username
    )

    with self.assertRaises(db.UnknownScheduledFlowError) as e:
      self.db.DeleteScheduledFlow(client_id, username, "2")

    self.assertEqual(e.exception.client_id, client_id)
    self.assertEqual(e.exception.creator, username)
    self.assertEqual(e.exception.scheduled_flow_id, "2")

    with self.assertRaises(db.UnknownScheduledFlowError):
      self.db.DeleteScheduledFlow(client_id, "nonexistent", "1")

    with self.assertRaises(db.UnknownScheduledFlowError):
      self.db.DeleteScheduledFlow("C.1234123412341234", username, "1")

  def testDeleteUserDeletesScheduledFlows(self):
    client_id = db_test_utils.InitializeClient(self.db)
    client_id2 = db_test_utils.InitializeClient(self.db)
    username1 = db_test_utils.InitializeUser(self.db)
    username2 = db_test_utils.InitializeUser(self.db)

    self._SetupScheduledFlow(client_id=client_id, creator=username1)
    self._SetupScheduledFlow(client_id=client_id, creator=username1)
    self._SetupScheduledFlow(client_id=client_id2, creator=username1)
    self._SetupScheduledFlow(client_id=client_id, creator=username2)

    self.db.DeleteGRRUser(username1)

    self.assertEmpty(self.db.ListScheduledFlows(client_id, username1))
    self.assertEmpty(self.db.ListScheduledFlows(client_id2, username1))

    results = self.db.ListScheduledFlows(client_id, username2)
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id)
    self.assertEqual(results[0].creator, username2)


class DatabaseLargeTestFlowMixin(object):
  """An abstract class for large tests of database flow methods."""

  # TODO(hanuszczak): Remove code duplication in the three methods below shared
  # with the `DatabaseTestFlowMixin` class.

  def _Responses(
      self, client_id, flow_id, request_id, num_responses
  ) -> list[flows_pb2.FlowResponse]:
    # TODO(hanuszczak): Fix this lint properly.
    # pylint: disable=g-complex-comprehension
    return [
        flows_pb2.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_id,
            response_id=i,
        )
        for i in range(1, num_responses + 1)
    ]

  # pylint: enable=g-complex-comprehension

  def _ResponsesAndStatus(
      self, client_id, flow_id, request_id, num_responses
  ) -> list[Union[flows_pb2.FlowResponse, flows_pb2.FlowStatus]]:
    return self._Responses(client_id, flow_id, request_id, num_responses) + [
        flows_pb2.FlowStatus(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_id,
            response_id=num_responses + 1,
        )
    ]

  def _WriteResponses(self, num) -> tuple[
      flows_pb2.FlowRequest,
      list[Union[flows_pb2.FlowResponse, flows_pb2.FlowStatus]],
  ]:
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )

    request = flows_pb2.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=2
    )
    self.db.WriteFlowRequests([request])

    # Generate responses together with a status message.
    responses = self._ResponsesAndStatus(client_id, flow_id, 2, num)

    # Write responses. This should trigger flow request processing.
    self.db.WriteFlowResponses(responses)

    return request, responses

  def test40001RequestsCanBeWrittenAndRead(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )

    requests = [
        flows_pb2.FlowRequest(
            client_id=client_id, flow_id=flow_id, request_id=i
        )
        for i in range(40001)
    ]
    self.db.WriteFlowRequests(requests)

    self.assertLen(
        self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id), 40001
    )

  def test40001ResponsesCanBeWrittenAndRead(self):
    before_write = self.db.Now()
    request, responses = self._WriteResponses(40001)
    after_write = self.db.Now()

    expected_request = flows_pb2.FlowRequest(
        client_id=request.client_id,
        flow_id=request.flow_id,
        request_id=request.request_id,
        needs_processing=True,
        nr_responses_expected=40002,
    )

    rrp = self.db.ReadFlowRequests(
        request.client_id,
        request.flow_id,
    )
    self.assertLen(rrp, 1)
    fetched_request, fetched_responses = rrp[request.request_id]

    self.assertIsInstance(fetched_request, flows_pb2.FlowRequest)
    self.assertEqual(fetched_request.client_id, expected_request.client_id)
    self.assertEqual(fetched_request.flow_id, expected_request.flow_id)
    self.assertEqual(fetched_request.request_id, expected_request.request_id)
    self.assertEqual(
        fetched_request.needs_processing, expected_request.needs_processing
    )
    self.assertEqual(
        fetched_request.nr_responses_expected,
        expected_request.nr_responses_expected,
    )
    self.assertBetween(fetched_request.timestamp, before_write, after_write)

    for r in fetched_responses:
      # `responses` does not have the timestamp as it is only available after
      # reading, not writing, so we compare it manually and remove it from the
      # proto.
      self.assertBetween(r.timestamp, before_write, after_write)
      r.ClearField("timestamp")
    self.assertEqual(fetched_responses, responses)

    arrp = self.db.ReadAllFlowRequestsAndResponses(
        request.client_id, request.flow_id
    )
    self.assertLen(arrp, 1)
    fetched_request, fetched_responses = arrp[0]
    self.assertIsInstance(fetched_request, flows_pb2.FlowRequest)
    self.assertEqual(fetched_request.client_id, expected_request.client_id)
    self.assertEqual(fetched_request.flow_id, expected_request.flow_id)
    self.assertEqual(fetched_request.request_id, expected_request.request_id)
    self.assertEqual(
        fetched_request.needs_processing, expected_request.needs_processing
    )
    self.assertEqual(
        fetched_request.nr_responses_expected,
        expected_request.nr_responses_expected,
    )
    self.assertBetween(fetched_request.timestamp, before_write, after_write)
    for r in fetched_responses.values():
      # `responses` does not have the timestamp as it is only available after
      # reading, not writing, so we compare it manually and remove it from the
      # proto.
      self.assertBetween(r.timestamp, before_write, after_write)
      r.ClearField("timestamp")
    self.assertEqual(
        [r for _, r in sorted(fetched_responses.items())], responses
    )

  def testDeleteAllFlowRequestsAndResponsesHandles11000Responses(self):
    request, _ = self._WriteResponses(11000)

    self.db.DeleteAllFlowRequestsAndResponses(
        request.client_id, request.flow_id
    )
    arrp = self.db.ReadAllFlowRequestsAndResponses(
        request.client_id, request.flow_id
    )
    self.assertEmpty(arrp)

  def testDeleteFlowRequestsHandles11000Responses(self):
    request, _ = self._WriteResponses(11000)
    self.db.DeleteFlowRequests([request])
    arrp = self.db.ReadAllFlowRequestsAndResponses(
        request.client_id, request.flow_id
    )
    self.assertEmpty(arrp)

  def testDeleteFlowRequestsHandles11000Requests(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(
        self.db, client_id, next_request_to_process=2
    )

    requests = [
        flows_pb2.FlowRequest(
            client_id=client_id, flow_id=flow_id, request_id=i
        )
        for i in range(2, 11002)
    ]
    self.db.WriteFlowRequests(requests)

    self.assertLen(
        self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id), 11000
    )

    self.db.DeleteFlowRequests(requests)

    self.assertEmpty(
        self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    )

  def testWritesAndCounts40001FlowResults(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    client_summary_result = flows_pb2.FlowResult(
        client_id=client_id, flow_id=flow_id
    )
    client_summary_result.payload.Pack(
        jobs_pb2.ClientSummary(client_id=client_id)
    )

    sample_results = [client_summary_result] * 40001

    self.db.WriteFlowResults(sample_results)

    result_count = self.db.CountFlowResults(client_id, flow_id)
    self.assertEqual(result_count, 40001)

  def testWritesAndCounts40001FlowErrors(self):
    client_id = db_test_utils.InitializeClient(self.db)
    flow_id = db_test_utils.InitializeFlow(self.db, client_id)

    client_summary_error = flows_pb2.FlowError(
        client_id=client_id, flow_id=flow_id
    )
    client_summary_error.payload.Pack(
        jobs_pb2.ClientSummary(client_id=client_id)
    )
    sample_errors = [client_summary_error] * 40001

    self.db.WriteFlowErrors(sample_errors)

    error_count = self.db.CountFlowErrors(client_id, flow_id)
    self.assertEqual(error_count, 40001)


# This file is a test library and thus does not require a __main__ block.
