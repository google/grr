#!/usr/bin/env python
"""Tests the queue manager."""


import time


from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import flags
from grr.lib import queue_manager
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib import test_lib
from grr.lib.rdfvalues import flows as rdf_flows

# pylint: mode=test


class QueueManagerTest(test_lib.FlowTestsBaseclass):
  """Test the task scheduler abstraction."""

  def setUp(self):
    super(QueueManagerTest, self).setUp()

    self.retransmission_metric_value = stats.STATS.GetMetricValue(
        "grr_task_retransmission_count")

    test_lib.GRRBaseTest.setUp(self)
    self._current_mock_time = 1000.015
    self.old_time = time.time
    time.time = lambda: self._current_mock_time

  def tearDown(self):
    time.time = self.old_time

  def testQueueing(self):
    """Tests that queueing and fetching of requests and responses work."""
    session_id = rdfvalue.SessionID(flow_name="test")

    request = rdf_flows.RequestState(
        id=1, client_id=self.client_id,
        next_state="TestState",
        session_id=session_id)

    with queue_manager.QueueManager(token=self.token) as manager:
      manager.QueueRequest(session_id, request)

    # We only have one unanswered request on the queue.
    all_requests = list(manager.FetchRequestsAndResponses(session_id))
    self.assertEqual(len(all_requests), 1)
    self.assertEqual(all_requests[0], (request, []))

    # FetchCompletedRequests should return nothing now.
    self.assertEqual(list(manager.FetchCompletedRequests(session_id)), [])

    # Now queue more requests and responses:
    with queue_manager.QueueManager(token=self.token) as manager:
      # Start with request 2 - leave request 1 un-responded to.
      for request_id in range(2, 5):
        request = rdf_flows.RequestState(
            id=request_id, client_id=self.client_id,
            next_state="TestState", session_id=session_id)

        manager.QueueRequest(session_id, request)

        response_id = None
        for response_id in range(1, 10):
          # Normal message.
          manager.QueueResponse(session_id, rdf_flows.GrrMessage(
              request_id=request_id, response_id=response_id))

        # And a status message.
        manager.QueueResponse(session_id, rdf_flows.GrrMessage(
            request_id=request_id, response_id=response_id + 1,
            type=rdf_flows.GrrMessage.Type.STATUS))

    completed_requests = list(manager.FetchCompletedRequests(session_id))
    self.assertEqual(len(completed_requests), 3)

    # First completed message is request_id = 2 with 10 responses.
    self.assertEqual(completed_requests[0][0].id, 2)

    # Last message is the status message.
    self.assertEqual(completed_requests[0][-1].type,
                     rdf_flows.GrrMessage.Type.STATUS)
    self.assertEqual(completed_requests[0][-1].response_id, 10)

    # Now fetch all the completed responses. Set the limit so we only fetch some
    # of the responses.
    completed_response = list(manager.FetchCompletedResponses(session_id))
    self.assertEqual(len(completed_response), 3)
    for i, (request, responses) in enumerate(completed_response, 2):
      self.assertEqual(request.id, i)
      self.assertEqual(len(responses), 10)

    # Now check if the limit is enforced. The limit refers to the total number
    # of responses to return. We ask for maximum 15 responses, so we should get
    # a single request with 10 responses (since 2 requests will exceed the
    # limit).
    more_data = False
    i = 0
    try:
      partial_response = manager.FetchCompletedResponses(session_id, limit=15)
      for i, (request, responses) in enumerate(partial_response, 2):
        self.assertEqual(request.id, i)
        self.assertEqual(len(responses), 10)
    except queue_manager.MoreDataException:
      more_data = True

    # Returns the first request that is completed.
    self.assertEqual(i, 3)

    # Make sure the manager told us that more data is available.
    self.assertTrue(more_data)

  def testDeleteFlowRequestStates(self):
    """Check that we can efficiently destroy a single flow request."""
    session_id = rdfvalue.SessionID(flow_name="test3")

    request = rdf_flows.RequestState(
        id=1, client_id=self.client_id,
        next_state="TestState",
        session_id=session_id)

    with queue_manager.QueueManager(token=self.token) as manager:
      manager.QueueRequest(session_id, request)
      manager.QueueResponse(session_id, rdf_flows.GrrMessage(
          request_id=1, response_id=1))

    # Check the request and responses are there.
    all_requests = list(manager.FetchRequestsAndResponses(session_id))
    self.assertEqual(len(all_requests), 1)
    self.assertEqual(all_requests[0][0], request)

    with queue_manager.QueueManager(token=self.token) as manager:
      manager.DeleteFlowRequestStates(session_id, request)

    all_requests = list(manager.FetchRequestsAndResponses(session_id))
    self.assertEqual(len(all_requests), 0)

  def testDestroyFlowStates(self):
    """Check that we can efficiently destroy the flow's request queues."""
    session_id = rdfvalue.SessionID(flow_name="test2")

    request = rdf_flows.RequestState(
        id=1, client_id=self.client_id,
        next_state="TestState",
        session_id=session_id)

    with queue_manager.QueueManager(token=self.token) as manager:
      manager.QueueRequest(session_id, request)
      manager.QueueResponse(session_id, rdf_flows.GrrMessage(
          request_id=1, response_id=1))

    # Check the request and responses are there.
    all_requests = list(manager.FetchRequestsAndResponses(session_id))
    self.assertEqual(len(all_requests), 1)
    self.assertEqual(all_requests[0][0], request)

    # Ensure the rows are in the data store:
    self.assertEqual(
        data_store.DB.ResolveRegex(
            session_id.Add("state"), ".*", token=self.token)[0][0],
        "flow:request:00000001")

    self.assertEqual(
        data_store.DB.ResolveRegex(
            session_id.Add("state/request:00000001"), ".*",
            token=self.token)[0][0],
        "flow:response:00000001:00000001")

    with queue_manager.QueueManager(token=self.token) as manager:
      manager.DestroyFlowStates(session_id)

    all_requests = list(manager.FetchRequestsAndResponses(session_id))
    self.assertEqual(len(all_requests), 0)

    # Ensure the rows are gone from the data store.
    self.assertEqual(
        data_store.DB.ResolveRegex(
            session_id.Add("state/request:00000001"), ".*", token=self.token),
        [])

    self.assertEqual(
        data_store.DB.ResolveRegex(
            session_id.Add("state"), ".*", token=self.token), [])

  def testSchedule(self):
    """Test the ability to schedule a task."""
    test_queue = rdfvalue.RDFURN("fooSchedule")
    task = rdf_flows.GrrMessage(queue=test_queue, task_ttl=5,
                                session_id="aff4:/Test")
    manager = queue_manager.QueueManager(token=self.token)
    manager.Schedule([task])

    self.assert_(task.task_id > 0)
    self.assert_(task.task_id & 0xffffffff > 0)
    self.assertEqual((long(self._current_mock_time * 1000) & 0xffffffff) << 32,
                     task.task_id & 0x1fffffff00000000)
    self.assertEqual(task.task_ttl, 5)

    value, ts = data_store.DB.Resolve(
        test_queue, manager._TaskIdToColumn(task.task_id),
        token=self.token)

    decoded = rdf_flows.GrrMessage(value)
    self.assertRDFValueEqual(decoded, task)
    self.assert_(ts > 0)

    # Get a lease on the task
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEqual(len(tasks), 1)
    self.assertEqual(tasks[0].task_ttl, 4)

    self.assertEqual(tasks[0].session_id, "aff4:/Test")

    # If we try to get another lease on it we should fail
    self._current_mock_time += 10
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEqual(len(tasks), 0)

    # However after 100 seconds this should work again
    self._current_mock_time += 110
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEqual(len(tasks), 1)
    self.assertEqual(tasks[0].task_ttl, 3)

    # Check now that after a few retransmits we drop the message
    for i in range(2, 0, -1):
      self._current_mock_time += 110
      tasks = manager.QueryAndOwn(test_queue, lease_seconds=100)

      self.assertEqual(len(tasks), 1)
      self.assertEqual(tasks[0].task_ttl, i)

    # The task is now gone
    self._current_mock_time += 110
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100)
    self.assertEqual(len(tasks), 0)

  def testTaskRetransmissionsAreCorrectlyAccounted(self):
    test_queue = rdfvalue.RDFURN("fooSchedule")
    task = rdf_flows.GrrMessage(queue=test_queue,
                                task_ttl=5, session_id="aff4:/Test")

    manager = queue_manager.QueueManager(token=self.token)
    manager.Schedule([task])

    # Get a lease on the task
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEqual(len(tasks), 1)
    self.assertEqual(tasks[0].task_ttl, 4)

    self.assertEqual(
        stats.STATS.GetMetricValue("grr_task_retransmission_count"),
        self.retransmission_metric_value)

    # Get a lease on the task 100 seconds later
    self._current_mock_time += 110
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEqual(len(tasks), 1)
    self.assertEqual(tasks[0].task_ttl, 3)

    self.assertEqual(
        stats.STATS.GetMetricValue("grr_task_retransmission_count"),
        self.retransmission_metric_value + 1)

  def testDelete(self):
    """Test that we can delete tasks."""

    test_queue = rdfvalue.RDFURN("fooDelete")
    task = rdf_flows.GrrMessage(queue=test_queue,
                                session_id="aff4:/Test")

    manager = queue_manager.QueueManager(token=self.token)
    manager.Schedule([task])

    # Get a lease on the task
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEqual(len(tasks), 1)

    self.assertEqual(tasks[0].session_id, "aff4:/Test")

    # Now delete the task
    manager.Delete(test_queue, tasks)

    # Should not exist in the table
    value, ts = data_store.DB.Resolve(test_queue,
                                      "task:%08d" % task.task_id,
                                      token=self.token)

    self.assertEqual(value, None)
    self.assertEqual(ts, 0)

    # If we try to get another lease on it we should fail - even after
    # expiry time.
    self._current_mock_time += 1000
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEqual(len(tasks), 0)

  def testReSchedule(self):
    """Test the ability to re-schedule a task."""
    test_queue = rdfvalue.RDFURN("fooReschedule")
    task = rdf_flows.GrrMessage(queue=test_queue, task_ttl=5,
                                session_id="aff4:/Test")

    manager = queue_manager.QueueManager(token=self.token)
    manager.Schedule([task])

    # Get a lease on the task
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEqual(len(tasks), 1)

    # Record the task id
    original_id = tasks[0].task_id

    # If we try to get another lease on it we should fail
    tasks_2 = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEqual(len(tasks_2), 0)

    # Now we reschedule it
    manager.Schedule(tasks)

    # The id should not change
    self.assertEqual(tasks[0].task_id, original_id)

    # If we try to get another lease on it we should not fail
    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEqual(len(tasks), 1)

    # But the id should not change
    self.assertEqual(tasks[0].task_id, original_id)

  def testPriorityScheduling(self):
    test_queue = rdfvalue.RDFURN("fooReschedule")

    tasks = []
    for i in range(10):
      msg = rdf_flows.GrrMessage(
          session_id="Test%d" % i,
          priority=i % 3,
          queue=test_queue)

      tasks.append(msg)

    manager = queue_manager.QueueManager(token=self.token)
    manager.Schedule(tasks)

    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=3)

    self.assertEqual(len(tasks), 3)
    for task in tasks:
      self.assertEqual(task.priority, 2)

    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=3)

    self.assertEqual(len(tasks), 3)
    for task in tasks:
      self.assertEqual(task.priority, 1)

    tasks = manager.QueryAndOwn(test_queue, lease_seconds=100, limit=100)

    self.assertEqual(len(tasks), 4)
    for task in tasks:
      self.assertEqual(task.priority, 0)

    # Now for Query.
    tasks = manager.Query(test_queue, limit=100)
    self.assertEqual(len(tasks), 10)
    self.assertEqual([task.priority for task in tasks],
                     [2, 2, 2, 1, 1, 1, 0, 0, 0, 0])

  def testUsesFrozenTimestampWhenDeletingAndFetchingNotifications(self):
    # When used in "with" statement QueueManager uses the frozen timestamp
    # when fetching and deleting data. Test that if we have 2 managers
    # created at different times,  they will behave correctly when dealing
    # with notifications for the same session ids. I.e. older queue_manager
    # will only "see" it's own notification and younger queue_manager will
    # "see" both.
    with queue_manager.QueueManager(token=self.token) as manager1:
      manager1.QueueNotification(
          session_id=rdfvalue.SessionID(base="aff4:/hunts",
                                        queue=queues.HUNTS,
                                        flow_name="123456"))
      manager1.Flush()

      self._current_mock_time += 10
      with queue_manager.QueueManager(token=self.token) as manager2:
        manager2.QueueNotification(
            session_id=rdfvalue.SessionID(base="aff4:/hunts",
                                          queue=queues.HUNTS,
                                          flow_name="123456"))
        manager2.Flush()

        self.assertEqual(
            len(manager1.GetNotificationsForAllShards(queues.HUNTS)), 1)
        self.assertEqual(
            len(manager2.GetNotificationsForAllShards(queues.HUNTS)), 1)

        manager1.DeleteNotification(rdfvalue.SessionID(base="aff4:/hunts",
                                                       queue=queues.HUNTS,
                                                       flow_name="123456"))

        self.assertEqual(
            len(manager1.GetNotificationsForAllShards(queues.HUNTS)), 0)
        self.assertEqual(
            len(manager2.GetNotificationsForAllShards(queues.HUNTS)), 1)

  def testMultipleNotificationsForTheSameSessionId(self):
    manager = queue_manager.QueueManager(token=self.token)
    manager.QueueNotification(
        session_id=rdfvalue.SessionID(base="aff4:/hunts",
                                      queue=queues.HUNTS,
                                      flow_name="123456"),
        timestamp=(self._current_mock_time + 10) * 1e6)
    manager.QueueNotification(
        session_id=rdfvalue.SessionID(base="aff4:/hunts",
                                      queue=queues.HUNTS,
                                      flow_name="123456"),
        timestamp=(self._current_mock_time + 20) * 1e6)
    manager.QueueNotification(
        session_id=rdfvalue.SessionID(base="aff4:/hunts",
                                      queue=queues.HUNTS,
                                      flow_name="123456"),
        timestamp=(self._current_mock_time + 30) * 1e6)
    manager.Flush()

    self.assertEqual(
        len(manager.GetNotificationsForAllShards(queues.HUNTS)), 0)

    self._current_mock_time += 10
    self.assertEqual(
        len(manager.GetNotificationsForAllShards(queues.HUNTS)), 1)
    manager.DeleteNotification(rdfvalue.SessionID(base="aff4:/hunts",
                                                  queue=queues.HUNTS,
                                                  flow_name="123456"))

    self._current_mock_time += 10
    self.assertEqual(
        len(manager.GetNotificationsForAllShards(queues.HUNTS)), 1)
    manager.DeleteNotification(rdfvalue.SessionID(base="aff4:/hunts",
                                                  queue=queues.HUNTS,
                                                  flow_name="123456"))

    self._current_mock_time += 10
    self.assertEqual(
        len(manager.GetNotificationsForAllShards(queues.HUNTS)), 1)
    manager.DeleteNotification(rdfvalue.SessionID(base="aff4:/hunts",
                                                  queue=queues.HUNTS,
                                                  flow_name="123456"))

    self._current_mock_time += 10
    self.assertEqual(
        len(manager.GetNotificationsForAllShards(queues.HUNTS)), 0)


class MultiShardedQueueManagerTest(QueueManagerTest):
  """Test for QueueManager with multiple notification shards enabled."""

  def setUp(self):
    super(MultiShardedQueueManagerTest, self).setUp()

    config_lib.CONFIG.Set("Worker.queue_shards", 2)

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
        session_id=rdfvalue.SessionID(base="aff4:/hunts",
                                      queue=queues.HUNTS,
                                      flow_name="42"))
    manager.Flush()
    manager.QueueNotification(
        session_id=rdfvalue.SessionID(base="aff4:/hunts",
                                      queue=queues.HUNTS,
                                      flow_name="43"))
    manager.Flush()
    # There should be two notifications in two different shards.
    shards_with_data = 0
    for _ in range(manager.num_notification_shards):
      shard_sessions = manager.GetNotifications(queues.HUNTS)
      if shard_sessions:
        shards_with_data += 1
        self.assertEqual(len(shard_sessions), 1)
    self.assertEqual(shards_with_data, 2)

    # This should still work, as we delete notifications from all shards.
    manager.DeleteNotification(rdfvalue.SessionID(base="aff4:/hunts",
                                                  queue=queues.HUNTS,
                                                  flow_name="43"))
    manager.DeleteNotification(rdfvalue.SessionID(base="aff4:/hunts",
                                                  queue=queues.HUNTS,
                                                  flow_name="42"))
    for _ in range(manager.num_notification_shards):
      shard_sessions = manager.GetNotifications(queues.HUNTS)
      self.assertFalse(shard_sessions)

  def testGetNotificationsForAllShards(self):
    manager = queue_manager.QueueManager(token=self.token)
    print "notification shards:" + str(manager.num_notification_shards)
    manager.QueueNotification(session_id=rdfvalue.SessionID(base="aff4:/hunts",
                                                            queue=queues.HUNTS,
                                                            flow_name="42"))
    manager.Flush()

    manager.QueueNotification(session_id=rdfvalue.SessionID(base="aff4:/hunts",
                                                            queue=queues.HUNTS,
                                                            flow_name="43"))
    manager.Flush()

    live_shard_count = 0
    for _ in range(manager.num_notification_shards):
      shard_sessions = manager.GetNotifications(queues.HUNTS)
      print "retrieved sessions:" + str(shard_sessions)
      self.assertLess(len(shard_sessions), 2)
      if len(shard_sessions) == 1:
        live_shard_count += 1
    self.assertEqual(live_shard_count, 2)

    notifications = manager.GetNotificationsForAllShards(queues.HUNTS)
    self.assertEqual(len(notifications), 2)

  def testNotificationRequeueing(self):
    config_lib.CONFIG.Set("Worker.queue_shards", 1)
    session_id = rdfvalue.SessionID(base="aff4:/testflows",
                                    queue=queues.HUNTS,
                                    flow_name="123")
    with test_lib.FakeTime(1000):
      # Schedule a notification.
      with queue_manager.QueueManager(token=self.token) as manager:
        manager.QueueNotification(session_id=session_id)

    with test_lib.FakeTime(1100):
      with queue_manager.QueueManager(token=self.token) as manager:
        notifications = manager.GetNotifications(queues.HUNTS)
        self.assertEqual(len(notifications), 1)
        # This notification was first queued and last queued at time 1000.
        notification = notifications[0]
        self.assertEqual(notification.timestamp.AsSecondsFromEpoch(), 1000)
        self.assertEqual(notification.first_queued.AsSecondsFromEpoch(), 1000)
        # Now requeue the same notification.
        manager.DeleteNotification(session_id)
        manager.QueueNotification(notification)

    with test_lib.FakeTime(1200):
      with queue_manager.QueueManager(token=self.token) as manager:
        notifications = manager.GetNotifications(queues.HUNTS)
        self.assertEqual(len(notifications), 1)
        notification = notifications[0]
        # Now the last queue time is 1100, the first queue time is still 1000.
        self.assertEqual(notification.timestamp.AsSecondsFromEpoch(), 1100)
        self.assertEqual(notification.first_queued.AsSecondsFromEpoch(), 1000)
        # Again requeue the same notification.
        manager.DeleteNotification(session_id)
        manager.QueueNotification(notification)

    expired = 1000 + config_lib.CONFIG["Worker.notification_expiry_time"]
    with test_lib.FakeTime(expired):
      with queue_manager.QueueManager(token=self.token) as manager:
        notifications = manager.GetNotifications(queues.HUNTS)
        self.assertEqual(len(notifications), 1)
        # Again requeue the notification, this time it should be dropped.
        manager.DeleteNotification(session_id)
        manager.QueueNotification(notifications[0])

      with queue_manager.QueueManager(token=self.token) as manager:
        notifications = manager.GetNotifications(queues.HUNTS)
        self.assertEqual(len(notifications), 0)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
