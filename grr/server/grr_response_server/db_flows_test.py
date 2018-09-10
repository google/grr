#!/usr/bin/env python
"""Tests for the flow database api."""

import Queue
import random

from builtins import range  # pylint: disable=redefined-builtin
from future.utils import iteritems
import mock

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import db
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr.test_lib import test_lib


class DatabaseTestFlowMixin(object):
  """An abstract class for testing db.Database implementations.

  This mixin adds methods to test the handling of flows.
  """

  def _SetupClientAndFlow(self, **additional_flow_args):
    flow_id = u"1234ABCD"
    client_id = u"C.1234567890123456"

    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    rdf_flow = rdf_flow_objects.Flow(
        client_id=client_id, flow_id=flow_id, **additional_flow_args)
    self.db.WriteFlowObject(rdf_flow)

    return client_id, flow_id

  def testClientMessageStorage(self):

    client_id = self.InitializeClient()
    msg = rdf_flows.GrrMessage(queue=client_id, generate_task_id=True)

    self.db.WriteClientMessages([msg])

    read_msgs = self.db.ReadClientMessages(client_id)
    self.assertEqual(len(read_msgs), 1)
    self.assertEqual(msg, read_msgs[0])

    self.db.DeleteClientMessages([msg])
    read_msgs = self.db.ReadClientMessages(client_id)
    self.assertEqual(len(read_msgs), 0)

    # Extra delete should not raise.
    self.db.DeleteClientMessages([msg])

    # Deleting the same message multiple times is an error.
    with self.assertRaises(ValueError):
      self.db.DeleteClientMessages([msg, msg])

  def testClientMessageUpdate(self):
    client_id = self.InitializeClient()
    msg = rdf_flows.GrrMessage(queue=client_id, generate_task_id=True)

    ttl = msg.ttl
    self.assertGreater(ttl, 5)

    for _ in range(5):
      msg.ttl -= 1
      self.db.WriteClientMessages([msg])
      read_msgs = self.db.ReadClientMessages(client_id)
      self.assertEqual(len(read_msgs), 1)
      self.assertEqual(msg, read_msgs[0])

  def testClientMessageLeasing(self):

    client_id = self.InitializeClient()
    messages = [
        rdf_flows.GrrMessage(queue=client_id, generate_task_id=True)
        for _ in range(10)
    ]
    lease_time = rdfvalue.Duration("5m")

    self.db.WriteClientMessages(messages)

    t0 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000)
    with test_lib.FakeTime(t0):
      t0_expiry = t0 + lease_time
      leased = self.db.LeaseClientMessages(
          client_id, lease_time=lease_time, limit=5)

      self.assertEqual(len(leased), 5)

      for request in leased:
        self.assertEqual(request.leased_until, t0_expiry)
        self.assertEqual(request.leased_by, utils.ProcessIdString())

    t1 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 100)
    with test_lib.FakeTime(t1):
      t1_expiry = t1 + lease_time
      leased = self.db.LeaseClientMessages(
          client_id, lease_time=lease_time, limit=5)

      self.assertEqual(len(leased), 5)

      for request in leased:
        self.assertEqual(request.leased_until, t1_expiry)
        self.assertEqual(request.leased_by, utils.ProcessIdString())

      # Nothing left to lease.
      leased = self.db.LeaseClientMessages(
          client_id, lease_time=lease_time, limit=2)

      self.assertEqual(len(leased), 0)

    read = self.db.ReadClientMessages(client_id)

    self.assertEqual(len(read), 10)
    for r in read:
      self.assertEqual(r.leased_by, utils.ProcessIdString())

    self.assertEqual(len([r for r in read if r.leased_until == t0_expiry]), 5)
    self.assertEqual(len([r for r in read if r.leased_until == t1_expiry]), 5)

    # Half the leases expired.
    t2 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 350)
    with test_lib.FakeTime(t2):
      leased = self.db.LeaseClientMessages(client_id, lease_time=lease_time)

      self.assertEqual(len(leased), 5)

    # All of them expired.
    t3 = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100000 + 10350)
    with test_lib.FakeTime(t3):
      leased = self.db.LeaseClientMessages(client_id, lease_time=lease_time)

      self.assertEqual(len(leased), 10)

  def testClientMessagesAreSorted(self):
    client_id = self.InitializeClient()
    messages = [
        rdf_flows.GrrMessage(queue=client_id, generate_task_id=True)
        for _ in range(10)
    ]

    random.shuffle(messages)

    self.db.WriteClientMessages(messages)

    read = self.db.ReadClientMessages(client_id)

    self.assertEqual(len(read), 10)
    task_ids = [m.task_id for m in read]
    self.assertEqual(task_ids, sorted(task_ids))

    lease_time = rdfvalue.Duration("10m")
    leased = self.db.LeaseClientMessages(client_id, lease_time=lease_time)
    task_ids = [m.task_id for m in leased]
    self.assertEqual(task_ids, sorted(task_ids))

  def testFlowWritingUnknownClient(self):
    flow_id = u"1234ABCD"
    client_id = u"C.1234567890123456"

    rdf_flow = rdf_flow_objects.Flow(client_id=client_id, flow_id=flow_id)

    with self.assertRaises(db.UnknownClientError):
      self.db.WriteFlowObject(rdf_flow)

  def testFlowWriting(self):
    flow_id = u"1234ABCD"
    client_id = u"C.1234567890123456"

    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    rdf_flow = rdf_flow_objects.Flow(client_id=client_id, flow_id=flow_id)
    self.db.WriteFlowObject(rdf_flow)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)

    self.assertEqual(read_flow, rdf_flow)

    # Invalid flow id or client id raises.
    with self.assertRaises(db.UnknownFlowError):
      self.db.ReadFlowObject(client_id, u"1234AAAA")

    with self.assertRaises(db.UnknownFlowError):
      self.db.ReadFlowObject(u"C.1234567890000000", flow_id)

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

  def testRequestWriting(self):
    client_id_1 = u"C.1234567890123456"
    client_id_2 = u"C.1234567890123457"
    flow_id_1 = u"1234ABCD"
    flow_id_2 = u"ABCD1234"

    with self.assertRaises(db.UnknownFlowError):
      self.db.WriteFlowRequests([
          rdf_flow_objects.FlowRequest(
              client_id=client_id_1, flow_id=flow_id_1)
      ])
    for client_id in [client_id_1, client_id_2]:
      self.db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    requests = []
    for flow_id in [flow_id_1, flow_id_2]:
      for client_id in [client_id_1, client_id_2]:
        rdf_flow = rdf_flow_objects.Flow(client_id=client_id, flow_id=flow_id)
        self.db.WriteFlowObject(rdf_flow)

        for i in range(1, 4):
          requests.append(
              rdf_flow_objects.FlowRequest(
                  client_id=client_id, flow_id=flow_id, request_id=i))

    self.db.WriteFlowRequests(requests)

    with self.assertRaises(db.UnknownFlowError):
      self.db.ReadAllFlowRequestsAndResponses(
          client_id=client_id_1, flow_id=u"11111111")

    for flow_id in [flow_id_1, flow_id_2]:
      for client_id in [client_id_1, client_id_2]:
        read = self.db.ReadAllFlowRequestsAndResponses(
            client_id=client_id, flow_id=flow_id)

        self.assertEqual(len(read), 3)
        self.assertEqual([req.request_id for (req, _) in read], list(
            range(1, 4)))
        for _, responses in read:
          self.assertEqual(responses, [])

  def _WriteRequestForProcessing(self, client_id, flow_id, request_id):
    with mock.patch.object(self.db.delegate,
                           "WriteFlowProcessingRequests") as req_func:

      request = rdf_flow_objects.FlowRequest(
          flow_id=flow_id,
          client_id=client_id,
          request_id=request_id,
          needs_processing=True)
      self.db.WriteFlowRequests([request])

      return req_func.call_count

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

  def testDeleteFlowRequests(self):
    client_id, flow_id = self._SetupClientAndFlow()

    requests = []
    for request_id in range(1, 4):
      requests.append(
          rdf_flow_objects.FlowRequest(
              client_id=client_id, flow_id=flow_id, request_id=request_id))

    self.db.WriteFlowRequests(requests)

    request_list = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertItemsEqual([req.request_id for req, _ in request_list],
                          [req.request_id for req in requests])

    random.shuffle(requests)

    while requests:
      request = requests.pop()
      self.db.DeleteFlowRequests([request])
      request_list = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
      self.assertItemsEqual([req.request_id for req, _ in request_list],
                            [req.request_id for req in requests])

  def testResponsesForUnknownFlow(self):
    client_id = u"C.1234567890123456"
    flow_id = u"1234ABCD"

    with self.assertRaises(db.UnknownFlowError):
      self.db.WriteFlowResponses([
          rdf_flow_objects.FlowResponse(
              client_id=client_id, flow_id=flow_id, request_id=1, response_id=1)
      ])

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
    self.assertEqual(len(read), 1)
    request, responses = read[0]
    self.assertEqual(len(responses), 1)

  def testResponseWriting(self):
    client_id, flow_id = self._SetupClientAndFlow()

    request = rdf_flow_objects.FlowRequest(
        client_id=client_id, flow_id=flow_id, request_id=1)
    self.db.WriteFlowRequests([request])

    responses = [
        rdf_flow_objects.FlowResponse(
            client_id=client_id, flow_id=flow_id, request_id=1, response_id=i)
        for i in range(3)
    ]

    self.db.WriteFlowResponses(responses)

    all_requests = self.db.ReadAllFlowRequestsAndResponses(client_id, flow_id)
    self.assertEqual(len(all_requests), 1)

    read_request, read_responses = all_requests[0]
    self.assertEqual(read_request, request)
    self.assertEqual(list(read_responses), [0, 1, 2])

    for response_id, response in iteritems(read_responses):
      self.assertEqual(response.response_id, response_id)

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

    with mock.patch.object(self.db.delegate,
                           "WriteFlowProcessingRequests") as req_func:
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
      return req_func.call_count

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

  def testReadFlowForProcessingThatIsAlreadyBeingProcessed(self):
    client_id, flow_id = self._SetupClientAndFlow()
    processing_time = rdfvalue.Duration("60s")

    flow_for_processing = self.db.ReadFlowForProcessing(client_id, flow_id,
                                                        processing_time)

    # Already marked as being processed.
    with self.assertRaises(ValueError):
      self.db.ReadFlowForProcessing(client_id, flow_id, processing_time)

    self.db.ReturnProcessedFlow(flow_for_processing)

    # Should work again.
    self.db.ReadFlowForProcessing(client_id, flow_id, processing_time)

  def testReadFlowForProcessingAfterProcessingTimeExpiration(self):
    client_id, flow_id = self._SetupClientAndFlow()
    processing_time = rdfvalue.Duration("60s")
    now = rdfvalue.RDFDatetime.Now()

    with test_lib.FakeTime(now):
      self.db.ReadFlowForProcessing(client_id, flow_id, processing_time)

    # Already marked as being processed.
    with self.assertRaises(ValueError):
      self.db.ReadFlowForProcessing(client_id, flow_id, processing_time)

    after_deadline = now + processing_time + rdfvalue.Duration("1s")
    with test_lib.FakeTime(after_deadline):
      # Should work again.
      self.db.ReadFlowForProcessing(client_id, flow_id, processing_time)

  def testReadFlowForProcessingUpdatesFlowObjects(self):
    client_id, flow_id = self._SetupClientAndFlow()

    now = rdfvalue.RDFDatetime.Now()
    processing_time = rdfvalue.Duration("60s")
    processing_deadline = now + processing_time

    with test_lib.FakeTime(now):
      flow_for_processing = self.db.ReadFlowForProcessing(
          client_id, flow_id, processing_time)

    self.assertEqual(flow_for_processing.processing_on, utils.ProcessIdString())
    self.assertEqual(flow_for_processing.processing_since, now)
    self.assertEqual(flow_for_processing.processing_deadline,
                     processing_deadline)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(read_flow.processing_on, utils.ProcessIdString())
    self.assertEqual(read_flow.processing_since, now)
    self.assertEqual(read_flow.processing_deadline, processing_deadline)

    self.db.ReturnProcessedFlow(flow_for_processing)
    self.assertFalse(flow_for_processing.processing_on)
    self.assertIsNone(flow_for_processing.processing_since)
    self.assertIsNone(flow_for_processing.processing_deadline)

    read_flow = self.db.ReadFlowObject(client_id, flow_id)
    self.assertFalse(read_flow.processing_on)
    self.assertIsNone(read_flow.processing_since)
    self.assertIsNone(read_flow.processing_deadline)

  def testReturnProcessedFlow(self):
    client_id, flow_id = self._SetupClientAndFlow(next_request_to_process=1)

    processing_time = rdfvalue.Duration("60s")

    processed_flow = self.db.ReadFlowForProcessing(client_id, flow_id,
                                                   processing_time)

    # Let's say we processed on request on this flow.
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

    self.db.ReturnProcessedFlow(processed_flow)

    processed_flow = self.db.ReadFlowForProcessing(client_id, flow_id,
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

    self.assertFalse(self.db.ReturnProcessedFlow(processed_flow))

  def testReadChildFlows(self):
    client_id = u"C.1234567890123456"
    self.db.WriteClientMetadata(client_id, fleetspeak_enabled=False)

    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(flow_id=u"00000000", client_id=client_id))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            flow_id=u"00000001",
            client_id=client_id,
            parent_flow_id=u"00000000"))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            flow_id=u"00000002",
            client_id=client_id,
            parent_flow_id=u"00000001"))
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            flow_id=u"00000003",
            client_id=client_id,
            parent_flow_id=u"00000000"))

    # This one is completely unrelated (different client id).
    self.db.WriteClientMetadata(u"C.1234567890123457", fleetspeak_enabled=False)
    self.db.WriteFlowObject(
        rdf_flow_objects.Flow(
            flow_id=u"00000001",
            client_id=u"C.1234567890123457",
            parent_flow_id=u"00000000"))

    children = self.db.ReadChildFlowObjects(client_id, u"00000000")
    self.assertEqual(len(children), 2)
    for c in children:
      self.assertEqual(c.parent_flow_id, u"00000000")

    children = self.db.ReadChildFlowObjects(client_id, u"00000001")
    self.assertEqual(len(children), 1)
    self.assertEqual(children[0].parent_flow_id, u"00000001")
    self.assertEqual(children[0].flow_id, u"00000002")

    children = self.db.ReadChildFlowObjects(client_id, u"00000002")
    self.assertEqual(len(children), 0)

  def _WriteRequestAndResponses(self, client_id, flow_id):
    rdf_flow = rdf_flow_objects.Flow(client_id=client_id, flow_id=flow_id)
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
    self.assertEqual(len(all_requests), 3)
    for _, responses in all_requests:
      self.assertEqual(len(responses), 2)

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

  def testReadFlowRequestsReadyForProcessing(self):
    client_id = u"C.1234567890000000"
    flow_id = u"12344321"

    with self.assertRaises(db.UnknownFlowError):
      self.db.ReadFlowRequestsReadyForProcessing(client_id, flow_id)

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
        client_id, flow_id)

    # We expect three requests here. Req #1 is old and should not be there, req
    # #7 can't be processed since we are missing #6 in between. That leaves
    # requests #3, #4 and #5.
    self.assertEqual(len(requests_for_processing), 3)
    self.assertEqual(list(requests_for_processing), [3, 4, 5])

    for request_id in requests_for_processing:
      request, _ = requests_for_processing[request_id]
      self.assertEqual(request_id, request.request_id)

    self.assertEqual(requests_for_processing[4][1], responses)

  def testFlowProcessingRequestsQueue(self):
    client_id, flow_id = self._SetupClientAndFlow()

    queue = Queue.Queue()
    self.db.RegisterFlowProcessingHandler(queue.put)

    requests = []
    for i in xrange(5):
      requests.append(
          rdf_flows.FlowProcessingRequest(
              client_id=client_id, flow_id=flow_id, request_id=i))

    self.db.WriteFlowProcessingRequests(requests)

    got = []
    while len(got) < 5:
      try:
        l = queue.get(True, timeout=6)
      except Queue.Empty:
        self.fail(
            "Timed out waiting for messages, expected 5, got %d" % len(got))
      got.append(l)

    got.sort(key=lambda req: req.request_id)
    self.assertEqual(requests, got)

    self.db.UnregisterFlowProcessingHandler()

  def testFlowProcessingRequestsQueueWithDelay(self):
    client_id, flow_id = self._SetupClientAndFlow()

    queue = Queue.Queue()
    self.db.RegisterFlowProcessingHandler(queue.put)

    now = rdfvalue.RDFDatetime.Now()
    delivery_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(
        now.AsSecondsSinceEpoch() + 0.5)
    requests = []
    for i in xrange(5):
      requests.append(
          rdf_flows.FlowProcessingRequest(
              client_id=client_id,
              flow_id=flow_id,
              request_id=i,
              delivery_time=delivery_time))

    self.db.WriteFlowProcessingRequests(requests)

    got = []
    while len(got) < 5:
      try:
        l = queue.get(True, timeout=6)
      except Queue.Empty:
        self.fail(
            "Timed out waiting for messages, expected 5, got %d" % len(got))
      got.append(l)
      self.assertGreater(rdfvalue.RDFDatetime.Now(), l.delivery_time)

    got.sort(key=lambda req: req.request_id)
    self.assertEqual(requests, got)

    self.db.UnregisterFlowProcessingHandler()

  def testFlowProcessingRequestDeletion(self):
    client_id, flow_id = self._SetupClientAndFlow()
    now = rdfvalue.RDFDatetime.Now()
    delivery_time = now + rdfvalue.Duration("10m")
    requests = []
    for i in xrange(5):
      requests.append(
          rdf_flows.FlowProcessingRequest(
              client_id=client_id,
              flow_id=flow_id,
              request_id=i,
              delivery_time=delivery_time))

    self.db.WriteFlowProcessingRequests(requests)

    stored_requests = self.db.ReadFlowProcessingRequests()
    self.assertEqual(len(stored_requests), 5)
    self.assertItemsEqual([r.request_id for r in stored_requests],
                          [0, 1, 2, 3, 4])

    self.db.DeleteFlowProcessingRequests(requests[1:3])
    stored_requests = self.db.ReadFlowProcessingRequests()
    self.assertEqual(len(stored_requests), 3)
    self.assertItemsEqual([r.request_id for r in stored_requests], [0, 3, 4])
