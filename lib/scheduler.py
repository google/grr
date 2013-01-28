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
import os
import random
import socket
import struct
import threading
import time

from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
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
  PREDICATE_PREFIX = "task:%s"

  def __init__(self, store=None):
    if store is None:
      store = data_store.DB

    self.data_store = store

  def _TaskIdToColumn(self, task_id):
    """Return a predicate representing this task."""
    return self.PREDICATE_PREFIX % ("%08d" % task_id)

  @classmethod
  def QueueNameFromURN(cls, urn):
    """Returns the queue name from a flow URN.

    Args:
      urn: The Flow urn. Normally of the format: aff4:/client_id/flows/W:12345/

    Returns:
      The Queue name.
    """
    return rdfvalue.RDFURN(urn).Basename().split(":")[0]

  def Delete(self, queue, tasks, token=None):
    """Removes the tasks from the queue.

    Note that tasks can already have been removed. It is not an error
    to re-delete an already deleted task.

    Args:
     queue: A queue to clear.
     tasks: A list of tasks to remove. Tasks may be Task() instances
          or integers representing the task_id.
     token: An access token to access the data store.
    """
    if queue:
      self.data_store.RetryWrapper(
          queue, self._Delete, tasks=tasks, token=token)

  def _Delete(self, transaction, tasks=None):
    for task in tasks:
      try:
        ts_id = task.id
      except AttributeError:
        ts_id = int(task)

      transaction.DeleteAttribute(self._TaskIdToColumn(ts_id))

  def Schedule(self, tasks, sync=False, timestamp=None, token=None):
    """Schedule a set of Task() instances."""

    for queue, queued_tasks in utils.GroupBy(tasks, lambda x: x.queue):
      if queue:
        to_schedule = dict(
            [(self._TaskIdToColumn(task.id), [task.SerializeToString()])
             for task in queued_tasks])

        self.data_store.MultiSet(
            queue, to_schedule, timestamp=timestamp, sync=sync, token=token)

  def NotifyQueue(self, queue, session_id,
                  priority=rdfvalue.GRRMessage.Enum("MEDIUM_PRIORITY"),
                  **kwargs):
    """This signals that there are new messages available in a queue."""
    self.MultiNotifyQueue(queue, [session_id], [priority], **kwargs)

  def GetSessionsFromQueue(self, queue, token=None):
    """Retrieves candidate session ids for processing from the datastore."""

    # Check which sessions have new data.
    now = int(time.time() * 1e6)
    # Read all the sessions that have notifications.
    sessions_by_priority = {}
    for predicate, priority, _ in data_store.DB.ResolveRegex(
        queue, self.PREDICATE_PREFIX % ".*",
        timestamp=(0, now), token=token, limit=10000):
      # Strip the prefix from the predicate.
      predicate = predicate[len(self.PREDICATE_PREFIX % ""):]

      sessions_by_priority.setdefault(priority, []).append(predicate)

    # We want to return the sessions by order of priority,
    # but with all sessions at the same priority randomly shuffled.
    sessions_available = []
    for priority in sorted(sessions_by_priority, reverse=True):
      session_ids = sessions_by_priority[priority]
      random.shuffle(session_ids)
      sessions_available.extend(session_ids)

    return sessions_available

  def MultiNotifyQueue(self, queue, session_ids, priorities, timestamp=None,
                       token=None):
    """This is the same as NotifyQueue but for several session_ids at once.

    Args:
      queue: The queue to notify.
      session_ids: A list of session_ids with new messages to process.
      priorities: A list of priorities, one for each session_id in the
                  session_id list.
      timestamp: An optional timestamp for this notification.
      token: An access token to access the data store.
    """
    data_store.DB.MultiSet(
        queue,
        dict([(self.PREDICATE_PREFIX % session_id, str(priority))
              for session_id, priority in zip(session_ids, priorities)]),
        sync=True, replace=True, token=token, timestamp=timestamp)

  def DeleteNotification(self, queue, session_id, token=None):
    """This deletes the notification when all messages have been processed."""
    data_store.DB.DeleteAttributes(
        queue, [self.PREDICATE_PREFIX % session_id],
        token=token)

  def Query(self, queue, limit=1, decoder=None, token=None, task_id=None):
    """Retrieves tasks from a queue without leasing them.

    This is good for a read only snapshot of the tasks.

    Args:
       queue: The task queue that this task belongs to.
       limit: Number of values to fetch.
       decoder: An decoder to be used to decode the value.
       token: An access token to access the data store.
       task_id: If an id is provided we only query for this id.

    Returns:
        A list of Task() objects.
    """
    tasks = []

    if task_id is None:
      regex = self.PREDICATE_PREFIX % ".*"
    else:
      regex = utils.SmartStr(task_id)

    all_tasks = list(self.data_store.ResolveRegex(
        queue, regex, decoder=functools.partial(self.Task, decoder=decoder),
        timestamp=self.data_store.ALL_TIMESTAMPS, token=token))

    all_tasks.sort(key=lambda task: task[1].priority, reverse=True)

    # This function should return all tasks - even those which are
    # currently leased (These will have timestamps in the future).
    for task_id, task, timestamp in all_tasks:
      task.task_id = task_id
      task.eta = timestamp
      tasks.append(task)

      if len(tasks) >= limit:
        break

    return tasks

  def MultiQuery(self, queues, decoder=None, limit=100000, token=None):
    """Like Query above but opens multiple tasks at once."""

    return self.data_store.MultiResolveRegex(
        queues, self.PREDICATE_PREFIX % ".*",
        decoder=functools.partial(self.Task, decoder=decoder),
        timestamp=self.data_store.ALL_TIMESTAMPS,
        limit=limit, token=token)

  def DropQueue(self, queue, token=None):
    """Deletes a queue - all tasks will be lost."""
    data_store.DB.DeleteSubject(queue, token=token)

  def QueryAndOwn(self, queue, lease_seconds=10, limit=1, decoder=None,
                  token=None):
    """Returns a list of Tasks leased for a certain time.

    Args:
      queue: The queue to query from.
      lease_seconds: The tasks will be leased for this long.
      limit: Number of values to fetch.
      decoder: A decoder to be used to decode the value.
      token: An access token to access the data store.
    Returns:
        A list of Task() objects leased.
    """
    user = ""
    if token:
      user = token.username
    # Do the real work in a transaction
    try:
      res = self.data_store.RetryWrapper(
          queue, self._QueryAndOwn, decoder=decoder,
          lease_seconds=lease_seconds, limit=limit, token=token,
          user=user)

      return res
    except data_store.TransactionError:
      # This exception just means that we could not obtain the lock on the queue
      # so we just return an empty list, let the worker sleep and come back to
      # fetch more tasks.
      return []
    except data_store.Error as e:
      logging.warning("Datastore exception: %s", e)
      return []

  def _QueryAndOwn(self, transaction, lease_seconds=100,
                   limit=1, decoder=None, user=""):
    """Does the real work of self.QueryAndOwn()."""
    tasks = []

    now = long(time.time() * 1e6)
    lease = long(lease_seconds * 1e6)

    all_tasks = list(transaction.ResolveRegex(
        self.PREDICATE_PREFIX % ".*",
        decoder=functools.partial(self.Task, decoder=decoder),
        timestamp=(0, now)))
    all_tasks.sort(key=lambda task: task[1].priority, reverse=True)

    # Only grab attributes with timestamps in the past
    for predicate, task, timestamp in all_tasks:
      task.eta = timestamp
      task.last_lease = "%s@%s:%d" % (user,
                                      socket.gethostname(),
                                      os.getpid())
      # Decrement the ttl
      task.ttl -= 1
      if task.ttl <= 0:
        # Remove the task if ttl is exhausted.
        transaction.DeleteAttribute(predicate)
        logging.info("TTL exceeded on task %s:%s, dequeueing", task.queue,
                     task.id)
        stats.STATS.Increment("grr_task_ttl_expired_count")
      else:
        if task.ttl != self.Task.max_ttl - 1:
          stats.STATS.Increment("grr_task_retransmission_count")

        # Update the timestamp on the value to be in the future
        transaction.Set(predicate, task.SerializeToString(), replace=True,
                        timestamp=now + lease)
        tasks.append(task)

      if len(tasks) >= limit:
        break
    return tasks

  class Task(object):
    """Tasks are scheduled on the TaskScheduler."""

    lock = threading.Lock()
    next_id_base = 0
    max_ttl = jobs_pb2.Task().ttl

    def __init__(self, decoder=None, value="", **kwargs):
      """Constructor.

      Args:
        decoder: An decoder to be used to decode the value when
             parsing. (Can be a protobuf class).
        value: Something to populate the value field with.
        **kwargs: passthrough to Task protobuf.
      """
      self.proto = jobs_pb2.Task(**kwargs)
      self.decoder = decoder
      self.value = value
      self.eta = 0

      if self.proto.id:
        self.id = self.proto.id
      else:
        # 16 bit random numbers
        random_number = struct.unpack("H", os.urandom(2))[0]
        while random_number == 0:
          random_number = struct.unpack("H", os.urandom(2))[0]

        with TaskScheduler.Task.lock:
          next_id_base = TaskScheduler.Task.next_id_base

          id_base = (next_id_base + random_number) & 0xFFFFFFFF
          if id_base < next_id_base:
            time.sleep(0.001)

          TaskScheduler.Task.next_id_base = id_base

        # 32 bit timestamp (in 1/1000 second resolution)
        time_base = (long(time.time() * 1000) & 0xFFFFFFFF) << 32

        self.id = time_base + id_base

      try:
        self.proto.priority = self.value.priority
      except AttributeError:
        pass

    def __getattr__(self, attr):
      return getattr(self.proto, attr)

    def __setattr__(self, attr, value):
      try:
        if attr != "proto":
          return setattr(self.proto, attr, value)
      except (AttributeError, TypeError):
        pass

      object.__setattr__(self, attr, value)

    def SerializeToString(self):
      try:
        self.proto.value = self.value.SerializeToString()
      except AttributeError:
        pass

      return self.proto.SerializeToString()

    def ParseFromString(self, string):
      self.proto.ParseFromString(string)
      self.value = self.proto.value

      if self.decoder:
        value = self.decoder()
        value.ParseFromString(self.value)
        self.value = value

    def __str__(self):
      result = ""
      for field in ["id", "value", "ttl", "eta", "queue", "priority"]:
        value = getattr(self, field)
        if field == "eta":
          value = time.ctime(self.eta / 1e6)
          lease = (self.eta / 1e6) - time.time()
          if lease < 0:
            value += ", available for leasing"
          else:
            value += ", leased for another %d seconds" % int(lease)

        result += u"%s: %s\n" % (field, utils.SmartUnicode(value))

      return result

    def __repr__(self):
      result = []
      for field in ["id", "ttl", "eta", "queue", "priority"]:
        value = getattr(self, field)
        if field == "eta":
          value = time.ctime(self.eta / 1e6)
          lease = (self.eta / 1e6) - time.time()
          if lease < 0:
            value += ", available for leasing."
          else:
            value += ", leased for another %d seconds." % int(lease)

        result.append(u"%s: %s" % (field, utils.SmartUnicode(value)))

      return u"<Task %s>" % u",". join(result)

# These are globally available handles to factories
# pylint: disable=W0603
# pylint: disable=C6409


class SchedulerInit(registry.InitHook):
  """Ensures that the scheduler exists."""

  pre = ["AFF4InitHook"]

  def Run(self):
    # Counters used by Scheduler.
    stats.STATS.RegisterVar("grr_task_retransmission_count")
    stats.STATS.RegisterVar("grr_task_ttl_expired_count")
    # Make global handlers
    global SCHEDULER

    SCHEDULER = TaskScheduler()

SCHEDULER = None

# pylint: enable=W0603
# pylint: enable=C6409
