#!/usr/bin/env python

# Copyright 2011 Google Inc.
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

"""This is the main task scheduler."""

import functools
import logging
import time

from grr.lib import data_store
from grr.lib import utils
from grr.proto import jobs_pb2


class TaskScheduler(object):
  """Implements a mechanism for task scheduling.

  This effectively implements a workflow system based on the data
  store. The common usage pattern involves:

  1) Create a bunch of tasks using the Task() object above. Tasks must
  be assigned to queues and contain arbitrary values (possibly
  protobufs).

  2) Call TaskScheduler.Schedule(task) to add the tasks to their queues.

  3) In another thread, call TaskScheduler.QueryAndOwn(queue) to
  obtain a list of tasks leased for a particular time.

  4) If the lease time expires, the tasks automatically become
  available for consumption. When done with the task we can remove it
  from the scheduler using TaskScheduler.Delete(tasks).

  5) Tasks can be re-leased by calling TaskScheduler.Schedule(task)
  repeatedly. Each call will extend the lease by the specified amount.
  """
  # This is the column name for counting the next available task ID:
  MAX_TS_ID = "metadata:task_counter"
  SUBJECT_PREFIX = "task:"
  PREDICATE_PREFIX = "task:"

  @classmethod
  def QueueToSubject(cls, queue):
    """Return an object name which manages that queue."""
    return "%s%s" % (cls.SUBJECT_PREFIX, queue)

  def _TaskIdToColumn(self, task_id):
    """Return a predicate representing this task."""
    return "%s%08d" % (self.PREDICATE_PREFIX, task_id)

  @classmethod
  def SubjectToQueue(cls, row_name):
    """Convert a subject name to a queue name."""
    return row_name[len(cls.SUBJECT_PREFIX):]

  def Delete(self, queue, tasks):
    """Removes the tasks from the queue.

    Note that tasks can already have been removed. It is not an error
    to re-delete an already deleted task.

    Args:
     queue: A queue to clear.
     tasks: A list of tasks to remove. Tasks may be Task() instances
          or integers representing the task_id.
    """
    data_store.DB.RetryWrapper(self.QueueToSubject(queue),
                               self._Delete, tasks=tasks)

  def _Delete(self, transaction, tasks=None):
    for task in tasks:
      try:
        ts_id = task.id
      except AttributeError:
        ts_id = int(task)

      transaction.DeleteAttribute(self._TaskIdToColumn(ts_id))

  def Schedule(self, tasks):
    """Schedule a set of Task() instances."""
    for queue, queued_tasks in utils.GroupBy(tasks, lambda x: x.queue):
      if queue:
        data_store.DB.RetryWrapper(self.QueueToSubject(queue),
                                   self._Schedule, tasks=queued_tasks)

  def _Schedule(self, transaction, tasks=None):
    """Schedule the tasks in a transaction.

    Args:
       transaction: The transaction object.
       tasks: The list of tasks to schedule. This can not be None and must be
            specified.
    """
    max_counter, _ = transaction.Resolve(self.MAX_TS_ID)
    if max_counter is None: max_counter = 0

    max_counter = int(max_counter)

    for task in tasks:
      # Allow a leased task to be rescheduled again.
      if not task.id:
        max_counter += 1
        task.id = max_counter

      now = long(time.time() * 1e6)
      transaction.Set(self._TaskIdToColumn(task.id),
                      task, timestamp=now,
                      replace=True)

    transaction.Set(self.MAX_TS_ID, max_counter)

  def Query(self, queue, limit=1, decoder=None):
    """Retrieves tasks from a queue without leasing them.

    This is good for a read only snapshot of the tasks.

    Args:
       queue: The task queue that this task belongs to.
       limit: Number of values to fetch.
       decoder: An decoder to be used to decode the value.

    Returns:
        A list of Task() objects.
    """
    subject = self.QueueToSubject(queue)

    # Do the real work in a transaction. This doesn't strictly need to
    # be in a transaction but it might give us more consistency.
    return data_store.DB.RetryWrapper(subject, self._RetrieveTasks,
                                      limit=limit, decoder=decoder)

  def _RetrieveTasks(self, transaction, limit=1, decoder=None):
    tasks = []

    # This function should return all tasks - even those which are
    # currently leased (These will have timestamps in the future).
    for _, task, timestamp in transaction.ResolveRegex(
        "%s.*" % self.PREDICATE_PREFIX,
        decoder=functools.partial(self.Task, decoder=decoder),
        timestamp=data_store.ALL_TIMESTAMPS):

      task.eta = timestamp
      tasks.append(task)

      if len(tasks) >= limit:
        break

    # We didn't write anything here
    transaction.Abort()
    return tasks

  def ListQueues(self):
    """Returns a list of all queues in the scheduler."""
    for row in data_store.DB.Query(
        [], filter_obj=data_store.Filter.HasPredicateFilter(self.MAX_TS_ID)):
      yield self.SubjectToQueue(row["subject"])

  def DropQueue(self, queue):
    """Deletes a queue - all tasks will be lost."""
    subject = self.QueueToSubject(queue)

    return data_store.DB.RetryWrapper(
        subject, lambda transaction: transaction.DeleteSubject())

  def QueryAndOwn(self, queue, lease_seconds=10, limit=1, decoder=None):
    """Returns a list of Tasks leased for a certain time.

    Args:
      queue: The queue to query from.
      lease_seconds: The tasks will be leased for this long.
      limit: Number of values to fetch.
      decoder: A decoder to be used to decode the value.

    Returns:
        A list of Task() objects leased.
    """
    subject = self.QueueToSubject(queue)

    # Do the real work in a transaction
    return data_store.DB.RetryWrapper(
        subject, self._QueryAndOwn, decoder=decoder,
        lease_seconds=lease_seconds, limit=limit)

  def _QueryAndOwn(self, transaction, lease_seconds=100,
                   limit=1, decoder=None):
    """Does the real work of self.QueryAndOwn()."""
    tasks = []

    now = long(time.time() * 1e6)
    lease = long(lease_seconds * 1e6)

    # Only grab attributes with timestamps in the past
    for predicate, task, _ in transaction.ResolveRegex(
        "%s.*" % (self.PREDICATE_PREFIX),
        decoder=functools.partial(self.Task, decoder=decoder),
        timestamp=(0, now)):
      # Decrement the ttl
      task.ttl -= 1
      if task.ttl <= 0:
        # Remove the task if ttl is exhausted.
        transaction.DeleteAttribute(predicate)
        logging.info("TTL exceeded on task %s:%s, dequeueing", task.queue,
                     task.id)
      else:
        # Update the timestamp on the value to be in the future
        transaction.Set(predicate, task, replace=True, timestamp=now + lease)
        tasks.append(task)

      if len(tasks) >= limit:
        break

    return tasks

  class Task(object):
    """Tasks are scheduled on the TaskScheduler."""

    def __init__(self, decoder=None, value="", **kwargs):
      """Constructor.

      Args:
        decoder: An decoder to be used to decode the value when
             parsing. (Can be a protobuf class).
        value: Something to populate the value field with.
        kwargs: passthrough to Task protobuf.
      """
      self.proto = jobs_pb2.Task(**kwargs)
      self.decoder = decoder
      self.value = value

    def __getattr__(self, attr):
      return getattr(self.proto, attr)

    def __setattr__(self, attr, value):
      try:
        if attr != "proto":
          return setattr(self.proto, attr, value)
      except (AttributeError, TypeError): pass

      object.__setattr__(self, attr, value)

    def __str__(self):
      return str(self.proto)

    def SerializeToString(self):
      try:
        self.proto.value = self.value.SerializeToString()
      except AttributeError: pass

      return self.proto.SerializeToString()

    def ParseFromString(self, string):
      self.proto.ParseFromString(string)
      self.value = self.proto.value

      if self.decoder:
        value = self.decoder()
        value.ParseFromString(self.value)
        self.value = value
