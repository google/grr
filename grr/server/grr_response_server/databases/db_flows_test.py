#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for the flow database api."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import itertools
import random
import time

from future.builtins import range
from future.utils import iteritems
import mock
import queue

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import compatibility
from grr_response_server import flow
from grr_response_server.databases import db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import hunt_objects as rdf_hunt_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class DatabaseTestFlowMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of flows.
  """

  def _SetupClientAndFlow(self, client_id=None, **additional_flow_args):
    client_id = client_id or u"C.1234567890123456"
    flow_id = flow.RandomFlowId()
    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id=flow_id,
        create_time=rdfvalue.RDFDatetime.Now(),
        **additional_flow_args)
    self.db.WriteFlowObject(rdf_flow)

    return client_id, flow_id

  def testClientActionRequestStorage(self):
    client_id, flow_id = self._SetupClientAndFlow()
    self.db.WriteFlowRequests([
        rdf_flow_objects.FlowRequest(
            client_id=client_id, flow_id=flow_id, request_id=1)
    ])
    req = rdf_flows.ClientActionRequest(
        client_id=client_id, flow_id=flow_id, request_id=1)

    self.db.WriteClientActionRequests([req])

    read_reqs = self.db.ReadAllClientActionRequests(client_id)
    self.assertLen(read_reqs, 1)
    self.assertEqual(req, read_reqs[0])

    self.db.DeleteClientActionRequests([req])
    read_reqs = self.db.ReadAllClientActionRequests(client_id)
    self.assertEmpty(read_reqs)

    # Extra delete should not raise.
    self.db.DeleteClientActionRequests([req])

    # Deleting the same message multiple times is an error.
    with self.assertRaises(ValueError):
      self.db.DeleteClientActionRequests([req, req])

  def testWriteClientActionRequestsRaisesOnUnknownRequest(self):
    req = rdf_flows.ClientActionRequest(
        client_id=u"C.1234567890000000", flow_id="ABCD1234", request_id=5)
    with self.assertRaises(db.AtLeastOneUnknownRequestError):
      self.db.WriteClientActionRequests([req])

  def testClientActionRequestUpdate(self):
    client_id, flow_id = self._SetupClientAndFlow()
    req = rdf_flows.ClientActionRequest(
        client_id=client_id, flow_id=flow_id, request_id=1)
    self.db.WriteFlowRequests([
        rdf_flow_objects.FlowRequest(
            client_id=client_id, flow_id=flow_id, request_id=1)
    ])

    cpu_limit = req.cpu_limit_ms
    self.assertGreater(cpu_limit, 1000000)

    for _ in range(5):
      req.cpu_limit_ms -= 100000
      self.db.WriteClientActionRequests([req])
      read_reqs = self.db.ReadAllClientActionRequests(client_id)
      self.assertLen(read_reqs, 1)
      self.assertEqual(req, read_reqs[0])

  def testClientActionRequestLeasing(self):

    client_id, flow_id = self._SetupClientAndFlow()
    flow_requests = []
    client_requests = []
    for i in range(10):
      flow_requests.append(
          rdf_flow_objects.FlowRequest(
              client_id=client_id, flow_id=flow_id, request_id=i))
      client_requests.append(
          rdf_flows.ClientActionRequest(
              client_id=client_id, flow_id=flow_id, request_id=i))

    lease_time = rdfvalue.Duration("5m")
    self.db.WriteFlowRequests(flow_requests)
    self.db.WriteClientActionRequests(client_requests)

    t0 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000)
    with test_lib.FakeTime(t0):
      t0_expiry = t0 + lease_time
      leased = self.db.LeaseClientActionRequests(
          client_id, lease_time=lease_time, limit=5)

      self.assertLen(leased, 5)

      for request in leased:
        self.assertEqual(request.leased_until, t0_expiry)
        self.assertEqual(request.leased_by, utils.ProcessIdString())

    t1 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 100)
    with test_lib.FakeTime(t1):
      t1_expiry = t1 + lease_time
      leased = self.db.LeaseClientActionRequests(
          client_id, lease_time=lease_time, limit=5)

      self.assertLen(leased, 5)

      for request in leased:
        self.assertEqual(request.leased_until, t1_expiry)
        self.assertEqual(request.leased_by, utils.ProcessIdString())

      # Nothing left to lease.
      leased = self.db.LeaseClientActionRequests(
          client_id, lease_time=lease_time, limit=2)

      self.assertEmpty(leased)

    read = self.db.ReadAllClientActionRequests(client_id)

    self.assertLen(read, 10)
    for r in read:
      self.assertEqual(r.leased_by, utils.ProcessIdString())

    self.assertLen([r for r in read if r.leased_until == t0_expiry], 5)
    self.assertLen([r for r in read if r.leased_until == t1_expiry], 5)

    # Half the leases expired.
    t2 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 350)
    with test_lib.FakeTime(t2):
      leased = self.db.LeaseClientActionRequests(
          client_id, lease_time=lease_time)

      self.assertLen(leased, 5)

    # All of them expired.
    t3 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 10350)
    with test_lib.FakeTime(t3):
      leased = self.db.LeaseClientActionRequests(
          client_id, lease_time=lease_time)

      self.assertLen(leased, 10)

  def testClientActionRequestsTTL(self):
    client_id, flow_id = self._SetupClientAndFlow()
    flow_requests = []
    client_requests = []
    for i in range(10):
      flow_requests.append(
          rdf_flow_objects.FlowRequest(
              client_id=client_id, flow_id=flow_id, request_id=i))
      client_requests.append(
          rdf_flows.ClientActionRequest(
              client_id=client_id, flow_id=flow_id, request_id=i))
    self.db.WriteFlowRequests(flow_requests)
    self.db.WriteClientActionRequests(client_requests)

    reqs = self.db.ReadAllClientActionRequests(client_id)
    self.assertLen(reqs, 10)

    for request in reqs:
      self.assertEqual(request.ttl, db.Database.CLIENT_MESSAGES_TTL)

    now = rdfvalue.RDFDatetime.Now()
    lease_time = rdfvalue.Duration("60s")

    for i in range(db.Database.CLIENT_MESSAGES_TTL):
      now += rdfvalue.Duration("120s")
      with test_lib.FakeTime(now):
        leased = self.db.LeaseClientActionRequests(
            client_id, lease_time=lease_time, limit=10)
        self.assertLen(leased, 10)

        # Check that the ttl is read.
        for request in leased:
          self.assertEqual(request.ttl, db.Database.CLIENT_MESSAGES_TTL - i - 1)

        reqs = self.db.ReadAllClientActionRequests(client_id)
        self.assertLen(reqs, 10)

        for request in reqs:
          self.assertEqual(request.ttl, db.Database.CLIENT_MESSAGES_TTL - i - 1)

    now += rdfvalue.Duration("120s")
    with test_lib.FakeTime(now):
      leased = self.db.LeaseClientActionRequests(
          client_id, lease_time=lease_time, limit=10)
      self.assertEmpty(leased)

    # ReadAllClientActionRequests includes also requests whose TTL has
    # expired. Make sure that the requests have been deleted from the db.
    self.assertEqual(self.db.ReadAllClientActionRequests(client_id), [])

  def testFlowWritingUnknownClient(self):
    flow_id = u"1234ABCD"
    client_id = u"C.1234567890123456"

    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id=flow_id,
        create_time=rdfvalue.RDFDatetime.Now())

    with self.assertRaises(db.UnknownClientError):
      self.db.WriteFlowObject(rdf_flow)

  def testFlowWriting(self):
    flow_id = u"1234ABCD"
    client_id = u"C.1234567890123456"

    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id=flow_id,
        next_request_to_process=4,
        create_time=rdfvalue.RDFDatetime.Now())
    self.db.WriteFlowObject(rdf_flow)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)

    # Last update time has changed, everything else should be equal.
    read_flow.last_update_time = None

    self.assertEqual(read_flow, rdf_flow)

    # Invalid flow id or client id raises.
    with self.assertRaises(db.UnknownFlowError):
      self.db.ReadFlowObject(client_id, u"1234AAAA")

    with self.assertRaises(db.UnknownFlowError):
      self.db.ReadFlowObject(u"C.1234567890000000", flow_id)

  def testFlowOverwrite(self):
    flow_id = u"1234ABCD"
    client_id = u"C.1234567890123456"

    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id=flow_id,
        next_request_to_process=4,
        create_time=rdfvalue.RDFDatetime.Now())
    self.db.WriteFlowObject(rdf_flow)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)

    # Last update time has changed, everything else should be equal.
    read_flow.last_update_time = None

    self.assertEqual(read_flow, rdf_flow)

    # Now change the flow object.
    rdf_flow.next_request_to_process = 5

    self.db.WriteFlowObject(rdf_flow)

    read_flow_after_update = self.db.ReadFlowObject(client_id, flow_id)

    self.assertEqual(read_flow_after_update.next_request_to_process, 5)

  def testReadAllFlowObjects(self):
    client_id_1 = "C.1111111111111111"
    client_id_2 = "C.2222222222222222"

    self.db.WriteClientMetadata(client_id_1, fleetspeak_enabled=False)
    self.db.WriteClientMetadata(client_id_2, fleetspeak_enabled=False)

    # Write a flow and a child flow for client 1.
    flow1 = rdf_flow_objects.Flow(
        client_id=client_id_1,
        flow_id="000A0001",
        create_time=rdfvalue.RDFDatetime.Now())
    self.db.WriteFlowObject(flow1)
    flow2 = rdf_flow_objects.Flow(
        client_id=client_id_1,
        flow_id="000A0002",
        parent_flow_id="000A0001",
        create_time=rdfvalue.RDFDatetime.Now())
    self.db.WriteFlowObject(flow2)

    # Same flow id for client 2.
    flow3 = rdf_flow_objects.Flow(
        client_id=client_id_2,
        flow_id="000A0001",
        create_time=rdfvalue.RDFDatetime.Now())
    self.db.WriteFlowObject(flow3)

    flows = self.db.ReadAllFlowObjects()
    self.assertCountEqual([f.flow_id for f in flows],
                          ["000A0001", "000A0002", "000A0001"])

  def testReadAllFlowObjectsWithMinCreateTime(self):
    now = rdfvalue.RDFDatetime.Now()
    client_id_1 = "C.1111111111111111"
    self.db.WriteClientMetadata(client_id_1, fleetspeak_enabled=False)

    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_1,
            flow_id="0000001A",
            create_time=now - rdfvalue.Duration("2h")))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_1,
            flow_id="0000001B",
            create_time=now - rdfvalue.Duration("1h")))

    flows = self.db.ReadAllFlowObjects(min_create_time=now -
                                       rdfvalue.Duration("1h"))
    self.assertEqual([f.flow_id for f in flows], ["0000001B"])

  def testReadAllFlowObjectsWithMaxCreateTime(self):
    now = rdfvalue.RDFDatetime.Now()
    client_id_1 = "C.1111111111111111"
    self.db.WriteClientMetadata(client_id_1, fleetspeak_enabled=False)

    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_1,
            flow_id="0000001A",
            create_time=now - rdfvalue.Duration("2h")))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_1,
            flow_id="0000001B",
            create_time=now - rdfvalue.Duration("1h")))

    flows = self.db.ReadAllFlowObjects(max_create_time=now -
                                       rdfvalue.Duration("2h"))
    self.assertEqual([f.flow_id for f in flows], ["0000001A"])

  def testReadAllFlowObjectsWithClientID(self):
    now = rdfvalue.RDFDatetime.Now()
    client_id_1 = "C.1111111111111111"
    client_id_2 = "C.2222222222222222"
    self.db.WriteClientMetadata(client_id_1, fleetspeak_enabled=False)
    self.db.WriteClientMetadata(client_id_2, fleetspeak_enabled=False)

    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_1, flow_id="0000001A", create_time=now))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_2, flow_id="0000001B", create_time=now))

    flows = self.db.ReadAllFlowObjects(client_id=client_id_1)
    self.assertEqual([f.flow_id for f in flows], ["0000001A"])

  def testReadAllFlowObjectsWithoutChildren(self):
    now = rdfvalue.RDFDatetime.Now()
    client_id_1 = "C.1111111111111111"
    self.db.WriteClientMetadata(client_id_1, fleetspeak_enabled=False)

    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_1, flow_id="0000001A", create_time=now))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_1,
            flow_id="0000001B",
            parent_flow_id="0000001A",
            create_time=now))

    flows = self.db.ReadAllFlowObjects(include_child_flows=False)
    self.assertEqual([f.flow_id for f in flows], ["0000001A"])

  def testReadAllFlowObjectsWithAllConditions(self):
    now = rdfvalue.RDFDatetime.Now()
    client_id_1 = "C.1111111111111111"
    client_id_2 = "C.2222222222222222"
    self.db.WriteClientMetadata(client_id_1, fleetspeak_enabled=False)
    self.db.WriteClientMetadata(client_id_2, fleetspeak_enabled=False)

    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_1, flow_id="0000000A", create_time=now))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_1,
            flow_id="0000000B",
            parent_flow_id="0000000A",
            create_time=now))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_1,
            flow_id="0000000C",
            create_time=now - rdfvalue.Duration.FromSeconds(1)))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_1,
            flow_id="0000000D",
            create_time=now + rdfvalue.Duration.FromSeconds(1)))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            client_id=client_id_2, flow_id="0000000E", create_time=now))

    flows = self.db.ReadAllFlowObjects(
        client_id=client_id_1,
        min_create_time=now,
        max_create_time=now,
        include_child_flows=False)
    self.assertEqual([f.flow_id for f in flows], ["0000000A"])

  def testUpdateUnknownFlow(self):
    _, flow_id = self._SetupClientAndFlow()

    crash_info = rdf_client.ClientCrash(crash_message="oh no")
    with self.assertRaises(db.UnknownFlowError):
      self.db.UpdateFlow(
          u"C.1234567890AAAAAA", flow_id, client_crash_info=crash_info)

  def testFlowUpdateChangesAllFields(self):
    client_id, flow_id = self._SetupClientAndFlow()

    flow_obj = self.db.ReadFlowObject(client_id, flow_id)

    flow_obj.cpu_time_used.user_cpu_time = 0.5
    flow_obj.cpu_time_used.system_cpu_time = 1.5
    flow_obj.num_replies_sent = 10
    flow_obj.network_bytes_sent = 100

    self.db.UpdateFlow(client_id, flow_id, flow_obj=flow_obj)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)

    # Last update times will differ.
    read_flow.last_update_time = None
    flow_obj.last_update_time = None

    self.assertEqual(read_flow, flow_obj)

  def testFlowStateUpdate(self):
    client_id, flow_id = self._SetupClientAndFlow()

    # Check that just updating flow_state works fine.
    self.db.UpdateFlow(
        client_id, flow_id, flow_state=rdf_flow_objects.Flow.FlowState.CRASHED)
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.flow_state,
                     rdf_flow_objects.Flow.FlowState.CRASHED)

    # TODO(user): remove an option to update the flow by updating flow_obj.
    # It makes the DB API unnecessary complicated.
    # Check that changing flow_state through flow_obj works too.
    read_flow.flow_state = rdf_flow_objects.Flow.FlowState.RUNNING
    self.db.UpdateFlow(client_id, flow_id, flow_obj=read_flow)

    read_flow_2 = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow_2.flow_state,
                     rdf_flow_objects.Flow.FlowState.RUNNING)

  def testUpdatingFlowObjAndFlowStateInSingleUpdateRaises(self):
    client_id, flow_id = self._SetupClientAndFlow()

    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    with self.assertRaises(db.ConflictingUpdateFlowArgumentsError):
      self.db.UpdateFlow(
          client_id,
          flow_id,
          flow_obj=read_flow,
          flow_state=rdf_flow_objects.Flow.FlowState.CRASHED)

  def testCrashInfoUpdate(self):
    client_id, flow_id = self._SetupClientAndFlow()

    crash_info = rdf_client.ClientCrash(crash_message="oh no")
    self.db.UpdateFlow(client_id, flow_id, client_crash_info=crash_info)
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.client_crash_info, crash_info)

  def testPendingTerminationUpdate(self):
    client_id, flow_id = self._SetupClientAndFlow()

    pending_termination = rdf_flow_objects.PendingFlowTermination(reason="test")
    self.db.UpdateFlow(
        client_id, flow_id, pending_termination=pending_termination)
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.pending_termination, pending_termination)

  def testProcessingInformationUpdate(self):
    client_id, flow_id = self._SetupClientAndFlow()

    now = rdfvalue.RDFDatetime.Now()
    deadline = now + rdfvalue.Duration("6h")
    self.db.UpdateFlow(
        client_id,
        flow_id,
        processing_on="Worker1",
        processing_since=now,
        processing_deadline=deadline)
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.processing_on, "Worker1")
    self.assertEqual(read_flow.processing_since, now)
    self.assertEqual(read_flow.processing_deadline, deadline)

    # None can be used to clear some fields.
    self.db.UpdateFlow(client_id, flow_id, processing_on=None)
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.processing_on, "")

    self.db.UpdateFlow(client_id, flow_id, processing_since=None)
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.processing_since, None)

    self.db.UpdateFlow(client_id, flow_id, processing_deadline=None)
    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.processing_deadline, None)

  def testUpdateFlowsIgnoresMissingFlows(self):
    _, flow_id = self._SetupClientAndFlow()
    pending_termination = rdf_flow_objects.PendingFlowTermination(reason="test")
    self.db.UpdateFlows([("C.1234567890AAAAAA", flow_id),
                         ("C.1234567890BBBBBB", flow_id)],
                        pending_termination=pending_termination)

  def testUpdateFlowsUpdatesMultipleFlowsCorrectly(self):
    client_id_1, flow_id_1 = self._SetupClientAndFlow(
        client_id="C.1234567890AAAAAA")
    client_id_2, flow_id_2 = self._SetupClientAndFlow(
        client_id="C.1234567890BBBBBB")

    pending_termination = rdf_flow_objects.PendingFlowTermination(reason="test")
    self.db.UpdateFlows([(client_id_1, flow_id_1), (client_id_2, flow_id_2)],
                        pending_termination=pending_termination)

    read_flow_1 = self.db.ReadFlowObject(client_id_1, flow_id_1)
    self.assertEqual(read_flow_1.pending_termination, pending_termination)

    read_flow_2 = self.db.ReadFlowObject(client_id_2, flow_id_2)
    self.assertEqual(read_flow_2.pending_termination, pending_termination)

  def testRequestWriting(self):
    client_id_1 = u"C.1234567890123456"
    client_id_2 = u"C.1234567890123457"
    flow_id_1 = u"1234ABCD"
    flow_id_2 = u"ABCD1234"

    with self.assertRaises(db.AtLeastOneUnknownFlowError):
      self.db.WriteFlowRequests([
          rdf_flow_objects.FlowRequest(
              client_id=client_id_1, flow_id=flow_id_1)
      ])
    for client_id in [client_id_1, client_id_2]:
      self.db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    requests = []
    for flow_id in [flow_id_1, flow_id_2]:
      for client_id in [client_id_1, client_id_2]:
        rdf_flow = rdf_flow_objects.Flow(
            client_id=client_id,
            flow_id=flow_id,
            create_time=rdfvalue.RDFDatetime.Now())
        self.db.WriteFlowObject(rdf_flow)

        for i in range(1, 4):
          requests.append(
              rdf_flow_objects.FlowRequest(
                  client_id=client_id, flow_id=flow_id, request_id=i))

    self.db.WriteFlowRequests(requests)

    for flow_id in [flow_id_1, flow_id_2]:
      for client_id in [client_id_1, client_id_2]:
        read = self.db.ReadAllFlowRequestsAndResponses(
            client_id=client_id, flow_id=flow_id)

        self.assertLen(read, 3)
        self.assertEqual([req.request_id for (req, _) in read],
                         list(range(1, 4)))
        for _, responses in read:
          self.assertEqual(responses, {})

  def _WriteRequestForProcessing(self, client_id, flow_id, request_id):
    req_func = mock.Mock()
    self.db.RegisterFlowProcessingHandler(req_func)
    self.addCleanup(self.db.UnregisterFlowProcessingHandler)

    _, marked_flow_id = self._SetupClientAndFlow(
        client_id=client_id, next_request_to_process=3)

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
    request = rdf_flow_objects.FlowRequest(
        flow_id=flow_id,
        client_id=client_id,
        request_id=request_id,
        needs_processing=True)
    marked_request = rdf_flow_objects.FlowRequest(
        flow_id=marked_flow_id,
        client_id=client_id,
        request_id=3,
        needs_processing=True)

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
      if rdfvalue.RDFDatetime.Now() - cur_time > rdfvalue.Duration("10s"):
        self.fail("Flow request was not processed in time.")

  def testRequestWritingHighIDDoesntTriggerFlowProcessing(self):
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=3)

    requests_triggered = self._WriteRequestForProcessing(client_id, flow_id, 4)
    # Not the expected request.
    self.assertEqual(requests_triggered, 0)

  def testRequestWritingLowIDDoesntTriggerFlowProcessing(self):
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=3)

    requests_triggered = self._WriteRequestForProcessing(client_id, flow_id, 2)
    # Not the expected request.
    self.assertEqual(requests_triggered, 0)

  def testRequestWritingExpectedIDTriggersFlowProcessing(self):
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=3)

    requests_triggered = self._WriteRequestForProcessing(client_id, flow_id, 3)
    # This one is.
    self.assertEqual(requests_triggered, 1)

  def testFlowRequestsWithStartTimeAreCorrectlyDelayed(self):
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=3)

    req_func = mock.Mock()
    self.db.RegisterFlowProcessingHandler(req_func)
    self.addCleanup(self.db.UnregisterFlowProcessingHandler)

    cur_time = rdfvalue.RDFDatetime.Now()
    request = rdf_flow_objects.FlowRequest(
        flow_id=flow_id,
        client_id=client_id,
        request_id=3,
        start_time=cur_time + rdfvalue.Duration("2s"),
        needs_processing=True)

    self.db.WriteFlowRequests([request])
    self.assertEqual(req_func.call_count, 0)

    while req_func.call_count == 0:
      time.sleep(0.1)
      if rdfvalue.RDFDatetime.Now() - cur_time > rdfvalue.Duration("10s"):
        self.fail("Flow request was not processed in time.")

    self.assertGreaterEqual(rdfvalue.RDFDatetime.Now() - cur_time,
                            rdfvalue.Duration("2s"))

  def testDeleteFlowRequests(self):
    client_id, flow_id = self._SetupClientAndFlow()

    requests = []
    responses = []
    client_requests = []
    for request_id in range(1, 4):
      requests.append(
          rdf_flow_objects.FlowRequest(
              client_id=client_id, flow_id=flow_id, request_id=request_id))
      responses.append(
          rdf_flow_objects.FlowResponse(
              client_id=client_id,
              flow_id=flow_id,
              request_id=request_id,
              response_id=1))
      client_requests.append(
          rdf_flows.ClientActionRequest(
              client_id=client_id, flow_id=flow_id, request_id=request_id))

    self.db.WriteFlowRequests(requests)
    self.db.WriteFlowResponses(responses)
    self.db.WriteClientActionRequests(client_requests)

    request_list = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertCountEqual([req.request_id for req, _ in request_list],
                          [req.request_id for req in requests])

    random.shuffle(requests)

    while requests:
      request = requests.pop()
      self.db.DeleteFlowRequests([request])
      request_list = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
      self.assertCountEqual([req.request_id for req, _ in request_list],
                            [req.request_id for req in requests])

  def testResponsesForUnknownFlow(self):
    client_id = u"C.1234567890123456"
    flow_id = u"1234ABCD"

    # This will not raise but also not write anything.
    with test_lib.SuppressLogs():
      self.db.WriteFlowResponses([
          rdf_flow_objects.FlowResponse(
              client_id=client_id, flow_id=flow_id, request_id=1, response_id=1)
      ])
    read = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertEqual(read, [])

  def testResponsesForUnknownRequest(self):
    client_id, flow_id = self._SetupClientAndFlow()

    request = rdf_flow_objects.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1)
    self.db.WriteFlowRequests([request])

    # Write two responses at a time, one request exists, the other doesn't.
    with test_lib.SuppressLogs():
      self.db.WriteFlowResponses([
          rdf_flow_objects.FlowResponse(
              client_id=client_id, flow_id=flow_id, request_id=1,
              response_id=1),
          rdf_flow_objects.FlowResponse(
              client_id=client_id, flow_id=flow_id, request_id=2, response_id=1)
      ])

    # We should have one response in the db.
    read = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(read, 1)
    request, responses = read[0]
    self.assertLen(responses, 1)

  def testStatusForUnknownRequest(self):
    client_id, flow_id = self._SetupClientAndFlow()

    request = rdf_flow_objects.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1)
    self.db.WriteFlowRequests([request])

    # Write two status responses at a time, one for the request that exists, one
    # for a request that doesn't.
    with test_lib.SuppressLogs():
      self.db.WriteFlowResponses([
          rdf_flow_objects.FlowStatus(
              client_id=client_id, flow_id=flow_id, request_id=1,
              response_id=1),
          rdf_flow_objects.FlowStatus(
              client_id=client_id, flow_id=flow_id, request_id=2, response_id=1)
      ])

    # We should have one response in the db.
    read = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(read, 1)
    request, responses = read[0]
    self.assertLen(responses, 1)

    self.assertEqual(request.nr_responses_expected, 1)

  def testResponseWriting(self):
    client_id, flow_id = self._SetupClientAndFlow()

    request = rdf_flow_objects.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=1,
        needs_processing=False)
    self.db.WriteFlowRequests([request])

    responses = [
        rdf_flow_objects.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=i)
        for i in range(3)
    ]

    self.db.WriteFlowResponses(responses)

    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(all_requests, 1)

    read_request, read_responses = all_requests[0]
    self.assertEqual(read_request, request)
    self.assertEqual(list(read_responses), [0, 1, 2])

    for response_id, response in iteritems(read_responses):
      self.assertEqual(response.response_id, response_id)

  def testResponseWritingForDuplicateResponses(self):
    client_id, flow_id = self._SetupClientAndFlow()

    request = rdf_flow_objects.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=1,
        needs_processing=False)
    self.db.WriteFlowRequests([request])

    responses = [
        rdf_flow_objects.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=0),
        rdf_flow_objects.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=0)
    ]

    self.db.WriteFlowResponses(responses)

    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(all_requests, 1)

    read_request, read_responses = all_requests[0]
    self.assertEqual(read_request, request)
    self.assertEqual(list(read_responses), [0])

    for response_id, response in iteritems(read_responses):
      self.assertEqual(response.response_id, response_id)

  def testStatusMessagesCanBeWrittenAndRead(self):
    client_id, flow_id = self._SetupClientAndFlow()

    request = rdf_flow_objects.FlowRequest(
        client_id=client_id,
        flow_id=flow_id,
        request_id=1,
        needs_processing=False)
    self.db.WriteFlowRequests([request])

    responses = [
        rdf_flow_objects.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=i)
        for i in range(3)
    ]
    # Also store an Iterator, why not.
    responses.append(
        rdf_flow_objects.FlowIterator(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=3))
    responses.append(
        rdf_flow_objects.FlowStatus(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=4))
    self.db.WriteFlowResponses(responses)

    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(all_requests, 1)

    _, read_responses = all_requests[0]
    self.assertEqual(list(read_responses), [0, 1, 2, 3, 4])
    for i in range(3):
      self.assertIsInstance(read_responses[i], rdf_flow_objects.FlowResponse)
    self.assertIsInstance(read_responses[3], rdf_flow_objects.FlowIterator)
    self.assertIsInstance(read_responses[4], rdf_flow_objects.FlowStatus)

  def _ReadRequest(self, client_id, flow_id, request_id):
    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    for request, unused_responses in all_requests:
      if request.request_id == request_id:
        return request

  def _ResponsesAndStatus(self, client_id, flow_id, request_id, num_responses):
    return [
        rdf_flow_objects.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_id,
            response_id=i) for i in range(1, num_responses + 1)
    ] + [
        rdf_flow_objects.FlowStatus(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_id,
            response_id=num_responses + 1)
    ]

  def _WriteRequestAndCompleteResponses(self, client_id, flow_id, request_id,
                                        num_responses):
    request = rdf_flow_objects.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=request_id)
    self.db.WriteFlowRequests([request])

    return self._WriteCompleteResponses(
        client_id=client_id,
        flow_id=flow_id,
        request_id=request_id,
        num_responses=num_responses)

  def _WriteCompleteResponses(self, client_id, flow_id, request_id,
                              num_responses):
    # Write <num_responses> responses and a status in random order.
    responses = self._ResponsesAndStatus(client_id, flow_id, request_id,
                                         num_responses)
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
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=2)
    requests_triggered = self._WriteRequestAndCompleteResponses(
        client_id, flow_id, request_id=1, num_responses=3)

    # No flow processing request generated for request 1 (we are waiting
    # for #2).
    self.assertEqual(requests_triggered, 0)

  def testResponsesForLaterRequestDontTriggerFlowProcessing(self):
    # Write a flow that is waiting for request #2.
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=2)
    requests_triggered = self._WriteRequestAndCompleteResponses(
        client_id, flow_id, request_id=3, num_responses=7)

    # No flow processing request generated for request 3 (we are waiting
    # for #2).
    self.assertEqual(requests_triggered, 0)

  def testResponsesForExpectedRequestTriggerFlowProcessing(self):
    # Write a flow that is waiting for request #2.
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=2)
    requests_triggered = self._WriteRequestAndCompleteResponses(
        client_id, flow_id, request_id=2, num_responses=5)

    # This one generates a request.
    self.assertEqual(requests_triggered, 1)

  def testRewritingResponsesForRequestDoesNotTriggerAdditionalProcessing(self):
    # Write a flow that is waiting for request #2.
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=2)
    marked_client_id, marked_flow_id = self._SetupClientAndFlow(
        next_request_to_process=2)

    request = rdf_flow_objects.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=2)
    self.db.WriteFlowRequests([request])

    marked_request = rdf_flow_objects.FlowRequest(
        client_id=marked_client_id, flow_id=marked_flow_id, request_id=2)
    self.db.WriteFlowRequests([marked_request])

    # Generate responses together with a status message.
    responses = self._ResponsesAndStatus(client_id, flow_id, 2, 4)
    marked_responses = self._ResponsesAndStatus(marked_client_id,
                                                marked_flow_id, 2, 4)

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
      if rdfvalue.RDFDatetime.Now() - cur_time > rdfvalue.Duration("10s"):
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
      if rdfvalue.RDFDatetime.Now() - cur_time > rdfvalue.Duration("10s"):
        self.fail("Flow request was not processed in time.")

  def testResponsesAnyRequestTriggerClientActionRequestDeletion(self):
    # Write a flow that is waiting for request #2.
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=2)
    for i in range(5):
      self.db.WriteFlowRequests([
          rdf_flow_objects.FlowRequest(
              client_id=client_id, flow_id=flow_id, request_id=i)
      ])

    req = rdf_flows.ClientActionRequest(
        client_id=client_id, flow_id=flow_id, request_id=3)
    self.db.WriteClientActionRequests([req])

    self.assertTrue(self.db.ReadAllClientActionRequests(client_id))

    self._WriteCompleteResponses(
        client_id, flow_id, request_id=3, num_responses=3)

    self.assertFalse(self.db.ReadAllClientActionRequests(client_id))

  def _WriteResponses(self, num):
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=2)

    request = rdf_flow_objects.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=2)
    self.db.WriteFlowRequests([request])

    # Generate responses together with a status message.
    responses = self._ResponsesAndStatus(client_id, flow_id, 2, num)

    # Write responses. This should trigger flow request processing.
    self.db.WriteFlowResponses(responses)

    return request, responses

  def test40000ResponsesCanBeWrittenAndRead(self):
    request, responses = self._WriteResponses(40000)

    expected_request = rdf_flow_objects.FlowRequest(
        client_id=request.client_id,
        flow_id=request.flow_id,
        request_id=request.request_id,
        needs_processing=True,
        nr_responses_expected=40001)

    rrp = self.db.ReadFlowRequestsReadyForProcessing(
        request.client_id,
        request.flow_id,
        next_needed_request=request.request_id)
    self.assertLen(rrp, 1)
    fetched_request, fetched_responses = rrp[request.request_id]
    self.assertEqual(fetched_request, expected_request)
    self.assertEqual(fetched_responses, responses)

    arrp = self.db.ReadAllFlowRequestsAndResponses(request.client_id,
                                                   request.flow_id)
    self.assertLen(arrp, 1)
    fetched_request, fetched_responses = arrp[0]
    self.assertEqual(fetched_request, expected_request)
    self.assertEqual([r for _, r in sorted(fetched_responses.items())],
                     responses)

  def testDeleteAllFlowRequestsAndResponsesHandles11000Responses(self):
    request, _ = self._WriteResponses(11000)

    self.db.DeleteAllFlowRequestsAndResponses(request.client_id,
                                              request.flow_id)
    arrp = self.db.ReadAllFlowRequestsAndResponses(request.client_id,
                                                   request.flow_id)
    self.assertEmpty(arrp)

  def testDeleteFlowRequestsHandles11000Responses(self):
    request, _ = self._WriteResponses(11000)

    self.db.DeleteFlowRequests([request])
    arrp = self.db.ReadAllFlowRequestsAndResponses(request.client_id,
                                                   request.flow_id)
    self.assertEmpty(arrp)

  def testDeleteFlowRequestsHandles11000Requests(self):
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=2)

    requests = [
        rdf_flow_objects.FlowRequest(
            client_id=client_id, flow_id=flow_id, request_id=i)
        for i in range(2, 11002)
    ]
    self.db.WriteFlowRequests(requests)

    self.assertLen(
        self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id), 11000)

    self.db.DeleteFlowRequests(requests)

    self.assertEmpty(
        self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id))

  def testLeaseFlowForProcessingRaisesIfParentHuntIsStoppedOrCompleted(self):
    hunt_obj = rdf_hunt_objects.Hunt()
    self.db.WriteHuntObject(hunt_obj)
    self.db.UpdateHuntObject(
        hunt_obj.hunt_id, hunt_state=rdf_hunt_objects.Hunt.HuntState.STOPPED)

    client_id, flow_id = self._SetupClientAndFlow(
        parent_hunt_id=hunt_obj.hunt_id)
    processing_time = rdfvalue.Duration("60s")

    with self.assertRaises(db.ParentHuntIsNotRunningError):
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

    self.db.UpdateHuntObject(
        hunt_obj.hunt_id, hunt_state=rdf_hunt_objects.Hunt.HuntState.COMPLETED)

    with self.assertRaises(db.ParentHuntIsNotRunningError):
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

    self.db.UpdateHuntObject(
        hunt_obj.hunt_id, hunt_state=rdf_hunt_objects.Hunt.HuntState.STARTED)

    # Should work again.
    self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

  def testLeaseFlowForProcessingThatIsAlreadyBeingProcessed(self):
    client_id, flow_id = self._SetupClientAndFlow()
    processing_time = rdfvalue.Duration("60s")

    flow_for_processing = self.db.LeaseFlowForProcessing(
        client_id, flow_id, processing_time)

    # Already marked as being processed.
    with self.assertRaises(ValueError):
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

    self.db.ReleaseProcessedFlow(flow_for_processing)

    # Should work again.
    self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

  def testLeaseFlowForProcessingAfterProcessingTimeExpiration(self):
    client_id, flow_id = self._SetupClientAndFlow()
    processing_time = rdfvalue.Duration("60s")
    now = rdfvalue.RDFDatetime.Now()

    with test_lib.FakeTime(now):
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

    # Already marked as being processed.
    with self.assertRaises(ValueError):
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

    after_deadline = now + processing_time + rdfvalue.Duration("1s")
    with test_lib.FakeTime(after_deadline):
      # Should work again.
      self.db.LeaseFlowForProcessing(client_id, flow_id, processing_time)

  def testLeaseFlowForProcessingUpdatesHuntCounters(self):
    hunt_obj = rdf_hunt_objects.Hunt(description="foo")
    self.db.WriteHuntObject(hunt_obj)
    hunt_id = hunt_obj.hunt_id

    processing_time = rdfvalue.Duration("60s")

    client_id, flow_id = self._SetupClientAndFlow(parent_hunt_id=hunt_id)
    flow_for_processing = self.db.LeaseFlowForProcessing(
        client_id, flow_id, processing_time)
    flow_for_processing.num_replies_sent = 10
    sample_results = [
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            hunt_id=hunt_id,
            payload=rdf_client.ClientSummary(client_id=client_id))
    ] * 10
    self._WriteFlowResults(sample_results)

    self.assertTrue(self.db.ReleaseProcessedFlow(flow_for_processing))

    counters = self.db.ReadHuntCounters(hunt_id)
    self.assertEqual(counters.num_clients_with_results, 1)
    self.assertEqual(counters.num_results, 10)

  def testLeaseFlowForProcessingUpdatesFlowObjects(self):
    client_id, flow_id = self._SetupClientAndFlow()

    now = rdfvalue.RDFDatetime.Now()
    processing_time = rdfvalue.Duration("60s")
    processing_deadline = now + processing_time

    with test_lib.FakeTime(now):
      flow_for_processing = self.db.LeaseFlowForProcessing(
          client_id, flow_id, processing_time)

    self.assertEqual(flow_for_processing.processing_on, utils.ProcessIdString())
    self.assertEqual(flow_for_processing.processing_since, now)
    self.assertEqual(flow_for_processing.processing_deadline,
                     processing_deadline)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.processing_on, utils.ProcessIdString())
    self.assertEqual(read_flow.processing_since, now)
    self.assertEqual(read_flow.processing_deadline, processing_deadline)
    self.assertEqual(read_flow.num_replies_sent, 0)

    flow_for_processing.next_request_to_process = 5
    flow_for_processing.num_replies_sent = 10

    self.assertTrue(self.db.ReleaseProcessedFlow(flow_for_processing))
    # Check that returning the flow doesn't change the flow object.
    self.assertEqual(read_flow.processing_on, utils.ProcessIdString())
    self.assertEqual(read_flow.processing_since, now)
    self.assertEqual(read_flow.processing_deadline, processing_deadline)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertFalse(read_flow.processing_on)
    self.assertIsNone(read_flow.processing_since)
    self.assertIsNone(read_flow.processing_deadline)
    self.assertEqual(read_flow.next_request_to_process, 5)
    self.assertEqual(read_flow.num_replies_sent, 10)

  def testFlowLastUpateTime(self):
    processing_time = rdfvalue.Duration("60s")

    t0 = rdfvalue.RDFDatetime.Now()
    client_id, flow_id = self._SetupClientAndFlow()
    t1 = rdfvalue.RDFDatetime.Now()

    read_flow = self.db.ReadFlowObject(client_id, flow_id)

    self.assertBetween(read_flow.last_update_time, t0, t1)

    flow_for_processing = self.db.LeaseFlowForProcessing(
        client_id, flow_id, processing_time)
    self.assertBetween(flow_for_processing.last_update_time, t0, t1)

    t2 = rdfvalue.RDFDatetime.Now()
    self.db.ReleaseProcessedFlow(flow_for_processing)
    t3 = rdfvalue.RDFDatetime.Now()

    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertBetween(read_flow.last_update_time, t2, t3)

  def testReleaseProcessedFlow(self):
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=1)

    processing_time = rdfvalue.Duration("60s")

    processed_flow = self.db.LeaseFlowForProcessing(client_id, flow_id,
                                                    processing_time)

    # Let's say we processed one request on this flow.
    processed_flow.next_request_to_process = 2

    # There are some requests ready for processing but not #2.
    self.db.WriteFlowRequests([
        rdf_flow_objects.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=1,
            needs_processing=True),
        rdf_flow_objects.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=4,
            needs_processing=True)
    ])

    self.assertTrue(self.db.ReleaseProcessedFlow(processed_flow))

    processed_flow = self.db.LeaseFlowForProcessing(client_id, flow_id,
                                                    processing_time)
    # And another one.
    processed_flow.next_request_to_process = 3

    # But in the meantime, request 3 is ready for processing.
    self.db.WriteFlowRequests([
        rdf_flow_objects.FlowRequest(
            client_id=client_id,
            flow_id=flow_id,
            request_id=3,
            needs_processing=True)
    ])

    self.assertFalse(self.db.ReleaseProcessedFlow(processed_flow))

  def testReadChildFlows(self):
    client_id = u"C.1234567890123456"
    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            flow_id=u"00000001",
            client_id=client_id,
            create_time=rdfvalue.RDFDatetime.Now()))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            flow_id=u"00000002",
            client_id=client_id,
            parent_flow_id=u"00000001",
            create_time=rdfvalue.RDFDatetime.Now()))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            flow_id=u"00000003",
            client_id=client_id,
            parent_flow_id=u"00000002",
            create_time=rdfvalue.RDFDatetime.Now()))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            flow_id=u"00000004",
            client_id=client_id,
            parent_flow_id=u"00000001",
            create_time=rdfvalue.RDFDatetime.Now()))

    # This one is completely unrelated (different client id).
    self.db.WriteClientMetadata(u"C.1234567890123457", fleetspeak_enabled=False)
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            flow_id=u"00000002",
            client_id=u"C.1234567890123457",
            parent_flow_id=u"00000001",
            create_time=rdfvalue.RDFDatetime.Now()))

    children = self.db.ReadChildFlowObjects(client_id, u"00000001")

    self.assertLen(children, 2)
    for c in children:
      self.assertEqual(c.parent_flow_id, u"00000001")

    children = self.db.ReadChildFlowObjects(client_id, u"00000002")
    self.assertLen(children, 1)
    self.assertEqual(children[0].parent_flow_id, u"00000002")
    self.assertEqual(children[0].flow_id, u"00000003")

    children = self.db.ReadChildFlowObjects(client_id, u"00000003")
    self.assertEmpty(children)

  def _WriteRequestAndResponses(self, client_id, flow_id):
    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id,
        flow_id=flow_id,
        create_time=rdfvalue.RDFDatetime.Now())
    self.db.WriteFlowObject(rdf_flow)

    for request_id in range(1, 4):
      request = rdf_flow_objects.FlowRequest(
          client_id=client_id, flow_id=flow_id, request_id=request_id)
      self.db.WriteFlowRequests([request])

      for response_id in range(1, 3):
        response = rdf_flow_objects.FlowResponse(
            client_id=client_id,
            flow_id=flow_id,
            request_id=request_id,
            response_id=response_id)
        self.db.WriteFlowResponses([response])

  def _CheckRequestsAndResponsesAreThere(self, client_id, flow_id):
    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertLen(all_requests, 3)
    for _, responses in all_requests:
      self.assertLen(responses, 2)

  def testDeleteAllFlowRequestsAndResponses(self):
    client_id1 = u"C.1234567890123456"
    client_id2 = u"C.1234567890123457"
    flow_id1 = u"1234ABCD"
    flow_id2 = u"1234ABCE"

    self.db.WriteClientMetadata(client_id1, fleetspeak_enabled=True)
    self.db.WriteClientMetadata(client_id2, fleetspeak_enabled=True)

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

  def testDeleteAllFlowRequestsAndResponsesWithClientRequests(self):
    client_id = u"C.1234567890123456"
    flow_id = u"1234ABCD"

    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=True)

    self._WriteRequestAndResponses(client_id, flow_id)

    req = rdf_flows.ClientActionRequest(
        client_id=client_id, flow_id=flow_id, request_id=1)
    self.db.WriteClientActionRequests([req])

    self._CheckRequestsAndResponsesAreThere(client_id, flow_id)

    self.db.DeleteAllFlowRequestsAndResponses(client_id, flow_id)

    self.assertEmpty(
        self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id))

  def testReadFlowRequestsReadyForProcessing(self):
    client_id = u"C.1234567890000000"
    flow_id = u"12344321"

    requests_for_processing = self.db.ReadFlowRequestsReadyForProcessing(
        client_id, flow_id, next_needed_request=1)
    self.assertEqual(requests_for_processing, {})

    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=3)

    for request_id in [1, 3, 4, 5, 7]:
      request = rdf_flow_objects.FlowRequest(
          client_id=client_id,
          flow_id=flow_id,
          request_id=request_id,
          needs_processing=True)
      self.db.WriteFlowRequests([request])

    # Request 4 has some responses.
    responses = [
        rdf_flow_objects.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=4, response_id=i)
        for i in range(3)
    ]
    self.db.WriteFlowResponses(responses)

    requests_for_processing = self.db.ReadFlowRequestsReadyForProcessing(
        client_id, flow_id, next_needed_request=3)

    # We expect three requests here. Req #1 is old and should not be there, req
    # #7 can't be processed since we are missing #6 in between. That leaves
    # requests #3, #4 and #5.
    self.assertLen(requests_for_processing, 3)
    self.assertEqual(list(requests_for_processing), [3, 4, 5])

    for request_id in requests_for_processing:
      request, _ = requests_for_processing[request_id]
      self.assertEqual(request_id, request.request_id)

    self.assertEqual(requests_for_processing[4][1], responses)

  def testFlowProcessingRequestsQueue(self):
    flow_ids = []
    for _ in range(5):
      client_id, flow_id = self._SetupClientAndFlow()
      flow_ids.append(flow_id)

    request_queue = queue.Queue()

    def Callback(request):
      self.db.AckFlowProcessingRequests([request])
      request_queue.put(request)

    self.db.RegisterFlowProcessingHandler(Callback)
    self.addCleanup(self.db.UnregisterFlowProcessingHandler)

    requests = []
    for flow_id in flow_ids:
      requests.append(
          rdf_flows.FlowProcessingRequest(client_id=client_id, flow_id=flow_id))

    self.db.WriteFlowProcessingRequests(requests)

    got = []
    while len(got) < 5:
      try:
        l = request_queue.get(True, timeout=6)
      except queue.Empty:
        self.fail("Timed out waiting for messages, expected 5, got %d" %
                  len(got))
      got.append(l)

    self.assertCountEqual(requests, got)

  def testFlowProcessingRequestsQueueWithDelay(self):
    flow_ids = []
    for _ in range(5):
      client_id, flow_id = self._SetupClientAndFlow()
      flow_ids.append(flow_id)

    request_queue = queue.Queue()

    def Callback(request):
      self.db.AckFlowProcessingRequests([request])
      request_queue.put(request)

    self.db.RegisterFlowProcessingHandler(Callback)
    self.addCleanup(self.db.UnregisterFlowProcessingHandler)

    now = rdfvalue.RDFDatetime.Now()
    delivery_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
        now.AsSecondsSinceEpoch() + 0.5)
    requests = []
    for flow_id in flow_ids:
      requests.append(
          rdf_flows.FlowProcessingRequest(
              client_id=client_id, flow_id=flow_id,
              delivery_time=delivery_time))

    self.db.WriteFlowProcessingRequests(requests)

    got = []
    while len(got) < 5:
      try:
        l = request_queue.get(True, timeout=6)
      except queue.Empty:
        self.fail("Timed out waiting for messages, expected 5, got %d" %
                  len(got))
      got.append(l)
      self.assertGreater(rdfvalue.RDFDatetime.Now(), l.delivery_time)

    self.assertCountEqual(requests, got)

    leftover = self.db.ReadFlowProcessingRequests()
    self.assertEqual(leftover, [])

  def testAcknowledgingFlowProcessingRequestsWorks(self):
    flow_ids = []
    for _ in range(5):
      client_id, flow_id = self._SetupClientAndFlow()
      flow_ids.append(flow_id)
    flow_ids.sort()

    now = rdfvalue.RDFDatetime.Now()
    delivery_time = now + rdfvalue.Duration("10m")
    requests = []
    for flow_id in flow_ids:
      requests.append(
          rdf_flows.FlowProcessingRequest(
              client_id=client_id, flow_id=flow_id,
              delivery_time=delivery_time))

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
    self.assertCountEqual([r.flow_id for r in stored_requests],
                          [flow_ids[0], flow_ids[3], flow_ids[4]])

    # Make sure DeleteAllFlowProcessingRequests removes all requests.
    self.db.DeleteAllFlowProcessingRequests()
    self.assertEqual(self.db.ReadFlowProcessingRequests(), [])

    self.db.UnregisterFlowProcessingHandler()

  def _SampleResults(self, client_id, flow_id, hunt_id=None):
    sample_results = []
    for i in range(10):
      sample_results.append(
          rdf_flow_objects.FlowResult(
              client_id=client_id,
              flow_id=flow_id,
              hunt_id=hunt_id,
              tag="tag_%d" % i,
              payload=rdf_client.ClientSummary(
                  client_id=client_id,
                  system_manufacturer="manufacturer_%d" % i,
                  install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10 +
                                                                          i))))

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

  def testWritesAndCounts40001FlowResults(self):
    client_id, flow_id = self._SetupClientAndFlow()
    sample_results = [
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            payload=rdf_client.ClientSummary(client_id=client_id))
    ] * 40001

    self.db.WriteFlowResults(sample_results)

    result_count = self.db.CountFlowResults(client_id, flow_id)
    self.assertEqual(result_count, 40001)

  def testWritesAndReadsSingleFlowResultOfSingleType(self):
    client_id, flow_id = self._SetupClientAndFlow()
    sample_result = rdf_flow_objects.FlowResult(
        client_id=client_id,
        flow_id=flow_id,
        payload=rdf_client.ClientSummary(client_id=client_id))

    with test_lib.FakeTime(42):
      self.db.WriteFlowResults([sample_result])

    results = self.db.ReadFlowResults(client_id, flow_id, 0, 100)
    self.assertLen(results, 1)
    self.assertEqual(results[0].payload, sample_result.payload)
    self.assertEqual(results[0].timestamp.AsSecondsSinceEpoch(), 42)

  def testWritesAndReadsMultipleFlowResultsOfSingleType(self):
    client_id, flow_id = self._SetupClientAndFlow()
    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id))

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
    client_id, flow_id = self._SetupClientAndFlow()
    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True)

    results = self.db.ReadFlowResults(client_id, flow_id, 0, 100)
    self.assertLen(results, len(sample_results))

    # Returned results have to be sorted by the timestamp in the ascending
    # order.
    self.assertEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results],
    )

  def testWritesAndReadsMultipleFlowResultsOfMultipleTypes(self):
    client_id, flow_id = self._SetupClientAndFlow()

    sample_results = self._WriteFlowResults(sample_results=[
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            payload=rdf_client.ClientSummary(
                client_id=client_id,
                install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10 +
                                                                        i)))
        for i in range(10)
    ])
    sample_results.extend(
        self._WriteFlowResults(sample_results=[
            rdf_flow_objects.FlowResult(
                client_id=client_id,
                flow_id=flow_id,
                payload=rdf_client.ClientCrash(
                    client_id=client_id,
                    timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10 +
                                                                         i)))
            for i in range(10)
        ]))
    sample_results.extend(
        self._WriteFlowResults(sample_results=[
            rdf_flow_objects.FlowResult(
                client_id=client_id,
                flow_id=flow_id,
                payload=rdf_client.ClientInformation(client_version=i))
            for i in range(10)
        ]))

    results = self.db.ReadFlowResults(client_id, flow_id, 0, 100)
    self.assertLen(results, len(sample_results))

    self.assertCountEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results],
    )

  def testReadFlowResultsCorrectlyAppliesOffsetAndCountFilters(self):
    client_id, flow_id = self._SetupClientAndFlow()
    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True)

    for l in range(1, 11):
      for i in range(10):
        results = self.db.ReadFlowResults(client_id, flow_id, i, l)
        expected = sample_results[i:i + l]

        result_payloads = [x.payload for x in results]
        expected_payloads = [x.payload for x in expected]
        self.assertEqual(
            result_payloads, expected_payloads,
            "Results differ from expected (from %d, size %d): %s vs %s" %
            (i, l, result_payloads, expected_payloads))

  def testReadFlowResultsCorrectlyAppliesWithTagFilter(self):
    client_id, flow_id = self._SetupClientAndFlow()
    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True)

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_tag="blah")
    self.assertFalse(results)

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_tag="tag")
    self.assertFalse(results)

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_tag="tag_1")
    self.assertEqual([i.payload for i in results], [sample_results[1].payload])

  def testReadFlowResultsCorrectlyAppliesWithTypeFilter(self):
    client_id, flow_id = self._SetupClientAndFlow()
    sample_results = self._WriteFlowResults(sample_results=[
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            payload=rdf_client.ClientSummary(
                client_id=client_id,
                install_date=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10 +
                                                                        i)))
        for i in range(10)
    ])
    sample_results.extend(
        self._WriteFlowResults(sample_results=[
            rdf_flow_objects.FlowResult(
                client_id=client_id,
                flow_id=flow_id,
                payload=rdf_client.ClientCrash(
                    client_id=client_id,
                    timestamp=rdfvalue.RDFDatetime.FromSecondsSinceEpoch(10 +
                                                                         i)))
            for i in range(10)
        ]))

    results = self.db.ReadFlowResults(
        client_id,
        flow_id,
        0,
        100,
        with_type=compatibility.GetName(rdf_client.ClientInformation))
    self.assertFalse(results)

    results = self.db.ReadFlowResults(
        client_id,
        flow_id,
        0,
        100,
        with_type=compatibility.GetName(rdf_client.ClientSummary))
    self.assertCountEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results[:10]],
    )

  def testReadFlowResultsCorrectlyAppliesWithSubstringFilter(self):
    client_id, flow_id = self._SetupClientAndFlow()
    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True)

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_substring="blah")
    self.assertFalse(results)

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_substring="manufacturer")
    self.assertEqual(
        [i.payload for i in results],
        [i.payload for i in sample_results],
    )

    results = self.db.ReadFlowResults(
        client_id, flow_id, 0, 100, with_substring="manufacturer_1")
    self.assertEqual([i.payload for i in results], [sample_results[1].payload])

  def testReadFlowResultsCorrectlyAppliesVariousCombinationsOfFilters(self):
    client_id, flow_id = self._SetupClientAndFlow()
    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True)

    tags = {"tag_1": set([sample_results[1]])}
    substrings = {
        "manufacturer": set(sample_results),
        "manufacturer_1": set([sample_results[1]])
    }
    types = {
        compatibility.GetName(rdf_client.ClientSummary): set(sample_results)
    }

    no_tag = [(None, set(sample_results))]

    for tag_value, tag_expected in itertools.chain(tags.items(), no_tag):
      for substring_value, substring_expected in itertools.chain(
          substrings.items(), no_tag):
        for type_value, type_expected in itertools.chain(types.items(), no_tag):
          expected = tag_expected & substring_expected & type_expected
          results = self.db.ReadFlowResults(
              client_id,
              flow_id,
              0,
              100,
              with_tag=tag_value,
              with_type=type_value,
              with_substring=substring_value)

          self.assertCountEqual(
              [i.payload for i in expected], [i.payload for i in results],
              "Result items do not match for "
              "(tag=%s, type=%s, substring=%s): %s vs %s" %
              (tag_value, type_value, substring_value, expected, results))

  def testReadFlowResultsReturnsPayloadWithMissingTypeAsSpecialValue(self):
    client_id, flow_id = self._SetupClientAndFlow()
    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True)

    type_name = compatibility.GetName(rdf_client.ClientSummary)
    try:
      cls = rdfvalue.RDFValue.classes.pop(type_name)

      results = self.db.ReadFlowResults(client_id, flow_id, 0, 100)
    finally:
      rdfvalue.RDFValue.classes[type_name] = cls

    self.assertLen(sample_results, len(results))
    for r in results:
      self.assertIsInstance(r.payload,
                            rdf_objects.SerializedValueOfUnrecognizedType)
      self.assertEqual(r.payload.type_name, type_name)

  def testCountFlowResultsReturnsCorrectResultsCount(self):
    client_id, flow_id = self._SetupClientAndFlow()
    sample_results = self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True)

    num_results = self.db.CountFlowResults(client_id, flow_id)
    self.assertEqual(num_results, len(sample_results))

  def testCountFlowResultsCorrectlyAppliesWithTagFilter(self):
    client_id, flow_id = self._SetupClientAndFlow()
    self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True)

    num_results = self.db.CountFlowResults(client_id, flow_id, with_tag="blah")
    self.assertEqual(num_results, 0)

    num_results = self.db.CountFlowResults(client_id, flow_id, with_tag="tag_1")
    self.assertEqual(num_results, 1)

  def testCountFlowResultsCorrectlyAppliesWithTypeFilter(self):
    client_id, flow_id = self._SetupClientAndFlow()
    self._WriteFlowResults(sample_results=[
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            payload=rdf_client.ClientSummary(client_id=client_id))
        for _ in range(10)
    ])
    self._WriteFlowResults(sample_results=[
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            payload=rdf_client.ClientCrash(client_id=client_id))
        for _ in range(10)
    ])

    num_results = self.db.CountFlowResults(
        client_id,
        flow_id,
        with_type=compatibility.GetName(rdf_client.ClientInformation))
    self.assertEqual(num_results, 0)

    num_results = self.db.CountFlowResults(
        client_id,
        flow_id,
        with_type=compatibility.GetName(rdf_client.ClientSummary))
    self.assertEqual(num_results, 10)

    num_results = self.db.CountFlowResults(
        client_id,
        flow_id,
        with_type=compatibility.GetName(rdf_client.ClientCrash))
    self.assertEqual(num_results, 10)

  def testCountFlowResultsCorrectlyAppliesWithTagAndWithTypeFilters(self):
    client_id, flow_id = self._SetupClientAndFlow()
    self._WriteFlowResults(
        self._SampleResults(client_id, flow_id), multiple_timestamps=True)

    num_results = self.db.CountFlowResults(
        client_id,
        flow_id,
        with_tag="tag_1",
        with_type=compatibility.GetName(rdf_client.ClientSummary))
    self.assertEqual(num_results, 1)

  def testCountFlowResultsByTypeReturnsCorrectNumbers(self):
    client_id, flow_id = self._SetupClientAndFlow()
    sample_results = self._WriteFlowResults(sample_results=[
        rdf_flow_objects.FlowResult(
            client_id=client_id,
            flow_id=flow_id,
            payload=rdf_client.ClientSummary(client_id=client_id))
    ] * 3)
    sample_results.extend(
        self._WriteFlowResults(sample_results=[
            rdf_flow_objects.FlowResult(
                client_id=client_id,
                flow_id=flow_id,
                payload=rdf_client.ClientCrash(client_id=client_id))
        ] * 5))

    counts_by_type = self.db.CountFlowResultsByType(client_id, flow_id)
    self.assertEqual(counts_by_type, {
        "ClientSummary": 3,
        "ClientCrash": 5,
    })

  def testWritesAndReadsSingleFlowLogEntry(self):
    client_id, flow_id = self._SetupClientAndFlow()
    message = "blah: ٩(͡๏̯͡๏)۶"

    self.db.WriteFlowLogEntries([
        rdf_flow_objects.FlowLogEntry(
            client_id=client_id, flow_id=flow_id, message=message)
    ])

    entries = self.db.ReadFlowLogEntries(client_id, flow_id, 0, 100)
    self.assertLen(entries, 1)
    self.assertEqual(entries[0].message, message)

  def _WriteFlowLogEntries(self, client_id, flow_id):
    messages = ["blah_%d" % i for i in range(10)]
    for message in messages:
      self.db.WriteFlowLogEntries([
          rdf_flow_objects.FlowLogEntry(
              client_id=client_id, flow_id=flow_id, message=message)
      ])

    return messages

  def testWritesAndReadsMultipleFlowLogEntries(self):
    client_id, flow_id = self._SetupClientAndFlow()
    messages = self._WriteFlowLogEntries(client_id, flow_id)

    entries = self.db.ReadFlowLogEntries(client_id, flow_id, 0, 100)
    self.assertEqual([e.message for e in entries], messages)

  def testReadFlowLogEntriesCorrectlyAppliesOffsetAndCountFilters(self):
    client_id, flow_id = self._SetupClientAndFlow()
    messages = self._WriteFlowLogEntries(client_id, flow_id)

    for i in range(10):
      for size in range(1, 10):
        entries = self.db.ReadFlowLogEntries(client_id, flow_id, i, size)
        self.assertEqual([e.message for e in entries], messages[i:i + size])

  def testReadFlowLogEntriesCorrectlyAppliesWithSubstringFilter(self):
    client_id, flow_id = self._SetupClientAndFlow()
    messages = self._WriteFlowLogEntries(client_id, flow_id)

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 0, 100, with_substring="foobar")
    self.assertFalse(entries)

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 0, 100, with_substring="blah")
    self.assertEqual([e.message for e in entries], messages)

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 0, 100, with_substring="blah_1")
    self.assertEqual([e.message for e in entries], [messages[1]])

  def testReadFlowLogEntriesCorrectlyAppliesVariousCombinationsOfFilters(self):
    client_id, flow_id = self._SetupClientAndFlow()
    messages = self._WriteFlowLogEntries(client_id, flow_id)

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 0, 100, with_substring="foobar")
    self.assertFalse(entries)

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 1, 2, with_substring="blah")
    self.assertEqual([e.message for e in entries], [messages[1], messages[2]])

    entries = self.db.ReadFlowLogEntries(
        client_id, flow_id, 0, 1, with_substring="blah_1")
    self.assertEqual([e.message for e in entries], [messages[1]])

  def testCountFlowLogEntriesReturnsCorrectFlowLogEntriesCount(self):
    client_id, flow_id = self._SetupClientAndFlow()
    messages = self._WriteFlowLogEntries(client_id, flow_id)

    num_entries = self.db.CountFlowLogEntries(client_id, flow_id)
    self.assertEqual(num_entries, len(messages))

  def testFlowLogsAndErrorsForUnknownFlowsRaise(self):
    client_id = u"C.1234567890123456"
    flow_id = flow.RandomFlowId()
    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    with self.assertRaises(db.AtLeastOneUnknownFlowError):
      self.db.WriteFlowLogEntries([
          rdf_flow_objects.FlowLogEntry(
              client_id=client_id, flow_id=flow_id, message="test")
      ])

  def _WriteFlowOutputPluginLogEntries(self, client_id, flow_id,
                                       output_plugin_id):
    entries = []
    for i in range(10):
      message = "blah_🚀_%d" % i
      enum = rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType
      if i % 3 == 0:
        log_entry_type = enum.ERROR
      else:
        log_entry_type = enum.LOG

      entry = rdf_flow_objects.FlowOutputPluginLogEntry(
          client_id=client_id,
          flow_id=flow_id,
          output_plugin_id=output_plugin_id,
          message=message,
          log_entry_type=log_entry_type)
      entries.append(entry)

      self.db.WriteFlowOutputPluginLogEntries([entry])

    return entries

  def testFlowOutputPluginLogEntriesCanBeWrittenAndThenRead(self):
    client_id, flow_id = self._SetupClientAndFlow()
    output_plugin_id = "1"

    written_entries = self._WriteFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id)
    read_entries = self.db.ReadFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id, 0, 100)

    self.assertEqual(len(written_entries), len(read_entries))
    self.assertEqual([e.message for e in written_entries],
                     [e.message for e in read_entries])

  def testFlowOutputPluginLogEntryWith1MbMessageCanBeWrittenAndThenRead(self):
    client_id, flow_id = self._SetupClientAndFlow()
    output_plugin_id = "1"

    entry = rdf_flow_objects.FlowOutputPluginLogEntry(
        client_id=client_id,
        flow_id=flow_id,
        output_plugin_id=output_plugin_id,
        message="x" * 1024 * 1024,
        log_entry_type=rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType
        .LOG)

    self.db.WriteFlowOutputPluginLogEntries([entry])
    read_entries = self.db.ReadFlowOutputPluginLogEntries(
        client_id, flow_id, output_plugin_id, 0, 100)

    self.assertLen(read_entries, 1)
    self.assertEqual(read_entries[0].message, entry.message)

  def testFlowOutputPluginLogEntriesCanBeReadWithTypeFilter(self):
    client_id, flow_id = self._SetupClientAndFlow()
    output_plugin_id = "1"

    self._WriteFlowOutputPluginLogEntries(client_id, flow_id, output_plugin_id)

    read_entries = self.db.ReadFlowOutputPluginLogEntries(
        client_id,
        flow_id,
        output_plugin_id,
        0,
        100,
        with_type=rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.ERROR)
    self.assertEqual(len(read_entries), 4)

    read_entries = self.db.ReadFlowOutputPluginLogEntries(
        client_id,
        flow_id,
        output_plugin_id,
        0,
        100,
        with_type=rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.LOG)
    self.assertEqual(len(read_entries), 6)

  def testReadFlowOutputPluginLogEntriesCorrectlyAppliesOffsetCounter(self):
    client_id, flow_id = self._SetupClientAndFlow()
    output_plugin_id = "1"

    entries = self._WriteFlowOutputPluginLogEntries(client_id, flow_id,
                                                    output_plugin_id)

    for l in range(1, 11):
      for i in range(10):
        results = self.db.ReadFlowOutputPluginLogEntries(
            client_id, flow_id, output_plugin_id, i, l)
        expected = entries[i:i + l]

        result_messages = [x.message for x in results]
        expected_messages = [x.message for x in expected]
        self.assertEqual(
            result_messages, expected_messages,
            "Results differ from expected (from %d, size %d): %s vs %s" %
            (i, l, result_messages, expected_messages))

  def testReadFlowOutputPluginLogEntriesAppliesOffsetCounterWithType(self):
    client_id, flow_id = self._SetupClientAndFlow()
    output_plugin_id = "1"

    entries = self._WriteFlowOutputPluginLogEntries(client_id, flow_id,
                                                    output_plugin_id)

    for l in range(1, 11):
      for i in range(10):
        for with_type in [
            rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.LOG,
            rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.ERROR
        ]:
          results = self.db.ReadFlowOutputPluginLogEntries(
              client_id, flow_id, output_plugin_id, i, l, with_type=with_type)
          expected = [e for e in entries if e.log_entry_type == with_type
                     ][i:i + l]

          result_messages = [x.message for x in results]
          expected_messages = [x.message for x in expected]
          self.assertEqual(
              result_messages, expected_messages,
              "Results differ from expected (from %d, size %d): %s vs %s" %
              (i, l, result_messages, expected_messages))

  def testFlowOutputPluginLogEntriesCanBeCountedPerPlugin(self):
    client_id, flow_id = self._SetupClientAndFlow()

    output_plugin_id_1 = "1"
    self._WriteFlowOutputPluginLogEntries(client_id, flow_id,
                                          output_plugin_id_1)

    output_plugin_id_2 = "2"
    self._WriteFlowOutputPluginLogEntries(client_id, flow_id,
                                          output_plugin_id_2)

    self.assertEqual(
        self.db.CountFlowOutputPluginLogEntries(client_id, flow_id,
                                                output_plugin_id_1), 10)
    self.assertEqual(
        self.db.CountFlowOutputPluginLogEntries(client_id, flow_id,
                                                output_plugin_id_2), 10)

  def testCountFlowOutputPluginLogEntriesRespectsWithTypeFilter(self):
    client_id, flow_id = self._SetupClientAndFlow()

    output_plugin_id = "1"
    self._WriteFlowOutputPluginLogEntries(client_id, flow_id, output_plugin_id)

    self.assertEqual(
        self.db.CountFlowOutputPluginLogEntries(
            client_id,
            flow_id,
            output_plugin_id,
            with_type=rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType.LOG
        ),
        6,
    )
    self.assertEqual(
        self.db.CountFlowOutputPluginLogEntries(
            client_id,
            flow_id,
            output_plugin_id,
            with_type=rdf_flow_objects.FlowOutputPluginLogEntry.LogEntryType
            .ERROR),
        4,
    )


# This file is a test library and thus does not require a __main__ block.
