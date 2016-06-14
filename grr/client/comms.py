#!/usr/bin/env python
"""This class handles the GRR Client Communication.

The GRR client uses HTTP to communicate with the server.

The client connections are controlled via a number of config parameters:

- Client.retry_error_limit: Number of times the client will try existing
  connections before giving up.

- Client.connection_error_limit: The client will exit after this many
  consecutive errors.

- Client.error_poll_min: Time to wait between retries in an ERROR state.

- Client.server_urls: A list of URLs for the base control server.

- Client.proxy_servers: A list of proxies to try to connect through.

- Client.poll_max, Client.poll_min: Parameters for timing of SLOW POLL and FAST
  POLL modes.

The client goes through a state machine:

1) In the INITIAL state, the client has no active server URL or active proxy and
   it is therefore searching through the list of proxies and connection URLs for
   one that works. The client will try each combination of proxy/URL in turn
   without delay until a 200 or a 406 message is seen. If all possibilities are
   exhausted, and a connection is not established, the client will switch to
   SLOW POLL mode (and retry connection every Client.poll_max).

2) In SLOW POLL mode the client will wait Client.poll_max between re-connection
   attempts.

3) If a server is detected, the client will communicate with it. If the server
   returns a 406 error, the client will send an enrollment request. Enrollment
   requests are only re-sent every 10 minutes (regardless of the frequency of
   406 responses). Note that a 406 message is considered a valid connection and
   the client will not search for URL/Proxy combinations as long as it keep
   receiving 406 responses.

4) During CONNECTED state, the client has a valid server certificate, receives
   200 responses from the server and is able to send messages to the server. The
   polling frequency in this state is determined by the polling mode requested
   by the messages received or send. If any message from the server or from the
   worker queue (to the server) has the require_fastpoll flag set, the client
   switches into FAST POLL mode.

5) When not in FAST POLL mode, the polling frequency is controlled by the
   Timer() object. It is currently a geometrically decreasing function which
   starts at the Client.poll_min and approaches the Client.poll_max setting.

6) If a 500 error occurs in the CONNECTED state, the client will assume that the
   server is temporarily down. The client will switch to the RETRY state and
   retry sending the data with a fixed frequency determined by
   Client.error_poll_min to the same URL/Proxy combination. The client will
   retry for Client.retry_error_limit times (default 10) before exiting the
   CONNECTED state and returning to the INITIAL state (i.e. the client will
   start searching for a new URL/Proxy combination). If a retry is successful,
   the client will return to its designated polling frequency.

7) If there are Client.connection_error_limit failures, the client will
   exit. Hopefully the nanny will restart the client.

Examples:

1) Client starts up on a disconnected network: Client will try every URL/Proxy
   combination once every Client.poll_max (default 10 minutes).

2) Client connects successful but loses network connectivity. Client will re-try
   Client.retry_error_limit (10 times) every Client.error_poll_min (1 Min) to
   resent the last message. If it does not succeed it starts searching for a new
   URL/Proxy combination as in example 1.

"""


import hashlib
import os

import pdb
import posixpath
import Queue
import socket
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

import logging

from grr.client import actions
from grr.client import client_stats
from grr.client import client_utils
from grr.lib import communicator
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import queues
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import stats
from grr.lib import type_info
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto as rdf_crypto
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict


class HTTPObject(object):
  """Data returned from a HTTP connection."""

  def __init__(self, url="", data="", proxy="", code=500, duration=0):
    self.url = url
    self.data = data
    self.proxy = proxy
    self.code = code
    # Contains the decoded data from the 'control' endpoint.
    self.messages = self.source = self.nonce = None
    self.duration = duration

  def Success(self):
    """Returns if the request was successful."""
    return self.code in (200, 406)


class HTTPManager(object):
  """A manager for all HTTP/S connections.

  NOTE: This HTTPManager is not thread safe and should not be shared between
  threads.
  """

  def __init__(self, heart_beat_cb=None):
    self.heart_beat_cb = heart_beat_cb
    self.proxies = self._GetProxies()
    self.base_urls = self._GetBaseURLs()

    # We start checking with this proxy.
    self.last_proxy_index = 0
    self.last_base_url_index = 0

    # If we have connected previously but now suddenly fail to connect, we try
    # the connection a few times (Client.retry_error_limit) before we determine
    # that it is failed.
    self.consecutive_connection_errors = 0
    self.retry_error_limit = config_lib.CONFIG["Client.retry_error_limit"]

    self.active_base_url = None
    self.error_poll_min = config_lib.CONFIG["Client.error_poll_min"]

  def _GetBaseURLs(self):
    """Gathers a list of base URLs we will try."""
    result = config_lib.CONFIG["Client.server_urls"]
    if not result:
      # Backwards compatibility - deduce server_urls from Client.control_urls.
      for control_url in config_lib.CONFIG["Client.control_urls"]:
        result.append(posixpath.dirname(control_url) + "/")

    # Check the URLs for trailing /. This traps configuration errors.
    for url in result:
      if not url.endswith("/"):
        raise RuntimeError("Bad URL: %s URLs must end with /" % url)

    return result

  def _GetProxies(self):
    """Gather a list of proxies to use."""
    # Detect proxies from the OS environment.
    result = client_utils.FindProxies()

    # Also try to connect directly if all proxies fail.
    result.append("")

    # Also try all proxies configured in the config system.
    result.extend(config_lib.CONFIG["Client.proxy_servers"])

    return result

  def _ConcatenateURL(self, base, url):
    if not url.startswith("/"):
      url = "/" + url

    if base.endswith("/"):
      base = base[:-1]

    return base + url

  def OpenServerEndpoint(self,
                         path,
                         verify_cb=lambda x: True,
                         data=None,
                         request_opts=None):
    """Search through all the base URLs to connect to one that works."""
    tries = 0
    last_error = HTTPObject(code=404)

    while tries < len(self.base_urls):
      base_url_index = self.last_base_url_index % len(self.base_urls)
      active_base_url = self.base_urls[base_url_index]

      result = self.OpenURL(
          self._ConcatenateURL(active_base_url, path),
          data=data,
          verify_cb=verify_cb,
          request_opts=request_opts)

      if not result.Success():
        tries += 1
        self.last_base_url_index += 1
        last_error = result
        continue

      # The URL worked - we record that.
      self.active_base_url = active_base_url

      return result

    # No connection is possible at all.
    logging.info("Could not connect to GRR servers %s, directly or through "
                 "these proxies: %s.", self.base_urls, self.proxies)

    return last_error

  def OpenURL(self,
              url,
              verify_cb=lambda x: True,
              data=None,
              request_opts=None):
    """Get the requested URL.

    Note that we do not have any concept of timing here - we try to connect
    through all proxies as fast as possible until one works. Timing and poll
    frequency is left to the calling code.

    Args:
      url: The URL to fetch
      verify_cb: An optional callback which can be used to validate the URL. It
        receives the HTTPObject and return True if this seems OK, False
        otherwise. For example, if we are behind a captive portal we might
        receive invalid object even though HTTP status is 200.
      data: If specified, we POST this data to the server.
      request_opts: A dict containing optional headers.

    Returns:
      An HTTPObject instance or None if a connection could not be made.
    """
    # Start checking the proxy from the last value found.
    tries = 0
    last_error = 500

    while tries < len(self.proxies):
      proxy_index = self.last_proxy_index % len(self.proxies)
      proxy = self.proxies[proxy_index]
      try:
        proxydict = {}
        if proxy:
          proxydict["http"] = proxy
          proxydict["https"] = proxy

        proxy_support = urllib2.ProxyHandler(proxydict)
        opener = urllib2.build_opener(proxy_support)
        urllib2.install_opener(opener)

        request_opts = (request_opts or {}).copy()
        request_opts["Cache-Control"] = "no-cache"
        request = urllib2.Request(url, data, request_opts)

        duration, handle = self._RetryRequest(request)
        data = handle.read()

        result = HTTPObject(url=url,
                            data=data,
                            proxy=proxy,
                            code=200,
                            duration=duration)

        if not verify_cb(result):
          raise urllib2.HTTPError(url=url,
                                  code=500,
                                  msg="Data not verified.",
                                  hdrs=[],
                                  fp=handle)

        # The last connection worked.
        self.consecutive_connection_errors = 0
        return result

      except urllib2.HTTPError as e:
        # Especially trap a 406 error message - it means the client needs to
        # enroll.
        if e.code == 406:
          # A 406 is not considered an error as the frontend is reachable. If we
          # considered it as an error the client would be unable to send the
          # enrollment request since connection errors disable message draining.
          self.consecutive_connection_errors = 0
          return HTTPObject(code=406)

        # Try the next proxy
        self.last_proxy_index = proxy_index + 1
        tries += 1
        last_error = e.code

      except urllib2.URLError as e:
        # Try the next proxy
        self.last_proxy_index = proxy_index + 1
        tries += 1
        last_error = 500

    # We failed to connect at all here.
    return HTTPObject(code=last_error)

  def _RetryRequest(self, request):
    """Retry the request a few times before we determine it failed.

    Sometimes the frontend becomes loaded and issues a 500 error to throttle the
    clients. We wait Client.error_poll_min seconds between each attempt to back
    off the frontend. Note that this does not affect any timing algorithm in the
    client itself which is controlled by the Timer() class.

    Args:
      request: A urllib2 request object.

    Returns:
      a tuple of duration, urllib2.urlopen response.

    """
    while True:
      try:
        now = time.time()
        result = urllib2.urlopen(
            request, timeout=config_lib.CONFIG["Client.http_timeout"])

        return time.time() - now, result

      except (urllib2.HTTPError, urllib2.URLError, socket.timeout) as e:
        self.consecutive_connection_errors += 1

        # Request failed. If we connected successfully before we attempt a few
        # connections before we determine that it really failed. This might
        # happen if the front end is loaded and returns a few throttling 500
        # messages.
        if self.active_base_url is not None:
          # Propagate 406 immediately without retrying, as 406 is a valid
          # response that inidicate a need for enrollment.
          if getattr(e, "code", None) == 406:
            raise

          if self.consecutive_connection_errors >= self.retry_error_limit:
            # We tried several times but this really did not work, just fail it.
            logging.info(
                "Too many connection errors to %s, retrying another URL",
                self.active_base_url)
            self.active_base_url = None
            raise e

          # Back off hard to allow the front end to recover.
          logging.debug(
              "Unable to connect to frontend. Backing off %s seconds.",
              self.error_poll_min)
          self.Wait(self.error_poll_min)

        # We never previously connected, maybe the URL/proxy is wrong? Just fail
        # right away to allow callers to try a different URL.
        else:
          raise e

  def Wait(self, timeout):
    """Wait for the specified timeout."""
    time.sleep(timeout - int(timeout))

    # Split a long sleep interval into 1 second intervals so we can heartbeat.
    for _ in xrange(int(timeout)):
      time.sleep(1)

      if self.heart_beat_cb:
        self.heart_beat_cb()


class Timer(object):
  """Implements the polling policy.

  External code simply calls our Wait() method without regard to the exact
  timing policy.
  """

  def __init__(self, heart_beat_cb=None):
    self.heart_beat_cb = heart_beat_cb
    self.poll_min = config_lib.CONFIG["Client.poll_min"]
    self.sleep_time = self.poll_max = config_lib.CONFIG["Client.poll_max"]
    self.poll_slew = config_lib.CONFIG["Client.poll_slew"]

  def FastPoll(self):
    """Switch to fast poll mode."""
    self.sleep_time = self.poll_min

  def SlowPoll(self):
    """Switch to slow poll mode."""
    self.sleep_time = self.poll_max

  def Wait(self):
    """Wait until the next action is needed."""
    time.sleep(self.sleep_time - int(self.sleep_time))

    # Split a long sleep interval into 1 second intervals so we can heartbeat.
    for _ in xrange(int(self.sleep_time)):
      time.sleep(1)

      if self.heart_beat_cb:
        self.heart_beat_cb()

    # Back off slowly at first and fast if no answer.
    self.sleep_time = min(self.poll_max,
                          max(self.poll_min, self.sleep_time) * self.poll_slew)


class CommsInit(registry.InitHook):

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

    # The worker may communicate over HTTP independently from the comms
    # thread. This way we do not need to synchronize the HTTP manager between
    # the two threads.
    self.http_manager = HTTPManager(
        heart_beat_cb=self.nanny_controller.Heartbeat)

  def Sleep(self, timeout):
    """Sleeps the calling thread with heartbeat."""
    self.nanny_controller.Heartbeat()
    time.sleep(timeout - int(timeout))

    # Split a long sleep interval into 1 second intervals so we can heartbeat.
    for _ in xrange(int(timeout)):
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
    queue = rdf_flows.MessageList()

    length = 0
    self._out_queue.sort(key=lambda msg: msg[0])

    # Front pops are quadratic so we reverse the queue.
    self._out_queue.reverse()

    while self._out_queue and length < max_size:
      message = self._out_queue.pop()[1]
      queue.job.Append(message)
      stats.STATS.IncrementCounter("grr_client_sent_messages")

      # We deliberately look at the serialized length as bytes here.
      message_length = len(message.Get("args"))

      # Maintain the output queue tally
      length += message_length
      self._out_queue_size -= message_length

    # Restore the old order.
    self._out_queue.reverse()

    return queue

  def SendReply(self,
                rdf_value=None,
                request_id=None,
                response_id=None,
                priority=None,
                session_id="W:0",
                message_type=None,
                name=None,
                require_fastpoll=None,
                ttl=None,
                blocking=True,
                task_id=None):
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

    message = rdf_flows.GrrMessage(session_id=session_id,
                                   task_id=task_id,
                                   name=name,
                                   response_id=response_id,
                                   request_id=request_id,
                                   priority=priority,
                                   require_fastpoll=require_fastpoll,
                                   ttl=ttl,
                                   type=message_type)

    if rdf_value:
      message.payload = rdf_value

    serialized_message = message.SerializeToString()

    self.ChargeBytesToSession(session_id, len(serialized_message))

    if message.type == rdf_flows.GrrMessage.Type.STATUS:
      rdf_value.network_bytes_sent = self.sent_bytes_per_flow[session_id]
      del self.sent_bytes_per_flow[session_id]
      message.payload = rdf_value

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

  def QueueResponse(self,
                    message,
                    priority=rdf_flows.GrrMessage.Priority.MEDIUM_PRIORITY,
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
    self._out_queue_size += len(message.Get("args"))

  def HandleMessage(self, message):
    """Entry point for processing jobs.

    Args:
        message: The GrrMessage that was delivered from the server.
    """
    self._is_active = True
    try:
      # Try to retrieve a suspended action from the client worker.
      try:
        suspended_action_id = message.payload.iterator.suspended_action
        action = self.suspended_actions[suspended_action_id]

      except (AttributeError, KeyError):
        # Otherwise make a new action instance.
        action_cls = actions.ActionPlugin.classes.get(message.name)
        if action_cls is None:
          raise RuntimeError("Client action %r not known" % message.name)

        action = action_cls(grr_worker=self)

      # Write the message to the transaction log.
      self.nanny_controller.WriteTransactionLog(message)

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
            rdf_flows.GrrStatus(
                status=rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR,
                error_message=utils.SmartUnicode(e)),
            request_id=message.request_id,
            response_id=message.response_id,
            session_id=message.session_id,
            task_id=message.task_id,
            message_type=rdf_flows.GrrMessage.Type.STATUS)
        if flags.FLAGS.debug:
          pdb.post_mortem()

  def MemoryExceeded(self):
    """Returns True if our memory footprint is too large."""
    rss_size = self.proc.memory_info().rss
    return rss_size / 1024 / 1024 > config_lib.CONFIG["Client.rss_max"]

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

    time_since_last_check = (
        rdfvalue.RDFDatetime().Now() - self.last_stats_sent_time)

    # No matter what, we don't want to send stats more often than
    # once per STATS_MIN_SEND_INTERVAL.
    if time_since_last_check < self.STATS_MIN_SEND_INTERVAL:
      return

    if (time_since_last_check > self.STATS_MAX_SEND_INTERVAL or
        self._is_active or self._send_stats_on_check):

      self._send_stats_on_check = False

      logging.info("Sending back client statistics to the server.")

      action_cls = actions.ActionPlugin.classes.get("GetClientStatsAuto",
                                                    actions.ActionPlugin)
      action = action_cls(grr_worker=self)
      action.Run(rdf_client.GetClientStatsRequest(
          start_time=self.last_stats_sent_time))

      self.last_stats_sent_time = rdfvalue.RDFDatetime().Now()
      stats.STATS.SetGaugeValue("grr_client_last_stats_sent_time",
                                self.last_stats_sent_time.AsSecondsFromEpoch())

  def SendNannyMessage(self):
    msg = self.nanny_controller.GetNannyMessage()
    if msg:
      self.SendReply(
          rdf_protodict.DataBlob(string=msg),
          session_id=rdfvalue.FlowSessionID(flow_name="NannyMessage"),
          priority=rdf_flows.GrrMessage.Priority.LOW_PRIORITY,
          require_fastpoll=False)
      self.nanny_controller.ClearNannyMessage()

  def SendClientAlert(self, msg):
    self.SendReply(
        rdf_protodict.DataBlob(string=msg),
        session_id=rdfvalue.FlowSessionID(flow_name="ClientAlert"),
        priority=rdf_flows.GrrMessage.Priority.LOW_PRIORITY,
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

  def Put(self,
          item,
          priority=rdf_flows.GrrMessage.Priority.MEDIUM_PRIORITY,
          block=True,
          timeout=1000):
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

    if priority >= rdf_flows.GrrMessage.Priority.HIGH_PRIORITY:
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
        callback=self.nanny_controller.Heartbeat,
        maxsize=1024)

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
    for _ in xrange(int(timeout)):
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
    queue = rdf_flows.MessageList()
    length = 0

    for message in self._out_queue.Get():
      queue.job.Append(rdf_flows.GrrMessage(message))
      stats.STATS.IncrementCounter("grr_client_sent_messages")
      length += len(message)

      if length > max_size:
        break

    return queue

  def QueueResponse(self,
                    message,
                    priority=rdf_flows.GrrMessage.Priority.MEDIUM_PRIORITY,
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
      status = rdf_flows.GrrStatus(
          status=rdf_flows.GrrStatus.ReturnedStatus.CLIENT_KILLED,
          error_message="Client killed during transaction")
      nanny_status = self.nanny_controller.GetNannyStatus()
      if nanny_status:
        status.nanny_status = nanny_status

      self.SendReply(status,
                     request_id=last_request.request_id,
                     response_id=1,
                     session_id=last_request.session_id,
                     message_type=rdf_flows.GrrMessage.Type.STATUS)

    self.nanny_controller.CleanTransactionLog()

    # Inform the server that we started.
    action_cls = actions.ActionPlugin.classes.get("SendStartupInfo",
                                                  actions.ActionPlugin)
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
            rdf_flows.GrrStatus(
                status=rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR,
                error_message=utils.SmartUnicode(e)),
            request_id=message.request_id,
            response_id=1,
            session_id=message.session_id,
            task_id=message.task_id,
            message_type=rdf_flows.GrrMessage.Type.STATUS)
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

  The client then creates a HTTPManager() instance to control communication with
  the front end over HTTP, and a Timer() instance to control polling policy.

  The HTTP client simply reads pending messages from the client worker queues
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

  http_manager_class = HTTPManager

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

    # The server's PEM encoded certificate.
    self.server_certificate = None

    # This manages our HTTP connections. Note: The comms thread is allowed to
    # block indefinitely since the worker thread is responsible for
    # heart-beating the nanny. We assume that HTTP requests can not block
    # indefinitely.
    self.http_manager = self.http_manager_class()

    # The communicator manages our crypto with the server.
    self.communicator = ClientCommunicator(private_key=private_key)

    # This controls our polling frequency.
    self.timer = Timer()

    # The time we last sent an enrollment request. Enrollment requests are
    # throttled especially to a maximum of one every 10 minutes.
    self.last_enrollment_time = 0

    # The time we last checked with the foreman.
    self.last_foreman_check = 0

    # The client worker does all the real work here.
    if worker:
      self.client_worker = worker()
    else:
      self.client_worker = GRRThreadedWorker()

  def VerifyServerPEM(self, http_object):
    """Check the server PEM for validity.

    This is used to determine connectivity to the server. Sometimes captive
    portals return a valid HTTP status, but the data is corrupted.

    Args:
      http_object: The response received from the server.

    Returns:
      True if the response contains a valid server certificate.
    """
    try:
      server_pem = http_object.data
      server_url = http_object.url

      if "BEGIN CERTIFICATE" in server_pem:
        # Now we know that this proxy is working. We still have to verify the
        # certificate. This will raise if the server cert is invalid.
        self.communicator.LoadServerCertificate(server_certificate=server_pem,
                                                ca_certificate=self.ca_cert)

        logging.info("Server PEM re-keyed.")
        return True
    except Exception as e:  # pylint: disable=broad-except
      logging.info("Unable to verify server certificate at %s: %s", server_url,
                   e)

      return False

  def VerifyServerControlResponse(self, http_object):
    """Verify the server response to a 'control' endpoint POST message.

    We consider the message correct if and only if we can decrypt it
    properly. Note that in practice we can not use the HTTP status to figure out
    if the request worked because captive proxies have a habit of lying and
    returning a HTTP success code even when there is no connectivity.

    Args:
      http_object: The HTTPObject returned from the HTTP transaction.

    Returns:
      True if the http_object is correct. False if it is not valid.

    Side Effect:
      Fill in the decoded_data attribute in the http_object.
    """
    if http_object.code != 200:
      return False

    # Try to decrypt the message into the http_object.
    try:
      http_object.messages, http_object.source, http_object.nonce = (
          self.communicator.DecryptMessage(http_object.data))

      return True

    # Something went wrong - the response seems invalid!
    except communicator.DecodingError as e:
      logging.info("Protobuf decode error: %s.", e)
      return False

  def MakeRequest(self, data):
    """Make a HTTP Post request to the server 'control' endpoint."""
    stats.STATS.IncrementCounter("grr_client_sent_bytes", len(data))

    # Verify the response is as it should be from the control endpoint.
    response = self.http_manager.OpenServerEndpoint(
        path="control?api=%s" % config_lib.CONFIG["Network.api"],
        verify_cb=self.VerifyServerControlResponse,
        data=data,
        request_opts={"Content-Type": "binary/octet-stream"})

    if response.code == 406:
      self.InitiateEnrolment()
      return response

    if response.code == 200:
      stats.STATS.IncrementCounter("grr_client_received_bytes",
                                   len(response.data))
      return response

    # An unspecified error occured.
    return response

  def RunOnce(self):
    """Makes a single request to the GRR server.

    Returns:
      A Status() object indicating how the last POST went.
    """
    # Attempt to fetch and load server certificate.
    if not self._FetchServerCertificate():
      self.timer.Wait()
      return HTTPObject(code=500)

    # Here we only drain messages if we were able to connect to the server in
    # the last poll request. Otherwise we just wait until the connection comes
    # back so we don't expire our messages too fast.
    if self.http_manager.consecutive_connection_errors == 0:
      # Grab some messages to send
      message_list = self.client_worker.Drain(
          max_size=config_lib.CONFIG["Client.max_post_size"])
    else:
      message_list = rdf_flows.MessageList()

    # If any outbound messages require fast poll we switch to fast poll mode.
    for message in message_list.job:
      if message.require_fastpoll:
        self.timer.FastPoll()
        break

    # Make new encrypted ClientCommunication rdfvalue.
    payload = rdf_flows.ClientCommunication()

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
    payload_data = payload.SerializeToString()
    response = self.MakeRequest(payload_data)

    # Unable to decode response or response not valid.
    if response.code != 200 or response.messages is None:
      # We don't print response here since it should be encrypted and will
      # cause ascii conversion errors.
      logging.info("%s: Could not connect to server at %s, status %s",
                   self.communicator.common_name,
                   self.http_manager.active_base_url, response.code)

      # Force the server pem to be reparsed on the next connection.
      self.server_certificate = None

      # Reschedule the tasks back on the queue so they get retried next time.
      messages = list(message_list.job)
      for message in messages:
        message.priority = rdf_flows.GrrMessage.Priority.HIGH_PRIORITY
        message.require_fastpoll = False
        message.ttl -= 1
        if message.ttl > 0:
          # Schedule with high priority to make it jump the queue.
          self.client_worker.QueueResponse(
              message, rdf_flows.GrrMessage.Priority.HIGH_PRIORITY + 1)
        else:
          logging.info("Dropped message due to retransmissions.")

      return response

    # Check the decoded nonce was as expected.
    if response.nonce != nonce:
      logging.info("Nonce not matched.")
      response.code = 500
      return response

    if response.source != self.communicator.server_name:
      logging.info("Received a message not from the server "
                   "%s, expected %s.", response.source,
                   self.communicator.server_name)
      response.code = 500
      return response

    # Check to see if any inbound messages want us to fastpoll. This means we
    # drop to fastpoll immediately on a new request rather than waiting for the
    # next beacon to report results.
    for message in response.messages:
      if message.require_fastpoll:
        self.timer.FastPoll()
        break

    # Process all messages. Messages can be processed by clients in
    # any order since clients do not have state.
    self.client_worker.QueueMessages(response.messages)

    cn = self.communicator.common_name
    logging.info("%s: Sending %s(%s), Received %s messages in %s sec. "
                 "Sleeping for %s", cn, len(message_list), len(payload_data),
                 len(response.messages), response.duration,
                 self.timer.sleep_time)

    return response

  def SendForemanRequest(self):
    self.client_worker.SendReply(
        rdf_protodict.DataBlob(),
        session_id=rdfvalue.FlowSessionID(flow_name="Foreman"),
        priority=rdf_flows.GrrMessage.Priority.LOW_PRIORITY,
        require_fastpoll=False)

  def _FetchServerCertificate(self):
    """Attempts to fetch the server cert.

    Returns:
      True if we succeed.
    """
    # Certificate is loaded and still valid.
    if self.server_certificate:
      return True

    response = self.http_manager.OpenServerEndpoint(
        "server.pem", verify_cb=self.VerifyServerPEM)

    if response.Success():
      self.server_certificate = response.data
      return True

    # We failed to fetch the cert, switch to slow poll mode.
    self.timer.SlowPoll()
    return False

  def Run(self):
    """The main run method of the client.

    This method does not normally return. Only if there have been more than
    Client.connection_error_limit failures, the method returns and allows the
    client to exit.
    """
    while True:
      if self.http_manager.consecutive_connection_errors > config_lib.CONFIG[
          "Client.connection_error_limit"]:
        return

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
              rdf_protodict.DataBlob(),
              session_id=rdfvalue.FlowSessionID(flow_name="Foreman"),
              priority=rdf_flows.GrrMessage.Priority.LOW_PRIORITY,
              require_fastpoll=False,
              blocking=False)
          self.last_foreman_check = now
        except Queue.Full:
          pass

      try:
        self.RunOnce()
      except Exception:  # pylint: disable=broad-except
        # Catch everything, yes, this is terrible but necessary
        logging.warn("Uncaught exception caught: %s", traceback.format_exc())
        if flags.FLAGS.debug:
          pdb.post_mortem()

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

      self.timer.Wait()

  def InitiateEnrolment(self):
    """Initiate the enrollment process.

    We do not sent more than one enrollment request every 10 minutes. Note that
    we still communicate to the server in fast poll mode, but these requests are
    not carrying any payload.
    """
    logging.debug("sending enrollment request")
    now = time.time()
    if now > self.last_enrollment_time + 10 * 60:
      if not self.last_enrollment_time:
        # This is the first enrollment request - we should enter fastpoll mode.
        self.timer.FastPoll()

      self.last_enrollment_time = now
      # Send registration request:
      self.client_worker.SendReply(
          rdf_crypto.Certificate(type=rdf_crypto.Certificate.Type.CSR,
                                 pem=self.communicator.GetCSR()),
          session_id=rdfvalue.SessionID(queue=queues.ENROLLMENT,
                                        flow_name="Enrol"))


class ClientCommunicator(communicator.Communicator):
  """A communicator implementation for clients.

    This extends the generic communicator to include verification of
    server side certificates.
  """

  def _ParseRSAKey(self, rsa):
    """Use the RSA private key to initialize our parameters.

    We set our client name as the hash of the RSA private key.

    Args:
      rsa: An RSA key pair.
    """
    # Our CN will be the first 64 bits of the hash of the public key.
    public_key = rsa.pub()[1]
    self.common_name = rdf_client.ClientURN("C.%s" % (
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
    rsa = RSA.gen_key(config_lib.CONFIG["Client.rsa_key_length"], 65537,
                      lambda: None)

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

    self.private_key = rdf_crypto.PEMPrivateKey(bio.read_all())

    config_lib.CONFIG.Set("Client.private_key", self.private_key)
    config_lib.CONFIG.Write()

  def LoadServerCertificate(self, server_certificate=None, ca_certificate=None):
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
    self.pub_key_cache.Put(self.server_name,
                           self.pub_key_cache.PubKeyFromCert(server_cert))

  def EncodeMessages(self, message_list, result, **kwargs):
    # Force the right API to be used
    kwargs["api_version"] = config_lib.CONFIG["Network.api"]
    return super(ClientCommunicator, self).EncodeMessages(message_list, result,
                                                          **kwargs)
