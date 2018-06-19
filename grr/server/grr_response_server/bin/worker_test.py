#!/usr/bin/env python
"""Tests for the worker."""

import threading
import time

import mock

from grr import config
from grr.lib import flags
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.server.grr_response_server import aff4
from grr.server.grr_response_server import data_store
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import flow_runner
from grr.server.grr_response_server import frontend_lib
from grr.server.grr_response_server import queue_manager
from grr.server.grr_response_server import worker_lib
from grr.server.grr_response_server.flows.general import administrative
from grr.server.grr_response_server.hunts import implementation
from grr.server.grr_response_server.hunts import standard
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

# A global collector for test results
RESULTS = []


class WorkerSendingTestFlow(flow.GRRFlow):
  """Tests that sent messages are correctly collected."""

  @flow.StateHandler()
  def Start(self):
    for i in range(10):
      self.CallClient(
          client_test_lib.Test,
          rdf_protodict.DataBlob(string="test%s" % i),
          data=str(i),
          next_state="Incoming")

  @flow.StateHandler()
  def Incoming(self, responses):
    # We push the result into a global array so we can examine it
    # better.
    for response in responses:
      RESULTS.append(response.string)


class WorkerSendingTestFlow2(WorkerSendingTestFlow):
  """Only send a single request."""

  @flow.StateHandler()
  def Start(self):
    i = 1
    self.CallClient(
        client_test_lib.Test,
        rdf_protodict.DataBlob(string="test%s" % i),
        data=str(i),
        next_state="Incoming")


class WorkerSendingWKTestFlow(flow.WellKnownFlow):

  well_known_session_id = rdfvalue.SessionID(
      flow_name="WorkerSendingWKTestFlow")

  def ProcessMessage(self, message):
    RESULTS.append(message)


class RaisingTestFlow(WorkerSendingTestFlow):

  @flow.StateHandler()
  def Incoming(self, responses):
    raise AttributeError("Some Error.")


class WorkerStuckableHunt(implementation.GRRHunt):

  # Semaphore used by test code to wait until the hunt is being processed.
  WAIT_FOR_HUNT_SEMAPHORE = threading.Semaphore(0)
  # Semaphore used by the hunt to wait until the external test code does its
  # thing.
  WAIT_FOR_TEST_SEMAPHORE = threading.Semaphore(0)

  @classmethod
  def Reset(cls):
    cls.WAIT_FOR_HUNT_SEMAPHORE = threading.Semaphore(0)
    cls.WAIT_FOR_TEST_SEMAPHORE = threading.Semaphore(0)

  @classmethod
  def WaitUntilWorkerStartsProcessing(cls):
    cls.WAIT_FOR_HUNT_SEMAPHORE.acquire()

  @classmethod
  def LetWorkerFinishProcessing(cls):
    cls.WAIT_FOR_TEST_SEMAPHORE.release()

  @flow.StateHandler()
  def RunClient(self, responses):
    cls = WorkerStuckableHunt

    # After starting this hunt, the test should call
    # WaitUntilWorkerStartsProcessing() which will block until
    # WAIT_FOR_HUNT_SEMAPHORE is released. This way the test
    # knows exactly when the hunt has actually started being
    # executed.
    cls.WAIT_FOR_HUNT_SEMAPHORE.release()

    # We block here until WAIT_FOR_TEST_SEMAPHORE is released. It's released
    # when the test calls LetWorkerFinishProcessing(). This way the test
    # can control precisely when flow finishes.
    cls.WAIT_FOR_TEST_SEMAPHORE.acquire()


class WorkerStuckableTestFlow(flow.GRRFlow):
  """Flow that can be paused with sempahores when processed by the worker."""

  # Semaphore used by test code to wait until the flow is being processed.
  WAIT_FOR_FLOW_SEMAPHORE = threading.Semaphore(0)
  # Semaphore used by the flow to wait until the external test code does its
  # thing.
  WAIT_FOR_TEST_SEMAPHORE = threading.Semaphore(0)
  # Semaphore used by the flow to wait until it has to heartbeat.
  WAIT_FOR_TEST_PERMISSION_TO_HEARTBEAT_SEMAPHORE = threading.Semaphore(0)
  # Semaphore used by the test to wait until the flow heartbeats.
  WAIT_FOR_FLOW_HEARTBEAT_SEMAPHORE = threading.Semaphore(0)

  HEARTBEAT = False

  @classmethod
  def Reset(cls, heartbeat=False):
    cls.WAIT_FOR_FLOW_SEMAPHORE = threading.Semaphore(0)
    cls.WAIT_FOR_TEST_SEMAPHORE = threading.Semaphore(0)
    cls.HEARTBEAT = heartbeat

  @classmethod
  def WaitUntilWorkerStartsProcessing(cls):
    cls.WAIT_FOR_FLOW_SEMAPHORE.acquire()

  @classmethod
  def LetFlowHeartBeat(cls):
    if not cls.HEARTBEAT:
      raise RuntimeError("LetFlowHeartBeat called, but heartbeat "
                         "not enabled.")

    cls.WAIT_FOR_TEST_PERMISSION_TO_HEARTBEAT_SEMAPHORE.release()

  @classmethod
  def WaitForFlowHeartBeat(cls, last_heartbeat=False):
    """Called by the test to wait until the flow heartbeats.

    Args:
      last_heartbeat: If True, the flow won't heartbeat anymore. Consequently,
                      the test won't be supposed to call LetFlowHeartBeat and
                      WaitForFlowHeartBeat methods.

    Raises:
      RuntimeError: if heartbeat is not enabled. Heartbeat can be enabled via
                    Reset() method.
    """
    if not cls.HEARTBEAT:
      raise RuntimeError("WaitForFlowHeartBeat called, but heartbeat "
                         "not enabled.")

    if last_heartbeat:
      cls.HEARTBEAT = False
    cls.WAIT_FOR_FLOW_HEARTBEAT_SEMAPHORE.acquire()

  @classmethod
  def LetWorkerFinishProcessing(cls):
    cls.WAIT_FOR_TEST_SEMAPHORE.release()

  @flow.StateHandler()
  def Start(self):
    cls = WorkerStuckableTestFlow

    # After starting this flow, the test should call
    # WaitUntilWorkerStartsProcessing() which will block until
    # WAIT_FOR_FLOW_SEMAPHORE is released. This way the test
    # knows exactly when the flow has actually started being
    # executed.
    cls.WAIT_FOR_FLOW_SEMAPHORE.release()

    while cls.HEARTBEAT:
      # The test is expected to call LetFlowHeartBeat(). We block here
      # until it's called. This way the test can control
      # the way the flow heartbeats. For example, it can mock time.time()
      # differently for every call.
      cls.WAIT_FOR_TEST_PERMISSION_TO_HEARTBEAT_SEMAPHORE.acquire()
      self.HeartBeat()
      # The test is expected to call WaitForFlowHeartBeat() and block
      # until we release WAIT_FOR_FLOW_HEARTBEAT_SEMAPHORE. This way
      # the test knows exactly when the heartbeat was done.
      cls.WAIT_FOR_FLOW_HEARTBEAT_SEMAPHORE.release()

    # We block here until WAIT_FOR_TEST_SEMAPHORE is released. It's released
    # when the test calls LetWorkerFinishProcessing(). This way the test
    # can control precisely when flow finishes.
    cls.WAIT_FOR_TEST_SEMAPHORE.acquire()


class ShardedQueueManager(queue_manager.QueueManager):
  """Operate on all shards at once.

  These tests call the worker's RunOnce and expect to see all notifications.
  This doesn't work when shards are enabled, since each worker is only looking
  at its own shard. This class gives the worker visibility across all shards.
  """

  def GetNotificationsByPriority(self, queue):
    return self.GetNotificationsByPriorityForAllShards(queue)

  def GetNotifications(self, queue):
    return self.GetNotificationsForAllShards(queue)


class GrrWorkerTest(flow_test_lib.FlowTestsBaseclass):
  """Tests the GRR Worker."""

  def setUp(self):
    super(GrrWorkerTest, self).setUp()
    self.client_id = test_lib.TEST_CLIENT_ID
    WorkerStuckableTestFlow.Reset()
    self.patch_get_notifications = mock.patch.object(
        queue_manager, "QueueManager", ShardedQueueManager)
    self.patch_get_notifications.start()

    # Clear the results global
    del RESULTS[:]

  def tearDown(self):
    super(GrrWorkerTest, self).tearDown()
    self.patch_get_notifications.stop()

  def testProcessMessages(self):
    """Test processing of several inbound messages."""

    # Create a couple of flows
    flow_obj = self.FlowSetup("WorkerSendingTestFlow")
    session_id_1 = flow_obj.session_id
    flow_obj.Close()

    flow_obj = self.FlowSetup("WorkerSendingTestFlow2")
    session_id_2 = flow_obj.session_id
    flow_obj.Close()

    manager = queue_manager.QueueManager(token=self.token)
    # Check that client queue has messages
    tasks_on_client_queue = manager.Query(self.client_id.Queue(), 100)

    # should have 10 requests from WorkerSendingTestFlow and 1 from
    # SendingTestFlow2
    self.assertEqual(len(tasks_on_client_queue), 11)

    # Send each of the flows a repeated message
    self.SendResponse(session_id_1, "Hello1")
    self.SendResponse(session_id_2, "Hello2")
    self.SendResponse(session_id_1, "Hello1")
    self.SendResponse(session_id_2, "Hello2")

    worker_obj = worker_lib.GRRWorker(token=self.token)

    # Process all messages
    worker_obj.RunOnce()

    worker_obj.thread_pool.Join()

    # Ensure both requests ran exactly once
    RESULTS.sort()
    self.assertEqual(2, len(RESULTS))
    self.assertEqual("Hello1", RESULTS[0])
    self.assertEqual("Hello2", RESULTS[1])

    # Check that client queue is cleared - should have 2 less messages (since
    # two were completed).
    tasks_on_client_queue = manager.Query(self.client_id.Queue(), 100)

    self.assertEqual(len(tasks_on_client_queue), 9)

    # Ensure that processed requests are removed from state subject
    outstanding_requests = list(
        data_store.DB.ReadRequestsAndResponses(session_id_1))

    self.assertEqual(len(outstanding_requests), 9)
    for request, _ in outstanding_requests:
      self.assertNotEqual(request.request.request_id, 0)

    # This flow is still in state Incoming.
    flow_obj = aff4.FACTORY.Open(session_id_1, token=self.token)
    self.assertTrue(
        flow_obj.context.state != rdf_flows.FlowContext.State.TERMINATED)
    self.assertEqual(flow_obj.context.current_state, "Incoming")
    # This flow should be done.
    flow_obj = aff4.FACTORY.Open(session_id_2, token=self.token)
    self.assertTrue(
        flow_obj.context.state == rdf_flows.FlowContext.State.TERMINATED)
    self.assertEqual(flow_obj.context.current_state, "End")

  def testNoNotificationRescheduling(self):
    """Test that no notifications are rescheduled when a flow raises."""

    with test_lib.FakeTime(10000):
      flow_obj = self.FlowSetup("RaisingTestFlow")
      session_id = flow_obj.session_id
      flow_obj.Close()

      # Send the flow some messages.
      self.SendResponse(session_id, "Hello1", request_id=1)
      self.SendResponse(session_id, "Hello2", request_id=2)
      self.SendResponse(session_id, "Hello3", request_id=3)

      worker_obj = worker_lib.GRRWorker(token=self.token)

      # Process all messages.
      worker_obj.RunOnce()
      worker_obj.thread_pool.Join()

    delay = flow_runner.FlowRunner.notification_retry_interval
    with test_lib.FakeTime(10000 + 100 + delay):
      manager = queue_manager.QueueManager(token=self.token)
      self.assertFalse(manager.GetNotificationsForAllShards(session_id.Queue()))

  def testNotificationReschedulingTTL(self):
    """Test that notifications are not rescheduled forever."""

    with test_lib.FakeTime(10000):
      worker_obj = worker_lib.GRRWorker(token=self.token)
      flow_obj = self.FlowSetup("RaisingTestFlow")
      session_id = flow_obj.session_id
      flow_obj.Close()

      with queue_manager.QueueManager(token=self.token) as manager:
        notification = rdf_flows.GrrNotification(
            session_id=session_id, timestamp=time.time(), last_status=1)
        with data_store.DB.GetMutationPool() as pool:
          manager.NotifyQueue(notification, mutation_pool=pool)

        notifications = manager.GetNotifications(queues.FLOWS)
        # Check the notification is there.
        notifications = [n for n in notifications if n.session_id == session_id]
        self.assertEqual(len(notifications), 1)

    delay = flow_runner.FlowRunner.notification_retry_interval

    ttl = notification.ttl
    for i in xrange(ttl - 1):
      with test_lib.FakeTime(10000 + 100 + delay * (i + 1)):
        # Process all messages.
        worker_obj.RunOnce()
        worker_obj.thread_pool.Join()

        notifications = manager.GetNotifications(queues.FLOWS)
        # Check the notification is for the correct session_id.
        notifications = [n for n in notifications if n.session_id == session_id]
        self.assertEqual(len(notifications), 1)

    with test_lib.FakeTime(10000 + 100 + delay * ttl):
      # Process all messages.
      worker_obj.RunOnce()
      worker_obj.thread_pool.Join()

      notifications = manager.GetNotifications(queues.FLOWS)
      self.assertEqual(len(notifications), 0)

  def testNoKillNotificationsScheduledForHunts(self):
    worker_obj = worker_lib.GRRWorker(token=self.token)
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)

    try:
      with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
        with implementation.GRRHunt.StartHunt(
            hunt_name=WorkerStuckableHunt.__name__,
            client_rate=0,
            token=self.token) as hunt:
          hunt.GetRunner().Start()

        implementation.GRRHunt.StartClients(hunt.session_id, [self.client_id])

        # Process all messages
        while worker_obj.RunOnce():
          pass
        # Wait until worker thread starts processing the flow.
        WorkerStuckableHunt.WaitUntilWorkerStartsProcessing()

        # Assert that there are no stuck notifications in the worker's queue.
        with queue_manager.QueueManager(token=self.token) as manager:
          for queue in worker_obj.queues:
            notifications = manager.GetNotificationsByPriority(queue)
          self.assertFalse(manager.STUCK_PRIORITY in notifications)

    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      WorkerStuckableHunt.LetWorkerFinishProcessing()
      worker_obj.thread_pool.Join()

  def testKillNotificationsScheduledForFlows(self):
    worker_obj = worker_lib.GRRWorker(token=self.token)
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)

    try:
      with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
        flow.GRRFlow.StartFlow(
            flow_name=WorkerStuckableTestFlow.__name__,
            client_id=self.client_id,
            token=self.token,
            sync=False)

        # Process all messages
        worker_obj.RunOnce()
        # Wait until worker thread starts processing the flow.
        WorkerStuckableTestFlow.WaitUntilWorkerStartsProcessing()

        # Assert that there are no stuck notifications in the worker's
        # queue.
        with queue_manager.QueueManager(token=self.token) as manager:
          for queue in worker_obj.queues:
            notifications = manager.GetNotificationsByPriority(queue)
            self.assertFalse(manager.STUCK_PRIORITY in notifications)

    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      WorkerStuckableTestFlow.LetWorkerFinishProcessing()
      worker_obj.thread_pool.Join()

  def testStuckFlowGetsTerminated(self):
    worker_obj = worker_lib.GRRWorker(token=self.token)
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)

    try:
      with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
        session_id = flow.GRRFlow.StartFlow(
            flow_name=WorkerStuckableTestFlow.__name__,
            client_id=self.client_id,
            token=self.token,
            sync=False)
        # Process all messages
        while worker_obj.RunOnce():
          pass
        # Wait until worker thread starts processing the flow.
        WorkerStuckableTestFlow.WaitUntilWorkerStartsProcessing()

      # Set the time to max worker flow duration + 1 minute. The flow is
      # currently blocked because of the way semaphores are set up.
      # Worker should consider the flow to be stuck and terminate it.
      stuck_flows_timeout = flow_runner.FlowRunner.stuck_flows_timeout
      future_time = (
          initial_time + rdfvalue.Duration("1m") + stuck_flows_timeout)

      with test_lib.FakeTime(future_time.AsSecondsSinceEpoch()):
        worker_obj.RunOnce()

    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      WorkerStuckableTestFlow.LetWorkerFinishProcessing()
      worker_obj.thread_pool.Join()

    killed_flow = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertEqual(killed_flow.context.state,
                     rdf_flows.FlowContext.State.ERROR)
    self.assertEqual(killed_flow.context.status,
                     "Terminated by user test. Reason: Stuck in the worker")

  def testStuckNotificationGetsDeletedAfterTheFlowIsTerminated(self):
    worker_obj = worker_lib.GRRWorker(token=self.token)
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)
    stuck_flows_timeout = flow_runner.FlowRunner.stuck_flows_timeout

    try:
      with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
        session_id = flow.GRRFlow.StartFlow(
            flow_name=WorkerStuckableTestFlow.__name__,
            client_id=self.client_id,
            token=self.token,
            sync=False)

        # Process all messages
        worker_obj.RunOnce()
        # Wait until worker thread starts processing the flow.
        WorkerStuckableTestFlow.WaitUntilWorkerStartsProcessing()

      # Set the time to max worker flow duration + 1 minute. The flow is
      # currently blocked because of the way how semaphores are set up.
      # Worker should consider the flow to be stuck and terminate it.
      future_time = (
          initial_time + rdfvalue.Duration("1m") + stuck_flows_timeout)
      with test_lib.FakeTime(future_time.AsSecondsSinceEpoch()):
        worker_obj.RunOnce()

      killed_flow = aff4.FACTORY.Open(session_id, token=self.token)
      self.assertEqual(killed_flow.context.state,
                       rdf_flows.FlowContext.State.ERROR)
      self.assertEqual(killed_flow.context.status,
                       "Terminated by user test. Reason: Stuck in the worker")

      # Check that stuck notification has been removed.
      qm = queue_manager.QueueManager(token=self.token)
      notifications_by_priority = qm.GetNotificationsByPriority(queues.FLOWS)
      self.assertTrue(qm.STUCK_PRIORITY not in notifications_by_priority)
    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      WorkerStuckableTestFlow.LetWorkerFinishProcessing()
      worker_obj.thread_pool.Join()

  def testHeartBeatingFlowIsNotTreatedAsStuck(self):
    worker_obj = worker_lib.GRRWorker(token=self.token)
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)

    stuck_flows_timeout = flow_runner.FlowRunner.stuck_flows_timeout
    lease_timeout = rdfvalue.Duration(worker_lib.GRRWorker.flow_lease_time)

    WorkerStuckableTestFlow.Reset(heartbeat=True)
    try:
      with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
        session_id = flow.GRRFlow.StartFlow(
            flow_name=WorkerStuckableTestFlow.__name__,
            client_id=self.client_id,
            token=self.token,
            sync=False)
        # Process all messages
        worker_obj.RunOnce()
        # Wait until worker thread starts processing the flow.
        WorkerStuckableTestFlow.WaitUntilWorkerStartsProcessing()

      # Increase the time in steps, using LetFlowHeartBeat/WaitForFlowHeartBeat
      # to control the flow execution that happens in the parallel thread.
      current_time = rdfvalue.RDFDatetime(initial_time)
      future_time = initial_time + stuck_flows_timeout + rdfvalue.Duration("1m")
      while current_time <= future_time:
        current_time += lease_timeout - rdfvalue.Duration("1s")

        with test_lib.FakeTime(current_time.AsSecondsSinceEpoch()):
          checked_flow = aff4.FACTORY.Open(session_id, token=self.token)
          WorkerStuckableTestFlow.LetFlowHeartBeat()
          WorkerStuckableTestFlow.WaitForFlowHeartBeat(
              last_heartbeat=current_time > future_time)
      # Now current_time is > future_time, where future_time is the time
      # when stuck flow should have been killed. Calling RunOnce() here,
      # because if the flow is going to be killed, it will be killed
      # during worker.RunOnce() call.
      with test_lib.FakeTime(current_time.AsSecondsSinceEpoch()):
        worker_obj.RunOnce()

      # Check that the flow wasn't killed forecfully.
      checked_flow = aff4.FACTORY.Open(session_id, token=self.token)
      self.assertEqual(checked_flow.context.state,
                       rdf_flows.FlowContext.State.RUNNING)

    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      with test_lib.FakeTime(current_time.AsSecondsSinceEpoch()):
        WorkerStuckableTestFlow.LetWorkerFinishProcessing()
        worker_obj.thread_pool.Join()

    # Check that the flow has finished normally.
    checked_flow = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertEqual(checked_flow.context.state,
                     rdf_flows.FlowContext.State.TERMINATED)

  def testNonStuckFlowDoesNotGetTerminated(self):
    worker_obj = worker_lib.GRRWorker(token=self.token)
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)
    stuck_flows_timeout = flow_runner.FlowRunner.stuck_flows_timeout

    with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
      session_id = flow.GRRFlow.StartFlow(
          flow_name="WorkerSendingTestFlow",
          client_id=self.client_id,
          token=self.token,
          sync=False)

      # Process all messages
      worker_obj.RunOnce()
      worker_obj.thread_pool.Join()

    flow_obj = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertEqual(flow_obj.context.state,
                     rdf_flows.FlowContext.State.RUNNING)

    # Set the time to max worker flow duration + 1 minute. If the 'kill'
    # notification isn't deleted we should get it now.
    future_time = initial_time + rdfvalue.Duration("1m") + stuck_flows_timeout
    with test_lib.FakeTime(future_time.AsSecondsSinceEpoch()):
      worker_obj.RunOnce()
      worker_obj.thread_pool.Join()

    flow_obj = aff4.FACTORY.Open(session_id, token=self.token)
    # Check that flow didn't get terminated due to a logic bug.
    self.assertEqual(flow_obj.context.state,
                     rdf_flows.FlowContext.State.RUNNING)

  def testProcessMessagesWellKnown(self):
    self._testProcessMessagesWellKnown()

  def testMessageHandlers(self):
    with test_lib.ConfigOverrider({
        "Database.useForReads": True,
        "Database.useForReads.message_handlers": True
    }):
      self._testProcessMessagesWellKnown()

    # Make sure there are no leftover requests.
    self.assertEqual(data_store.REL_DB.ReadMessageHandlerRequests(), [])

  def _testProcessMessagesWellKnown(self):
    worker_obj = worker_lib.GRRWorker(token=self.token)

    # Send a message to a WellKnownFlow - ClientStatsAuto.
    session_id = administrative.GetClientStatsAuto.well_known_session_id
    client_id = rdf_client.ClientURN("C.1100110011001100")
    self.SendResponse(
        session_id,
        data=rdf_client.ClientStats(RSS_size=1234),
        client_id=client_id,
        well_known=True)

    # Process all messages
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    client = aff4.FACTORY.Open(client_id.Add("stats"), token=self.token)
    stats = client.Get(client.Schema.STATS)
    self.assertEqual(stats.RSS_size, 1234)

    # Make sure no notifications have been sent.
    user = aff4.FACTORY.Open(
        "aff4:/users/%s" % self.token.username, token=self.token)
    notifications = user.Get(user.Schema.PENDING_NOTIFICATIONS)
    self.assertIsNone(notifications)

  def testWellKnownFlowResponsesAreProcessedOnlyOnce(self):
    worker_obj = worker_lib.GRRWorker(token=self.token)

    # Send a message to a WellKnownFlow - ClientStatsAuto.
    client_id = rdf_client.ClientURN("C.1100110011001100")
    self.SendResponse(
        rdfvalue.SessionID(queue=queues.STATS, flow_name="Stats"),
        data=rdf_client.ClientStats(RSS_size=1234),
        client_id=client_id,
        well_known=True)

    # Process all messages
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    client = aff4.FACTORY.Open(client_id.Add("stats"), token=self.token)
    stats = client.Get(client.Schema.STATS)
    self.assertEqual(stats.RSS_size, 1234)

    aff4.FACTORY.Delete(client_id.Add("stats"), token=self.token)

    # Process all messages once again - there should be no actual processing
    # done, as all the responses were processed last time.
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    # Check that stats haven't changed as no new responses were processed.
    client = aff4.FACTORY.Open(client_id.Add("stats"), token=self.token)
    self.assertIsNone(client.Get(client.Schema.STATS))

  def CheckNotificationsDisappear(self, session_id):
    worker_obj = worker_lib.GRRWorker(token=self.token)
    manager = queue_manager.QueueManager(token=self.token)
    notification = rdf_flows.GrrNotification(session_id=session_id)
    with data_store.DB.GetMutationPool() as pool:
      manager.NotifyQueue(notification, mutation_pool=pool)

    notifications = manager.GetNotificationsByPriority(queues.FLOWS).get(
        notification.priority, [])

    # Check the notification is there. With multiple worker queue shards we can
    # get other notifications such as for audit event listeners, so we need to
    # filter out ours.
    notifications = [x for x in notifications if x.session_id == session_id]
    self.assertEqual(len(notifications), 1)

    # Process all messages
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    notifications = manager.GetNotificationsByPriority(queues.FLOWS).get(
        notification.priority, [])
    notifications = [x for x in notifications if x.session_id == session_id]

    # Check the notification is now gone.
    self.assertEqual(len(notifications), 0)

  def testWorkerDeletesNotificationsForBrokenObjects(self):
    # Test notifications for objects that don't exist.
    session_id = rdfvalue.SessionID(queue=queues.FLOWS, flow_name="123456")

    self.CheckNotificationsDisappear(session_id)

    # Now check objects that are actually broken.

    # Start a new flow.
    session_id = flow.GRRFlow.StartFlow(
        flow_name="WorkerSendingTestFlow",
        client_id=self.client_id,
        token=self.token)
    # Overwrite the type of the object such that opening it will now fail.
    data_store.DB.Set(session_id, "aff4:type", "DeprecatedClass")

    # Starting a new flow schedules notifications for the worker already but
    # this test actually checks that there are none. Thus, we have to delete
    # them or the test fails.
    data_store.DB.DeleteSubject(queues.FLOWS)

    # Check it really does.
    with self.assertRaises(aff4.InstantiationError):
      aff4.FACTORY.Open(session_id, token=self.token)

    self.CheckNotificationsDisappear(session_id)

  def testNotificationRacesAreResolved(self):
    # We need a random flow object for this test.
    session_id = flow.GRRFlow.StartFlow(
        client_id=self.client_id,
        flow_name="WorkerSendingTestFlow",
        token=self.token)
    worker_obj = worker_lib.GRRWorker(token=self.token)
    manager = queue_manager.QueueManager(token=self.token)
    manager.DeleteNotification(session_id)
    manager.Flush()

    # We simulate a race condition here - the notification for request #1 is
    # there but the actual request #1 is not. The worker should pick up the
    # notification, notice that the request #1 is not there yet and reschedule
    # the notification.
    notification = rdf_flows.GrrNotification(
        session_id=session_id, last_status=1)
    with data_store.DB.GetMutationPool() as pool:
      manager.NotifyQueue(notification, mutation_pool=pool)

    notifications = manager.GetNotifications(queues.FLOWS)
    # Check the notification is there.
    notifications = [n for n in notifications if n.session_id == session_id]
    self.assertEqual(len(notifications), 1)

    # Process all messages
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    delay = flow_runner.FlowRunner.notification_retry_interval
    with test_lib.FakeTime(time.time() + 10 + delay):
      requeued_notifications = manager.GetNotifications(queues.FLOWS)
      # Check that there is a new notification.
      notifications = [n for n in notifications if n.session_id == session_id]
      self.assertEqual(len(requeued_notifications), 1)

      self.assertEqual(requeued_notifications[0].first_queued,
                       notifications[0].first_queued)
      self.assertNotEqual(requeued_notifications[0].timestamp,
                          notifications[0].timestamp)

  def testNoValidStatusRaceIsResolved(self):

    # This tests for the regression of a long standing race condition we saw
    # where notifications would trigger the reading of another request that
    # arrives later but wasn't completely written to the database yet.
    # Timestamp based notification handling should eliminate this bug.

    # We need a random flow object for this test.
    session_id = flow.GRRFlow.StartFlow(
        client_id=self.client_id,
        flow_name="WorkerSendingTestFlow",
        token=self.token)
    worker_obj = worker_lib.GRRWorker(token=self.token)
    manager = queue_manager.QueueManager(token=self.token)

    manager.DeleteNotification(session_id)
    manager.Flush()

    # We have a first request that is complete (request_id 1, response_id 1).
    self.SendResponse(session_id, "Response 1")

    # However, we also have request #2 already coming in. The race is that
    # the queue manager might write the status notification to
    # session_id/state as "status:00000002" but not the status response
    # itself yet under session_id/state/request:00000002

    request_id = 2
    response_id = 1
    flow_manager = queue_manager.QueueManager(token=self.token)
    flow_manager.FreezeTimestamp()

    flow_manager.QueueResponse(
        rdf_flows.GrrMessage(
            source=self.client_id,
            session_id=session_id,
            payload=rdf_protodict.DataBlob(string="Response 2"),
            request_id=request_id,
            auth_state="AUTHENTICATED",
            response_id=response_id))

    status = rdf_flows.GrrMessage(
        source=self.client_id,
        session_id=session_id,
        payload=rdf_flows.GrrStatus(
            status=rdf_flows.GrrStatus.ReturnedStatus.OK),
        request_id=request_id,
        response_id=response_id + 1,
        auth_state="AUTHENTICATED",
        type=rdf_flows.GrrMessage.Type.STATUS)

    # Now we write half the status information.
    data_store.DB.StoreRequestsAndResponses(new_responses=[(status, None)])

    # We make the race even a bit harder by saying the new notification gets
    # written right before the old one gets deleted. If we are not careful here,
    # we delete the new notification as well and the flow becomes stuck.

    def WriteNotification(self, arg_session_id, start=None, end=None):
      if arg_session_id == session_id:
        flow_manager.QueueNotification(session_id=arg_session_id)
        flow_manager.Flush()

      self.DeleteNotification.old_target(
          self, arg_session_id, start=start, end=end)

    with utils.Stubber(queue_manager.QueueManager, "DeleteNotification",
                       WriteNotification):
      # This should process request 1 but not touch request 2.
      worker_obj.RunOnce()
      worker_obj.thread_pool.Join()

    flow_obj = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertFalse(flow_obj.context.backtrace)
    self.assertNotEqual(flow_obj.context.state,
                        rdf_flows.FlowContext.State.ERROR)

    request_data = data_store.DB.ReadResponsesForRequestId(session_id, 2)
    request_data.sort(key=lambda msg: msg.response_id)
    self.assertEqual(len(request_data), 2)

    # Make sure the status and the original request are still there.
    self.assertEqual(request_data[0].args_rdf_name, "DataBlob")
    self.assertEqual(request_data[1].args_rdf_name, "GrrStatus")

    # But there is nothing for request 1.
    request_data = data_store.DB.ReadResponsesForRequestId(session_id, 1)
    self.assertEqual(request_data, [])

    # The notification for request 2 should have survived.
    with queue_manager.QueueManager(token=self.token) as manager:
      notifications = manager.GetNotifications(queues.FLOWS)
      self.assertEqual(len(notifications), 1)
      notification = notifications[0]
      self.assertEqual(notification.session_id, session_id)
      self.assertEqual(notification.timestamp, flow_manager.frozen_timestamp)

    self.assertEqual(RESULTS, ["Response 1"])

    # The last missing piece of request 2 is the actual status message.
    flow_manager.QueueResponse(status)
    flow_manager.Flush()

    # Now make sure request 2 runs as expected.
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    self.assertEqual(RESULTS, ["Response 1", "Response 2"])

  def testUniformTimestamps(self):
    session_id = flow.GRRFlow.StartFlow(
        client_id=self.client_id,
        flow_name="WorkerSendingTestFlow",
        token=self.token)

    # Convert to int to make test output nicer in case of failure.
    frozen_timestamp = int(self.SendResponse(session_id, "Hey"))

    request_id = 1
    messages = data_store.DB.ReadResponsesForRequestId(session_id, request_id)
    self.assertEqual(len(messages), 2)
    self.assertItemsEqual([m.args_rdf_name for m in messages],
                          ["DataBlob", "GrrStatus"])

    for m in messages:
      self.assertEqual(m.timestamp, frozen_timestamp)

  def testEqualTimestampNotifications(self):
    frontend_server = frontend_lib.FrontEndServer(
        certificate=config.CONFIG["Frontend.certificate"],
        private_key=config.CONFIG["PrivateKeys.server_key"],
        message_expiry_time=100,
        threadpool_prefix="notification-test")

    # This schedules 10 requests.
    session_id = flow.GRRFlow.StartFlow(
        client_id=self.client_id,
        flow_name="WorkerSendingTestFlow",
        token=self.token)

    # We pretend that the client processed all the 10 requests at once and
    # sends the replies in a single http poll.
    messages = [
        rdf_flows.GrrMessage(
            request_id=i,
            response_id=1,
            session_id=session_id,
            payload=rdf_protodict.DataBlob(string="test%s" % i),
            auth_state="AUTHENTICATED",
            generate_task_id=True) for i in range(1, 11)
    ]
    status = rdf_flows.GrrStatus(status=rdf_flows.GrrStatus.ReturnedStatus.OK)
    statuses = [
        rdf_flows.GrrMessage(
            request_id=i,
            response_id=2,
            session_id=session_id,
            payload=status,
            type=rdf_flows.GrrMessage.Type.STATUS,
            auth_state="AUTHENTICATED",
            generate_task_id=True) for i in range(1, 11)
    ]

    frontend_server.ReceiveMessages(self.client_id, messages + statuses)

    with queue_manager.QueueManager(token=self.token) as q:
      all_notifications = q.GetNotificationsByPriorityForAllShards(
          rdfvalue.RDFURN("aff4:/F"))
      medium_priority = rdf_flows.GrrNotification.Priority.MEDIUM_PRIORITY
      medium_notifications = all_notifications[medium_priority]
      my_notifications = [
          n for n in medium_notifications if n.session_id == session_id
      ]
      # There must not be more than one notification.
      self.assertEqual(len(my_notifications), 1)
      notification = my_notifications[0]
      self.assertEqual(notification.first_queued, notification.timestamp)
      self.assertEqual(notification.last_status, 10)

  def testCPULimitForFlows(self):
    """This tests that the client actions are limited properly."""
    result = {}
    client_mock = action_mocks.CPULimitClientMock(result)
    client_mock = flow_test_lib.MockClient(
        self.client_id, client_mock, token=self.token)

    client_mock.EnableResourceUsage(
        user_cpu_usage=[10], system_cpu_usage=[10], network_usage=[1000])

    worker_obj = worker_lib.GRRWorker(token=self.token)

    flow.GRRFlow.StartFlow(
        client_id=self.client_id,
        flow_name=flow_test_lib.CPULimitFlow.__name__,
        cpu_limit=1000,
        network_bytes_limit=10000,
        token=self.token)

    self._Process([client_mock], worker_obj)

    self.assertEqual(result["cpulimit"], [1000, 980, 960])
    self.assertEqual(result["networklimit"], [10000, 9000, 8000])

    return result

  def _Process(self, client_mocks, worker_obj):
    while True:
      client_msgs_processed = 0
      for client_mock in client_mocks:
        client_msgs_processed += client_mock.Next()
      worker_msgs_processed = worker_obj.RunOnce()
      worker_obj.thread_pool.Join()
      if not client_msgs_processed and not worker_msgs_processed:
        break

  def testCPULimitForHunts(self):
    worker_obj = worker_lib.GRRWorker(token=self.token)

    client_ids = ["C.%016X" % i for i in xrange(10, 20)]
    result = {}
    client_mocks = []
    for client_id in client_ids:
      client_mock = action_mocks.CPULimitClientMock(result)
      client_mock = flow_test_lib.MockClient(
          rdf_client.ClientURN(client_id), client_mock, token=self.token)

      client_mock.EnableResourceUsage(
          user_cpu_usage=[10], system_cpu_usage=[10], network_usage=[1000])
      client_mocks.append(client_mock)

    flow_runner_args = rdf_flows.FlowRunnerArgs(
        flow_name=flow_test_lib.CPULimitFlow.__name__)
    with implementation.GRRHunt.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=flow_runner_args,
        cpu_limit=5000,
        per_client_cpu_limit=10000,
        network_bytes_limit=1000000,
        client_rate=0,
        token=self.token) as hunt:
      hunt.GetRunner().Start()

    implementation.GRRHunt.StartClients(hunt.session_id, client_ids[:1])
    self._Process(client_mocks, worker_obj)
    implementation.GRRHunt.StartClients(hunt.session_id, client_ids[1:2])
    self._Process(client_mocks, worker_obj)
    implementation.GRRHunt.StartClients(hunt.session_id, client_ids[2:3])
    self._Process(client_mocks, worker_obj)

    # The limiting factor here is the overall hunt limit of 5000 cpu
    # seconds. Clients that finish should decrease the remaining quota
    # and the following clients should get the reduced quota.
    self.assertEqual(result["cpulimit"], [
        5000.0, 4980.0, 4960.0, 4940.0, 4920.0, 4900.0, 4880.0, 4860.0, 4840.0
    ])
    self.assertEqual(result["networklimit"], [
        1000000L, 999000L, 998000L, 997000L, 996000L, 995000L, 994000L, 993000L,
        992000L
    ])

    result.clear()

    with implementation.GRRHunt.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=flow_runner_args,
        per_client_cpu_limit=3000,
        per_client_network_limit_bytes=3000000,
        client_rate=0,
        token=self.token) as hunt:
      hunt.GetRunner().Start()

    implementation.GRRHunt.StartClients(hunt.session_id, client_ids[:1])
    self._Process(client_mocks, worker_obj)
    implementation.GRRHunt.StartClients(hunt.session_id, client_ids[1:2])
    self._Process(client_mocks, worker_obj)
    implementation.GRRHunt.StartClients(hunt.session_id, client_ids[2:3])
    self._Process(client_mocks, worker_obj)

    # This time, the per client limit is 3000s / 3000000 bytes. Every
    # client should get the same limit.
    self.assertEqual(result["cpulimit"], [
        3000.0, 2980.0, 2960.0, 3000.0, 2980.0, 2960.0, 3000.0, 2980.0, 2960.0
    ])
    self.assertEqual(result["networklimit"], [
        3000000, 2999000, 2998000, 3000000, 2999000, 2998000, 3000000, 2999000,
        2998000
    ])
    result.clear()

    for client_mock in client_mocks:
      client_mock.EnableResourceUsage(
          user_cpu_usage=[500], system_cpu_usage=[500], network_usage=[1000000])

    with implementation.GRRHunt.StartHunt(
        hunt_name=standard.GenericHunt.__name__,
        flow_runner_args=flow_runner_args,
        per_client_cpu_limit=3000,
        cpu_limit=5000,
        per_client_network_limit_bytes=3000000,
        network_bytes_limit=5000000,
        client_rate=0,
        token=self.token) as hunt:
      hunt.GetRunner().Start()

    implementation.GRRHunt.StartClients(hunt.session_id, client_ids[:1])
    self._Process(client_mocks, worker_obj)
    implementation.GRRHunt.StartClients(hunt.session_id, client_ids[1:2])
    self._Process(client_mocks, worker_obj)
    implementation.GRRHunt.StartClients(hunt.session_id, client_ids[2:3])
    self._Process(client_mocks, worker_obj)

    # The first client gets the full per client limit of 3000s, and
    # uses all of it. The hunt has a limit of just 5000 total so the
    # second client gets started with a limit of 2000. It can only run
    # two of three states, the last client will not be started at all
    # due to out of quota.
    self.assertEqual(result["cpulimit"],
                     [3000.0, 2000.0, 1000.0, 2000.0, 1000.0])
    self.assertEqual(result["networklimit"],
                     [3000000, 2000000, 1000000, 2000000, 1000000])

    errors = list(hunt.GetClientsErrors())
    self.assertEqual(len(errors), 2)
    # Client side out of cpu.
    self.assertIn("CPU limit exceeded", errors[0].log_message)
    # Server side out of cpu.
    self.assertIn("Out of CPU quota", errors[1].backtrace)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
