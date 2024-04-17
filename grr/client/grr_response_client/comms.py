#!/usr/bin/env python
"""This class handles the GRR Client Communication."""

import collections
import logging
import os
import pdb
import queue
import signal
import threading
import time

from absl import flags
import psutil

from grr_response_client import actions
from grr_response_client import client_actions
from grr_response_client import client_utils
from grr_response_client.client_actions import admin
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict


class GRRClientWorker(threading.Thread):
  """This client worker runs the main loop in another thread.

  The client which uses this worker is not blocked while queuing messages to be
  worked on. There is only a single working thread though.

  The overall effect is that the HTTP client is not blocked waiting for actions
  to be executed, and at the same time, the client working thread is not blocked
  waiting on network latency.
  """

  sent_bytes_per_flow = {}

  def __init__(self, client=None, out_queue=None, heart_beat_cb=None):
    threading.Thread.__init__(self)

    # A reference to the parent client that owns us.
    self.client = client

    self._is_active = False

    self.proc = psutil.Process()

    self.transaction_log = client_utils.TransactionLog()

    def HeartBeatStub():
      pass

    # If the heartbeat callback is not provided, a stub will be used instead.
    self.heart_beat_cb = heart_beat_cb or HeartBeatStub

    self.lock = threading.RLock()

    # This queue should never hit its maximum since the server will throttle
    # messages before this.
    self._in_queue = utils.HeartbeatQueue(callback=heart_beat_cb, maxsize=1024)

    if out_queue is not None:
      self._out_queue = out_queue
    else:
      # The size of the output queue controls the worker thread. Once this queue
      # is too large, the worker thread will block until the queue is drained.
      self._out_queue = SizeLimitedQueue(
          maxsize=config.CONFIG["Client.max_out_queue"],
          heart_beat_cb=self.heart_beat_cb,
      )

    self.daemon = True

  def QueueResponse(self, message, blocking=True):
    """Pushes the Serialized Message on the output queue."""
    self._out_queue.Put(message, block=blocking)

  def Drain(self, max_size=1024):
    """Return a GrrQueue message list from the queue, draining it.

    This is used to get the messages going _TO_ the server when the
    client connects.

    Args:
       max_size: The size (in bytes) of the returned protobuf will be at most
         one message length over this size.

    Returns:
       A MessageList protobuf
    """
    return self._out_queue.GetMessages(soft_size_limit=max_size)

  def QueueMessages(self, messages):
    """Push messages to the input queue."""
    # Push all the messages to our input queue
    for message in messages:
      self._in_queue.put(message, block=True)

  def InQueueSize(self):
    """Returns the number of protobufs ready to be sent in the queue."""
    return self._in_queue.qsize()

  def OutQueueSize(self):
    """Returns the total size of messages ready to be sent."""
    return self._out_queue.Size()

  def SyncTransactionLog(self):
    self.transaction_log.Sync()

  def Heartbeat(self):
    if self.heart_beat_cb:
      self.heart_beat_cb()

  def SendReply(
      self,
      rdf_value=None,
      request_id=None,
      response_id=None,
      session_id="W:0",
      message_type=None,
      name=None,
      ttl=None,
      blocking=True,
      task_id=None,
  ):
    """Send the protobuf to the server.

    Args:
      rdf_value: The RDFvalue to return.
      request_id: The id of the request this is a response to.
      response_id: The id of this response.
      session_id: The session id of the flow.
      message_type: The contents of this message, MESSAGE, STATUS or RDF_VALUE.
      name: The name of the client action that sends this response.
      ttl: The time to live of this message.
      blocking: If the output queue is full, block until there is space.
      task_id: The task ID that the request was queued at. We send this back to
        the server so it can de-queue the request.

    Raises:
      RuntimeError: An object other than an RDFValue was passed for sending.
    """
    if not isinstance(rdf_value, rdfvalue.RDFValue):
      raise RuntimeError("Sending objects other than RDFValues not supported.")

    message = rdf_flows.GrrMessage(
        session_id=session_id,
        task_id=task_id,
        name=name,
        response_id=response_id,
        request_id=request_id,
        ttl=ttl,
        type=message_type,
    )

    if rdf_value is not None:
      message.payload = rdf_value

    serialized_message = message.SerializeToBytes()

    self.ChargeBytesToSession(session_id, len(serialized_message))

    if message.type == rdf_flows.GrrMessage.Type.STATUS:
      rdf_value.network_bytes_sent = self.sent_bytes_per_flow[session_id]
      del self.sent_bytes_per_flow[session_id]
      message.payload = rdf_value

    try:
      self.QueueResponse(message, blocking=blocking)
    except queue.Full:
      # In the case of a non blocking send, we reraise the exception to notify
      # the caller that something went wrong.
      if not blocking:
        raise

      # There is nothing we can do about it here - we just lose the message and
      # keep going.
      logging.info("Queue is full, dropping messages.")

  @utils.Synchronized
  def ChargeBytesToSession(self, session_id, length, limit=0):
    self.sent_bytes_per_flow.setdefault(session_id, 0)
    self.sent_bytes_per_flow[session_id] += length

    # Check after incrementing so that sent_bytes_per_flow goes over the limit
    # even though we don't send those bytes.  This makes sure flow_runner will
    # die on the flow.
    if limit and self.sent_bytes_per_flow[session_id] > limit:
      raise actions.NetworkBytesExceededError(
          "Action exceeded network send limit."
      )

  def HandleMessage(self, message):
    """Entry point for processing jobs.

    Args:
        message: The GrrMessage that was delivered from the server.

    Raises:
        RuntimeError: The client action requested was not found.
    """
    self._is_active = True
    try:
      action_cls = client_actions.REGISTRY.get(message.name)
      if action_cls is None:
        raise RuntimeError("Client action %r not known" % message.name)

      action = action_cls(grr_worker=self)

      # Write the message to the transaction log.
      self.transaction_log.Write(message)

      # Heartbeat so we have the full period to work on this message.
      action.Progress()
      action.Execute(message)

      # If we get here without exception, we can remove the transaction.
      self.transaction_log.Clear()
    finally:
      self._is_active = False

  def MemoryExceeded(self):
    """Returns True if our memory footprint is too large."""
    rss_size = self.proc.memory_info().rss
    return rss_size // 1024 // 1024 > config.CONFIG["Client.rss_max"]

  def IsActive(self):
    """Returns True if worker is currently handling a message."""
    return self._is_active

  def SendClientAlert(self, msg):
    self.SendReply(
        rdf_protodict.DataBlob(string=msg),
        session_id=rdfvalue.FlowSessionID(flow_name="ClientAlert"),
    )

  def Sleep(self, timeout):
    """Sleeps the calling thread with heartbeat."""
    # Split a long sleep interval into 1 second intervals so we can heartbeat.
    while timeout > 0:
      time.sleep(min(1.0, timeout))
      timeout -= 1
      # If the output queue is full, we are ready to do a post - no
      # point in waiting.
      if self._out_queue.Full():
        return

  def OnStartup(self):
    """A handler that is called on client startup."""
    # We read the transaction log and fail any requests that are in it. If there
    # is anything in the transaction log we assume its there because we crashed
    # last time and let the server know.

    last_request = self.transaction_log.Get()
    if last_request:
      status = rdf_flows.GrrStatus(
          status=rdf_flows.GrrStatus.ReturnedStatus.CLIENT_KILLED,
          error_message="Client killed during transaction",
      )

      self.SendReply(
          status,
          request_id=last_request.request_id,
          response_id=1,
          session_id=last_request.session_id,
          message_type=rdf_flows.GrrMessage.Type.STATUS,
      )

    self.transaction_log.Clear()

    # Inform the server that we started.
    action = admin.SendStartupInfo(grr_worker=self)
    action.Run(None, ttl=1)

  def run(self):
    """Main thread for processing messages."""

    self.OnStartup()

    try:
      while True:
        message = self._in_queue.get()

        # A message of None is our terminal message.
        if message is None:
          break

        try:
          self.HandleMessage(message)
          # Catch any errors and keep going here
        except Exception as e:  # pylint: disable=broad-except
          logging.warning("%s", e)
          self.SendReply(
              rdf_flows.GrrStatus(
                  status=rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR,
                  error_message=utils.SmartUnicode(e),
              ),
              request_id=message.request_id,
              response_id=1,
              session_id=message.session_id,
              task_id=message.task_id,
              message_type=rdf_flows.GrrMessage.Type.STATUS,
          )
          if flags.FLAGS.pdb_post_mortem:
            pdb.post_mortem()

    except Exception as e:  # pylint: disable=broad-except
      logging.error("Exception outside of the processing loop: %r", e)
    finally:
      # There's no point in running the client if it's broken out of the
      # processing loop and it should be restarted shortly anyway.
      logging.fatal("The client has broken out of its processing loop.")

      # The binary (Python threading library, perhaps) has proven in tests to be
      # very persistent to termination calls, so we kill it with fire.
      os.kill(os.getpid(), signal.SIGKILL)


class SizeLimitedQueue(object):
  """A Queue which limits the total size of its elements.

  The standard Queue implementations uses the total number of elements to block
  on. In the client we want to limit the total memory footprint, hence we need
  to use the total size as a measure of how full the queue is.
  """

  def __init__(self, heart_beat_cb, maxsize=1024):
    self._queue = collections.deque()
    self._lock = threading.Lock()
    self._total_size = 0
    self._maxsize = maxsize
    self._heart_beat_cb = heart_beat_cb

  def Put(self, message, block=True, timeout=1000):
    """Put a message on the queue, blocking if it is too full.

    Blocks when the queue contains more than the threshold.

    Args:
      message: rdf_flows.GrrMessage The message to put.
      block: bool If True, we block and wait for the queue to have more space.
        Otherwise, if the queue is full, we raise.
      timeout: int Maximum time (in seconds, with 1 sec resolution) we spend
        waiting on the queue.

    Raises:
      queue.Full: if the queue is full and block is False, or
        timeout is exceeded.
    """
    # We only queue already serialized objects so we know how large they are.
    message = message.SerializeToBytes()

    if not block:
      if self.Full():
        raise queue.Full

    else:
      t0 = time.time()
      while self.Full():
        time.sleep(1)
        self._heart_beat_cb()

        if time.time() - t0 > timeout:
          raise queue.Full

    with self._lock:
      self._queue.appendleft(message)
      self._total_size += len(message)

  def _Generate(self):
    """Yields messages from the queue. Lock should be held by the caller."""
    while self._queue:
      yield self._queue.pop()

  def GetMessages(self, soft_size_limit=None):
    """Retrieves and removes the messages from the queue.

    Args:
      soft_size_limit: int If there is more data in the queue than
        soft_size_limit bytes, the returned list of messages will be
        approximately this large. If None (default), returns all messages
        currently on the queue.

    Returns:
      rdf_flows.MessageList A list of messages that were .Put on the queue
      earlier.
    """
    with self._lock:
      ret = rdf_flows.MessageList()
      ret_size = 0
      for message in self._Generate():
        self._total_size -= len(message)
        ret.job.append(rdf_flows.GrrMessage.FromSerializedBytes(message))
        ret_size += len(message)
        if soft_size_limit is not None and ret_size > soft_size_limit:
          break

      return ret

  def Size(self):
    return self._total_size

  def Full(self):
    return self._total_size >= self._maxsize
