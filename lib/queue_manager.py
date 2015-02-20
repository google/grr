#!/usr/bin/env python
"""This is the manager for the various queues."""



import os
import random
import socket
import time

import logging

from grr.lib import config_lib
from grr.lib import data_store
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils


class Error(Exception):
  """Base class for errors in this module."""


class MoreDataException(Error):
  """Raised when there is more data available."""


class QueueManager(object):
  """This class manages the representation of the flow within the data store.

  The workflow for client task scheduling is as follows:

  1) Create a bunch of tasks (rdfvalue.GrrMessage()). Tasks must
  be assigned to queues and contain arbitrary values.

  2) Call QueueManager.Schedule(task) to add the tasks to their queues.

  3) In another thread, call QueueManager.QueryAndOwn(queue) to
  obtain a list of tasks leased for a particular time.

  4) If the lease time expires, the tasks automatically become
  available for consumption. When done with the task we can remove it
  from the scheduler using QueueManager.Delete(tasks).

  5) Tasks can be re-leased by calling QueueManager.Schedule(task)
  repeatedly. Each call will extend the lease by the specified amount.

  Important QueueManager's feature is the ability to freeze the timestamp used
  for time-limiting Resolve and Delete queries to the datastore. "with"
  statement should be used to freeze the timestamp, like:
    with queue_manager.QueueManager(token=self.token) as manager:
      ...

  Another option is to use FreezeTimestamp()/UnfreezeTimestamp() methods:
    queue_manager.FreezeTimestamp()
    ...
    queue_manager.UnfreezeTimestamp()
  """

  # These attributes are related to a flow's internal data structures Requests
  # are protobufs of type RequestState. They have a constant prefix followed by
  # the request number:
  FLOW_REQUEST_PREFIX = "flow:request:"
  FLOW_REQUEST_TEMPLATE = FLOW_REQUEST_PREFIX + "%08X"

  # When a status message is received from the client, we write it with the
  # request using the following template.
  FLOW_STATUS_TEMPLATE = "flow:status:%08X"
  FLOW_STATUS_REGEX = "flow:status:.*"

  # This regex will return all the requests in order
  FLOW_REQUEST_REGEX = FLOW_REQUEST_PREFIX + ".*"

  # Each request may have any number of responses. Responses are kept in their
  # own subject object. The subject name is derived from the session id.
  FLOW_RESPONSE_PREFIX = "flow:response:%08X:"
  FLOW_RESPONSE_TEMPLATE = FLOW_RESPONSE_PREFIX + "%08X"

  # This regex will return all the responses in order
  FLOW_RESPONSE_REGEX = "flow:response:.*"

  TASK_PREDICATE_PREFIX = "task:%s"
  NOTIFY_PREDICATE_PREFIX = "notify:%s"

  STUCK_PRIORITY = "Flow stuck"

  request_limit = 1000000
  response_limit = 1000000

  notification_shard_counters = {}

  def __init__(self, store=None, sync=True, token=None):
    self.sync = sync
    self.token = token
    if store is None:
      store = data_store.DB

    self.data_store = store

    # We cache all these and write/delete in one operation.
    self.to_write = {}
    self.to_delete = {}

    # A queue of client messages to remove. Keys are client ids, values are
    # lists of task ids.
    self.client_messages_to_delete = {}
    self.new_client_messages = []
    self.notifications = []

    self.prev_frozen_timestamps = []
    self.frozen_timestamp = None

    self.num_notification_shards = config_lib.CONFIG["Worker.queue_shards"]

  def GetNotificationShard(self, queue):
    queue_name = str(queue)
    QueueManager.notification_shard_counters.setdefault(queue_name, 0)
    QueueManager.notification_shard_counters[queue_name] += 1
    notification_shard_index = (
        QueueManager.notification_shard_counters[queue_name] %
        self.num_notification_shards)
    if notification_shard_index > 0:
      return queue.Add(str(notification_shard_index))
    else:
      return queue

  def GetAllNotificationShards(self, queue):
    result = [queue]
    for i in range(1, self.num_notification_shards):
      result.append(queue.Add(str(i)))
    return result

  def Copy(self):
    """Return a copy of the queue manager.

    Returns:
    Copy of the QueueManager object.
    NOTE: pending writes/deletions are not copied. On the other hand, if the
    original object has a frozen timestamp, a copy will have it as well.
    """
    result = QueueManager(store=self.data_store, sync=self.sync,
                          token=self.token)
    result.prev_frozen_timestamps = self.prev_frozen_timestamps
    result.frozen_timestamp = self.frozen_timestamp
    return result

  def FreezeTimestamp(self):
    """Freezes the timestamp used for resolve/delete database queries.

    Frozen timestamp is used to consistently limit the datastore resolve and
    delete queries by time range: from 0 to self.frozen_timestamp. This is
    done to avoid possible race conditions, like accidentally deleting
    notifications that were written by another process while we were
    processing requests.
    """
    self.prev_frozen_timestamps.append(self.frozen_timestamp)
    self.frozen_timestamp = rdfvalue.RDFDatetime().Now()

  def UnfreezeTimestamp(self):
    """Unfreezes the timestamp used for resolve/delete database queries."""
    if not self.prev_frozen_timestamps:
      raise RuntimeError("Unbalanced UnfreezeTimestamp call.")
    self.frozen_timestamp = self.prev_frozen_timestamps.pop()

  def __enter__(self):
    """Supports 'with' protocol."""
    self.FreezeTimestamp()
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    """Supports 'with' protocol."""
    self.UnfreezeTimestamp()
    self.Flush()

  def GetFlowResponseSubject(self, session_id, request_id):
    """The subject used to carry all the responses for a specific request_id."""
    return session_id.Add("state/request:%08X" % request_id)

  def DeQueueClientRequest(self, client_id, task_id):
    """Remove the message from the client queue that this request forms."""
    # Check this request was actually bound for a client.
    if client_id:
      client_id = rdfvalue.ClientURN(client_id)

      self.client_messages_to_delete.setdefault(client_id, []).append(task_id)

  def MultiCheckStatus(self, messages):
    """Checks if there is a client status queued for a number of requests."""
    subjects = [m.session_id.Add("state") for m in messages]

    statuses_found = {}

    for subject, result in self.data_store.MultiResolveRegex(
        subjects, self.FLOW_STATUS_REGEX,
        token=self.token):
      for predicate, _, _ in result:
        request_nr = int(predicate.split(":")[-1], 16)
        statuses_found.setdefault(subject, set()).add(request_nr)

    status_available = set()
    for m in messages:
      if m.request_id in statuses_found.get(m.session_id.Add("state"), set()):
        status_available.add(m)
    return status_available

  def FetchCompletedRequests(self, session_id, timestamp=None):
    """Fetch all the requests with a status message queued for them."""
    subject = session_id.Add("state")
    requests = {}
    status = {}

    if timestamp is None:
      timestamp = (0, self.frozen_timestamp or rdfvalue.RDFDatetime().Now())

    for predicate, serialized, _ in self.data_store.ResolveRegex(
        subject, [self.FLOW_REQUEST_REGEX, self.FLOW_STATUS_REGEX],
        token=self.token, limit=self.request_limit, timestamp=timestamp):

      parts = predicate.split(":", 3)
      request_id = parts[2]
      if parts[1] == "status":
        status[request_id] = serialized
      else:
        requests[request_id] = serialized

    for request_id, serialized in sorted(requests.items()):
      if request_id in status:
        yield (rdfvalue.RequestState(serialized),
               rdfvalue.GrrMessage(status[request_id]))

  def FetchCompletedResponses(self, session_id, timestamp=None, limit=10000):
    """Fetch only completed requests and responses up to a limit."""
    response_subjects = {}

    if timestamp is None:
      timestamp = (0, self.frozen_timestamp or rdfvalue.RDFDatetime().Now())
    total_size = 0
    for request, status in self.FetchCompletedRequests(
        session_id, timestamp=timestamp):
      # Make sure at least one response is fetched.
      response_subject = self.GetFlowResponseSubject(session_id, request.id)
      response_subjects[response_subject] = request

      # Quit if there are too many responses.
      total_size += status.response_id
      if total_size > limit:
        break

    response_data = dict(self.data_store.MultiResolveRegex(
        response_subjects, self.FLOW_RESPONSE_REGEX, token=self.token,
        timestamp=timestamp))

    for response_urn, request in sorted(response_subjects.items()):
      responses = []
      for _, serialized, _ in response_data.get(response_urn, []):
        responses.append(rdfvalue.GrrMessage(serialized))

      yield (request, sorted(responses, key=lambda msg: msg.response_id))

    # Indicate to the caller that there are more messages.
    if total_size > limit:
      raise MoreDataException()

  def FetchRequestsAndResponses(self, session_id, timestamp=None):
    """Fetches all outstanding requests and responses for this flow.

    We first cache all requests and responses for this flow in memory to
    prevent round trips.

    Args:
      session_id: The session_id to get the requests/responses for.
      timestamp: Tupe (start, end) with a time range. Fetched requests and
                 responses will have timestamp in this range.

    Yields:
      an tuple (request protobufs, list of responses messages) in ascending
      order of request ids.

    Raises:
      MoreDataException: When there is more data available than read by the
                         limited query.
    """
    subject = session_id.Add("state")
    requests = {}

    if timestamp is None:
      timestamp = (0, self.frozen_timestamp or rdfvalue.RDFDatetime().Now())

    # Get some requests.
    for predicate, serialized, _ in self.data_store.ResolveRegex(
        subject, self.FLOW_REQUEST_REGEX, token=self.token,
        limit=self.request_limit, timestamp=timestamp):

      request_id = predicate.split(":", 1)[1]
      requests[str(subject.Add(request_id))] = serialized

    # And the responses for them.
    response_data = dict(self.data_store.MultiResolveRegex(
        requests.keys(), self.FLOW_RESPONSE_REGEX,
        limit=self.response_limit, token=self.token,
        timestamp=timestamp))

    for urn, request_data in sorted(requests.items()):
      request = rdfvalue.RequestState(request_data)
      responses = []
      for _, serialized, _ in response_data.get(urn, []):
        responses.append(rdfvalue.GrrMessage(serialized))

      yield (request, sorted(responses, key=lambda msg: msg.response_id))

    if len(requests) >= self.request_limit:
      raise MoreDataException()

  def DeleteFlowRequestStates(self, session_id, request_state):
    """Deletes the request and all its responses from the flow state queue."""
    queue = self.to_delete.setdefault(session_id.Add("state"), [])
    queue.append(self.FLOW_REQUEST_TEMPLATE % request_state.id)
    queue.append(self.FLOW_STATUS_TEMPLATE % request_state.id)

    if request_state and request_state.HasField("request"):
      self.DeQueueClientRequest(request_state.client_id,
                                request_state.request.task_id)

    # Efficiently drop all responses to this request.
    response_subject = self.GetFlowResponseSubject(session_id, request_state.id)
    self.data_store.DeleteSubject(response_subject, token=self.token)

  def DestroyFlowStates(self, session_id):
    """Deletes all states in this flow and dequeue all client messages."""
    subject = session_id.Add("state")

    for _, serialized, _ in self.data_store.ResolveRegex(
        subject, self.FLOW_REQUEST_REGEX, token=self.token,
        limit=self.request_limit):

      request = rdfvalue.RequestState(serialized)

      # Efficiently drop all responses to this request.
      response_subject = self.GetFlowResponseSubject(session_id, request.id)
      self.data_store.DeleteSubject(response_subject, token=self.token)

      if request.HasField("request"):
        self.DeQueueClientRequest(request.client_id, request.request.task_id)

    # Now drop all the requests at once.
    self.data_store.DeleteSubject(subject, token=self.token)

  def Flush(self):
    """Writes the changes in this object to the datastore."""
    session_ids = set(self.to_write) | set(self.to_delete)
    for session_id in session_ids:
      try:
        self.data_store.MultiSet(session_id, self.to_write.get(session_id, {}),
                                 to_delete=self.to_delete.get(session_id, []),
                                 sync=False, token=self.token)
      except data_store.Error:
        pass

    for client_id, messages in self.client_messages_to_delete.iteritems():
      self.Delete(client_id.Queue(), messages)

    if self.new_client_messages:
      for timestamp, messages in utils.GroupBy(
          self.new_client_messages, lambda x: x[1]).iteritems():

        self.Schedule([x[0] for x in messages], timestamp=timestamp)

    # We need to make sure that notifications are written after the requests so
    # we flush here and only notify afterwards.
    if self.sync and session_ids:
      self.data_store.Flush()

    for notification, timestamp in self.notifications:
      self.NotifyQueue(notification, timestamp=timestamp, sync=False)

    if self.sync:
      self.data_store.Flush()

    self.to_write = {}
    self.to_delete = {}
    self.client_messages_to_delete = {}
    self.notifications = []
    self.new_client_messages = []

  def QueueResponse(self, session_id, response, timestamp=None):
    """Queues the message on the flow's state."""
    if timestamp is None:
      timestamp = self.frozen_timestamp

    # Status messages cause their requests to be marked as complete. This allows
    # us to quickly enumerate all the completed requests - it is essentially an
    # index for completed requests.
    if response.type == rdfvalue.GrrMessage.Type.STATUS:
      subject = session_id.Add("state")
      queue = self.to_write.setdefault(subject, {})
      queue.setdefault(
          self.FLOW_STATUS_TEMPLATE % response.request_id, []).append((
              response.SerializeToString(), timestamp))

    subject = self.GetFlowResponseSubject(session_id, response.request_id)
    queue = self.to_write.setdefault(subject, {})
    queue.setdefault(
        QueueManager.FLOW_RESPONSE_TEMPLATE % (
            response.request_id, response.response_id),
        []).append((response.SerializeToString(), timestamp))

  def QueueRequest(self, session_id, request_state, timestamp=None):
    if timestamp is None:
      timestamp = self.frozen_timestamp

    subject = session_id.Add("state")
    queue = self.to_write.setdefault(subject, {})
    queue.setdefault(
        self.FLOW_REQUEST_TEMPLATE % request_state.id, []).append(
            (request_state.SerializeToString(), timestamp))

  def QueueClientMessage(self, msg, timestamp=None):
    if timestamp is None:
      timestamp = self.frozen_timestamp

    self.new_client_messages.append((msg, timestamp))

  def QueueNotification(self, notification=None, timestamp=None, **kw):
    """Queues a notification for a flow."""

    if notification is None:
      notification = rdfvalue.GrrNotification(**kw)

    if notification.session_id:
      if timestamp is None:
        timestamp = self.frozen_timestamp

      self.notifications.append((notification, timestamp))

  def _TaskIdToColumn(self, task_id):
    """Return a predicate representing this task."""
    return self.TASK_PREDICATE_PREFIX % ("%08d" % task_id)

  def Delete(self, queue, tasks):
    """Removes the tasks from the queue.

    Note that tasks can already have been removed. It is not an error
    to re-delete an already deleted task.

    Args:
     queue: A queue to clear.
     tasks: A list of tasks to remove. Tasks may be Task() instances
          or integers representing the task_id.
    """
    if queue:
      predicates = []
      for task in tasks:
        try:
          task_id = task.task_id
        except AttributeError:
          task_id = int(task)
        predicates.append(self._TaskIdToColumn(task_id))

      data_store.DB.DeleteAttributes(
          queue, predicates, token=self.token, sync=False)

  def Schedule(self, tasks, sync=False, timestamp=None):
    """Schedule a set of Task() instances."""
    if timestamp is None:
      timestamp = self.frozen_timestamp

    for queue, queued_tasks in utils.GroupBy(
        tasks, lambda x: x.queue).iteritems():
      if queue:
        to_schedule = dict(
            [(self._TaskIdToColumn(task.task_id),
              [task.SerializeToString()]) for task in queued_tasks])

        self.data_store.MultiSet(
            queue, to_schedule, timestamp=timestamp, sync=sync,
            token=self.token)

  def _SortByPriority(self, notifications, queue, output_dict=None):
    """Sort notifications by priority into output_dict."""
    if not output_dict:
      output_dict = {}

    for notification in notifications:
      priority = notification.priority
      if notification.in_progress:
        priority = self.STUCK_PRIORITY

      output_dict.setdefault(priority, []).append(notification)

    for priority in output_dict:
      stats.STATS.SetGaugeValue("notification_queue_count",
                                len(output_dict[priority]),
                                fields=[queue.Basename(), str(priority)])
      random.shuffle(output_dict[priority])

    return output_dict

  def GetNotificationsByPriority(self, queue):
    """Retrieves session ids for processing grouped by priority."""
    # Check which sessions have new data.
    # Read all the sessions that have notifications.
    queue_shard = self.GetNotificationShard(queue)
    return self._SortByPriority(
        self._GetUnsortedNotifications(queue_shard).values(), queue)

  def GetNotificationsByPriorityForAllShards(self, queue):
    """Same as GetNotificationsByPriority but for all shards.

    Used by worker_test to cover all shards with a single worker.

    Args:
      queue: usually rdfvalue.RDFURN("aff4:/W")
    Returns:
      dict of notifications objects keyed by priority.
    """
    output_dict = {}
    for queue_shard in self.GetAllNotificationShards(queue):
      output_dict = self._GetUnsortedNotifications(
          queue_shard, notifications_by_session_id=output_dict)

    output_dict = self._SortByPriority(output_dict.values(), queue)
    return output_dict

  def GetNotifications(self, queue):
    """Returns all queue notifications sorted by priority."""
    queue_shard = self.GetNotificationShard(queue)
    notifications = self._GetUnsortedNotifications(queue_shard).values()
    notifications.sort(key=lambda notification: notification.priority,
                       reverse=True)
    return notifications

  def GetNotificationsForAllShards(self, queue):
    """Returns notifications for all shards of a queue at once.

    Used by test_lib.MockWorker to cover all shards with a single worker.

    Args:
      queue: usually rdfvalue.RDFURN("aff4:/W")
    Returns:
      List of rdfvalue.GrrNotification objects
    """
    notifications_by_session_id = {}
    for queue_shard in self.GetAllNotificationShards(queue):
      notifications_by_session_id = self._GetUnsortedNotifications(
          queue_shard, notifications_by_session_id=notifications_by_session_id)

    notifications = notifications_by_session_id.values()
    notifications.sort(key=lambda notification: notification.priority,
                       reverse=True)
    return notifications

  def _GetUnsortedNotifications(self, queue_shard,
                                notifications_by_session_id=None):
    """Returns all the available notifications for a queue_shard.

    Args:
      queue_shard: urn of queue shard
      notifications_by_session_id: store notifications in this dict rather than
        creating a new one

    Returns:
      dict of notifications. keys are session ids.
    """
    if not notifications_by_session_id:
      notifications_by_session_id = {}
    end_time = self.frozen_timestamp or rdfvalue.RDFDatetime().Now()
    for predicate, serialized_notification, ts in data_store.DB.ResolveRegex(
        queue_shard, self.NOTIFY_PREDICATE_PREFIX % ".*",
        timestamp=(0, end_time),
        token=self.token, limit=10000):

      # Parse the notification.
      try:
        notification = rdfvalue.GrrNotification(serialized_notification)
      except Exception:  # pylint: disable=broad-except
        logging.exception("Can't unserialize notification, deleting it: "
                          "predicate=%s, ts=%d", predicate, ts)
        data_store.DB.DeleteAttributes(
            queue_shard, [predicate], token=self.token,
            # Make the time range narrow, but be sure to include the needed
            # notification.
            start=ts, end=ts, sync=True)
        continue

      # Strip the prefix from the predicate to get the session_id.
      session_id = predicate[len(self.NOTIFY_PREDICATE_PREFIX % ""):]
      notification.session_id = session_id
      notification.timestamp = ts

      existing = notifications_by_session_id.get(notification.session_id)
      if existing:
        # If we have a notification for this session_id already, we only store
        # the one that was scheduled last.
        if notification.first_queued > existing.first_queued:
          notifications_by_session_id[notification.session_id] = notification
      else:
        notifications_by_session_id[notification.session_id] = notification

    return notifications_by_session_id

  def NotifyQueue(self, notification, **kwargs):
    """This signals that there are new messages available in a queue."""
    self._MultiNotifyQueue(notification.session_id.Queue(), [notification],
                           **kwargs)

  def MultiNotifyQueue(self, notifications, timestamp=None, sync=True):
    """This is the same as NotifyQueue but for several session_ids at once.

    Args:
      notifications: A list of notifications.
      timestamp: An optional timestamp for this notification.
      sync: If True, sync to the data_store immediately.
    Raises:
      RuntimeError: An invalid session_id was passed.
    """
    extract_queue = lambda notification: notification.session_id.Queue()
    for queue, notifications in utils.GroupBy(
        notifications, extract_queue).iteritems():
      self._MultiNotifyQueue(
          queue, notifications, timestamp=timestamp, sync=sync)

  def _MultiNotifyQueue(self, queue, notifications, timestamp=None, sync=True):
    """Does the actual queuing."""
    serialized_notifications = {}
    now = rdfvalue.RDFDatetime().Now()
    expiry_time = config_lib.CONFIG["Worker.notification_expiry_time"]
    for notification in notifications:
      if not notification.first_queued:
        notification.first_queued = (self.frozen_timestamp or
                                     rdfvalue.RDFDatetime().Now())
      else:
        diff = now - notification.first_queued
        if diff.seconds >= expiry_time:
          # This notification has been around for too long, we drop it.
          logging.debug("Dropping notification: %s", str(notification))
          continue
      session_id = notification.session_id
      # Don't serialize session ids to save some bytes.
      notification.session_id = None
      notification.timestamp = None
      serialized_notifications[session_id] = notification.SerializeToString()

    data_store.DB.MultiSet(
        self.GetNotificationShard(queue),
        dict([(self.NOTIFY_PREDICATE_PREFIX % session_id,
               [(data, timestamp)])
              for session_id, data in serialized_notifications.iteritems()]),
        sync=sync, replace=False, token=self.token)

  def DeleteNotification(self, session_id, start=None, end=None):
    """This deletes the notification when all messages have been processed."""
    if not isinstance(session_id, rdfvalue.SessionID):
      raise RuntimeError(
          "Can only delete notifications for rdfvalue.SessionIDs.")

    if start is None:
      start = 0
    else:
      start = int(start)

    if end is None:
      end = self.frozen_timestamp or rdfvalue.RDFDatetime().Now()

    for queue_shard in self.GetAllNotificationShards(session_id.Queue()):
      data_store.DB.DeleteAttributes(
          queue_shard, [self.NOTIFY_PREDICATE_PREFIX % session_id],
          token=self.token, start=start, end=end, sync=True)

  def Query(self, queue, limit=1, task_id=None):
    """Retrieves tasks from a queue without leasing them.

    This is good for a read only snapshot of the tasks.

    Args:
       queue: The task queue that this task belongs to, usually client.Queue()
              where client is the ClientURN object you want to schedule msgs on.
       limit: Number of values to fetch.
       task_id: If an id is provided we only query for this id.

    Returns:
        A list of Task() objects.
    """
    # This function is usually used for manual testing so we also accept client
    # ids and get the queue from it.
    if isinstance(queue, rdfvalue.ClientURN):
      queue = queue.Queue()

    if task_id is None:
      regex = self.TASK_PREDICATE_PREFIX % ".*"
    else:
      regex = utils.SmartStr(task_id)

    all_tasks = []

    for _, serialized, ts in self.data_store.ResolveRegex(
        queue, regex, timestamp=self.data_store.ALL_TIMESTAMPS,
        token=self.token):
      task = rdfvalue.GrrMessage(serialized)
      task.eta = ts
      all_tasks.append(task)

    # Sort the tasks in order of priority.
    all_tasks.sort(key=lambda task: task.priority, reverse=True)

    return all_tasks[:limit]

  def DropQueue(self, queue):
    """Deletes a queue - all tasks will be lost."""
    data_store.DB.DeleteSubject(queue, token=self.token)

  def QueryAndOwn(self, queue, lease_seconds=10, limit=1):
    """Returns a list of Tasks leased for a certain time.

    Args:
      queue: The queue to query from.
      lease_seconds: The tasks will be leased for this long.
      limit: Number of values to fetch.
    Returns:
        A list of GrrMessage() objects leased.
    """
    user = ""
    if self.token:
      user = self.token.username
    # Do the real work in a transaction
    try:
      res = self.data_store.RetryWrapper(
          queue, self._QueryAndOwn, lease_seconds=lease_seconds, limit=limit,
          token=self.token, user=user)

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

    lease = long(lease_seconds * 1e6)

    ttl_exceeded_count = 0

    # Only grab attributes with timestamps in the past.
    for predicate, task, timestamp in transaction.ResolveRegex(
        self.TASK_PREDICATE_PREFIX % ".*",
        timestamp=(0, self.frozen_timestamp or rdfvalue.RDFDatetime().Now())):
      task = rdfvalue.GrrMessage(task)
      task.eta = timestamp
      task.last_lease = "%s@%s:%d" % (user,
                                      socket.gethostname(),
                                      os.getpid())
      # Decrement the ttl
      task.task_ttl -= 1
      if task.task_ttl <= 0:
        # Remove the task if ttl is exhausted.
        transaction.DeleteAttribute(predicate)
        ttl_exceeded_count += 1
        stats.STATS.IncrementCounter("grr_task_ttl_expired_count")
      else:
        if task.task_ttl != rdfvalue.GrrMessage.max_ttl - 1:
          stats.STATS.IncrementCounter("grr_task_retransmission_count")

        # Update the timestamp on the value to be in the future
        transaction.Set(predicate, task.SerializeToString(), replace=True,
                        timestamp=long(time.time() * 1e6) + lease)
        tasks.append(task)
        if len(tasks) >= limit:
          break

    if ttl_exceeded_count:
      logging.info("TTL exceeded for %d messages on queue %s",
                   ttl_exceeded_count, transaction.subject)
    return tasks


class WellKnownQueueManager(QueueManager):
  """A flow manager for well known flows."""

  response_limit = 10000

  def DeleteWellKnownFlowResponses(self, session_id, responses):
    """Deletes given responses from the flow state queue."""
    subject = session_id.Add("state/request:00000000")
    predicates = []
    for response in responses:
      predicates.append(QueueManager.FLOW_RESPONSE_TEMPLATE % (
          response.request_id, response.response_id))

    data_store.DB.DeleteAttributes(
        subject, predicates, sync=True, start=0, token=self.token)

  def FetchRequestsAndResponses(self, session_id):
    """Well known flows do not have real requests.

    This manages retrieving all the responses without requiring corresponding
    requests.

    Args:
      session_id: The session_id to get the requests/responses for.

    Yields:
      A tuple of request (None) and responses.
    """
    subject = session_id.Add("state/request:00000000")

    # Get some requests
    for _, serialized, _ in sorted(self.data_store.ResolveRegex(
        subject, self.FLOW_RESPONSE_REGEX, token=self.token,
        limit=self.response_limit,
        timestamp=(0, self.frozen_timestamp or rdfvalue.RDFDatetime().Now()))):

      # The predicate format is flow:response:REQUEST_ID:RESPONSE_ID. For well
      # known flows both request_id and response_id are randomized.
      response = rdfvalue.GrrMessage(serialized)

      yield rdfvalue.RequestState(id=0), [response]


class QueueManagerInit(registry.InitHook):
  """Registers vars used by the QueueManager."""

  pre = ["StatsInit"]

  def Run(self):
    # Counters used by the QueueManager.
    stats.STATS.RegisterCounterMetric("grr_task_retransmission_count")
    stats.STATS.RegisterCounterMetric("grr_task_ttl_expired_count")
    stats.STATS.RegisterGaugeMetric("notification_queue_count", int,
                                    fields=[("queue_name", str),
                                            ("priority", str)])
