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

"""This class handles the GRR Client Communication."""


import hashlib
import os

import pdb
import posixpath
import Queue
import sys
import threading
import time
import urllib2



from M2Crypto import BIO
from M2Crypto import EVP
from M2Crypto import RSA
from M2Crypto import X509
import psutil

from google.protobuf import message as proto2_message
from grr.client import conf as flags
import logging

from grr.client import actions
from grr.client import client_config
from grr.client import client_log
from grr.client import client_utils
from grr.client import client_utils_common
from grr.client import conf
from grr.lib import communicator
from grr.lib import registry
from grr.lib import stats
from grr.lib import utils
from grr.proto import jobs_pb2

flags.DEFINE_float("poll_min", 0.2,
                   "Minimum time between polls in seconds")

flags.DEFINE_float("poll_max", 600,
                   "Maximum time between polls in seconds")

flags.DEFINE_float("poll_slew", 1.15,
                   "Slew of poll time in seconds")

flags.DEFINE_string("location", client_config.LOCATION,
                    "URL of the controlling server.")

flags.DEFINE_integer("max_post_size", 8000000,
                     "Maximum size of the post.")

flags.DEFINE_integer("max_out_queue", 10240000,
                     "Maximum size of the output queue.")

flags.DEFINE_integer("foreman_check_frequency", 3600,
                     "The minimum number of seconds before checking with "
                     "the foreman for new work.")

flags.DEFINE_float("rss_max", 100,
                   "Maximum memory footprint in MB.")

flags.DEFINE_string("certificate", "",
                    "A PEM encoded certificate file (combined private "
                    "and X509 key in PEM format)")

FLAGS = flags.FLAGS

# This determines after how many consecutive errors
# GRR will retry all known proxies.
PROXY_SCAN_ERROR_LIMIT = 10


class CommsInit(registry.InitHook):

  pre = ["StatsInit"]

  def RunOnce(self):
    # Counters used here
    stats.STATS.RegisterVar("grr_client_last_stats_sent_time")
    stats.STATS.RegisterVar("grr_client_received_bytes")
    stats.STATS.RegisterVar("grr_client_received_messages")
    stats.STATS.RegisterVar("grr_client_slave_restarts")
    stats.STATS.RegisterVar("grr_client_sent_bytes")
    stats.STATS.RegisterVar("grr_client_sent_messages")


class Status(object):
  """An abstraction to encapsulate results of the HTTP Post."""
  # Number of messages received
  received_count = 0

  # Number of messages sent to server.
  sent_count = 0
  sent_len = 0
  # Messages sent by priority.
  sent = {}

  require_fastpoll = False

  # Server status code (200 is OK)
  code = 200

  def __init__(self, **kwargs):
    self.__dict__.update(kwargs)


class GRRClientWorker(object):
  """The main GRR Client worker.

  This provides access to the GRR framework to plugins and other code.

  The client worker is the main thread in the client which processes requests
  from the server.
  """

  stats_collector = None

  IDLE_THRESHOLD = 0.3

  sent_bytes_per_flow = {}

  def __init__(self):
    """Create a new GRRClientWorker."""
    super(GRRClientWorker, self).__init__()

    # Queue of messages from the server to be processed.
    self._in_queue = []

    # Queue of messages to be sent to the server.
    self._out_queue = []

    # A tally of the total byte count of messages
    self._out_queue_size = 0

    self.proc = psutil.Process(os.getpid())

    # Use this to control the nanny transaction log.
    self.nanny_controller = client_utils.NannyController()
    self.nanny_controller.StartNanny()
    if not GRRClientWorker.stats_collector:
      GRRClientWorker.stats_collector = stats.StatsCollector()
      GRRClientWorker.stats_collector.start()

  def Sleep(self, timeout):
    """Sleeps the calling thread with heartbeat."""
    self.nanny_controller.Heartbeat()
    time.sleep(timeout - int(timeout))

    # Split a long sleep interval into 1 second intervals so we can heartbeat.
    for _ in range(int(timeout)):
      time.sleep(1)

      self.nanny_controller.Heartbeat()

  def ClientMachineIsIdle(self):
    return psutil.get_cpu_percent(0.05) <= 100 * self.IDLE_THRESHOLD

  def __del__(self):
    self.nanny_controller.StopNanny()

  def Drain(self, max_size=1024):
    """Return a GrrQueue message list from the queue, draining it.

    This is used to get the messages going _TO_ the server when the
    client connects.

    Args:
       max_size: The size of the returned protobuf will be at most one
       message length over this size.

    Returns:
       A MessageList protobuf
    """
    queue = jobs_pb2.MessageList()

    length = 0
    self._out_queue.sort(key=lambda msg: msg[0])

    # Front pops are quadratic so we reverse the queue.
    self._out_queue.reverse()

    # Use implicit True/False evaluation instead of len (WTF)
    while self._out_queue and length < max_size:
      message = self._out_queue.pop()[1]
      new_job = queue.job.add()
      new_job.MergeFromString(message)
      stats.STATS.Increment("grr_client_sent_messages")

      # Maintain the output queue tally
      length += len(message)
      self._out_queue_size -= len(message)

    # Restore the old order.
    self._out_queue.reverse()

    return queue

  def SendReply(self, protobuf=None, request_id=None, response_id=None,
                priority=None, session_id="W:0", message_type=None, name=None,
                require_fastpoll=None, jump_queue=False):
    """Send the protobuf to the server."""
    message = jobs_pb2.GrrMessage()
    if protobuf:
      message.args = protobuf.SerializeToString()

    message.session_id = session_id

    if name is not None:
      message.name = name

    if response_id is not None:
      message.response_id = response_id

    if request_id is not None:
      message.request_id = request_id

    if message_type is None:
      message_type = jobs_pb2.GrrMessage.MESSAGE

    if priority is not None:
      message.priority = priority

    if require_fastpoll is not None:
      message.require_fastpoll = require_fastpoll

    message.type = message_type

    serialized_message = message.SerializeToString()

    self.sent_bytes_per_flow.setdefault(session_id, 0)
    self.sent_bytes_per_flow[session_id] += len(serialized_message)

    if message.type == jobs_pb2.GrrMessage.STATUS:
      protobuf.network_bytes_sent = self.sent_bytes_per_flow[session_id]
      del self.sent_bytes_per_flow[session_id]
      message.args = protobuf.SerializeToString()
      serialized_message = message.SerializeToString()

    if jump_queue:
      self.QueueResponse(serialized_message,
                         jobs_pb2.GrrMessage.HIGH_PRIORITY + 1)
    else:
      self.QueueResponse(serialized_message, message.priority)

  def QueueResponse(self, serialized_message,
                    priority=jobs_pb2.GrrMessage.MEDIUM_PRIORITY):
    """Push the Serialized Message on the output queue."""
    self._out_queue.append((-1 * priority, serialized_message))
    # Maintain the tally of the output queue size
    self._out_queue_size += len(serialized_message)

  def HandleMessage(self, message):
    """Entry point for processing jobs.

    Args:
        message: The GrrMessage that was delivered from the server.
    """
    # Write the message to the transaction log.
    self.nanny_controller.WriteTransactionLog(message)
    action_cls = actions.ActionPlugin.classes.get(
        message.name, actions.ActionPlugin)
    action = action_cls(message=message, grr_worker=self)
    action.Execute(message)

    # If we get here without exception, we can remove the transaction.
    self.nanny_controller.CleanTransactionLog()

  def QueueMessages(self, messages):
    """Queue a message from the server for processing.

    We maintain all the incoming messages in a queue. These messages
    are consumed until the outgoing queue fills to the allowable
    level. This mechanism allows us to throttle the server messages
    and limit the size of the outgoing queue on the client.

    Note that we can only limit processing of single request messages
    so if a single request message generates huge amounts of response
    messages we will still overflow the output queue. Therefore
    actions must be written in such a way that each request generates
    a limited and known maximum number and size of responses. (e.g. do
    not write a single client action to fetch the entire disk).

    Args:
      messages: List of parsed protobuf arriving from the server.
    """
    # Push all the messages to our input queue
    for message in messages:
      self._in_queue.append(message)
      stats.STATS.Increment("grr_client_received_messages")

    # As long as our output queue has some room we can process some
    # input messages:
    while self._in_queue and (
        self._out_queue_size < FLAGS.max_out_queue):
      message = self._in_queue.pop(0)

      try:
        self.HandleMessage(message)
        # Catch any errors and keep going here
      except Exception, e:
        logging.warn("%s", e)
        self.SendReply(
            jobs_pb2.GrrStatus(
                status=jobs_pb2.GrrStatus.GENERIC_ERROR,
                error_message=utils.SmartUnicode(e)),
            request_id=message.request_id,
            response_id=message.response_id,
            session_id=message.session_id,
            message_type=jobs_pb2.GrrMessage.STATUS)
        if FLAGS.debug:
          pdb.post_mortem()

  def MemoryExceeded(self):
    """Returns True if our memory footprint is too large."""
    rss_size, _ = self.proc.get_memory_info()
    return rss_size/1024/1024 > FLAGS.rss_max

  def InQueueSize(self):
    """Returns the number of protobufs ready to be sent in the queue."""
    return len(self._in_queue)

  def OutQueueSize(self):
    """Returns the total size of messages ready to be sent."""
    return len(self._out_queue)


class SizeQueue(object):
  """A Queue which limits the total size of its elements.

  The standard Queue implementations uses the total number of elements to block
  on. In the client we want to limit the total memory footprint, hence we need
  to use the total size as a measure of how full the queue is.
  """
  total_size = 0

  def __init__(self, maxsize=1024, nanny=None):
    self.lock = threading.RLock()
    self.queue = []
    self._reversed = []
    self.total_size = 0
    self.maxsize = maxsize
    self.nanny = nanny

  def Put(self, item, priority=jobs_pb2.GrrMessage.MEDIUM_PRIORITY,
          block=True, timeout=1000):
    """Put an item on the queue, blocking if it is too full.

    This is a slightly modified Queue.put method which blocks when the queue
    contains more than the threshold.

    Args:
      item: The item to put - must have a __len__() method.
      priority: The priority of this message.
      block: If True we block indefinitely.
      timeout: Maximum time we spend waiting on the queue (1 sec resolution).

    Raises:
      Queue.Full: if the queue is full and block is False, or
        timeout is exceeded.
    """
    if priority >= jobs_pb2.GrrMessage.HIGH_PRIORITY:
      pass  # If high priority is set we dont care about the size of the queue.

    elif not block:
      if self.total_size >= self.maxsize:
        raise Queue.Full

    else:
      count = 0
      # Wait until the queue has more space. We do not hold the lock here to
      # ensure that the posting thread can drain this queue while we block here.
      while self.total_size >= self.maxsize:
        time.sleep(1)
        self.nanny.Heartbeat()
        count += 1

        if timeout and count > timeout:
          raise Queue.Full

    with self.lock:
      self.queue.append((-1 * priority, item))
      self.total_size += len(item)

  def Get(self):
    """Retrieves the items from the queue."""
    with self.lock:
      if self._reversed:
        # We have leftovers from a partial Get().
        self._reversed.reverse()
        self.queue = self._reversed + self.queue

      self.queue.sort(key=lambda msg: msg[0])  # by priority only.
      self.queue.reverse()
      self._reversed, self.queue = self.queue, []

      while self._reversed:
        item = self._reversed.pop()[1]
        self.total_size -= len(item)
        yield item

  def Size(self):
    return self.total_size

  def Full(self):
    return self.total_size >= self.maxsize


class GRRThreadedWorker(GRRClientWorker, threading.Thread):
  """This client worker runs the main loop in another thread.

  The client which uses this worker is not blocked while queuing messages to be
  worked on. There is only a single working thread though.

  The overall effect is that the HTTP client is not blocked waiting for actions
  to be executed, and at the same time, the client working thread is not blocked
  waiting on network latency.
  """

  def __init__(self):
    super(GRRThreadedWorker, self).__init__()

    # This queue should never hit its maximum since the server will throttle
    # messages before this.
    self._in_queue = Queue.Queue(maxsize=1024)

    # The size of the output queue controls the worker thread. Once this queue
    # is too large, the worker thread will block until the queue is drained.
    self._out_queue = SizeQueue(maxsize=FLAGS.max_out_queue,
                                nanny=self.nanny_controller)

    self.daemon = True

    # Start our working thread.
    self.start()

  def Sleep(self, timeout):
    """Sleeps the calling thread with heartbeat."""
    self.nanny_controller.Heartbeat()
    time.sleep(timeout - int(timeout))

    # Split a long sleep interval into 1 second intervals so we can heartbeat.
    for _ in range(int(timeout)):
      time.sleep(1)
      # If the output queue is full, we are ready to do a post - no
      # point in waiting.
      if self._out_queue.Full():
        return

      self.nanny_controller.Heartbeat()

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
    queue = jobs_pb2.MessageList()
    length = 0

    for message in self._out_queue.Get():
      new_job = queue.job.add()
      new_job.MergeFromString(message)
      stats.STATS.Increment("grr_client_sent_messages")
      length += len(message)

      if length > max_size:
        break

    return queue

  def QueueResponse(self, serialized_message,
                    priority=jobs_pb2.GrrMessage.MEDIUM_PRIORITY):
    """Push the Serialized Message on the output queue."""
    self._out_queue.Put(serialized_message, priority=priority)

  def QueueMessages(self, messages):
    """Push the message to the input queue."""
    # Push all the messages to our input queue
    for message in messages:
      # Block if we need to wait for the worker thread to drain it. We do not
      # forget about heartbeats too.
      while True:
        try:
          self._in_queue.put(message, block=True, timeout=10)
          break
        except Queue.Full:
          self.nanny_controller.Heartbeat()

      stats.STATS.Increment("grr_client_received_messages")

  def InQueueSize(self):
    """Returns the number of protobufs ready to be sent in the queue."""
    return self._in_queue.qsize()

  def OutQueueSize(self):
    """Returns the total size of messages ready to be sent."""
    return self._out_queue.Size()

  def __del__(self):
    # This signals our worker thread to quit.
    self._in_queue.put(None, block=True)
    self.nanny_controller.StopNanny()

  def run(self):
    """Main thread for processing messages."""
    # We read the transaction log and fail any requests that are in it. If there
    # is anything in the transaction log we assume its there because we crashed
    # last time and let the server know.
    last_request = self.nanny_controller.GetTransactionLog()
    if last_request:
      self.SendReply(jobs_pb2.GrrStatus(
          status=jobs_pb2.GrrStatus.CLIENT_KILLED,
          error_message="Client killed during transaction"),
                     request_id=last_request.request_id,
                     response_id=1,
                     session_id=last_request.session_id,
                     message_type=jobs_pb2.GrrMessage.STATUS)
      self.nanny_controller.CleanTransactionLog()

    # As long as our output queue has some room we can process some
    # input messages:
    while True:
      message = self._in_queue.get(block=True)

      # A message of None is our terminal message.
      if message is None:
        break

      try:
        self.HandleMessage(message)
        # Catch any errors and keep going here
      except Exception as e:
        logging.warn("%s", e)
        self.SendReply(
            jobs_pb2.GrrStatus(
                status=jobs_pb2.GrrStatus.GENERIC_ERROR,
                error_message=utils.SmartUnicode(e)),
            request_id=message.request_id,
            response_id=message.response_id,
            session_id=message.session_id,
            message_type=jobs_pb2.GrrMessage.STATUS)
        if FLAGS.debug:
          pdb.post_mortem()


class GRRHTTPClient(object):
  """A class which abstracts away HTTP communications.

  To create a new GRR HTTP client, intantiate this class and generate
  its Run() method.

  The HTTP client starts up by loading a communicator which will read the
  client's public key (or create a new random key). Since the client ID is based
  on the key (its a hash of the public key), the communicator controls the
  client name.

  The client worker is then created - this will be the main thread for executing
  server messages.

  The HTTP engine simply reads pending messages from the client worker queues
  and makes POST requests to the server. The POST request may return the
  following error conditions:

    - A successful POST is signified by a status of 200: The client worker is
      given any requests the server has sent.

    - A status code of 406 means that the server is unable to communicate with
      the client. The client will then prepare an enrollment request CSR and
      send that as a high priority. Enrollment requests are throttled to a
      maximum of one every 10 minutes.

    - A status code of 500 is an error, the messages are re-queued and the
      client waits and retried to send them later.
  """

  STATS_SEND_INTERVALL = 50 * 60  # 50 minutes

  def __init__(self, ca_cert=None, worker=None, certificate=None):
    """Constructor.

    Args:
      ca_cert: String representation of a CA certificate to use for checking
          server certificate.
      worker: The client worker class to use. Defaults to GRRThreadedWorker().
      certificate: The certificate for this client. Defaults to
          FLAGS.certificate.
    """
    self.ca_cert = ca_cert
    self.communicator = ClientCommunicator(certificate=certificate or
                                           FLAGS.certificate)
    self.active_proxy = None
    self.consecutive_connection_errors = 0

    # The time we last sent an enrollment request.
    self.last_enrollment_time = 0

    # The time we last checked with the foreman.
    self.last_foreman_check = 0

    # The client worker does all the real work here.
    if worker:
      self.client_worker = worker()
    else:
      self.client_worker = GRRThreadedWorker()

    # Start off with a maximum poling interval
    self.sleep_time = FLAGS.poll_max

  def FindProxy(self):
    """This method tries all known proxies until one works.

    It does so by downloading the server.pem from the GRR server and returns
    it so it can be used by GetServerCert immediately.

    Returns:
      Contents of server.pem.
    """
    proxies = client_utils.FindProxies()

    # Also try to connect directly if all proxies fail.
    proxies.append("")

    for proxy in proxies:
      try:
        proxydict = {}
        if proxy:
          proxydict["http"] = proxy
        proxy_support = urllib2.ProxyHandler(proxydict)
        opener = urllib2.build_opener(proxy_support)
        urllib2.install_opener(opener)

        cert_url = "/".join((posixpath.dirname(FLAGS.location), "server.pem"))
        request = urllib2.Request(cert_url, None, {"Cache-Control": "no-cache"})
        handle = urllib2.urlopen(request, timeout=10)
        server_pem = handle.read()
        # If we have reached this point, this proxy is working.
        self.active_proxy = proxy
        handle.close()
        return server_pem
      except urllib2.URLError:
        pass

    # No connection is possible at all.
    return None

  def GetServerCert(self):
    """Obtain the server certificate and initialize the client."""
    cert_url = "/".join((posixpath.dirname(FLAGS.location), "server.pem"))
    try:
      data = self.FindProxy()
      if not data:
        raise urllib2.URLError("Could not connect to GRR server.")

      self.communicator.LoadServerCertificate(
          server_certificate=data, ca_certificate=self.ca_cert)

      self.server_certificate = data
    # This has to succeed or we can not go on
    except Exception, e:
      client_utils_common.ErrorOnceAnHour(
          "Unable to verify server certificate at %s: %s", cert_url, e)
      logging.info("Unable to verify server certificate at %s: %s",
                   cert_url, e)
      self.client_worker.Sleep(60)

  def MakeRequest(self, data, status):
    """Make a HTTP Post request and return the raw results."""
    status.sent_len = len(data)
    stats.STATS.Add("grr_client_sent_bytes", len(data))
    try:
      # Now send the request using POST
      start = time.time()
      url = FLAGS.location + "?api=%s" % client_config.NETWORK_API
      req = urllib2.Request(url, data,
                            {"Content-Type": "binary/octet-stream"})
      handle = urllib2.urlopen(req)
      data = handle.read()
      logging.debug("Request took %s Seconds", time.time() - start)

      self.consecutive_connection_errors = 0

      stats.STATS.Add("grr_client_received_bytes", len(data))
      return data

    except urllib2.HTTPError, e:
      status.code = e.code
      # Server can not talk with us - re-enroll.
      if e.code == 406:
        self.InitiateEnrolment()
        return ""
      else:
        status.sent_count = 0
        return str(e)

    except urllib2.URLError, e:
      # Wait a bit to prevent expiring messages too quickly when aggressively
      # polling
      time.sleep(5)
      status.code = 500
      status.sent_count = 0
      self.consecutive_connection_errors += 1
      if self.consecutive_connection_errors % PROXY_SCAN_ERROR_LIMIT == 0:
        self.FindProxy()
      return str(e)

    # Error path:
    status.sent_count = 0
    return ""

  def CheckStats(self):
    """Checks if the last transmission of client stats is too long ago."""
    if not stats.STATS.Get("grr_client_last_stats_sent_time"):
      stats.STATS.Set("grr_client_last_stats_sent_time", time.time())

    last = stats.STATS.Get("grr_client_last_stats_sent_time")
    if time.time() - last > self.STATS_SEND_INTERVALL:
      logging.info("Sending back client statistics to the server.")
      stats.STATS.Set("grr_client_last_stats_sent_time", time.time())
      action_cls = actions.ActionPlugin.classes.get(
          "GetClientStatsAuto", actions.ActionPlugin)
      action = action_cls(None, grr_worker=self.client_worker)
      action.Run(None)

  def RunOnce(self):
    """Makes a single request to the GRR server.

    Returns:
      A Status() object indicating how the last POST went.
    """
    try:
      status = Status()

      # Check if we have to send back statistics.
      self.CheckStats()

      # Grab some messages to send
      message_list = self.client_worker.Drain(max_size=FLAGS.max_post_size)

      sent_count = 0
      sent = {}
      require_fastpoll = False
      for message in message_list.job:
        sent_count += 1

        require_fastpoll |= message.require_fastpoll

        sent.setdefault(message.priority, 0)
        sent[message.priority] += 1

      status = Status(sent_count=sent_count, sent=sent,
                      require_fastpoll=require_fastpoll)

      # Make new encrypted ClientCommunication protobuf
      payload = jobs_pb2.ClientCommunication()

      # If our memory footprint is too large, we advertise that our input queue
      # is full. This will prevent the server from sending us any messages, and
      # hopefully allow us to work down our memory usage, by processing any
      # outstanding messages.
      if self.client_worker.MemoryExceeded():
        logging.info("Memory exceeded, will not retrieve jobs.")
        payload.queue_size = 1000000
      else:
        # Let the server know how many messages are currently queued in
        # the input queue.
        payload.queue_size = self.client_worker.InQueueSize()

      nonce = self.communicator.EncodeMessages(message_list, payload)

      response = self.MakeRequest(payload.SerializeToString(), status)
      if status.code != 200:
        logging.info("%s: Could not connect to server at %s, status %s (%s)",
                     self.communicator.common_name,
                     FLAGS.location, status.code, response)

        # Reschedule the tasks back on the queue so they get retried next time.
        messages = list(message_list.job)
        for message in messages:
          message.priority = jobs_pb2.GrrMessage.HIGH_PRIORITY
          message.require_fastpoll = False
          message.ttl -= 1
          if message.ttl > 0:
            # Schedule with high priority to make it jump the queue.
            self.client_worker.QueueResponse(
                message.SerializeToString(),
                jobs_pb2.GrrMessage.HIGH_PRIORITY + 1)
          else:
            logging.info("Dropped message due to retransmissions.")
        return status

      if not response:
        return status

      try:
        tmp = self.communicator.DecryptMessage(response)
        (messages, source, server_nonce) = tmp

        if server_nonce != nonce:
          logging.info("Nonce not matched.")
          status.code = 500
          return status

      except proto2_message.DecodeError:
        logging.info("Protobuf decode error. Bad URL or auth.")
        status.code = 500
        return status

      if source != self.communicator.server_name:
        logging.info("Received a message not from the server "
                     "%s, expected %s.", source,
                     self.communicator.server_name)
        status.code = 500
        return status

      status.received_count = len(messages)

      # Process all messages. Messages can be processed by clients in
      # any order since clients do not have state.
      self.client_worker.QueueMessages(messages)

    except Exception, e:
      # Catch everything, yes, this is terrible but necessary
      logging.warn("Uncaught exception caught. %s: %s",
                   sys.exc_info()[0], e)
      if status:
        status.code = 500
      if FLAGS.debug:
        pdb.post_mortem()

    return status

  def Run(self):
    """A Generator which makes a single request to the GRR server.

    Callers should generate this when they wish to make a connection
    to the server. It is up to the caller to sleep between calls in
    order to enforce the required network and CPU utilization
    policies.

    Yields:
      A Status() object indicating how the last POST went.
    """
    while True:
      while self.communicator.server_name is None:
        self.GetServerCert()
        if self.communicator.server_name:
          # Everything went as expected - we don't need to return to
          # the main loop (which would mean sleeping for a poll_time).
          break
        yield Status()

      now = time.time()
      # Check with the foreman if we need to
      if now > self.last_foreman_check + FLAGS.foreman_check_frequency:
        self.client_worker.SendReply(
            jobs_pb2.DataBlob(), session_id="W:Foreman",
            priority=jobs_pb2.GrrMessage.LOW_PRIORITY,
            require_fastpoll=False)
        self.last_foreman_check = now

      status = self.RunOnce()
      client_log.SetLogLevels()

      # We suicide if our memory is exceeded, and there is no more work to do
      # right now. Our death should not result in loss of messages since we are
      # not holding any requests in our input queues.
      if (self.client_worker.MemoryExceeded() and
          self.client_worker.InQueueSize() == 0 and
          self.client_worker.OutQueueSize() == 0):
        logging.warning("Memory exceeded - exiting.")
        sys.exit(-1)

      self.Wait(status)

      yield status

  def Wait(self, status):
    """This function implements the backoff algorithm.

    We sleep for the required amount of time based on the status of the last
    request.

    Args:
      status: The status of the last request.
    """
    # If we communicated this time we want to continue aggressively
    if status.require_fastpoll > 0 or status.received_count > 0:
      self.sleep_time = FLAGS.poll_min

    cn = self.communicator.common_name
    logging.debug("%s: Sending %s(%s), Received %s messages. Sleeping for %s",
                  cn, status.sent_count, status.sent_len,
                  status.received_count,
                  self.sleep_time)

    self.Sleep(self.sleep_time)

    # Back off slowly at first and fast if no answer.
    self.sleep_time = min(
        FLAGS.poll_max,
        max(FLAGS.poll_min, self.sleep_time) * FLAGS.poll_slew)

  def InitiateEnrolment(self):
    """Initiate the enrollment process.

    We do not sent more than one request every 10 minutes.
    """
    now = time.time()
    if now > self.last_enrollment_time + 10 * 60:
      self.last_enrollment_time = now
      # Send registration request:
      self.client_worker.SendReply(
          jobs_pb2.Certificate(type=jobs_pb2.Certificate.CSR,
                               pem=self.communicator.GetCSR()),
          session_id="CA:Enrol")

  def Sleep(self, timeout):
    self.client_worker.Sleep(timeout)




class ClientCommunicator(communicator.Communicator):
  """A communicator implementation for clients.

    This extends the generic communicator to include verification of
    server side certificates.
  """

  BITS = 1024

  def _ParseRSAKey(self, rsa):
    """Use the RSA private key to initialize our parameters.

    We set our client name as the hash of the RSA private key.

    Args:
      rsa: An RSA key pair.
    """
    # Our CN will be the first 64 bits of the hash of the public key.
    public_key = rsa.pub()[1]
    self.common_name = "C.%s" % (
        hashlib.sha256(public_key).digest()[:8].encode("hex"))

  def _LoadOurCertificate(self, certificate):
    """Loads an RSA key from the certificate.

    If no certificate is found, or it is invalid, we make a new random RSA key,
    and store it as our certificate.

    Args:
      certificate: The certificate to try getting the key from.

    Returns:
      An RSA key - either from the certificate or a new random key.
    """
    try:
      # This is our private key - make sure it has no password set.
      rsa = RSA.load_key_string(certificate, callback=lambda x: "")
      self._ParseRSAKey(rsa)

      logging.info("Starting client %s", self.common_name)
    except (X509.X509Error, RSA.RSAError):
      # 65537 is the standard value for e
      rsa = RSA.gen_key(self.BITS, 65537, lambda: None)

      self._ParseRSAKey(rsa)
      logging.info("Client pending enrolment %s", self.common_name)

      # Make new keys
      pk = EVP.PKey()
      pk.assign_rsa(rsa)

      # Save the keys
      self.SavePrivateKey(pk)

    return rsa

  def GetCSR(self):
    """Return our CSR in pem format."""
    csr = X509.Request()
    pk = EVP.PKey()
    rsa = self._LoadOurCertificate(self.private_key)
    pk.assign_rsa(rsa)
    csr.set_pubkey(pk)
    name = csr.get_subject()
    name.CN = self.common_name

    return csr.as_pem()

  def SavePrivateKey(self, pkey):
    """Store the new private key on disk."""
    bio = BIO.MemoryBuffer()
    pkey.save_key_bio(bio, cipher=None)

    self.private_key = bio.read_all()

    FLAGS.certificate = self.private_key
    try:
      conf.PARSER.UpdateConfig(["certificate"])
    except (IOError, OSError):
      pass

  def LoadServerCertificate(self, server_certificate=None,
                            ca_certificate=None):
    """Loads and verifies the server certificate."""
    try:
      server_cert = X509.load_cert_string(server_certificate)
      ca_cert = X509.load_cert_string(ca_certificate)

      # Check that the server certificate verifies
      if server_cert.verify(ca_cert.get_pubkey()) == 0:
        self.server_name = None
        raise IOError("Server cert is invalid.")

      # Make sure that the serial number is higher.
      server_cert_serial = server_cert.get_serial_number()

      if server_cert_serial < long(FLAGS.server_serial_number):
        # We can not accept this serial number...
        raise IOError("Server cert is too old.")
      elif server_cert_serial > long(FLAGS.server_serial_number):
        logging.info("Server serial number updated to %s", server_cert_serial)
        FLAGS.server_serial_number = long(server_cert_serial)
        try:
          conf.PARSER.UpdateConfig(["server_serial_number"])
        except (IOError, OSError):
          pass

    except X509.X509Error:
      raise IOError("Server cert is invalid.")

    self.server_name = self.pub_key_cache.GetCNFromCert(server_cert)
    self.server_certificate = server_certificate
    self.ca_certificate = ca_certificate

    # We need to store the serialised version of the public key due
    # to M2Crypto memory referencing bugs
    self.pub_key_cache.Put(
        self.server_name, self.pub_key_cache.PubKeyFromCert(server_cert))

  def EncodeMessages(self, message_list, result, **kwargs):
    # Force the right API to be used
    kwargs["api_version"] = client_config.NETWORK_API
    return  super(ClientCommunicator, self).EncodeMessages(
        message_list, result, **kwargs)
