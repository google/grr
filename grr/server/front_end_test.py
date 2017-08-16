#!/usr/bin/env python
"""Unittest for grr frontend server."""

from grr import config
from grr.lib import communicator
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.server import data_store
from grr.server import flow
from grr.server import front_end
from grr.server import queue_manager
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class SendingTestFlow(flow.GRRFlow):
  """Tests that sent messages are correctly collected."""

  @flow.StateHandler()
  def Start(self):
    for i in range(10):
      self.CallClient(
          client_test_lib.Test,
          rdf_protodict.DataBlob(string="test%s" % i),
          data=str(i),
          next_state="Incoming")


class GRRFEServerTestBase(flow_test_lib.FlowTestsBaseclass):
  """Base for GRRFEServer tests."""
  string = "Test String"

  message_expiry_time = 100

  def InitTestServer(self):
    prefix = "pool-%s" % self._testMethodName
    self.server = front_end.FrontEndServer(
        certificate=config.CONFIG["Frontend.certificate"],
        private_key=config.CONFIG["PrivateKeys.server_key"],
        message_expiry_time=self.message_expiry_time,
        threadpool_prefix=prefix)

  def setUp(self):
    """Setup the server."""
    super(GRRFEServerTestBase, self).setUp()

    self.config_overrider = test_lib.ConfigOverrider({
        # Whitelist test flow.
        "Frontend.well_known_flows": [
            utils.SmartStr(flow_test_lib.WellKnownSessionTest.
                           well_known_session_id.FlowName())
        ],
        # For tests, small pools are ok.
        "Threadpool.size":
            10
    })
    self.config_overrider.Start()
    self.InitTestServer()

  def tearDown(self):
    super(GRRFEServerTestBase, self).tearDown()
    self.config_overrider.Stop()


class GRRFEServerTest(GRRFEServerTestBase):
  """Tests the GRRFEServer."""

  def testReceiveMessages(self):
    """Test Receiving messages with no status."""
    flow_obj = self.FlowSetup(flow_test_lib.FlowOrderTest.__name__)

    session_id = flow_obj.session_id
    messages = [
        rdf_flows.GrrMessage(
            request_id=1,
            response_id=i,
            session_id=session_id,
            payload=rdfvalue.RDFInteger(i)) for i in range(1, 10)
    ]

    self.server.ReceiveMessages(self.client_id, messages)

    # Make sure the task is still on the client queue
    manager = queue_manager.QueueManager(token=self.token)
    tasks_on_client_queue = manager.Query(self.client_id, 100)
    self.assertEqual(len(tasks_on_client_queue), 1)

    stored_messages = data_store.DB.ReadResponsesForRequestId(
        session_id, 1, token=self.token)

    self.assertEqual(len(stored_messages), len(messages))

    stored_messages.sort(key=lambda m: m.response_id)
    # Check that messages were stored correctly
    for stored_message, message in zip(stored_messages, messages):
      self.assertRDFValuesEqual(stored_message, message)

  def testReceiveMessagesWithStatus(self):
    """Receiving a sequence of messages with a status."""
    flow_obj = self.FlowSetup(flow_test_lib.FlowOrderTest.__name__)

    session_id = flow_obj.session_id
    messages = [
        rdf_flows.GrrMessage(
            request_id=1,
            response_id=i,
            session_id=session_id,
            payload=rdfvalue.RDFInteger(i),
            task_id=15) for i in range(1, 10)
    ]

    # Now add the status message
    status = rdf_flows.GrrStatus(status=rdf_flows.GrrStatus.ReturnedStatus.OK)
    messages.append(
        rdf_flows.GrrMessage(
            request_id=1,
            response_id=len(messages) + 1,
            task_id=15,
            session_id=messages[0].session_id,
            payload=status,
            type=rdf_flows.GrrMessage.Type.STATUS))

    self.server.ReceiveMessages(self.client_id, messages)

    # Make sure the task is still on the client queue
    manager = queue_manager.QueueManager(token=self.token)
    tasks_on_client_queue = manager.Query(self.client_id, 100)
    self.assertEqual(len(tasks_on_client_queue), 1)

    stored_messages = data_store.DB.ReadResponsesForRequestId(
        session_id, 1, token=self.token)

    self.assertEqual(len(stored_messages), len(messages))

    stored_messages.sort(key=lambda m: m.response_id)
    # Check that messages were stored correctly
    for stored_message, message in zip(stored_messages, messages):
      self.assertRDFValuesEqual(stored_message, message)

  def testReceiveUnsolicitedClientMessage(self):
    flow_obj = self.FlowSetup(flow_test_lib.FlowOrderTest.__name__)

    session_id = flow_obj.session_id
    status = rdf_flows.GrrStatus(status=rdf_flows.GrrStatus.ReturnedStatus.OK)
    messages = [
        # This message has no task_id set...
        rdf_flows.GrrMessage(
            request_id=1,
            response_id=1,
            session_id=session_id,
            payload=rdfvalue.RDFInteger(1),
            task_id=15),
        rdf_flows.GrrMessage(
            request_id=1,
            response_id=2,
            session_id=session_id,
            payload=status,
            type=rdf_flows.GrrMessage.Type.STATUS)
    ]

    self.server.ReceiveMessages(self.client_id, messages)
    manager = queue_manager.QueueManager(token=self.token)
    completed = list(manager.FetchCompletedRequests(session_id))
    self.assertEqual(len(completed), 1)

  def testWellKnownFlows(self):
    """Make sure that well known flows can run on the front end."""
    flow_test_lib.WellKnownSessionTest.messages = []
    session_id = flow_test_lib.WellKnownSessionTest.well_known_session_id

    messages = [
        rdf_flows.GrrMessage(
            request_id=0,
            response_id=0,
            session_id=session_id,
            payload=rdfvalue.RDFInteger(i)) for i in range(1, 10)
    ]

    self.server.ReceiveMessages(self.client_id, messages)

    # Wait for async actions to complete
    self.server.thread_pool.Join()

    flow_test_lib.WellKnownSessionTest.messages.sort()

    # Well known flows are now directly processed on the front end
    self.assertEqual(flow_test_lib.WellKnownSessionTest.messages,
                     list(range(1, 10)))

    # There should be nothing in the client_queue
    self.assertEqual([],
                     data_store.DB.ResolvePrefix(
                         self.client_id, "task:", token=self.token))

  def testWellKnownFlowsBlacklist(self):
    """Make sure that well known flows can run on the front end."""
    with test_lib.ConfigOverrider({
        "Frontend.DEBUG_well_known_flows_blacklist": [
            utils.SmartStr(flow_test_lib.WellKnownSessionTest.
                           well_known_session_id.FlowName())
        ]
    }):
      self.InitTestServer()

      flow_test_lib.WellKnownSessionTest.messages = []
      session_id = flow_test_lib.WellKnownSessionTest.well_known_session_id

      messages = [
          rdf_flows.GrrMessage(
              request_id=0,
              response_id=0,
              session_id=session_id,
              payload=rdfvalue.RDFInteger(i)) for i in range(1, 10)
      ]

      self.server.ReceiveMessages(self.client_id, messages)

      # Wait for async actions to complete
      self.server.thread_pool.Join()

      # Check that no processing took place.
      self.assertFalse(flow_test_lib.WellKnownSessionTest.messages)

      # There should be nothing in the client_queue
      self.assertEqual([],
                       data_store.DB.ResolvePrefix(
                           self.client_id, "task:", token=self.token))

  def testWellKnownFlowsRemote(self):
    """Make sure that flows that do not exist on the front end get scheduled."""
    flow_test_lib.WellKnownSessionTest.messages = []
    session_id = flow_test_lib.WellKnownSessionTest.well_known_session_id

    messages = [
        rdf_flows.GrrMessage(
            request_id=0,
            response_id=0,
            session_id=session_id,
            payload=rdfvalue.RDFInteger(i)) for i in range(1, 10)
    ]

    # Delete the local well known flow cache is empty.
    self.server.well_known_flows = {}
    self.server.ReceiveMessages(self.client_id, messages)

    # Wait for async actions to complete
    self.server.thread_pool.Join()

    # None get processed now
    self.assertEqual(flow_test_lib.WellKnownSessionTest.messages, [])

    # There should be nothing in the client_queue
    self.assertEqual([],
                     data_store.DB.ResolvePrefix(
                         self.client_id, "task:", token=self.token))

    # The well known flow messages should be waiting in the flow state now:
    queued_messages = []
    for predicate, _, _ in data_store.DB.ResolvePrefix(
        session_id.Add("state/request:00000000"), "flow:", token=self.token):
      queued_messages.append(predicate)

    self.assertEqual(len(queued_messages), 9)

  def testWellKnownFlowsNotifications(self):
    flow_test_lib.WellKnownSessionTest.messages = []
    flow_test_lib.WellKnownSessionTest2.messages = []
    session_id1 = flow_test_lib.WellKnownSessionTest.well_known_session_id
    session_id2 = flow_test_lib.WellKnownSessionTest2.well_known_session_id

    messages = []
    for i in range(1, 5):
      messages.append(
          rdf_flows.GrrMessage(
              request_id=0,
              response_id=0,
              session_id=session_id1,
              payload=rdfvalue.RDFInteger(i)))
      messages.append(
          rdf_flows.GrrMessage(
              request_id=0,
              response_id=0,
              session_id=session_id2,
              payload=rdfvalue.RDFInteger(i)))

    # This test whitelists only one flow.
    self.assertIn(session_id1.FlowName(), self.server.well_known_flows)
    self.assertNotIn(session_id2.FlowName(), self.server.well_known_flows)

    self.server.ReceiveMessages(self.client_id, messages)

    # Wait for async actions to complete
    self.server.thread_pool.Join()

    # Flow 1 should have been processed right away.
    flow_test_lib.WellKnownSessionTest.messages.sort()
    self.assertEqual(flow_test_lib.WellKnownSessionTest.messages,
                     list(range(1, 5)))

    # But not Flow 2.
    self.assertEqual(flow_test_lib.WellKnownSessionTest2.messages, [])

    manager = queue_manager.WellKnownQueueManager(token=self.token)

    notifications = manager.GetNotificationsForAllShards(session_id1.Queue())

    # Flow 1 was proecessed on the frontend, no queued responses available.
    responses = list(manager.FetchResponses(session_id1))
    self.assertEqual(responses, [])
    # And also no notifications.
    self.assertNotIn(session_id1, [
        notification.session_id for notification in notifications
    ])

    # But for Flow 2 there should be some responses + a notification.
    responses = list(manager.FetchResponses(session_id2))
    self.assertEqual(len(responses), 4)
    self.assertIn(session_id2,
                  [notification.session_id for notification in notifications])

  def testDrainUpdateSessionRequestStates(self):
    """Draining the flow requests and preparing messages."""
    # This flow sends 10 messages on Start()
    flow_obj = self.FlowSetup("SendingTestFlow")
    session_id = flow_obj.session_id

    # There should be 10 messages in the client's task queue
    manager = queue_manager.QueueManager(token=self.token)
    tasks = manager.Query(self.client_id, 100)
    self.assertEqual(len(tasks), 10)

    requests_by_id = {}

    for request, _ in data_store.DB.ReadRequestsAndResponses(
        session_id, token=self.token):
      requests_by_id[request.id] = request

    # Check that the response state objects have the correct ts_id set
    # in the client_queue:
    for task in tasks:
      request_id = task.request_id

      # Retrieve the request state for this request_id
      request = requests_by_id[request_id]

      # Check that task_id for the client message is correctly set in
      # request_state.
      self.assertEqual(request.request.task_id, task.task_id)

    # Now ask the server to drain the outbound messages into the
    # message list.
    response = rdf_flows.MessageList()

    response.job = self.server.DrainTaskSchedulerQueueForClient(
        self.client_id, 5)

    # Check that we received only as many messages as we asked for
    self.assertEqual(len(response.job), 5)

    for i in range(4):
      self.assertEqual(response.job[i].session_id, session_id)
      self.assertEqual(response.job[i].name, "Test")

  def testHandleMessageBundle(self):
    """Check that HandleMessageBundles() requeues messages if it failed.

    This test makes sure that when messages are pending for a client, and which
    we have no certificate for, the messages are requeued when sending fails.
    """
    # Make a new fake client
    client_id, = self.SetupClients(1)

    class MockCommunicator(object):
      """A fake that simulates an unenrolled client."""

      def DecodeMessages(self, *unused_args):
        """For simplicity client sends an empty request."""
        return ([], client_id, 100)

      def EncodeMessages(self, *unused_args, **unused_kw):
        """Raise because the server has no certificates for this client."""
        raise communicator.UnknownClientCert()

    # Install the mock.
    self.server._communicator = MockCommunicator()

    # First request, the server will raise UnknownClientCert.
    request_comms = rdf_flows.ClientCommunication()
    self.assertRaises(communicator.UnknownClientCert,
                      self.server.HandleMessageBundles, request_comms, 2)

    # We can still schedule a flow for it
    flow.GRRFlow.StartFlow(
        client_id=client_id,
        flow_name=flow_test_lib.SendingFlow.__name__,
        message_count=1,
        token=self.token)
    manager = queue_manager.QueueManager(token=self.token)
    tasks = manager.Query(client_id, limit=100)

    self.assertRaises(communicator.UnknownClientCert,
                      self.server.HandleMessageBundles, request_comms, 2)

    new_tasks = manager.Query(client_id, limit=100)

    # The different in eta times reflect the lease that the server took on the
    # client messages.
    lease_time = (new_tasks[0].eta - tasks[0].eta) / 1e6

    # This lease time must be small, as the HandleMessageBundles() call failed,
    # the pending client messages must be put back on the queue.
    self.assertLess(lease_time, 1)

    # Since the server tried to send it, the ttl must be decremented
    self.assertEqual(tasks[0].task_ttl - new_tasks[0].task_ttl, 1)

  def _ScheduleResponseAndStatus(self, client_id, flow_id):
    with queue_manager.QueueManager(token=self.token) as flow_manager:
      # Schedule a response.
      flow_manager.QueueResponse(
          rdf_flows.GrrMessage(
              source=client_id,
              session_id=flow_id,
              payload=rdf_protodict.DataBlob(string="Helllo"),
              request_id=1,
              response_id=1))
      # And a STATUS message.
      flow_manager.QueueResponse(
          rdf_flows.GrrMessage(
              source=client_id,
              session_id=flow_id,
              payload=rdf_flows.GrrStatus(
                  status=rdf_flows.GrrStatus.ReturnedStatus.OK),
              request_id=1,
              response_id=2,
              type=rdf_flows.GrrMessage.Type.STATUS))

  def testHandleClientMessageRetransmission(self):
    """Check that requests get retransmitted but only if there is no status."""
    # Make a new fake client
    client_id = self.SetupClients(1)[0]

    # Test the standard behavior.
    base_time = 1000
    msgs_recvd = []

    default_ttl = rdf_flows.GrrMessage().task_ttl
    with test_lib.FakeTime(base_time):
      flow.GRRFlow.StartFlow(
          client_id=client_id,
          flow_name=flow_test_lib.SendingFlow.__name__,
          message_count=1,
          token=self.token)

    for i in range(default_ttl):
      with test_lib.FakeTime(base_time + i * (self.message_expiry_time + 1)):

        tasks = self.server.DrainTaskSchedulerQueueForClient(client_id, 100000)
        msgs_recvd.append(tasks)

    # Should return a client message (ttl-1) times and nothing afterwards.
    self.assertEqual(
        map(bool, msgs_recvd),
        [True] * (rdf_flows.GrrMessage().task_ttl - 1) + [False])

    # Now we simulate that the workers are overloaded - the client messages
    # arrive but do not get processed in time.
    if default_ttl <= 3:
      self.fail("TTL too low for this test.")

    msgs_recvd = []

    with test_lib.FakeTime(base_time):
      flow_id = flow.GRRFlow.StartFlow(
          client_id=client_id,
          flow_name=flow_test_lib.SendingFlow.__name__,
          message_count=1,
          token=self.token)

    for i in range(default_ttl):
      if i == 2:
        self._ScheduleResponseAndStatus(client_id, flow_id)

      with test_lib.FakeTime(base_time + i * (self.message_expiry_time + 1)):

        tasks = self.server.DrainTaskSchedulerQueueForClient(client_id, 100000)
        msgs_recvd.append(tasks)

        if not tasks:
          # Even if the request has not been leased ttl times yet,
          # it should be dequeued by now.
          new_tasks = queue_manager.QueueManager(token=self.token).Query(
              queue=rdf_client.ClientURN(client_id).Queue(), limit=1000)
          self.assertEqual(len(new_tasks), 0)

    # Should return a client message twice and nothing afterwards.
    self.assertEqual(
        map(bool, msgs_recvd),
        [True] * 2 + [False] * (rdf_flows.GrrMessage().task_ttl - 2))


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  flags.StartMain(main)
