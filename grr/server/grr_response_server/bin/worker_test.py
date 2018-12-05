#!/usr/bin/env python
"""Tests for the worker."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import threading
import time


from builtins import range  # pylint: disable=redefined-builtin
import mock

from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import queues
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_stats as rdf_client_stats
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_server import aff4
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_runner
from grr_response_server import foreman
from grr_response_server import frontend_lib
from grr_response_server import queue_manager
from grr_response_server import worker_lib
from grr_response_server.flows.general import administrative
from grr_response_server.hunts import implementation
from grr_response_server.hunts import standard
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr.test_lib import action_mocks
from grr.test_lib import client_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

# A global collector for test results
RESULTS = []


class WorkerSendingTestFlow(flow.GRRFlow):
  """Tests that sent messages are correctly collected."""

  def Start(self):
    for i in range(10):
      self.CallClient(
          client_test_lib.Test,
          rdf_protodict.DataBlob(string="test%s" % i),
          data=str(i),
          next_state="Incoming")

  def Incoming(self, responses):
    # We push the result into a global array so we can examine it
    # better.
    for response in responses:
      RESULTS.append(response.string)


class WorkerSendingTestFlow2(WorkerSendingTestFlow):
  """Only send a single request."""

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

  # Semaphore used by the test to control the flow termination.
  WAIT_FOR_FLOW_TERMINATION_SEMAPHORE = threading.Semaphore(0)

  HEARTBEAT = False

  @classmethod
  def Reset(cls, heartbeat=False):
    cls.WAIT_FOR_FLOW_SEMAPHORE = threading.Semaphore(0)
    cls.WAIT_FOR_TEST_SEMAPHORE = threading.Semaphore(0)
    cls.HEARTBEAT = heartbeat

  @classmethod
  def WaitUntilWorkerStartsProcessing(cls):
    # After starting this flow, the test should call
    # WaitUntilWorkerStartsProcessing() which will block until
    # WAIT_FOR_FLOW_SEMAPHORE is released. This way the test
    # knows exactly when the flow has actually started being
    # executed.
    cls.WAIT_FOR_FLOW_SEMAPHORE.acquire()

  @classmethod
  def LetFlowHeartBeat(cls):
    """Unblocks the test flow to do one heartbeat."""
    cls.WAIT_FOR_TEST_SEMAPHORE.release()
    cls.WAIT_FOR_FLOW_SEMAPHORE.acquire()

  @classmethod
  def StopFlow(cls):
    cls.HEARTBEAT = False
    cls.WAIT_FOR_TEST_SEMAPHORE.release()

  @classmethod
  def LetWorkerFinishProcessing(cls):
    cls.WAIT_FOR_FLOW_TERMINATION_SEMAPHORE.release()

  def Start(self):
    cls = WorkerStuckableTestFlow

    while True:
      # The test is expected to call LetFlowHeartBeat(). We block here
      # until it's called. This way the test can control
      # the way the flow heartbeats. For example, it can mock time.time()
      # differently for every call.
      cls.WAIT_FOR_FLOW_SEMAPHORE.release()
      cls.WAIT_FOR_TEST_SEMAPHORE.acquire()
      if not cls.HEARTBEAT:
        break

      self.HeartBeat()

    # We block here until we are allowed to terminate by the test calling
    # LetWorkerFinishProcessing(). This way the test can control precisely when
    # flow finishes.
    cls.WAIT_FOR_FLOW_TERMINATION_SEMAPHORE.acquire()


class ShardedQueueManager(queue_manager.QueueManager):
  """Operate on all shards at once.

  These tests call the worker's RunOnce and expect to see all notifications.
  This doesn't work when shards are enabled, since each worker is only looking
  at its own shard. This class gives the worker visibility across all shards.
  """

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

    self.worker = None

    # Clear the results global
    del RESULTS[:]

  def _TestWorker(self):
    self.worker = worker_lib.GRRWorker(token=self.token)
    return self.worker

  def tearDown(self):
    self.patch_get_notifications.stop()
    if self.worker is not None:
      self.worker.Shutdown()

    super(GrrWorkerTest, self).tearDown()

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
    self.assertLen(tasks_on_client_queue, 11)

    # Send each of the flows a repeated message
    self.SendResponse(session_id_1, "Hello1")
    self.SendResponse(session_id_2, "Hello2")
    self.SendResponse(session_id_1, "Hello1")
    self.SendResponse(session_id_2, "Hello2")

    worker_obj = self._TestWorker()

    # Process all messages
    worker_obj.RunOnce()

    worker_obj.thread_pool.Join()

    # Ensure both requests ran exactly once
    RESULTS.sort()
    self.assertLen(RESULTS, 2)
    self.assertEqual("Hello1", RESULTS[0])
    self.assertEqual("Hello2", RESULTS[1])

    # Check that client queue is cleared - should have 2 less messages (since
    # two were completed).
    tasks_on_client_queue = manager.Query(self.client_id.Queue(), 100)

    self.assertLen(tasks_on_client_queue, 9)

    # Ensure that processed requests are removed from state subject
    outstanding_requests = list(
        data_store.DB.ReadRequestsAndResponses(session_id_1))

    self.assertLen(outstanding_requests, 9)
    for request, _ in outstanding_requests:
      self.assertNotEqual(request.request.request_id, 0)

    # This flow is still in state Incoming.
    flow_obj = aff4.FACTORY.Open(session_id_1, token=self.token)
    self.assertTrue(
        flow_obj.context.state != rdf_flow_runner.FlowContext.State.TERMINATED)
    self.assertEqual(flow_obj.context.current_state, "Incoming")
    # This flow should be done.
    flow_obj = aff4.FACTORY.Open(session_id_2, token=self.token)
    self.assertTrue(
        flow_obj.context.state == rdf_flow_runner.FlowContext.State.TERMINATED)
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

      worker_obj = self._TestWorker()

      # Process all messages.
      with test_lib.SuppressLogs():
        worker_obj.RunOnce()
        worker_obj.thread_pool.Join()

    delay = flow_runner.FlowRunner.notification_retry_interval
    with test_lib.FakeTime(10000 + 100 + delay):
      manager = queue_manager.QueueManager(token=self.token)
      self.assertFalse(manager.GetNotificationsForAllShards(session_id.Queue()))

  def testNotificationReschedulingTTL(self):
    """Test that notifications are not rescheduled forever."""

    with test_lib.FakeTime(10000):
      worker_obj = self._TestWorker()
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
        self.assertLen(notifications, 1)

    delay = flow_runner.FlowRunner.notification_retry_interval

    ttl = notification.ttl
    for i in range(ttl - 1):
      with test_lib.FakeTime(10000 + 100 + delay * (i + 1)):
        # Process all messages.
        worker_obj.RunOnce()
        worker_obj.thread_pool.Join()

        notifications = manager.GetNotifications(queues.FLOWS)
        # Check the notification is for the correct session_id.
        notifications = [n for n in notifications if n.session_id == session_id]
        self.assertLen(notifications, 1)

    with test_lib.FakeTime(10000 + 100 + delay * ttl):
      # Process all messages.
      worker_obj.RunOnce()
      worker_obj.thread_pool.Join()

      notifications = manager.GetNotifications(queues.FLOWS)
      self.assertEmpty(notifications)

  def testNoKillNotificationsScheduledForHunts(self):
    worker_obj = self._TestWorker()
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)

    try:
      with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
        with implementation.StartHunt(
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
            notifications = manager.GetNotifications(queue)
            for n in notifications:
              self.assertFalse(n.in_progress)

    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      WorkerStuckableHunt.LetWorkerFinishProcessing()
      worker_obj.thread_pool.Join()

  def testKillNotificationsScheduledForFlows(self):
    worker_obj = self._TestWorker()
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)

    try:
      with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
        flow.StartAFF4Flow(
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
            notifications = manager.GetNotifications(queue)
            for n in notifications:
              self.assertFalse(n.in_progress)

    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      WorkerStuckableTestFlow.StopFlow()
      WorkerStuckableTestFlow.LetWorkerFinishProcessing()
      worker_obj.thread_pool.Join()

  def testStuckFlowGetsTerminated(self):
    worker_obj = self._TestWorker()
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)

    with test_lib.SuppressLogs():

      try:
        with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
          session_id = flow.StartAFF4Flow(
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
        WorkerStuckableTestFlow.StopFlow()
        WorkerStuckableTestFlow.LetWorkerFinishProcessing()
        worker_obj.thread_pool.Join()

      killed_flow = aff4.FACTORY.Open(session_id, token=self.token)
      self.assertEqual(killed_flow.context.state,
                       rdf_flow_runner.FlowContext.State.ERROR)
      self.assertEqual(killed_flow.context.status,
                       "Terminated by user test. Reason: Stuck in the worker")

  def testStuckNotificationGetsDeletedAfterTheFlowIsTerminated(self):
    worker_obj = self._TestWorker()
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)
    stuck_flows_timeout = flow_runner.FlowRunner.stuck_flows_timeout

    try:
      with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
        session_id = flow.StartAFF4Flow(
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
                       rdf_flow_runner.FlowContext.State.ERROR)
      self.assertEqual(killed_flow.context.status,
                       "Terminated by user test. Reason: Stuck in the worker")

      # Check that stuck notification has been removed.
      qm = queue_manager.QueueManager(token=self.token)
      notifications = qm.GetNotifications(queues.FLOWS)
      for n in notifications:
        self.assertFalse(n.in_progress)
    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      WorkerStuckableTestFlow.StopFlow()
      WorkerStuckableTestFlow.LetWorkerFinishProcessing()
      worker_obj.thread_pool.Join()

  def testHeartBeatingFlowIsNotTreatedAsStuck(self):
    worker_obj = self._TestWorker()
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)

    stuck_flows_timeout = flow_runner.FlowRunner.stuck_flows_timeout
    lease_timeout = rdfvalue.Duration(worker_lib.GRRWorker.flow_lease_time)

    WorkerStuckableTestFlow.Reset(heartbeat=True)
    try:
      with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
        session_id = flow.StartAFF4Flow(
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

      WorkerStuckableTestFlow.StopFlow()

      # Now current_time is > future_time, where future_time is the time
      # when stuck flow should have been killed. Calling RunOnce() here,
      # because if the flow is going to be killed, it will be killed
      # during worker.RunOnce() call.
      with test_lib.FakeTime(current_time.AsSecondsSinceEpoch()):
        worker_obj.RunOnce()

      # Check that the flow wasn't killed forecfully.
      checked_flow = aff4.FACTORY.Open(session_id, token=self.token)
      self.assertEqual(checked_flow.context.state,
                       rdf_flow_runner.FlowContext.State.RUNNING)

    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      with test_lib.FakeTime(current_time.AsSecondsSinceEpoch()):
        WorkerStuckableTestFlow.LetWorkerFinishProcessing()
        worker_obj.thread_pool.Join()

    # Check that the flow has finished normally.
    checked_flow = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertEqual(checked_flow.context.state,
                     rdf_flow_runner.FlowContext.State.TERMINATED)

  def testNonStuckFlowDoesNotGetTerminated(self):
    worker_obj = self._TestWorker()
    initial_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(100)
    stuck_flows_timeout = flow_runner.FlowRunner.stuck_flows_timeout

    with test_lib.FakeTime(initial_time.AsSecondsSinceEpoch()):
      session_id = flow.StartAFF4Flow(
          flow_name="WorkerSendingTestFlow",
          client_id=self.client_id,
          token=self.token,
          sync=False)

      # Process all messages
      worker_obj.RunOnce()
      worker_obj.thread_pool.Join()

    flow_obj = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertEqual(flow_obj.context.state,
                     rdf_flow_runner.FlowContext.State.RUNNING)

    # Set the time to max worker flow duration + 1 minute. If the 'kill'
    # notification isn't deleted we should get it now.
    future_time = initial_time + rdfvalue.Duration("1m") + stuck_flows_timeout
    with test_lib.FakeTime(future_time.AsSecondsSinceEpoch()):
      worker_obj.RunOnce()
      worker_obj.thread_pool.Join()

    flow_obj = aff4.FACTORY.Open(session_id, token=self.token)
    # Check that flow didn't get terminated due to a logic bug.
    self.assertEqual(flow_obj.context.state,
                     rdf_flow_runner.FlowContext.State.RUNNING)

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
    worker_obj = self._TestWorker()

    # Send a message to a WellKnownFlow - ClientStatsAuto.
    session_id = administrative.GetClientStatsAuto.well_known_session_id
    client_id = rdf_client.ClientURN("C.1100110011001100")

    if data_store.RelationalDBReadEnabled(category="message_handlers"):
      done = threading.Event()

      def handle(l):
        worker_obj._ProcessMessageHandlerRequests(l)
        done.set()

      data_store.REL_DB.RegisterMessageHandler(
          handle, worker_obj.well_known_flow_lease_time, limit=1000)

      self.SendResponse(
          session_id,
          data=rdf_client_stats.ClientStats(RSS_size=1234),
          client_id=client_id,
          well_known=True)

      self.assertTrue(done.wait(10))
    else:
      self.SendResponse(
          session_id,
          data=rdf_client_stats.ClientStats(RSS_size=1234),
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

    if data_store.RelationalDBReadEnabled(category="message_handlers"):
      data_store.REL_DB.UnregisterMessageHandler(timeout=60)

  def testWellKnownFlowResponsesAreProcessedOnlyOnce(self):
    worker_obj = self._TestWorker()

    # Send a message to a WellKnownFlow - ClientStatsAuto.
    client_id = rdf_client.ClientURN("C.1100110011001100")
    self.SendResponse(
        rdfvalue.SessionID(queue=queues.STATS, flow_name="Stats"),
        data=rdf_client_stats.ClientStats(RSS_size=1234),
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
    worker_obj = self._TestWorker()
    manager = queue_manager.QueueManager(token=self.token)
    notification = rdf_flows.GrrNotification(session_id=session_id)
    with data_store.DB.GetMutationPool() as pool:
      manager.NotifyQueue(notification, mutation_pool=pool)

    notifications = manager.GetNotifications(queues.FLOWS)

    # Check the notification is there. With multiple worker queue shards we can
    # get other notifications such as for audit event listeners, so we need to
    # filter out ours.
    notifications = [x for x in notifications if x.session_id == session_id]
    self.assertLen(notifications, 1)

    # Process all messages
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    notifications = manager.GetNotifications(queues.FLOWS)
    notifications = [x for x in notifications if x.session_id == session_id]

    # Check the notification is now gone.
    self.assertEmpty(notifications)

  def testWorkerDeletesNotificationsForBrokenObjects(self):
    # Test notifications for objects that don't exist.
    session_id = rdfvalue.SessionID(queue=queues.FLOWS, flow_name="123456")

    self.CheckNotificationsDisappear(session_id)

    # Now check objects that are actually broken.

    # Start a new flow.
    session_id = flow.StartAFF4Flow(
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
    session_id = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name="WorkerSendingTestFlow",
        token=self.token)
    worker_obj = self._TestWorker()
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
    self.assertLen(notifications, 1)

    # Process all messages
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    delay = flow_runner.FlowRunner.notification_retry_interval
    with test_lib.FakeTime(time.time() + 10 + delay):
      requeued_notifications = manager.GetNotifications(queues.FLOWS)
      # Check that there is a new notification.
      notifications = [n for n in notifications if n.session_id == session_id]
      self.assertLen(requeued_notifications, 1)

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
    session_id = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name="WorkerSendingTestFlow",
        token=self.token)
    worker_obj = self._TestWorker()
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

    # pylint: disable=invalid-name
    def WriteNotification(self, arg_session_id, start=None, end=None):
      if arg_session_id == session_id:
        flow_manager.QueueNotification(session_id=arg_session_id)
        flow_manager.Flush()

      self.DeleteNotification.old_target(
          self, arg_session_id, start=start, end=end)

    # pylint: enable=invalid-name

    with utils.Stubber(queue_manager.QueueManager, "DeleteNotification",
                       WriteNotification):
      # This should process request 1 but not touch request 2.
      worker_obj.RunOnce()
      worker_obj.thread_pool.Join()

    flow_obj = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertFalse(flow_obj.context.backtrace)
    self.assertNotEqual(flow_obj.context.state,
                        rdf_flow_runner.FlowContext.State.ERROR)

    request_data = data_store.DB.ReadResponsesForRequestId(session_id, 2)
    request_data.sort(key=lambda msg: msg.response_id)
    self.assertLen(request_data, 2)

    # Make sure the status and the original request are still there.
    self.assertEqual(request_data[0].args_rdf_name, "DataBlob")
    self.assertEqual(request_data[1].args_rdf_name, "GrrStatus")

    # But there is nothing for request 1.
    request_data = data_store.DB.ReadResponsesForRequestId(session_id, 1)
    self.assertEqual(request_data, [])

    # The notification for request 2 should have survived.
    with queue_manager.QueueManager(token=self.token) as manager:
      notifications = manager.GetNotifications(queues.FLOWS)
      self.assertLen(notifications, 1)
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
    session_id = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name="WorkerSendingTestFlow",
        token=self.token)

    # Convert to int to make test output nicer in case of failure.
    frozen_timestamp = int(self.SendResponse(session_id, "Hey"))

    request_id = 1
    messages = data_store.DB.ReadResponsesForRequestId(session_id, request_id)
    self.assertLen(messages, 2)
    self.assertCountEqual([m.args_rdf_name for m in messages],
                          ["DataBlob", "GrrStatus"])

    for m in messages:
      self.assertEqual(m.timestamp, frozen_timestamp)

  def testEqualTimestampNotifications(self):
    frontend_server = frontend_lib.FrontEndServer(
        certificate=config.CONFIG["Frontend.certificate"],
        private_key=config.CONFIG["PrivateKeys.server_key"],
        message_expiry_time=100)
    # This schedules 10 requests.
    session_id = flow.StartAFF4Flow(
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
      all_notifications = q.GetNotificationsForAllShards(
          rdfvalue.RDFURN("aff4:/F"))
      my_notifications = [
          n for n in all_notifications if n.session_id == session_id
      ]
      # There must not be more than one notification.
      self.assertLen(my_notifications, 1)
      notification = my_notifications[0]
      self.assertEqual(notification.first_queued, notification.timestamp)
      self.assertEqual(notification.last_status, 10)

  def testCPULimitForFlows(self):
    """This tests that the client actions are limited properly."""
    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[10], system_cpu_usage=[10], network_usage=[1000])

    flow_test_lib.TestFlowHelper(
        flow_test_lib.CPULimitFlow.__name__,
        client_mock,
        token=self.token,
        client_id=self.client_id,
        cpu_limit=1000,
        network_bytes_limit=10000)

    self.assertEqual(client_mock.storage["cpulimit"], [1000, 980, 960])
    self.assertEqual(client_mock.storage["networklimit"], [10000, 9000, 8000])

  def _Process(self, client_mocks, worker_obj):
    while True:
      client_msgs_processed = 0
      for client_mock in client_mocks:
        client_msgs_processed += client_mock.Next()
      with test_lib.SuppressLogs():
        worker_msgs_processed = worker_obj.RunOnce()
        worker_obj.thread_pool.Join()
      if not client_msgs_processed and not worker_msgs_processed:
        break

  def testCPULimitForHunts(self):
    worker_obj = self._TestWorker()

    client_ids = ["C.%016X" % i for i in range(10, 20)]
    result = {}
    client_mocks = []
    for client_id in client_ids:
      client_mock = action_mocks.CPULimitClientMock(
          result,
          user_cpu_usage=[10],
          system_cpu_usage=[10],
          network_usage=[1000])
      client_mocks.append(
          flow_test_lib.MockClient(client_id, client_mock, token=self.token))

    flow_runner_args = rdf_flow_runner.FlowRunnerArgs(
        flow_name=flow_test_lib.CPULimitFlow.__name__)
    with implementation.StartHunt(
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
        1000000, 999000, 998000, 997000, 996000, 995000, 994000, 993000, 992000
    ])

    result.clear()

    with implementation.StartHunt(
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

    client_mocks = []
    for client_id in client_ids:
      client_mock = action_mocks.CPULimitClientMock(
          result,
          user_cpu_usage=[500],
          system_cpu_usage=[500],
          network_usage=[1000000])
      client_mocks.append(
          flow_test_lib.MockClient(client_id, client_mock, token=self.token))

    with implementation.StartHunt(
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
    self.assertLen(errors, 2)
    # Client side out of cpu.
    self.assertIn("CPU limit exceeded", errors[0].log_message)
    # Server side out of cpu.
    self.assertIn("Out of CPU quota", errors[1].backtrace)

  def testForemanMessageHandler(self):
    with test_lib.ConfigOverrider({
        "Database.useForReads": True,
        "Database.useForReads.message_handlers": True
    }):
      with mock.patch.object(foreman.Foreman, "AssignTasksToClient") as instr:
        worker_obj = self._TestWorker()

        # Send a message to the Foreman.
        session_id = administrative.Foreman.well_known_session_id
        client_id = rdf_client.ClientURN("C.1100110011001100")
        self.SendResponse(
            session_id,
            rdf_protodict.DataBlob(),
            client_id=client_id,
            well_known=True)

        done = threading.Event()

        def handle(l):
          worker_obj._ProcessMessageHandlerRequests(l)
          done.set()

        data_store.REL_DB.RegisterMessageHandler(
            handle, worker_obj.well_known_flow_lease_time, limit=1000)
        try:
          self.assertTrue(done.wait(10))

          # Make sure there are no leftover requests.
          self.assertEqual(data_store.REL_DB.ReadMessageHandlerRequests(), [])

          instr.assert_called_once_with(client_id)
        finally:
          data_store.REL_DB.UnregisterMessageHandler(timeout=60)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
