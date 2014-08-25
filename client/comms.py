#!/usr/bin/env python
"""This class handles the GRR Client Communication.

Tests are in lib/communicator_test.py
"""


import hashlib
import os

import pdb
import posixpath
import Queue
import sys
import threading
import time
import traceback
import urllib2



from M2Crypto import BIO
from M2Crypto import EVP
from M2Crypto import RSA
from M2Crypto import X509
import psutil

from google.protobuf import message as proto2_message

import logging

from grr.client import actions
from grr.client import client_stats
from grr.client import client_utils
from grr.lib import communicator
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import type_info
from grr.lib import utils


# This determines after how many consecutive errors
# GRR will retry all known proxies.
PROXY_SCAN_ERROR_LIMIT = 10


class CommsInit(registry.InitHook):

  pre = ["StatsInit"]

  def RunOnce(self):
    # Counters used here
    stats.STATS.RegisterGaugeMetric("grr_client_last_stats_sent_time", long)
    stats.STATS.RegisterCounterMetric("grr_client_received_bytes")
    stats.STATS.RegisterCounterMetric("grr_client_received_messages")
    stats.STATS.RegisterCounterMetric("grr_client_slave_restarts")
    stats.STATS.RegisterCounterMetric("grr_client_sent_bytes")
    stats.STATS.RegisterCounterMetric("grr_client_sent_messages")


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

  # Client sends stats notifications at least every 50 minutes.
  STATS_MAX_SEND_INTERVAL = rdfvalue.Duration("50m")

  # Client sends stats notifications at most every 60 seconds.
  STATS_MIN_SEND_INTERVAL = rdfvalue.Duration("60s")

  def __init__(self):
    """Create a new GRRClientWorker."""
    super(GRRClientWorker, self).__init__()

    # Queue of messages from the server to be processed.
    self._in_queue = []

    # Queue of messages to be sent to the server.
    self._out_queue = []

    # A tally of the total byte count of messages
    self._out_queue_size = 0

    self._is_active = False

    # If True, ClientStats will be forcibly sent to server during next
    # CheckStats() call, if less than STATS_MIN_SEND_INTERVAL time has passed
    # since last stats notification was sent.
    self._send_stats_on_check = False

    # Last time when we've sent stats back to the server.
    self.last_stats_sent_time = None

    self.proc = psutil.Process(os.getpid())

    # We store suspended actions in this dict. We can retrieve the suspended
    # client action from here if needed.
    self.suspended_actions = {}

    # Use this to control the nanny transaction log.
    self.nanny_controller = client_utils.NannyController()
    self.nanny_controller.StartNanny()
    if not GRRClientWorker.stats_collector:
      GRRClientWorker.stats_collector = client_stats.ClientStatsCollector(self)
      GRRClientWorker.stats_collector.start()

    self.lock = threading.RLock()

  def Sleep(self, timeout):
    """Sleeps the calling thread with heartbeat."""
    self.nanny_controller.Heartbeat()
    time.sleep(timeout - int(timeout))

    # Split a long sleep interval into 1 second intervals so we can heartbeat.
    for _ in range(int(timeout)):
      time.sleep(1)

      self.nanny_controller.Heartbeat()

  def ClientMachineIsIdle(self):
    return psutil.cpu_percent(0.05) <= 100 * self.IDLE_THRESHOLD

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
    queue = rdfvalue.MessageList()

    length = 0
    self._out_queue.sort(key=lambda msg: msg[0])

    # Front pops are quadratic so we reverse the queue.
    self._out_queue.reverse()

    # Use implicit True/False evaluation instead of len (WTF)
    while self._out_queue and length < max_size:
      message = self._out_queue.pop()[1]
      queue.job.Append(message)
      stats.STATS.IncrementCounter("grr_client_sent_messages")

      # Maintain the output queue tally
      length += len(message.args)
      self._out_queue_size -= len(message.args)

    # Restore the old order.
    self._out_queue.reverse()

    return queue

  def SendReply(self, rdf_value=None, request_id=None, response_id=None,
                priority=None, session_id="W:0", message_type=None, name=None,
                require_fastpoll=None, ttl=None, blocking=True, task_id=None):
    """Send the protobuf to the server.

    Args:
      rdf_value: The RDFvalue to return.
      request_id: The id of the request this is a response to.
      response_id: The id of this response.
      priority: The priority of this message, used to jump the scheduling queue.
      session_id: The session id of the flow.
      message_type: The contents of this message, MESSAGE, STATUS, ITERATOR or
                    RDF_VALUE.
      name: The name of the client action that sends this response.
      require_fastpoll: If set, this will set the client to fastpoll mode after
                        sending this message.
      ttl: The time to live of this message.
      blocking: If the output queue is full, block until there is space.
      task_id: The task ID that the request was queued at. We send this back to
        the server so it can de-queue the request.
    Raises:
      RuntimeError: An object other than an RDFValue was passed for sending.
    """
    if not isinstance(rdf_value, rdfvalue.RDFValue):
      raise RuntimeError("Sending objects other than RDFValues not supported.")

    message = rdfvalue.GrrMessage(
        session_id=session_id, task_id=task_id, name=name,
        response_id=response_id, request_id=request_id,
        priority=priority, require_fastpoll=require_fastpoll,
        ttl=ttl, type=message_type)

    if rdf_value:
      message.payload = rdf_value

    serialized_message = message.SerializeToString()

    self.ChargeBytesToSession(session_id, len(serialized_message))

    if message.type == rdfvalue.GrrMessage.Type.STATUS:
      rdf_value.network_bytes_sent = self.sent_bytes_per_flow[session_id]
      del self.sent_bytes_per_flow[session_id]
      message.args = rdf_value.SerializeToString()

    try:
      self.QueueResponse(message, priority=message.priority, blocking=blocking)
    except Queue.Full:
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
    if limit and (self.sent_bytes_per_flow[session_id] > limit):
      self.SendClientAlert("Network limit exceeded.")
      raise actions.NetworkBytesExceededError(
          "Action exceeded network send limit.")

  def QueueResponse(self, message,
                    priority=rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY,
                    blocking=True):
    """Push the Serialized Message on the output queue."""
    # The simple queue has no size restrictions so we never block and ignore
    # this parameter.
    _ = blocking
    self._out_queue.append((-1 * priority, message))

    # Maintain the tally of the output queue size.  We estimate the size of the
    # message by only considering the args member. This is usually close enough
    # estimate to the overall size and avoids us un-necessarily serializing
    # here.
    self._out_queue_size += len(message.args)

  def HandleMessage(self, message):
    """Entry point for processing jobs.

    Args:
        message: The GrrMessage that was delivered from the server.
    """
    self._is_active = True
    try:
      # Write the message to the transaction log.
      self.nanny_controller.WriteTransactionLog(message)

      # Try to retrieve a suspended action from the client worker.
      try:
        suspended_action_id = message.payload.iterator.suspended_action
        action = self.suspended_actions[suspended_action_id]

      except (AttributeError, KeyError):
        # Otherwise make a new action instance.
        action_cls = actions.ActionPlugin.classes.get(
            message.name, actions.ActionPlugin)
        action = action_cls(grr_worker=self)

      # Heartbeat so we have the full period to work on this message.
      action.Progress()
      action.Execute(message)

      # If we get here without exception, we can remove the transaction.
      self.nanny_controller.CleanTransactionLog()
    finally:
      self._is_active = False
      # We want to send ClientStats when client action is complete.
      self._send_stats_on_check = True

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
      stats.STATS.IncrementCounter("grr_client_received_messages")

    # As long as our output queue has some room we can process some
    # input messages:
    while self._in_queue and (
        self._out_queue_size < config_lib.CONFIG["Client.max_out_queue"]):
      message = self._in_queue.pop(0)

      try:
        self.HandleMessage(message)
        # Catch any errors and keep going here
      except Exception as e:  # pylint: disable=broad-except
        self.SendReply(
            rdfvalue.GrrStatus(
                status=rdfvalue.GrrStatus.ReturnedStatus.GENERIC_ERROR,
                error_message=utils.SmartUnicode(e)),
            request_id=message.request_id,
            response_id=message.response_id,
            session_id=message.session_id,
            task_id=message.task_id,
            message_type=rdfvalue.GrrMessage.Type.STATUS)
        if flags.FLAGS.debug:
          pdb.post_mortem()

  def MemoryExceeded(self):
    """Returns True if our memory footprint is too large."""
    rss_size, _ = self.proc.memory_info()
    return rss_size/1024/1024 > config_lib.CONFIG["Client.rss_max"]

  def InQueueSize(self):
    """Returns the number of protobufs ready to be sent in the queue."""
    return len(self._in_queue)

  def OutQueueSize(self):
    """Returns the total size of messages ready to be sent."""
    return len(self._out_queue)

  def IsActive(self):
    """Returns True if worker is currently handling a message."""
    return self._is_active

  def CheckStats(self):
    """Checks if the last transmission of client stats is too long ago."""
    if self.last_stats_sent_time is None:
      self.last_stats_sent_time = rdfvalue.RDFDatetime().Now()
      stats.STATS.SetGaugeValue("grr_client_last_stats_sent_time",
                                self.last_stats_sent_time.AsSecondsFromEpoch())

    time_since_last_check = (rdfvalue.RDFDatetime().Now() -
                             self.last_stats_sent_time)

    # No matter what, we don't want to send stats more often than
    # once per STATS_MIN_SEND_INTERVAL.
    if time_since_last_check < self.STATS_MIN_SEND_INTERVAL:
      return

    if (time_since_last_check > self.STATS_MAX_SEND_INTERVAL or
        self._is_active or self._send_stats_on_check):

      self._send_stats_on_check = False

      logging.info("Sending back client statistics to the server.")

      action_cls = actions.ActionPlugin.classes.get(
          "GetClientStatsAuto", actions.ActionPlugin)
      action = action_cls(grr_worker=self)
      action.Run(rdfvalue.GetClientStatsRequest(
          start_time=self.last_stats_sent_time))

      self.last_stats_sent_time = rdfvalue.RDFDatetime().Now()
      stats.STATS.SetGaugeValue("grr_client_last_stats_sent_time",
                                self.last_stats_sent_time.AsSecondsFromEpoch())

  def SendNannyMessage(self):
    msg = self.nanny_controller.GetNannyMessage()
    if msg:
      self.SendReply(
          rdfvalue.DataBlob(string=msg), session_id="W:NannyMessage",
          priority=rdfvalue.GrrMessage.Priority.LOW_PRIORITY,
          require_fastpoll=False)
      self.nanny_controller.ClearNannyMessage()

  def SendClientAlert(self, msg):
    self.SendReply(
        rdfvalue.DataBlob(string=msg), session_id="W:ClientAlert",
        priority=rdfvalue.GrrMessage.Priority.LOW_PRIORITY,
        require_fastpoll=False)


class SizeQueue(object):
  """A Queue which limits the total size of its elements.

  The standard Queue implementations uses the total number of elements to block
  on. In the client we want to limit the total memory footprint, hence we need
  to use the total size as a measure of how full the queue is.

  TODO(user): this class needs some attention to ensure it is thread safe.
  """
  total_size = 0

  def __init__(self, maxsize=1024, nanny=None):
    self.lock = threading.RLock()
    self.queue = []
    self._reversed = []
    self.total_size = 0
    self.maxsize = maxsize
    self.nanny = nanny

  def Put(self, item, priority=rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY,
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
    # We only queue already serialized objects so we know how large they are.
    if isinstance(item, rdfvalue.RDFValue):
      item = item.SerializeToString()

    if priority >= rdfvalue.GrrMessage.Priority.HIGH_PRIORITY:
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
    self._in_queue = utils.HeartbeatQueue(
        callback=self.nanny_controller.Heartbeat, maxsize=1024)

    # The size of the output queue controls the worker thread. Once this queue
    # is too large, the worker thread will block until the queue is drained.
    self._out_queue = SizeQueue(
        maxsize=config_lib.CONFIG["Client.max_out_queue"],
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
    queue = rdfvalue.MessageList()
    length = 0

    for message in self._out_queue.Get():
      queue.job.Append(message)
      stats.STATS.IncrementCounter("grr_client_sent_messages")
      length += len(message)

      if length > max_size:
        break

    return queue

  def QueueResponse(self, message,
                    priority=rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY,
                    blocking=True):
    """Push the Serialized Message on the output queue."""
    self._out_queue.Put(message, priority=priority, block=blocking)

  def QueueMessages(self, messages):
    """Push the message to the input queue."""
    # Push all the messages to our input queue
    for message in messages:
      self._in_queue.put(message, block=True)

      stats.STATS.IncrementCounter("grr_client_received_messages")

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

  def OnStartup(self):
    """A handler that is called on client startup."""
    # We read the transaction log and fail any requests that are in it. If there
    # is anything in the transaction log we assume its there because we crashed
    # last time and let the server know.
    last_request = self.nanny_controller.GetTransactionLog()
    if last_request:
      status = rdfvalue.GrrStatus(
          status=rdfvalue.GrrStatus.ReturnedStatus.CLIENT_KILLED,
          error_message="Client killed during transaction")
      nanny_status = self.nanny_controller.GetNannyStatus()
      if nanny_status:
        status.nanny_status = nanny_status

      self.SendReply(status,
                     request_id=last_request.request_id,
                     response_id=1,
                     session_id=last_request.session_id,
                     message_type=rdfvalue.GrrMessage.Type.STATUS)

    self.nanny_controller.CleanTransactionLog()

    # Inform the server that we started.
    action_cls = actions.ActionPlugin.classes.get(
        "SendStartupInfo", actions.ActionPlugin)
    action = action_cls(grr_worker=self)
    action.Run(None, ttl=1)

  def run(self):
    """Main thread for processing messages."""

    self.OnStartup()

    # As long as our output queue has some room we can process some
    # input messages:
    while True:
      message = self._in_queue.get()

      # A message of None is our terminal message.
      if message is None:
        break

      try:
        self.HandleMessage(message)
        # Catch any errors and keep going here
      except Exception as e:  # pylint: disable=broad-except
        logging.warn("%s", e)
        self.SendReply(
            rdfvalue.GrrStatus(
                status=rdfvalue.GrrStatus.ReturnedStatus.GENERIC_ERROR,
                error_message=utils.SmartUnicode(e)),
            request_id=message.request_id,
            response_id=message.response_id,
            session_id=message.session_id,
            task_id=message.task_id,
            message_type=rdfvalue.GrrMessage.Type.STATUS)
        if flags.FLAGS.debug:
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

  def __init__(self, ca_cert=None, worker=None, private_key=None):
    """Constructor.

    Args:
      ca_cert: String representation of a CA certificate to use for checking
          server certificate.

      worker: The client worker class to use. Defaults to GRRThreadedWorker().

      private_key: The private key for this client. Defaults to
          config Client.private_key.
    """
    self.ca_cert = ca_cert
    if private_key is None:
      private_key = config_lib.CONFIG.Get("Client.private_key", default=None)

    self.communicator = ClientCommunicator(private_key=private_key)

    self.active_server_url = None

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

    # Start off with a maximum polling interval
    self.sleep_time = config_lib.CONFIG["Client.poll_max"]

  def GetServerUrl(self):
    if not self.active_server_url:
      if not self.EstablishConnection():
        return ""
    return self.active_server_url

  def EstablishConnection(self):
    """Finds a connection to the server and initializes the client.

    This method tries all pairs of location urls and known proxies until it
    finds one that works.

    It does so by downloading the server.pem from the GRR server and verifies
    it directly. Note that this also refreshes the server certificate.

    Returns:
      A boolean indicating success.
    Side-effect:
      On success we set self.active_server_url, which is used by other methods
      to check if we have made a successful connection in the past.
    """
    # This gets proxies from the platform specific proxy settings.
    proxies = client_utils.FindProxies()

    # Also try to connect directly if all proxies fail.
    proxies.append("")

    # Also try all proxies configured in the config system.
    proxies.extend(config_lib.CONFIG["Client.proxy_servers"])
    for server_url in config_lib.CONFIG["Client.control_urls"]:
      for proxy in proxies:
        try:
          proxydict = {}
          if proxy:
            proxydict["http"] = proxy
          proxy_support = urllib2.ProxyHandler(proxydict)
          opener = urllib2.build_opener(proxy_support)
          urllib2.install_opener(opener)

          cert_url = "/".join((posixpath.dirname(server_url), "server.pem"))
          request = urllib2.Request(cert_url, None,
                                    {"Cache-Control": "no-cache"})
          handle = urllib2.urlopen(request, timeout=10)
          server_pem = handle.read()
          if "BEGIN CERTIFICATE" in server_pem:
            # Now we know that this proxy is working. We still have
            # to verify the certificate.
            self.communicator.LoadServerCertificate(
                server_certificate=server_pem, ca_certificate=self.ca_cert)

            # If we reach this point, the server can be reached and the
            # certificate is valid.
            self.server_certificate = server_pem
            self.active_server_url = server_url
            handle.close()
            return True
        except urllib2.URLError:
          pass
        except Exception as e:  # pylint: disable=broad-except
          logging.info("Unable to verify server certificate at %s: %s",
                       cert_url, e)

    # No connection is possible at all.
    logging.info("Could not connect to GRR servers %s, directly or through "
                 "these proxies: %s.", config_lib.CONFIG["Client.control_urls"],
                 proxies)
    return False

  def MakeRequest(self, data, status):
    """Make a HTTP Post request and return the raw results."""
    status.sent_len = len(data)
    stats.STATS.IncrementCounter("grr_client_sent_bytes", len(data))
    return_msg = ""

    try:
      # Now send the request using POST
      start = time.time()
      url = "%s?api=%s" % (self.GetServerUrl(),
                           config_lib.CONFIG["Network.api"])

      req = urllib2.Request(utils.SmartStr(url), data,
                            {"Content-Type": "binary/octet-stream"})
      handle = urllib2.urlopen(req)
      data = handle.read()
      logging.debug("Request took %s Seconds", time.time() - start)

      self.consecutive_connection_errors = 0

      stats.STATS.IncrementCounter("grr_client_received_bytes", len(data))
      return data

    except urllib2.HTTPError as e:
      status.code = e.code
      # Server can not talk with us - re-enroll.
      if e.code == 406:
        self.InitiateEnrolment(status)
        return_msg = ""
      else:
        self.consecutive_connection_errors += 1
        if self.consecutive_connection_errors % PROXY_SCAN_ERROR_LIMIT == 0:
          # Reset the active connection, this will trigger a reconnect attempt.
          self.active_server_url = None
        return_msg = str(e)

    except urllib2.URLError as e:
      status.code = 500
      self.consecutive_connection_errors += 1
      if self.consecutive_connection_errors % PROXY_SCAN_ERROR_LIMIT == 0:
        # Reset the active connection, this will trigger a reconnect attempt.
        self.active_server_url = None
      return_msg = str(e)

    # Error path:
    status.sent_count = 0
    return return_msg

  def RunOnce(self):
    """Makes a single request to the GRR server.

    Returns:
      A Status() object indicating how the last POST went.
    """
    try:
      status = Status()

      # Here we only drain messages if we were able to connect to the server in
      # the last poll request. Otherwise we just wait until the connection comes
      # back so we don't expire our messages too fast.
      if self.consecutive_connection_errors == 0:
        # Grab some messages to send
        message_list = self.client_worker.Drain(
            max_size=config_lib.CONFIG["Client.max_post_size"])
      else:
        message_list = rdfvalue.MessageList()

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

      # Make new encrypted ClientCommunication rdfvalue.
      payload = rdfvalue.ClientCommunication()

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
        # We don't print response here since it should be encrypted and will
        # cause ascii conversion errors.
        logging.info("%s: Could not connect to server at %s, status %s",
                     self.communicator.common_name,
                     self.GetServerUrl(),
                     status.code)

        # Reschedule the tasks back on the queue so they get retried next time.
        messages = list(message_list.job)
        for message in messages:
          message.priority = rdfvalue.GrrMessage.Priority.HIGH_PRIORITY
          message.require_fastpoll = False
          message.ttl -= 1
          if message.ttl > 0:
            # Schedule with high priority to make it jump the queue.
            self.client_worker.QueueResponse(
                message, rdfvalue.GrrMessage.Priority.HIGH_PRIORITY + 1)
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

      # If we're not going to fastpoll based on outbound messages, check to see
      # if any inbound messages want us to fastpoll. This means we drop to
      # fastpoll immediately on a new request rather than waiting for the next
      # beacon to report results.
      if not status.require_fastpoll:
        for message in messages:
          if message.require_fastpoll:
            status.require_fastpoll = True
            break

      # Process all messages. Messages can be processed by clients in
      # any order since clients do not have state.
      self.client_worker.QueueMessages(messages)

    except Exception:  # pylint: disable=broad-except
      # Catch everything, yes, this is terrible but necessary
      logging.warn("Uncaught exception caught: %s" % traceback.format_exc())
      if status:
        status.code = 500
      if flags.FLAGS.debug:
        pdb.post_mortem()

    return status

  def SendForemanRequest(self):
    self.client_worker.SendReply(
        rdfvalue.DataBlob(), session_id="W:Foreman",
        priority=rdfvalue.GrrMessage.Priority.LOW_PRIORITY,
        require_fastpoll=False)

  def Run(self):
    """A Generator which makes a single request to the GRR server.

    Callers should generate this when they wish to make a connection
    to the server. It is up to the caller to sleep between calls in
    order to enforce the required network and CPU utilization
    policies.

    Raises:
      RuntimeError: Too many connection errors have been encountered.
    Yields:
      A Status() object indicating how the last POST went.
    """
    while True:
      self.consecutive_connection_errors = 0
      while self.active_server_url is None:
        if self.EstablishConnection():
          # Everything went as expected - we don't need to return to
          # the main loop (which would mean sleeping for a poll_time).
          break
        else:
          # If we can't reconnect to the server for a long time, we restart
          # to reset our state. In some very rare cases, the urrlib can get
          # confused and we need to reset it before we can start talking to
          # the server again.
          self.consecutive_connection_errors += 1
          limit = config_lib.CONFIG["Client.connection_error_limit"]
          if self.consecutive_connection_errors > limit:
            raise RuntimeError("Too many connection errors, exiting.")

          # Constantly retrying will not work, we back off a bit.
          time.sleep(60)
        yield Status()

      # Check if there is a message from the nanny to be sent.
      self.client_worker.SendNannyMessage()

      now = time.time()
      # Check with the foreman if we need to
      if (now > self.last_foreman_check +
          config_lib.CONFIG["Client.foreman_check_frequency"]):
        # We must not queue messages from the comms thread with blocking=True
        # or we might deadlock. If the output queue is full, we can't accept
        # more work from the foreman anyways so it's ok to drop the message.
        try:
          self.client_worker.SendReply(
              rdfvalue.DataBlob(), session_id="W:Foreman",
              priority=rdfvalue.GrrMessage.Priority.LOW_PRIORITY,
              require_fastpoll=False, blocking=False)
          self.last_foreman_check = now
        except Queue.Full:
          pass

      status = self.RunOnce()

      # We suicide if our memory is exceeded, and there is no more work to do
      # right now. Our death should not result in loss of messages since we are
      # not holding any requests in our input queues.
      if (self.client_worker.MemoryExceeded() and
          not self.client_worker.IsActive() and
          self.client_worker.InQueueSize() == 0 and
          self.client_worker.OutQueueSize() == 0):
        logging.warning("Memory exceeded - exiting.")
        self.client_worker.SendClientAlert("Memory limit exceeded, exiting.")
        # Make sure this will return True so we don't get more work.
        # pylint: disable=g-bad-name
        self.client_worker.MemoryExceeded = lambda: True
        # pylint: enable=g-bad-name
        # Now send back the client message.
        self.RunOnce()
        # And done for now.
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
    if status.code == 500:
      # In this case, the server just became unavailable. We have been able
      # to make connections before but now we can't anymore for some reason.
      # We want to wait at least some time before retrying in case the frontend
      # served a 500 error because it is overloaded already.
      error_sleep_time = max(config_lib.CONFIG["Client.error_poll_min"],
                             self.sleep_time)
      logging.debug("Could not reach server. Sleeping for %s", error_sleep_time)
      self.Sleep(error_sleep_time, heartbeat=False)
      return

    # If we communicated this time we want to continue aggressively
    if status.require_fastpoll > 0:
      self.sleep_time = config_lib.CONFIG["Client.poll_min"]

    cn = self.communicator.common_name
    logging.debug("%s: Sending %s(%s), Received %s messages. Sleeping for %s",
                  cn, status.sent_count, status.sent_len,
                  status.received_count,
                  self.sleep_time)

    self.Sleep(self.sleep_time, heartbeat=False)

    # Back off slowly at first and fast if no answer.
    self.sleep_time = min(
        config_lib.CONFIG["Client.poll_max"],
        max(config_lib.CONFIG["Client.poll_min"], self.sleep_time) *
        config_lib.CONFIG["Client.poll_slew"])

  def InitiateEnrolment(self, status):
    """Initiate the enrollment process.

    We do not sent more than one request every 10 minutes.

    Args:
      status: The http status object, used to set fastpoll mode if this is the
              first enrollment request sent since restart.
    """
    now = time.time()
    if now > self.last_enrollment_time + 10 * 60:
      if not self.last_enrollment_time:
        # This is the first enrolment request - we should enter fastpoll mode.
        status.require_fastpoll = True
      self.last_enrollment_time = now
      # Send registration request:
      self.client_worker.SendReply(
          rdfvalue.Certificate(type=rdfvalue.Certificate.Type.CSR,
                               pem=self.communicator.GetCSR()),
          session_id=rdfvalue.SessionID("aff4:/flows/CA:Enrol"))

  def Sleep(self, timeout, heartbeat=False):
    if not heartbeat:
      time.sleep(timeout)
    else:
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
    self.common_name = rdfvalue.ClientURN("C.%s" % (
        hashlib.sha256(public_key).digest()[:8].encode("hex")))

  def _LoadOurCertificate(self):
    """Loads an RSA key from the certificate.

    If no certificate is found, or it is invalid, we make a new random RSA key,
    and store it as our certificate.

    Returns:
      An RSA key - either from the certificate or a new random key.
    """
    if self.private_key:
      try:
        # This is our private key - make sure it has no password set.
        self.private_key.Validate()
        rsa = self.private_key.GetPrivateKey()
        self._ParseRSAKey(rsa)

        logging.info("Starting client %s", self.common_name)
        return rsa

      except type_info.TypeValueError:
        pass

    # We either have an invalid key or no key. We just generate a new one.
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
    rsa = self._LoadOurCertificate()
    pk.assign_rsa(rsa)
    csr.set_pubkey(pk)
    name = csr.get_subject()
    name.CN = str(self.common_name)
    csr.sign(pk, "sha1")
    return csr.as_pem()

  def SavePrivateKey(self, pkey):
    """Store the new private key on disk."""
    bio = BIO.MemoryBuffer()
    pkey.save_key_bio(bio, cipher=None)

    self.private_key = rdfvalue.PEMPrivateKey(bio.read_all())

    config_lib.CONFIG.Set("Client.private_key", self.private_key)
    config_lib.CONFIG.Write()

  def LoadServerCertificate(self, server_certificate=None,
                            ca_certificate=None):
    """Loads and verifies the server certificate."""
    try:
      server_cert = X509.load_cert_string(str(server_certificate))
      ca_cert = X509.load_cert_string(str(ca_certificate))

      # Check that the server certificate verifies
      if server_cert.verify(ca_cert.get_pubkey()) != 1:
        self.server_name = None
        raise IOError("Server cert is invalid.")

      # Make sure that the serial number is higher.
      server_cert_serial = server_cert.get_serial_number()

      if server_cert_serial < config_lib.CONFIG["Client.server_serial_number"]:
        # We can not accept this serial number...
        raise IOError("Server cert is too old.")
      elif server_cert_serial > config_lib.CONFIG[
          "Client.server_serial_number"]:
        logging.info("Server serial number updated to %s", server_cert_serial)
        config_lib.CONFIG.Set("Client.server_serial_number", server_cert_serial)

        # Save the new data to the config file.
        config_lib.CONFIG.Write()

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
    kwargs["api_version"] = config_lib.CONFIG["Network.api"]
    return  super(ClientCommunicator, self).EncodeMessages(
        message_list, result, **kwargs)
