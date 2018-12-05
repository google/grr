#!/usr/bin/env python
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
import struct
import threading
import time


from future.utils import iteritems
from future.utils import itervalues
import queue

from fleetspeak.src.client.daemonservice.client import client as fs_client
from fleetspeak.src.common.proto.fleetspeak import common_pb2 as fs_common_pb2
from grr_response_client import comms
from grr_response_core import config
from grr_response_core.lib import communicator
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.stats import stats_collector_instance
from grr_response_proto import jobs_pb2

# pyformat: disable

START_STRING = "Starting client."

# //depot/grr/tools/benchmark.py,
# //depot/grr_response_client/comms.py)
# pyformat: enable


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
    self._threads["Worker"] = comms.GRRClientWorker(
        out_queue=_FleetspeakQueueForwarder(self._sender_queue),
        heart_beat_cb=heart_beat_cb,
        internal_nanny_monitoring=internal_nanny_monitoring,
        client=self)
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
        if flags.FLAGS.debug:
          pdb.post_mortem()
        # This will terminate execution in the current thread.
        raise e

  def FleetspeakEnabled(self):
    return True

  def Run(self):
    """The main run method of the client."""
    for thread in itervalues(self._threads):
      thread.start()
    logging.info(START_STRING)

    while True:
      dead_threads = [
          tn for (tn, t) in iteritems(self._threads) if not t.isAlive()
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

    try:
      sent_bytes = self._fs.Send(fs_msg)
    except (IOError, struct.error):
      logging.critical("Broken local Fleetspeak connection (write end).")
      raise

    stats_collector_instance.Get().IncrementCounter("grr_client_sent_bytes",
                                                    sent_bytes)

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
    size = len(msg.SerializeToString())

    while count < 100 and size < 1024 * 1024:
      try:
        msg = self._sender_queue.get(timeout=1)
        if not msg.require_fastpoll:
          background_msgs.append(msg)
        else:
          msgs.append(msg)
        count += 1
        size += len(msg.SerializeToString())
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
    if not received_type.endswith("grr.GrrMessage"):
      raise ValueError(
          "Unexpected proto type received through Fleetspeak: %r; expected "
          "grr.GrrMessage." % received_type)

    stats_collector_instance.Get().IncrementCounter("grr_client_received_bytes",
                                                    received_bytes)

    grr_msg = rdf_flows.GrrMessage.FromSerializedString(fs_msg.data.value)
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

  def Put(self, grr_msg, **_):
    self._sender_queue.put(grr_msg)

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
