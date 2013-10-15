#!/usr/bin/env python
"""This is the manager for the various queues."""



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

  PREDICATE_PREFIX = "task:%s"

  request_limit = 1000000
  response_limit = 1000000

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
    self.client_ids = {}
    self.notifications = {}

  def GetFlowResponseSubject(self, session_id, request_id):
    """The subject used to carry all the responses for a specific request_id."""
    return session_id.Add("state/request:%08X" % request_id)

  def DeQueueClientRequest(self, client_id, task_id):
    """Remove the message from the client queue that this request forms."""
    client_id = rdfvalue.ClientURN(client_id)

    self.client_messages_to_delete.setdefault(client_id, []).append(task_id)

  def FetchCompletedRequests(self, session_id):
    """Fetch all the requests with a status message queued for them."""
    subject = session_id.Add("state")
    requests = {}
    status = {}

    for predicate, serialized, _ in self.data_store.ResolveRegex(
        subject, [self.FLOW_REQUEST_REGEX, self.FLOW_STATUS_REGEX],
        token=self.token, limit=self.request_limit):

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

  def FetchCompletedResponses(self, session_id, limit=10000):
    """Fetch only completed requests and responses up to a limit."""
    response_subjects = {}

    total_size = 0
    for request, status in self.FetchCompletedRequests(session_id):
      # Make sure at least one response is fetched.
      response_subject = self.GetFlowResponseSubject(session_id, request.id)
      response_subjects[response_subject] = request

      # Quit if there are too many responses.
      total_size += status.response_id
      if total_size > limit:
        break

    response_data = dict(self.data_store.MultiResolveRegex(
        response_subjects, self.FLOW_RESPONSE_REGEX, token=self.token))

    for response_urn, request in sorted(response_subjects.items()):
      responses = []
      for _, serialized, _ in response_data.get(response_urn, []):
        responses.append(rdfvalue.GrrMessage(serialized))

      yield (request, sorted(responses, key=lambda msg: msg.response_id))

    # Indicate to the caller that there are more messages.
    if total_size > limit:
      raise MoreDataException()

  def FetchRequestsAndResponses(self, session_id):
    """Fetches all outstanding requests and responses for this flow.

    We first cache all requests and responses for this flow in memory to
    prevent round trips.

    Args:
      session_id: The session_id to get the requests/responses for.

    Yields:
      an tuple (request protobufs, list of responses messages) in ascending
      order of request ids.

    Raises:
      MoreDataException: When there is more data available than read by the
                         limited query.
    """
    subject = session_id.Add("state")
    requests = {}

    # Get some requests.
    for predicate, serialized, _ in self.data_store.ResolveRegex(
        subject, self.FLOW_REQUEST_REGEX, token=self.token,
        limit=self.request_limit):

      request_id = predicate.split(":", 1)[1]
      requests[str(subject.Add(request_id))] = serialized

    # And the responses for them.
    response_data = dict(self.data_store.MultiResolveRegex(
        requests.keys(), self.FLOW_RESPONSE_REGEX,
        limit=self.response_limit, token=self.token))

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
      if request_state.HasField("request"):
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

      # If the request refers to a client, dequeue client requests.
      if request.HasField("request"):
        self.DeQueueClientRequest(request.client_id, request.request.task_id)

    # Now drop all the requests at once.
    self.data_store.DeleteSubject(subject, token=self.token)

  def Flush(self):
    """Writes the changes in this object to the datastore."""
    for session_id in set(self.to_write) | set(self.to_delete):
      try:
        self.data_store.MultiSet(session_id, self.to_write.get(session_id, {}),
                                 to_delete=self.to_delete.get(session_id, []),
                                 sync=False, token=self.token)
      except data_store.Error:
        pass

    for client_id, messages in self.client_messages_to_delete.iteritems():
      self.Delete(client_id.Queue(), messages)

    if self.new_client_messages:
      self.Schedule(self.new_client_messages)

    for session_id, (priority, timestamp) in self.notifications.items():
      self.NotifyQueue(
          session_id, timestamp=timestamp, sync=False, priority=priority)

    if self.sync:
      self.data_store.Flush()

    self.to_write = {}
    self.to_delete = {}
    self.client_messages_to_delete = {}
    self.client_ids = {}
    self.notifications = {}
    self.new_client_messages = []

  def __enter__(self):
    return self

  def __exit__(self, unused_type, unused_value, unused_traceback):
    """Supports 'with' protocol."""
    self.Flush()

  def QueueResponse(self, session_id, response):
    """Queues the message on the flow's state."""
    # Status messages cause their requests to be marked as complete. This allows
    # us to quickly enumerate all the completed requests - it is essentially an
    # index for completed requests.
    if response.type == rdfvalue.GrrMessage.Type.STATUS:
      subject = session_id.Add("state")
      queue = self.to_write.setdefault(subject, {})
      queue.setdefault(
          self.FLOW_STATUS_TEMPLATE % response.request_id, []).append(
              response.SerializeToString())

    subject = self.GetFlowResponseSubject(session_id, response.request_id)
    queue = self.to_write.setdefault(subject, {})
    queue.setdefault(
        QueueManager.FLOW_RESPONSE_TEMPLATE % (
            response.request_id, response.response_id),
        []).append(response.SerializeToString())

  def QueueRequest(self, session_id, request_state):
    subject = session_id.Add("state")
    queue = self.to_write.setdefault(subject, {})
    queue.setdefault(
        self.FLOW_REQUEST_TEMPLATE % request_state.id, []).append(
            request_state.SerializeToString())

  def QueueClientMessage(self, msg):
    self.new_client_messages.append(msg)

  def QueueNotification(self, session_id, timestamp=None,
                        priority=rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY):
    if session_id:
      self.notifications[session_id] = (priority, timestamp)

  def _TaskIdToColumn(self, task_id):
    """Return a predicate representing this task."""
    return self.PREDICATE_PREFIX % ("%08d" % task_id)

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
    for queue, queued_tasks in utils.GroupBy(
        tasks, lambda x: x.queue).iteritems():
      if queue:
        to_schedule = dict(
            [(self._TaskIdToColumn(task.task_id),
              [task.SerializeToString()]) for task in queued_tasks])

        self.data_store.MultiSet(
            queue, to_schedule, timestamp=timestamp, sync=sync,
            token=self.token)

  def GetSessionsFromQueue(self, queue):
    """Retrieves candidate session ids for processing from the datastore."""

    # Check which sessions have new data.
    now = int(time.time() * 1e6)
    # Read all the sessions that have notifications.
    sessions_by_priority = {}
    for predicate, priority, _ in data_store.DB.ResolveRegex(
        queue, self.PREDICATE_PREFIX % ".*",
        timestamp=(0, now), token=self.token, limit=10000):
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
                       sync=True):
    """This is the same as NotifyQueue but for several session_ids at once.

    Args:
      session_ids: A list of session_ids with new messages to process.
      priorities: A dict of priorities, one for each session_id in the
                  session_id list.
      timestamp: An optional timestamp for this notification.
      sync: If True, sync to the data_store immediately.
    Raises:
      RuntimeError: An invalid session_id was passed.
    """
    for session_id in session_ids:
      if not isinstance(session_id, rdfvalue.SessionID):
        raise RuntimeError("Can only notify on rdfvalue.SessionIDs.")

    for queue, ids in utils.GroupBy(
        session_ids, lambda session_id: session_id.Queue()).iteritems():

      self._MultiNotifyQueue(
          queue, ids, priorities, timestamp=timestamp, sync=sync)

  def _MultiNotifyQueue(self, queue, session_ids, priorities, timestamp=None,
                        sync=True):
    data_store.DB.MultiSet(
        queue,
        dict([(self.PREDICATE_PREFIX % session_id,
               str(int(priorities[session_id])))
              for session_id in session_ids]),
        sync=sync, replace=True, token=self.token, timestamp=timestamp)

  def DeleteNotification(self, session_id):
    """This deletes the notification when all messages have been processed."""
    if not isinstance(session_id, rdfvalue.SessionID):
      raise RuntimeError(
          "Can only delete notifications for rdfvalue.SessionIDs.")

    data_store.DB.DeleteAttributes(
        session_id.Queue(), [self.PREDICATE_PREFIX % session_id],
        token=self.token)

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
      regex = self.PREDICATE_PREFIX % ".*"
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

    now = long(time.time() * 1e6)
    lease = long(lease_seconds * 1e6)

    ttl_exceeded_count = 0

    # Only grab attributes with timestamps in the past.
    for predicate, task, timestamp in transaction.ResolveRegex(
        self.PREDICATE_PREFIX % ".*", timestamp=(0, now)):
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
                        timestamp=now + lease)
        tasks.append(task)
        if len(tasks) >= limit:
          break

    if ttl_exceeded_count:
      logging.info("TTL exceeded for %d messages on queue %s",
                   ttl_exceeded_count, transaction.subject)
    return tasks


class WellKnownQueueManager(QueueManager):
  """A flow manager for well known flows."""

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
        limit=self.request_limit)):

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
