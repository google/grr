#!/usr/bin/env python
# Lint as: python3
"""Fleetspeak-facing client related functionality.

This module contains glue code necessary for Fleetspeak and the GRR client
to work together.
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import pdb
import platform
import queue
import struct
import threading
import time

from absl import flags

from grr_response_client import comms
from grr_response_client import communicator
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import jobs_pb2
from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2
from fleetspeak.client_connector import connector as fs_client

# pyformat: disable

START_STRING = "Starting client."

# //depot/grr_response_client/comms.py)
# pyformat: enable

# Limit on the total size of GrrMessages to batch into a single
# PackedMessageList (before sending to Fleetspeak).
_MAX_MSG_LIST_BYTES = 1 << 20  # 1 MiB

# Maximum number of GrrMessages to put in one PackedMessageList.
_MAX_MSG_LIST_MSG_COUNT = 100

# Maximum size of annotations to add for a Fleetspeak message.
_MAX_ANNOTATIONS_BYTES = 3 << 10  # 3 KiB

_DATA_IDS_ANNOTATION_KEY = "data_ids"


class FatalError(Exception):
  pass


class GRRFleetspeakClient(object):
  """A Fleetspeak enabled client implementation."""

  # Only buffer at most ~100MB of data - the estimate comes from the Fleetspeak
  # message size limit - Fleetspeak refuses to process messages larger than 2MB.
  # This is a sanity safeguard against unlimited memory consumption.
  _SENDER_QUEUE_MAXSIZE = 50

  def __init__(self):
    self._fs = fs_client.FleetspeakConnection(
        version=config.CONFIG["Source.version_string"])

    self._sender_queue = queue.Queue(
        maxsize=GRRFleetspeakClient._SENDER_QUEUE_MAXSIZE)

    self._threads = {}

    if platform.system() == "Windows":
      internal_nanny_monitoring = False
      heart_beat_cb = self._fs.Heartbeat
    else:
      # TODO(amoser): Once the Fleetspeak nanny functionality is
      # production ready, change this to
      # internal_nanny_monitoring=False
      # heart_beat_cb=self._fs.Heartbeat
      internal_nanny_monitoring = True
      heart_beat_cb = None

    # The client worker does all the real work here.
    # In particular, we delegate sending messages to Fleetspeak to a separate
    # threading.Thread here.
    out_queue = _FleetspeakQueueForwarder(self._sender_queue)
    worker = self._threads["Worker"] = comms.GRRClientWorker(
        out_queue=out_queue,
        heart_beat_cb=heart_beat_cb,
        internal_nanny_monitoring=internal_nanny_monitoring,
        client=self)
    # TODO(user): this is an ugly way of passing the heartbeat callback to
    # the queue. Refactor the heartbeat callback initialization logic so that
    # this won't be needed.
    out_queue.heart_beat_cb = worker.Heartbeat

    self._threads["Foreman"] = self._CreateThread(self._ForemanOp)
    self._threads["Sender"] = self._CreateThread(self._SendOp)
    self._threads["Receiver"] = self._CreateThread(self._ReceiveOp)

  def _CreateThread(self, loop_op):
    thread = threading.Thread(target=self._RunInLoop, args=(loop_op,))
    thread.daemon = True
    return thread

  def _RunInLoop(self, loop_op):
    while True:
      try:
        loop_op()
      except Exception as e:
        logging.critical("Fatal error occurred:", exc_info=True)
        if flags.FLAGS.pdb_post_mortem:
          pdb.post_mortem()
        # This will terminate execution in the current thread.
        raise e

  def FleetspeakEnabled(self):
    return True

  def Run(self):
    """The main run method of the client."""
    for thread in self._threads.values():
      thread.start()
    logging.info(START_STRING)

    while True:
      dead_threads = [
          tn for (tn, t) in self._threads.items() if not t.isAlive()
      ]
      if dead_threads:
        raise FatalError(
            "These threads are dead: %r. Shutting down..." % dead_threads)
      time.sleep(10)

  def _ForemanOp(self):
    """Sends Foreman checks periodically."""
    period = config.CONFIG["Client.foreman_check_frequency"]
    self._threads["Worker"].SendReply(
        rdf_protodict.DataBlob(),
        session_id=rdfvalue.FlowSessionID(flow_name="Foreman"),
        require_fastpoll=False)
    time.sleep(period)

  def _SendMessages(self, grr_msgs, background=False):
    """Sends a block of messages through Fleetspeak."""
    message_list = rdf_flows.PackedMessageList()
    communicator.Communicator.EncodeMessageList(
        rdf_flows.MessageList(job=grr_msgs), message_list)
    fs_msg = fs_common_pb2.Message(
        message_type="MessageList",
        destination=fs_common_pb2.Address(service_name="GRR"),
        background=background)
    fs_msg.data.Pack(message_list.AsPrimitiveProto())

    for grr_msg in grr_msgs:
      if (grr_msg.session_id is None or grr_msg.request_id is None or
          grr_msg.response_id is None):
        continue
      # Place all ids in a single annotation, instead of having separate
      # annotations for the flow-id, request-id and response-id. This reduces
      # overall size of the annotations by half (~60 bytes to ~30 bytes).
      annotation = fs_msg.annotations.entries.add()
      annotation.key = _DATA_IDS_ANNOTATION_KEY
      annotation.value = "%s:%d:%d" % (grr_msg.session_id.Basename(),
                                       grr_msg.request_id, grr_msg.response_id)
      if fs_msg.annotations.ByteSize() >= _MAX_ANNOTATIONS_BYTES:
        break

    try:
      sent_bytes = self._fs.Send(fs_msg)
    except (IOError, struct.error):
      logging.critical("Broken local Fleetspeak connection (write end).")
      raise

    communicator.GRR_CLIENT_SENT_BYTES.Increment(sent_bytes)

  def _SendOp(self):
    """Sends messages through Fleetspeak."""
    msg = self._sender_queue.get()
    msgs = []
    background_msgs = []
    if not msg.require_fastpoll:
      background_msgs.append(msg)
    else:
      msgs.append(msg)

    count = 1
    size = len(msg.SerializeToBytes())

    while count < _MAX_MSG_LIST_MSG_COUNT and size < _MAX_MSG_LIST_BYTES:
      try:
        msg = self._sender_queue.get(timeout=1)
        if not msg.require_fastpoll:
          background_msgs.append(msg)
        else:
          msgs.append(msg)
        count += 1
        size += len(msg.SerializeToBytes())
      except queue.Empty:
        break

    if msgs:
      self._SendMessages(msgs)
    if background_msgs:
      self._SendMessages(background_msgs, background=True)

  def _ReceiveOp(self):
    """Receives a single message through Fleetspeak."""
    try:
      fs_msg, received_bytes = self._fs.Recv()
    except (IOError, struct.error):
      logging.critical("Broken local Fleetspeak connection (read end).")
      raise

    received_type = fs_msg.data.TypeName()
    if not received_type.endswith("GrrMessage"):
      raise ValueError(
          "Unexpected proto type received through Fleetspeak: %r; expected "
          "grr.GrrMessage." % received_type)

    communicator.GRR_CLIENT_RECEIVED_BYTES.Increment(received_bytes)

    grr_msg = rdf_flows.GrrMessage.FromSerializedBytes(fs_msg.data.value)
    # Authentication is ensured by Fleetspeak.
    grr_msg.auth_state = jobs_pb2.GrrMessage.AUTHENTICATED

    self._threads["Worker"].QueueMessages([grr_msg])


class _FleetspeakQueueForwarder(object):
  """Ducktyped replacement for SizeLimitedQueue; forwards to _SenderThread."""

  def __init__(self, sender_queue):
    """Constructor.

    Args:
      sender_queue: queue.Queue
    """
    self._sender_queue = sender_queue
    self.heart_beat_cb = lambda: None

  def Put(self, grr_msg, block=True, timeout=None):
    """Places a message in the queue."""
    if not block:
      self._sender_queue.put(grr_msg, block=False)
    else:
      t0 = time.time()
      while not timeout or (time.time() - t0 < timeout):
        self.heart_beat_cb()
        try:
          self._sender_queue.put(grr_msg, timeout=1)
          return
        except queue.Full:
          continue

      raise queue.Full

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
