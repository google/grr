#!/usr/bin/env python

# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests the data store abstraction."""


import time


from grr.client import conf
from grr.client import conf as flags
from grr.lib import data_store
from grr.lib import flow
from grr.lib import test_lib
from grr.proto import jobs_pb2


FLAGS = flags.FLAGS


class SchedulerTest(test_lib.GRRBaseTest):
  """Test the Task Scheduler abstraction."""

  def setUp(self):
    test_lib.GRRBaseTest.setUp(self)
    self._current_mock_time = 1000.015
    self.old_time = time.time
    time.time = lambda: self._current_mock_time

  def tearDown(self):
    time.time = self.old_time

  def testSchedule(self):
    """Test the ability to schedule a task."""
    test_queue = "fooSchedule"
    task = flow.SCHEDULER.Task(queue=test_queue, ttl=5,
                               value=jobs_pb2.GrrMessage(session_id="Test"))

    flow.SCHEDULER.Schedule([task])

    self.assert_(task.id > 0)
    self.assertEqual(task.ttl, 5)
    value, ts = data_store.DB.Resolve("task:%s" % test_queue,
                                      "task:%08d" % task.id)

    self.assertEqual(value, task.SerializeToString())
    self.assert_(ts > 0)

    # Get a lease on the task
    tasks = flow.SCHEDULER.QueryAndOwn(
        test_queue, lease_seconds=100,
        limit=100, decoder=jobs_pb2.GrrMessage)

    self.assertEqual(len(tasks), 1)
    self.assertEqual(tasks[0].ttl, 4)

    self.assertEqual(tasks[0].value.session_id, "Test")

    # If we try to get another lease on it we should fail
    self._current_mock_time += 10
    tasks = flow.SCHEDULER.QueryAndOwn(
        test_queue, lease_seconds=100,
        limit=100, decoder=jobs_pb2.GrrMessage)

    self.assertEqual(len(tasks), 0)

    # However after 100 seconds this should work again
    self._current_mock_time += 110
    tasks = flow.SCHEDULER.QueryAndOwn(
        test_queue, lease_seconds=100,
        limit=100, decoder=jobs_pb2.GrrMessage)

    self.assertEqual(len(tasks), 1)
    self.assertEqual(tasks[0].ttl, 3)

    # Check now that after a few retransmits we drop the message
    for i in range(2, 0, -1):
      self._current_mock_time += 110
      tasks = flow.SCHEDULER.QueryAndOwn(test_queue, lease_seconds=100)

      self.assertEqual(len(tasks), 1)
      self.assertEqual(tasks[0].ttl, i)

    # The task is now gone
    self._current_mock_time += 110
    tasks = flow.SCHEDULER.QueryAndOwn(test_queue, lease_seconds=100)
    self.assertEqual(len(tasks), 0)

  def testDelete(self):
    """Test that we can delete tasks."""

    test_queue = "fooDelete"
    task = flow.SCHEDULER.Task(queue=test_queue,
                               value=jobs_pb2.GrrMessage(session_id="Test"))

    flow.SCHEDULER.Schedule([task])

    # Get a lease on the task
    tasks = flow.SCHEDULER.QueryAndOwn(
        test_queue, lease_seconds=100,
        limit=100, decoder=jobs_pb2.GrrMessage)

    self.assertEqual(len(tasks), 1)

    self.assertEqual(tasks[0].value.session_id, "Test")

    # Now delete the task
    flow.SCHEDULER.Delete(test_queue, tasks)

    # Should not exist in the table
    value, ts = data_store.DB.Resolve("task:%s" % test_queue,
                                      "task:%08d" % task.id)

    self.assertEqual(value, None)
    self.assertEqual(ts, 0)

    # If we try to get another lease on it we should fail - even after
    # expiry time.
    self._current_mock_time += 1000
    tasks = flow.SCHEDULER.QueryAndOwn(
        test_queue, lease_seconds=100,
        limit=100, decoder=jobs_pb2.GrrMessage)

    self.assertEqual(len(tasks), 0)

  def testReSchedule(self):
    """Test the ability to re-schedule a task."""
    test_queue = "fooReschedule"
    task = flow.SCHEDULER.Task(queue=test_queue, value=jobs_pb2.GrrMessage(
        session_id="Test"))

    flow.SCHEDULER.Schedule([task])

    # Get a lease on the task
    tasks = flow.SCHEDULER.QueryAndOwn(
        test_queue, lease_seconds=100,
        limit=100, decoder=jobs_pb2.GrrMessage)

    self.assertEqual(len(tasks), 1)

    # Record the task id
    original_id = tasks[0].id

    # If we try to get another lease on it we should fail
    tasks_2 = flow.SCHEDULER.QueryAndOwn(
        test_queue, lease_seconds=100,
        limit=100, decoder=jobs_pb2.GrrMessage)

    self.assertEqual(len(tasks_2), 0)

    # Now we reschedule it
    flow.SCHEDULER.Schedule(tasks)

    # The id should not change
    self.assertEqual(tasks[0].id, original_id)

    # If we try to get another lease on it we should not fail
    tasks = flow.SCHEDULER.QueryAndOwn(
        test_queue, lease_seconds=100,
        limit=100, decoder=jobs_pb2.GrrMessage)

    self.assertEqual(len(tasks), 1)

    # But the id should not change
    self.assertEqual(tasks[0].id, original_id)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  conf.StartMain(main)
