#!/usr/bin/env python
"""Fleetspeak-facing client related functionality.

This module contains glue code necessary for Fleetspeak and the GRR client
to work together.
"""

import logging
import os
import pdb
import Queue
import struct
import threading
import time

from fleetspeak.src.client.daemonservice.client import client as fs_client
from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2
from grr import config
from grr.client import client_utils
from grr.client import comms
from grr.lib import communicator
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import stats
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.proto import jobs_pb2

# pyformat: disable

START_STRING = "Starting client."

# //depot/grr/tools/benchmark.py,
# //depot/grr/client/comms.py)
# pyformat: enable


class GRRFleetspeakClient(object):
  """A Fleetspeak enabled client implementation."""

  # Only buffer at most ~100MB of data - the estimate comes from the Fleetspeak
  # message size limit - Fleetspeak refuses to process messages larger than 2MB.
  # This is a sanity safeguard against unlimited memory consumption.
  _SENDER_QUEUE_MAXSIZE = 50

  def __init__(self):
    self._fs = fs_client.FleetspeakConnection()

    self._sender_queue = Queue.Queue(
        maxsize=GRRFleetspeakClient._SENDER_QUEUE_MAXSIZE)

    # The client worker does all the real work here.
    # In particular, we delegate sending messages to Fleetspeak to a separate
    # threading.Thread here.
    self._client_worker = comms.GRRThreadedWorker(
        out_queue=_FleetspeakQueueForwarder(self._sender_queue),
        start_worker_thread=False)

  def Run(self):
    """The main run method of the client."""
    self._client_worker.start()
    threading.Thread(target=self._ForemanCheckerThread).start()
    threading.Thread(target=self._SenderThread).start()
    logging.info(START_STRING)
    self._ReceiverThread()

  def _ForemanCheckerThread(self):
    """Sends Foreman checks periodically."""
    period = config.CONFIG["Client.foreman_check_frequency"]
    while True:
      self._client_worker.SendReply(
          rdf_protodict.DataBlob(),
          session_id=rdfvalue.FlowSessionID(flow_name="Foreman"),
          priority=rdf_flows.GrrMessage.Priority.LOW_PRIORITY)
      time.sleep(period)

  def _SendMessages(self, grr_msgs, priority=fs_common_pb2.Message.MEDIUM):
    """Sends a block of messages through Fleetspeak."""
    message_list = rdf_flows.PackedMessageList()
    communicator.Communicator.EncodeMessageList(
        rdf_flows.MessageList(job=grr_msgs), message_list)

    fs_msg = fs_common_pb2.Message(
        message_type="MessageList",
        destination=fs_common_pb2.Address(service_name="GRR"),
        priority=priority)
    fs_msg.data.Pack(message_list.AsPrimitiveProto())

    try:
      sent_bytes = self._fs.Send(fs_msg)
    except (IOError, struct.error) as e:
      logging.fatal(
          "Broken local Fleetspeak connection (write end): %r",
          e,
          exc_info=True)
      # The fatal call above doesn't terminate the program. The reasons for
      # this might include Python threads persistency, or Python logging
      # mechanisms' inconsistency.
      os._exit(1)  # pylint: disable=protected-access

    stats.STATS.IncrementCounter("grr_client_sent_bytes", sent_bytes)

  def _SenderThread(self):
    """Sends messages through Fleetspeak."""
    while True:
      msg = self._sender_queue.get()
      msgs = []
      low_msgs = []
      if msg.priority == rdf_flows.GrrMessage.Priority.LOW_PRIORITY:
        low_msgs.append(msg)
      else:
        msgs.append(msg)

      count = 1
      size = len(msg.SerializeToString())

      while count < 100 and size < 1024 * 1024:
        try:
          msg = self._sender_queue.get(timeout=1)
          if msg.priority == rdf_flows.GrrMessage.Priority.LOW_PRIORITY:
            low_msgs.append(msg)
          else:
            msgs.append(msg)
          count += 1
          size += len(msg.SerializeToString())
        except Queue.Empty:
          break

      if msgs:
        self._SendMessages(msgs)
      if low_msgs:
        self._SendMessages(low_msgs, priority=fs_common_pb2.Message.LOW)

  def _ReceiverThread(self):
    """Receives messages through Fleetspeak."""
    while True:
      try:
        self._ReceiveOnce()
      except Exception as e:  # pylint: disable=broad-except
        # Catch everything, because this is one of the main threads and we need
        # to be as persistent as possible.
        logging.warn(
            "Exception caught in the receiver thread's main loop: %r",
            e,
            exc_info=True)
        if flags.FLAGS.debug:
          pdb.post_mortem()

  def _ReceiveOnce(self):
    """Receives a single message through Fleetspeak."""
    try:
      fs_msg, received_bytes = self._fs.Recv()
    except (IOError, struct.error) as e:
      logging.fatal(
          "Broken local Fleetspeak connection (read end): %r", e, exc_info=True)

      # The fatal call above doesn't terminate the program. The reasons for this
      # might include Python threads persistency, or Python logging mechanisms'
      # inconsistency.
      os._exit(2)  # pylint: disable=protected-access

    received_type = fs_msg.data.TypeName()
    if not received_type.endswith("grr.GrrMessage"):
      raise ValueError(
          "Unexpected proto type received through Fleetspeak: %r; expected "
          "grr.GrrMessage." % received_type)

    stats.STATS.IncrementCounter("grr_client_received_bytes", received_bytes)

    grr_msg = rdf_flows.GrrMessage.FromSerializedString(fs_msg.data.value)
    # Authentication is ensured by Fleetspeak.
    grr_msg.auth_state = jobs_pb2.GrrMessage.AUTHENTICATED

    self._client_worker.QueueMessages([grr_msg])


class _FleetspeakQueueForwarder(object):
  """Ducktyped replacement for comms.SizeQueue; forwards to _SenderThread."""

  def __init__(self, sender_queue):
    """Constructor.

    Args:
      sender_queue: Queue.Queue
    """
    self._sender_queue = sender_queue
    self.nanny_controller = client_utils.NannyController()

  def Put(self, grr_msg, **_):
    while True:
      try:
        self._sender_queue.put(grr_msg, timeout=30)
        return
      except Queue.Full:
        self.nanny_controller.Heartbeat()

  def Get(self):
    raise NotImplementedError("This implementation only supports input.")

  def Size(self):
    """Returns the *approximate* size of the queue.

    See: https://docs.python.org/2/library/queue.html#Queue.Queue.qsize

    Returns:
      int
    """
    return self._sender_queue.qsize()

  def Full(self):
    return self._sender_queue.full()
