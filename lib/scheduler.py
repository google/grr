#!/usr/bin/env python
# Copyright 2011 Google Inc. All Rights Reserved.
"""This is the main task scheduler."""

import logging
import os
import random
import socket
import time

from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils


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
    if task_id == 1:
      return self.PREDICATE_PREFIX % "flow"
    return self.PREDICATE_PREFIX % ("%08d" % task_id)

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
        ts_id = task.task_id
      except AttributeError:
        ts_id = int(task)

      transaction.DeleteAttribute(self._TaskIdToColumn(ts_id))

  def Schedule(self, tasks, sync=False, timestamp=None, token=None):
    """Schedule a set of Task() instances."""
    for queue, queued_tasks in utils.GroupBy(tasks, lambda x: x.queue):
      if queue:
        to_schedule = dict(
            [(self._TaskIdToColumn(task.task_id), [task.SerializeToString()])
             for task in queued_tasks])

        self.data_store.MultiSet(
            queue, to_schedule, timestamp=timestamp, sync=sync, token=token)

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

  def NotifyQueue(self, session_id,
                  priority=rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY,
                  **kwargs):
    """This signals that there are new messages available in a queue."""
    self._MultiNotifyQueue(session_id.Queue(), [session_id],
                           {session_id: priority}, **kwargs)

  def MultiNotifyQueue(self, session_ids, priorities, timestamp=None,
                       sync=True, token=None):
    """This is the same as NotifyQueue but for several session_ids at once.

    Args:
      session_ids: A list of session_ids with new messages to process.
      priorities: A dict of priorities, one for each session_id in the
                  session_id list.
      timestamp: An optional timestamp for this notification.
      sync: If True, sync to the data_store immediately.
      token: An access token to access the data store.
    Raises:
      RuntimeError: An invalid session_id was passed.
    """
    for session_id in session_ids:
      if not isinstance(session_id, rdfvalue.SessionID):
        raise RuntimeError("Can only notify on rdfvalue.SessionIDs.")

    for queue, ids in utils.GroupBy(
        session_ids, lambda session_id: session_id.Queue()):

      self._MultiNotifyQueue(queue, ids, priorities, timestamp=timestamp,
                             sync=sync, token=token)

  def _MultiNotifyQueue(self, queue, session_ids, priorities, timestamp=None,
                        sync=True, token=None):
    data_store.DB.MultiSet(
        queue,
        dict([(self.PREDICATE_PREFIX % session_id,
               str(int(priorities[session_id])))
              for session_id in session_ids]),
        sync=sync, replace=True, token=token, timestamp=timestamp)

  def DeleteNotification(self, session_id, token=None):
    """This deletes the notification when all messages have been processed."""
    if not isinstance(session_id, rdfvalue.SessionID):
      raise RuntimeError(
          "Can only delete notifications for rdfvalue.SessionIDs.")

    data_store.DB.DeleteAttributes(
        session_id.Queue(), [self.PREDICATE_PREFIX % session_id],
        token=token)

  def Query(self, queue, limit=1, token=None, task_id=None):
    """Retrieves tasks from a queue without leasing them.

    This is good for a read only snapshot of the tasks.

    Args:
       queue: The task queue that this task belongs to.
       limit: Number of values to fetch.
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
        queue, regex, decoder=rdfvalue.GrrMessage,
        timestamp=self.data_store.ALL_TIMESTAMPS, token=token))
    all_tasks.sort(key=lambda task: task[1].priority, reverse=True)

    # This function should return all tasks - even those which are
    # currently leased (These will have timestamps in the future).
    for task_id, task, timestamp in all_tasks:
      task.eta = timestamp
      tasks.append(task)

      if len(tasks) >= limit:
        break

    return tasks

  def MultiQuery(self, queues, limit=100000, token=None):
    """Like Query above but opens multiple tasks at once."""

    return self.data_store.MultiResolveRegex(
        queues, self.PREDICATE_PREFIX % ".*",
        decoder=rdfvalue.GrrMessage,
        timestamp=self.data_store.ALL_TIMESTAMPS,
        limit=limit, token=token)

  def DropQueue(self, queue, token=None):
    """Deletes a queue - all tasks will be lost."""
    data_store.DB.DeleteSubject(queue, token=token)

  def QueryAndOwn(self, queue, lease_seconds=10, limit=1,
                  token=None):
    """Returns a list of Tasks leased for a certain time.

    Args:
      queue: The queue to query from.
      lease_seconds: The tasks will be leased for this long.
      limit: Number of values to fetch.
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
          queue, self._QueryAndOwn, lease_seconds=lease_seconds, limit=limit,
          token=token, user=user)

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
                   limit=1, user=""):
    """Does the real work of self.QueryAndOwn()."""
    tasks = []

    now = long(time.time() * 1e6)
    lease = long(lease_seconds * 1e6)

    all_tasks = list(transaction.ResolveRegex(
        self.PREDICATE_PREFIX % ".*",
        decoder=rdfvalue.GrrMessage,
        timestamp=(0, now)))

    all_tasks.sort(key=lambda task: task[1].priority, reverse=True)

    # Only grab attributes with timestamps in the past
    for predicate, task, timestamp in all_tasks:
      task.eta = timestamp
      task.last_lease = "%s@%s:%d" % (user,
                                      socket.gethostname(),
                                      os.getpid())
      # Decrement the ttl
      task.task_ttl -= 1
      if task.task_ttl <= 0:
        # Remove the task if ttl is exhausted.
        transaction.DeleteAttribute(predicate)
        logging.info("TTL exceeded on task %s:%s, dequeueing", task.queue,
                     task.task_id)
        stats.STATS.IncrementCounter("grr_task_ttl_expired_count")
      else:
        if task.task_ttl != rdfvalue.GrrMessage.max_ttl - 1:
          stats.STATS.IncrementCounter("grr_task_retransmission_count")

        # Update the timestamp on the value to be in the future
        transaction.Set(predicate, task.SerializeToString(), replace=True,
                        timestamp=now + lease)
        tasks.append(task)

      if len(tasks) >= limit:
        break
    return tasks

# These are globally available handles to factories
# pylint: disable=global-statement
# pylint: disable=g-bad-name


class SchedulerInit(registry.InitHook):
  """Ensures that the scheduler exists."""

  pre = ["AFF4InitHook"]

  def Run(self):
    # Counters used by Scheduler.
    stats.STATS.RegisterCounterMetric("grr_task_retransmission_count")
    stats.STATS.RegisterCounterMetric("grr_task_ttl_expired_count")
    # Make global handlers
    global SCHEDULER

    SCHEDULER = TaskScheduler()

SCHEDULER = None

# pylint: enable=global-statement
# pylint: enable=g-bad-name
