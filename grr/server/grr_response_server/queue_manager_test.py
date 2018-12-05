#!/usr/bin/env python
"""Tests the queue manager."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import time

from builtins import range  # pylint: disable=redefined-builtin
import mock

from grr_response_core.lib import flags
from grr_response_core.lib import queues
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.stats import stats_collector_instance
from grr_response_server import data_store
from grr_response_server import queue_manager
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

# pylint: mode=test


class QueueManagerTest(flow_test_lib.FlowTestsBaseclass):
  """Test the task scheduler abstraction."""

  def setUp(self):
    super(QueueManagerTest, self).setUp()
    stats_collector = stats_collector_instance.Get()
    self.retransmission_metric_value = stats_collector.GetMetricValue(
        "grr_task_retransmission_count")

    self._current_mock_time = 1000.015
    self.old_time = time.time
    time.time = lambda: self._current_mock_time

  def tearDown(self):
    time.time = self.old_time
    super(QueueManagerTest, self).tearDown()

  def testCountsActualNumberOfCompletedResponsesWhenApplyingTheLimit(self):
    session_id = rdfvalue.SessionID(flow_name="test")

    # Now queue more requests and responses:
    with queue_manager.QueueManager(token=self.token) as manager:
      # Start with request 1 - leave request 1 un-responded to.
      for request_id in range(5):
        request = rdf_flow_runner.RequestState(
            id=request_id,
            client_id=test_lib.TEST_CLIENT_ID,
            next_state="TestState",
            session_id=session_id)

        manager.QueueRequest(request)

        # Don't queue any actual responses, just a status message with a
        # fake response_id.
        manager.QueueResponse(
            rdf_flows.GrrMessage(
                session_id=session_id,
                request_id=request_id,
                response_id=1000,
                type=rdf_flows.GrrMessage.Type.STATUS))

    # Check that even though status message for every request indicates 1000
    # responses, only the actual response count is used to apply the limit
    # when FetchCompletedResponses is called.
    completed_response = list(
        manager.FetchCompletedResponses(session_id, limit=5))
    self.assertLen(completed_response, 5)
    for i, (request, responses) in enumerate(completed_response):
      self.assertEqual(request.id, i)
      # Responses contain just the status message.
      self.assertLen(responses, 1)

  def testDeleteRequest(self):
    """Check that we can efficiently destroy a single flow request."""
    session_id = rdfvalue.SessionID(flow_name="test3")

    request = rdf_flow_runner.RequestState(
        id=1,
        client_id=test_lib.TEST_CLIENT_ID,
        next_state="TestState",
        session_id=session_id)

    with queue_manager.QueueManager(token=self.token) as manager:
      manager.QueueRequest(request)
      manager.QueueResponse(
          rdf_flows.GrrMessage(
              session_id=session_id, request_id=1, response_id=1))

    # Check the request and responses are there.
    all_requests = list(manager.FetchRequestsAndResponses(session_id))
    self.assertLen(all_requests, 1)
    self.assertEqual(all_requests[0][0], request)

    with queue_manager.QueueManager(token=self.token) as manager:
      manager.DeleteRequest(request)

    all_requests = list(manager.FetchRequestsAndResponses(session_id))
    self.assertEmpty(all_requests)

  def testDestroyFlowStates(self):
    """Check that we can efficiently destroy the flow's request queues."""
    session_id = rdfvalue.SessionID(flow_name="test2")

    request = rdf_flow_runner.RequestState(
        id=1,
        client_id=test_lib.TEST_CLIENT_ID,
        next_state="TestState",
        session_id=session_id)

    with queue_manager.QueueManager(token=self.token) as manager:
      manager.QueueRequest(request)
      manager.QueueResponse(
          rdf_flows.GrrMessage(
              request_id=1, response_id=1, session_id=session_id))

    # Check the request and responses are there.
    all_requests = list(manager.FetchRequestsAndResponses(session_id))
    self.assertLen(all_requests, 1)
    self.assertEqual(all_requests[0][0], request)

    # Read the response directly.
    responses = data_store.DB.ReadResponsesForRequestId(session_id, 1)
    self.assertLen(responses, 1)
    response = responses[0]
    self.assertEqual(response.request_id, 1)
    self.assertEqual(response.response_id, 1)
    self.assertEqual(response.session_id, session_id)

    with queue_manager.QueueManager(token=self.token) as manager:
      manager.DestroyFlowStates(session_id)

    all_requests = list(manager.FetchRequestsAndResponses(session_id))
    self.assertEmpty(all_requests)

    # Check that the response is gone.
    responses = data_store.DB.ReadResponsesForRequestId(session_id, 1)
    self.assertEmpty(responses)

    # Ensure the rows are gone from the data store. Some data stores
    # don't store the queues in that way but there is no harm in
    # checking.
    self.assertEqual(
        data_store.DB.ResolveRow(session_id.Add("state/request:00000001")), [])

    self.assertEqual(data_store.DB.ResolveRow(session_id.Add("state")), [])

  def testSchedule(self):
    """Test the ability to schedule a task."""
    test_queue = rdfvalue.RDFURN("fooSchedule")
    task = rdf_flows.GrrMessage(
        queue=test_queue,
        task_ttl=5,
        session_id="aff4:/Test",
        generate_task_id=True)
    manager = queue_manager.QueueManager(token=self.token)
    with data_store.DB.GetMutationPool() as pool:
      manager.Schedule([task], pool)

    self.assertGreater(task.task_id, 0)
    self.assertGreater(task.task_id & 0xffffffff, 0)
    self.assertEqual((int(self._current_mock_time * 1000) & 0xffffffff) << 32,
                     task.task_id
                     & 0x1fffffff00000000)
    self.assertEqual(task.task_ttl, 5)

    stored_tasks = data_store.DB.QueueQueryTasks(test_queue, limit=100000)
    self.assertLen(stored_tasks, 1)
    stored_task = stored_tasks[0]
    self.assertGreater(stored_task.leased_until, 0)
    stored_task.leased_until = None

    self.assertRDFValuesEqual(stored_task, task)

    # Get a lease on the task
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertLen(tasks, 1)
    self.assertEqual(tasks[0].task_ttl, 4)

    self.assertEqual(tasks[0].session_id, "aff4:/Test")

    # If we try to get another lease on it we should fail
    self._current_mock_time += 10
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEmpty(tasks)

    # However after 100 seconds this should work again
    self._current_mock_time += 110
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertLen(tasks, 1)
    self.assertEqual(tasks[0].task_ttl, 3)

    # Check now that after a few retransmits we drop the message
    for i in range(2, 0, -1):
      self._current_mock_time += 110
      tasks = manager.QueryAndOwn(test_queue, lease_seconds=100)

      self.assertLen(tasks, 1)
      self.assertEqual(tasks[0].task_ttl, i)

    # The task is now gone
    self._current_mock_time += 110
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100)
    self.assertEmpty(tasks)

  def testTaskRetransmissionsAreCorrectlyAccounted(self):
    test_queue = rdfvalue.RDFURN("fooSchedule")
    task = rdf_flows.GrrMessage(
        queue=test_queue,
        task_ttl=5,
        session_id="aff4:/Test",
        generate_task_id=True)

    manager = queue_manager.QueueManager(token=self.token)
    with data_store.DB.GetMutationPool() as pool:
      manager.Schedule([task], pool)

    # Get a lease on the task
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertLen(tasks, 1)
    self.assertEqual(tasks[0].task_ttl, 4)

    self.assertEqual(
        stats_collector_instance.Get().GetMetricValue(
            "grr_task_retransmission_count"), self.retransmission_metric_value)

    # Get a lease on the task 100 seconds later
    self._current_mock_time += 110
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertLen(tasks, 1)
    self.assertEqual(tasks[0].task_ttl, 3)

    self.assertEqual(
        stats_collector_instance.Get().GetMetricValue(
            "grr_task_retransmission_count"),
        self.retransmission_metric_value + 1)

  def testDelete(self):
    """Test that we can delete tasks."""

    test_queue = rdfvalue.RDFURN("fooDelete")
    task = rdf_flows.GrrMessage(
        queue=test_queue, session_id="aff4:/Test", generate_task_id=True)

    with data_store.DB.GetMutationPool() as pool:
      manager = queue_manager.QueueManager(token=self.token)
      manager.Schedule([task], pool)

    # Get a lease on the task
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertLen(tasks, 1)

    self.assertEqual(tasks[0].session_id, "aff4:/Test")

    # Now delete the task
    with data_store.DB.GetMutationPool() as pool:
      manager.Delete(test_queue, tasks, mutation_pool=pool)

    # Task is now deleted.
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEmpty(tasks)

    # If we try to get another lease on it we should fail - even after
    # expiry time.
    self._current_mock_time += 1000
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEmpty(tasks)

  def testReSchedule(self):
    """Test the ability to re-schedule a task."""
    test_queue = rdfvalue.RDFURN("fooReschedule")
    task = rdf_flows.GrrMessage(
        queue=test_queue,
        task_ttl=5,
        session_id="aff4:/Test",
        generate_task_id=True)

    manager = queue_manager.QueueManager(token=self.token)
    with data_store.DB.GetMutationPool() as pool:
      manager.Schedule([task], pool)

    # Get a lease on the task
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertLen(tasks, 1)

    # Record the task id
    original_id = tasks[0].task_id

    # If we try to get another lease on it we should fail
    tasks_2 = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEmpty(tasks_2)

    # Now we reschedule it
    with data_store.DB.GetMutationPool() as pool:
      manager.Schedule([task], pool)

    # The id should not change
    self.assertEqual(tasks[0].task_id, original_id)

    # If we try to get another lease on it we should not fail
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertLen(tasks, 1)

    # But the id should not change
    self.assertEqual(tasks[0].task_id, original_id)

  def testUsesFrozenTimestampWhenDeletingAndFetchingNotifications(self):
    # When used in "with" statement QueueManager uses the frozen timestamp
    # when fetching and deleting data. Test that if we have 2 managers
    # created at different times,  they will behave correctly when dealing
    # with notifications for the same session ids. I.e. older queue_manager
    # will only "see" it's own notification and younger queue_manager will
    # "see" both.
    with queue_manager.QueueManager(token=self.token) as manager1:
      manager1.QueueNotification(
          session_id=rdfvalue.SessionID(
              base="aff4:/hunts", queue=queues.HUNTS, flow_name="123456"))
      manager1.Flush()

      self._current_mock_time += 10
      with queue_manager.QueueManager(token=self.token) as manager2:
        manager2.QueueNotification(
            session_id=rdfvalue.SessionID(
                base="aff4:/hunts", queue=queues.HUNTS, flow_name="123456"))
        manager2.Flush()

        self.assertEqual(
            len(manager1.GetNotificationsForAllShards(queues.HUNTS)), 1)
        self.assertEqual(
            len(manager2.GetNotificationsForAllShards(queues.HUNTS)), 1)

        manager1.DeleteNotification(
            rdfvalue.SessionID(
                base="aff4:/hunts", queue=queues.HUNTS, flow_name="123456"))

        self.assertEqual(
            len(manager1.GetNotificationsForAllShards(queues.HUNTS)), 0)
        self.assertEqual(
            len(manager2.GetNotificationsForAllShards(queues.HUNTS)), 1)

  def testMultipleNotificationsForTheSameSessionId(self):
    manager = queue_manager.QueueManager(token=self.token)
    manager.QueueNotification(
        session_id=rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="123456"),
        timestamp=(self._current_mock_time + 10) * 1e6)
    manager.QueueNotification(
        session_id=rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="123456"),
        timestamp=(self._current_mock_time + 20) * 1e6)
    manager.QueueNotification(
        session_id=rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="123456"),
        timestamp=(self._current_mock_time + 30) * 1e6)
    manager.Flush()

    self.assertEmpty(manager.GetNotificationsForAllShards(queues.HUNTS))

    self._current_mock_time += 10
    self.assertLen(manager.GetNotificationsForAllShards(queues.HUNTS), 1)
    manager.DeleteNotification(
        rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="123456"))

    self._current_mock_time += 10
    self.assertLen(manager.GetNotificationsForAllShards(queues.HUNTS), 1)
    manager.DeleteNotification(
        rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="123456"))

    self._current_mock_time += 10
    self.assertLen(manager.GetNotificationsForAllShards(queues.HUNTS), 1)
    manager.DeleteNotification(
        rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="123456"))

    self._current_mock_time += 10
    self.assertEmpty(manager.GetNotificationsForAllShards(queues.HUNTS))

  def testGetClientIdFromQueue(self):

    def MockQueue(path):
      return mock.MagicMock(Split=lambda: path.split("/")[1:])

    # Returns None if the path can't be parsed.
    self.assertIsNone(
        queue_manager._GetClientIdFromQueue(MockQueue("arbitrary string")))

    # Returns None if the queue isn't a client queue.
    self.assertIsNone(
        queue_manager._GetClientIdFromQueue(MockQueue("/H.fedcba98")))
    self.assertIsNone(
        queue_manager._GetClientIdFromQueue(MockQueue("/H.01234567/tasks")))

    # Returns None if the object isn't a queue.
    self.assertIsNone(
        queue_manager._GetClientIdFromQueue(MockQueue("/C.0123456789abcdef0")))
    # Returns client ID if the queue is a client queue.
    self.assertEqual(
        "C.abcdefabcdefabcde",
        queue_manager._GetClientIdFromQueue(
            MockQueue("/C.ABCDefabcdefabcde/tasks")))

    # Letter case doesn't matter. The return value is always lowercase, except
    # for the capital "C" in the front.
    self.assertEqual(
        "C.0123456789abcdef0",
        queue_manager._GetClientIdFromQueue(
            MockQueue("/C.0123456789AbCdEF0/TasKS")))
    self.assertEqual(
        "C.abcdefabcdefabcde",
        queue_manager._GetClientIdFromQueue(
            MockQueue("/c.ABCDEFABCDEFABCDE/tasks")))


class MultiShardedQueueManagerTest(QueueManagerTest):
  """Test for QueueManager with multiple notification shards enabled."""

  def setUp(self):
    super(MultiShardedQueueManagerTest, self).setUp()

    self.config_overrider = test_lib.ConfigOverrider({"Worker.queue_shards": 2})
    self.config_overrider.Start()

  def tearDown(self):
    super(MultiShardedQueueManagerTest, self).tearDown()
    self.config_overrider.Stop()

  def testFirstShardNameIsEqualToTheQueue(self):
    manager = queue_manager.QueueManager(token=self.token)
    while True:
      shard = manager.GetNotificationShard(queues.HUNTS)
      if (manager.notification_shard_counters[str(queues.HUNTS)] %
          manager.num_notification_shards) == 0:
        break

    self.assertEqual(shard, queues.HUNTS)

  def testNotFirstShardNameHasIndexSuffix(self):
    manager = queue_manager.QueueManager(token=self.token)
    while True:
      shard = manager.GetNotificationShard(queues.HUNTS)
      if (manager.notification_shard_counters[str(queues.HUNTS)] %
          manager.num_notification_shards) == 1:
        break

    self.assertEqual(shard, queues.HUNTS.Add("1"))

  def testNotificationsAreDeletedFromAllShards(self):
    manager = queue_manager.QueueManager(token=self.token)
    manager.QueueNotification(
        session_id=rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="42"))
    manager.Flush()
    manager.QueueNotification(
        session_id=rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="43"))
    manager.Flush()
    # There should be two notifications in two different shards.
    shards_with_data = 0
    for _ in range(manager.num_notification_shards):
      shard_sessions = manager.GetNotifications(queues.HUNTS)
      if shard_sessions:
        shards_with_data += 1
        self.assertLen(shard_sessions, 1)
    self.assertEqual(shards_with_data, 2)

    # This should still work, as we delete notifications from all shards.
    manager.DeleteNotification(
        rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="43"))
    manager.DeleteNotification(
        rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="42"))
    for _ in range(manager.num_notification_shards):
      shard_sessions = manager.GetNotifications(queues.HUNTS)
      self.assertFalse(shard_sessions)

  def testGetNotificationsForAllShards(self):
    manager = queue_manager.QueueManager(token=self.token)
    manager.QueueNotification(
        session_id=rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="42"))
    manager.Flush()

    manager.QueueNotification(
        session_id=rdfvalue.SessionID(
            base="aff4:/hunts", queue=queues.HUNTS, flow_name="43"))
    manager.Flush()

    live_shard_count = 0
    for _ in range(manager.num_notification_shards):
      shard_sessions = manager.GetNotifications(queues.HUNTS)
      self.assertLess(len(shard_sessions), 2)
      if len(shard_sessions) == 1:
        live_shard_count += 1
    self.assertEqual(live_shard_count, 2)

    notifications = manager.GetNotificationsForAllShards(queues.HUNTS)
    self.assertLen(notifications, 2)

  def testNotificationRequeueing(self):
    with test_lib.ConfigOverrider({"Worker.queue_shards": 1}):
      session_id = rdfvalue.SessionID(
          base="aff4:/testflows", queue=queues.HUNTS, flow_name="123")
      with test_lib.FakeTime(1000):
        # Schedule a notification.
        with queue_manager.QueueManager(token=self.token) as manager:
          manager.QueueNotification(session_id=session_id)

      with test_lib.FakeTime(1100):
        with queue_manager.QueueManager(token=self.token) as manager:
          notifications = manager.GetNotifications(queues.HUNTS)
          self.assertLen(notifications, 1)
          # This notification was first queued and last queued at time 1000.
          notification = notifications[0]
          self.assertEqual(notification.timestamp.AsSecondsSinceEpoch(), 1000)
          self.assertEqual(notification.first_queued.AsSecondsSinceEpoch(),
                           1000)
          # Now requeue the same notification.
          manager.DeleteNotification(session_id)
          manager.QueueNotification(notification)

      with test_lib.FakeTime(1200):
        with queue_manager.QueueManager(token=self.token) as manager:
          notifications = manager.GetNotifications(queues.HUNTS)
          self.assertLen(notifications, 1)
          notification = notifications[0]
          # Now the last queue time is 1100, the first queue time is still 1000.
          self.assertEqual(notification.timestamp.AsSecondsSinceEpoch(), 1100)
          self.assertEqual(notification.first_queued.AsSecondsSinceEpoch(),
                           1000)
          # Again requeue the same notification.
          manager.DeleteNotification(session_id)
          manager.QueueNotification(notification)

      expired = 1000 + queue_manager.QueueManager.notification_expiry_time
      with test_lib.FakeTime(expired):
        with queue_manager.QueueManager(token=self.token) as manager:
          notifications = manager.GetNotifications(queues.HUNTS)
          self.assertLen(notifications, 1)
          # Again requeue the notification, this time it should be dropped.
          manager.DeleteNotification(session_id)
          manager.QueueNotification(notifications[0])

        with queue_manager.QueueManager(token=self.token) as manager:
          notifications = manager.GetNotifications(queues.HUNTS)
          self.assertEmpty(notifications)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
