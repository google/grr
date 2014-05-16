#!/usr/bin/env python
"""Tests for the worker."""


import threading
import time

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import flow
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import worker


# A global collector for test results
RESULTS = []


class WorkerSendingTestFlow(flow.GRRFlow):
  """Tests that sent messages are correctly collected."""

  @flow.StateHandler(next_state="Incoming")
  def Start(self):
    for i in range(10):
      self.CallClient("Test",
                      rdfvalue.DataBlob(string="test%s" % i),
                      data=str(i),
                      next_state="Incoming")

  @flow.StateHandler(auth_required=False)
  def Incoming(self, responses):
    # Add a delay here to catch thread races.
    time.sleep(0.2)
    # We push the result into a global array so we can examine it
    # better.
    for response in responses:
      RESULTS.append(response.string)


class WorkerSendingTestFlow2(WorkerSendingTestFlow):
  """Only send a single request."""

  @flow.StateHandler(next_state="Incoming")
  def Start(self):
    i = 1
    self.CallClient("Test",
                    rdfvalue.DataBlob(string="test%s" % i),
                    data=str(i),
                    next_state="Incoming")


class WorkerSendingWKTestFlow(flow.WellKnownFlow):

  well_known_session_id = rdfvalue.SessionID(
      "aff4:/flows/WorkerSendingWKTestFlow")

  def ProcessMessage(self, message):
    RESULTS.append(message)


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

  @flow.StateHandler(next_state="End")
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


class GrrWorkerTest(test_lib.FlowTestsBaseclass):
  """Tests the GRR Worker."""

  def setUp(self):
    super(GrrWorkerTest, self).setUp()
    WorkerStuckableTestFlow.Reset()

  def SendResponse(self, session_id, data, client_id=None, well_known=False):
    if not isinstance(data, rdfvalue.RDFValue):
      data = rdfvalue.DataBlob(string=data)
    if well_known:
      request_id, response_id = 0, 12345
    else:
      request_id, response_id = 1, 1
    with queue_manager.QueueManager(token=self.token) as flow_manager:
      flow_manager.QueueResponse(session_id, rdfvalue.GrrMessage(
          source=client_id,
          session_id=session_id,
          payload=data,
          request_id=request_id,
          response_id=response_id))
      if not well_known:
        # For normal flows we have to send a status as well.
        flow_manager.QueueResponse(session_id, rdfvalue.GrrMessage(
            source=client_id,
            session_id=session_id,
            payload=rdfvalue.GrrStatus(
                status=rdfvalue.GrrStatus.ReturnedStatus.OK),
            request_id=request_id, response_id=response_id+1,
            type=rdfvalue.GrrMessage.Type.STATUS))

      flow_manager.QueueNotification(session_id=session_id)

  def testProcessMessages(self):
    """Test processing of several inbound messages."""
    worker_obj = worker.GRRWorker(worker.DEFAULT_WORKER_QUEUE,
                                  token=self.token)

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

    # Clear the results global
    del RESULTS[:]

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
    self.assertEqual((None, 0), data_store.DB.Resolve(
        session_id_1.Add("state"),
        manager.FLOW_REQUEST_TEMPLATE % 1,
        token=self.token))

    # This flow is still in state Incoming.
    flow_obj = aff4.FACTORY.Open(session_id_1, token=self.token)
    self.assertTrue(flow_obj.state.context.state !=
                    rdfvalue.Flow.State.TERMINATED)
    self.assertEqual(flow_obj.state.context["current_state"],
                     "Incoming")
    # This flow should be done.
    flow_obj = aff4.FACTORY.Open(session_id_2, token=self.token)
    self.assertTrue(flow_obj.state.context.state ==
                    rdfvalue.Flow.State.TERMINATED)
    self.assertEqual(flow_obj.state.context["current_state"],
                     "End")

  def testStuckFlowGetsTerminated(self):
    worker_obj = worker.GRRWorker(worker.DEFAULT_WORKER_QUEUE,
                                  token=self.token)
    initial_time = rdfvalue.RDFDatetime().FromSecondsFromEpoch(0)
    stuck_flows_timeout = rdfvalue.Duration(
        config_lib.CONFIG["Worker.stuck_flows_timeout"])

    try:
      with test_lib.FakeTime(initial_time.AsSecondsFromEpoch()):
        session_id = flow.GRRFlow.StartFlow(flow_name="WorkerStuckableTestFlow",
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
      future_time = (initial_time + rdfvalue.Duration("1m") +
                     stuck_flows_timeout)
      with test_lib.FakeTime(future_time.AsSecondsFromEpoch()):
        worker_obj.RunOnce()

    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      WorkerStuckableTestFlow.LetWorkerFinishProcessing()
      worker_obj.thread_pool.Join()

    killed_flow = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertEqual(killed_flow.state.context.state,
                     rdfvalue.Flow.State.ERROR)
    self.assertEqual(killed_flow.state.context.status,
                     "Terminated by user test. Reason: Stuck in the worker")

  def testStuckNotificationGetsDeletedAfterTheFlowIsTerminated(self):
    worker_obj = worker.GRRWorker(worker.DEFAULT_WORKER_QUEUE,
                                  token=self.token)
    initial_time = rdfvalue.RDFDatetime().FromSecondsFromEpoch(0)
    stuck_flows_timeout = rdfvalue.Duration(
        config_lib.CONFIG["Worker.stuck_flows_timeout"])

    try:
      with test_lib.FakeTime(initial_time.AsSecondsFromEpoch()):
        session_id = flow.GRRFlow.StartFlow(flow_name="WorkerStuckableTestFlow",
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
      future_time = (initial_time + rdfvalue.Duration("1m") +
                     stuck_flows_timeout)
      with test_lib.FakeTime(future_time.AsSecondsFromEpoch()):
        worker_obj.RunOnce()

      killed_flow = aff4.FACTORY.Open(session_id, token=self.token)
      self.assertEqual(killed_flow.state.context.state,
                       rdfvalue.Flow.State.ERROR)
      self.assertEqual(killed_flow.state.context.status,
                       "Terminated by user test. Reason: Stuck in the worker")

      # Check that stuck notification has been removed.
      qm = queue_manager.QueueManager(token=self.token)
      notifications_by_priority = qm.GetNotificationsByPriority(
          worker.DEFAULT_WORKER_QUEUE)
      self.assertTrue(qm.STUCK_PRIORITY not in notifications_by_priority)
    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      WorkerStuckableTestFlow.LetWorkerFinishProcessing()
      worker_obj.thread_pool.Join()

  def testHeartBeatingFlowIsNotTreatedAsStuck(self):
    worker_obj = worker.GRRWorker(worker.DEFAULT_WORKER_QUEUE,
                                  token=self.token)
    initial_time = rdfvalue.RDFDatetime().FromSecondsFromEpoch(0)

    stuck_flows_timeout = rdfvalue.Duration(
        config_lib.CONFIG["Worker.stuck_flows_timeout"])
    lease_timeout = rdfvalue.Duration(
        config_lib.CONFIG["Worker.flow_lease_time"])

    WorkerStuckableTestFlow.Reset(heartbeat=True)
    try:
      with test_lib.FakeTime(initial_time.AsSecondsFromEpoch()):
        session_id = flow.GRRFlow.StartFlow(flow_name="WorkerStuckableTestFlow",
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

        with test_lib.FakeTime(current_time.AsSecondsFromEpoch()):
          checked_flow = aff4.FACTORY.Open(session_id, token=self.token)
          WorkerStuckableTestFlow.LetFlowHeartBeat()
          WorkerStuckableTestFlow.WaitForFlowHeartBeat(
              last_heartbeat=current_time > future_time)

      # Now current_time is > future_time, where future_time is the time
      # when stuck flow should have been killed. Calling RunOnce() here,
      # because if the flow is going to be killed, it will be killed
      # during worker.RunOnce() call.
      with test_lib.FakeTime(current_time.AsSecondsFromEpoch()):
        worker_obj.RunOnce()

      # Check that the flow wasn't killed forecfully.
      checked_flow = aff4.FACTORY.Open(session_id, token=self.token)
      self.assertEqual(checked_flow.state.context.state,
                       rdfvalue.Flow.State.RUNNING)

    finally:
      # Release the semaphore so that worker thread unblocks and finishes
      # processing the flow.
      with test_lib.FakeTime(current_time.AsSecondsFromEpoch()):
        WorkerStuckableTestFlow.LetWorkerFinishProcessing()
        worker_obj.thread_pool.Join()

    # Check that the flow has finished normally.
    checked_flow = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertEqual(checked_flow.state.context.state,
                     rdfvalue.Flow.State.TERMINATED)

  def testNonStuckFlowDoesNotGetTerminated(self):
    worker_obj = worker.GRRWorker(worker.DEFAULT_WORKER_QUEUE,
                                  token=self.token)
    initial_time = rdfvalue.RDFDatetime().FromSecondsFromEpoch(0)
    stuck_flows_timeout = rdfvalue.Duration(
        config_lib.CONFIG["Worker.stuck_flows_timeout"])

    with test_lib.FakeTime(initial_time.AsSecondsFromEpoch()):
      session_id = flow.GRRFlow.StartFlow(flow_name="WorkerSendingTestFlow",
                                          client_id=self.client_id,
                                          token=self.token,
                                          sync=False)

      # Process all messages
      worker_obj.RunOnce()
      worker_obj.thread_pool.Join()

    flow_obj = aff4.FACTORY.Open(session_id, token=self.token)
    self.assertEqual(flow_obj.state.context.state,
                     rdfvalue.Flow.State.RUNNING)

    # Set the time to max worker flow duration + 1 minute. If the 'kill'
    # notification isn't deleted we should get it now.
    future_time = initial_time + rdfvalue.Duration("1m") + stuck_flows_timeout
    with test_lib.FakeTime(future_time.AsSecondsFromEpoch()):
      worker_obj.RunOnce()
      worker_obj.thread_pool.Join()

    flow_obj = aff4.FACTORY.Open(session_id, token=self.token)
    # Check that flow didn't get terminated due to a logic bug.
    self.assertEqual(flow_obj.state.context.state,
                     rdfvalue.Flow.State.RUNNING)

  def testProcessMessagesWellKnown(self):
    worker_obj = worker.GRRWorker(worker.DEFAULT_WORKER_QUEUE,
                                  token=self.token)

    # Send a message to a WellKnownFlow - ClientStatsAuto.
    client_id = rdfvalue.ClientURN("C.1100110011001100")
    self.SendResponse(rdfvalue.SessionID("aff4:/flows/W:Stats"),
                      data=rdfvalue.ClientStats(RSS_size=1234),
                      client_id=client_id, well_known=True)

    # Process all messages
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    client = aff4.FACTORY.Open(client_id.Add("stats"), token=self.token)
    stats = client.Get(client.Schema.STATS)
    self.assertEqual(stats.RSS_size, 1234)

    # Make sure no notifications have been sent.
    user = aff4.FACTORY.Open("aff4:/users/%s" % self.token.username,
                             token=self.token)
    notifications = user.Get(user.Schema.PENDING_NOTIFICATIONS)
    self.assertIsNone(notifications)

  def CheckNotificationsDisappear(self, session_id):
    worker_obj = worker.GRRWorker(worker.DEFAULT_WORKER_QUEUE,
                                  token=self.token)
    manager = queue_manager.QueueManager(token=self.token)
    notification = rdfvalue.GrrNotification(session_id=session_id)
    manager.NotifyQueue(notification)

    notifications = manager.GetNotificationsByPriority(
        worker.DEFAULT_WORKER_QUEUE).get(notification.priority, [])

    # Check the notification is there.
    self.assertEqual(len(notifications), 1)
    self.assertEqual(notifications[0].session_id, session_id)

    # Process all messages
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    notifications = manager.GetNotificationsByPriority(
        worker.DEFAULT_WORKER_QUEUE).get(notification.priority, [])
    # Check the notification is now gone.
    self.assertEqual(len(notifications), 0)

  def testWorkerDeletesNotificationsForBrokenObjects(self):
    # Test notifications for objects that don't exist.
    session_id = rdfvalue.SessionID("aff4:/flows/W:123456")

    self.CheckNotificationsDisappear(session_id)

    # Now check objects that are actually broken.

    # Start a new flow.
    session_id = flow.GRRFlow.StartFlow(flow_name="WorkerSendingTestFlow",
                                        client_id=self.client_id,
                                        token=self.token)
    # Overwrite the type of the object such that opening it will now fail.
    data_store.DB.Set(session_id, "aff4:type", "DeprecatedClass",
                      token=self.token)

    # Starting a new flow schedules notifications for the worker already but
    # this test actually checks that there are none. Thus, we have to delete
    # them or the test fails.
    data_store.DB.DeleteSubject(worker.DEFAULT_WORKER_QUEUE, token=self.token)

    # Check it really does.
    with self.assertRaises(aff4.InstantiationError):
      aff4.FACTORY.Open(session_id, token=self.token)

    self.CheckNotificationsDisappear(session_id)

  def testNotificationRacesAreResolved(self):
    # We need a random flow object for this test.
    session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        flow_name="WorkerSendingTestFlow",
                                        token=self.token)
    worker_obj = worker.GRRWorker(worker.DEFAULT_WORKER_QUEUE,
                                  token=self.token)
    manager = queue_manager.QueueManager(token=self.token)
    manager.DeleteNotification(session_id)
    manager.Flush()

    # We simulate a race condition here - the notification for request #1 is
    # there but the actual request #1 is not. The worker should pick up the
    # notification, notice that the request #1 is not there yet and reschedule
    # the notification.
    notification = rdfvalue.GrrNotification(session_id=session_id,
                                            last_status=1)
    manager.NotifyQueue(notification)

    notifications = manager.GetNotifications(worker.DEFAULT_WORKER_QUEUE)
    # Check the notification is there.
    notifications = [n for n in notifications if n.session_id == session_id]
    self.assertEqual(len(notifications), 1)

    # Process all messages
    worker_obj.RunOnce()
    worker_obj.thread_pool.Join()

    delay = config_lib.CONFIG["Worker.notification_retry_interval"]
    with test_lib.FakeTime(time.time() + 10 + delay):
      requeued_notifications = manager.GetNotifications(
          worker.DEFAULT_WORKER_QUEUE)
      # Check that there is a new notification.
      notifications = [n for n in notifications if n.session_id == session_id]
      self.assertEqual(len(requeued_notifications), 1)

      self.assertEqual(requeued_notifications[0].first_queued,
                       notifications[0].first_queued)
      self.assertNotEqual(requeued_notifications[0].timestamp,
                          notifications[0].timestamp)


def main(_):
  test_lib.main()

if __name__ == "__main__":
  flags.StartMain(main)
