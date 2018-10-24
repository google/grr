#!/usr/bin/env python
"""This class handles the GRR Client Communication.

The GRR client uses HTTP to communicate with the server.

The client connections are controlled via a number of config parameters:

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
   retry for retry_error_limit times before exiting the
   CONNECTED state and returning to the INITIAL state (i.e. the client will
   start searching for a new URL/Proxy combination). If a retry is successful,
   the client will return to its designated polling frequency.

7) If there are connection_error_limit failures, the client will
   exit. Hopefully the nanny will restart the client.

Examples:

1) Client starts up on a disconnected network: Client will try every URL/Proxy
   combination once every Client.poll_max (default 10 minutes).

2) Client connects successful but loses network connectivity. Client will re-try
   retry_error_limit (10 times) every Client.error_poll_min (1 Min) to
   resent the last message. If it does not succeed it starts searching for a new
   URL/Proxy combination as in example 1.

"""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import logging
import os
import pdb
import posixpath
import signal
import sys
import threading
import time
import traceback


from builtins import range  # pylint: disable=redefined-builtin
import psutil
import queue
import requests

from google.protobuf import json_format

from grr_response_client import actions
from grr_response_client import client_stats
from grr_response_client import client_utils
from grr_response_client.client_actions import admin
from grr_response_core import config
from grr_response_core.lib import communicator
from grr_response_core.lib import flags
from grr_response_core.lib import queues
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import rekall_types as rdf_rekall_types
from grr_response_core.stats import stats_collector_instance


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

  # If the client encounters this many connection errors, it searches
  # for a new proxy/server url combination.
  retry_error_limit = 10

  # If the client encounters this many connection errors, it exits and
  # restarts. Retries are one minute apart.
  connection_error_limit = 60 * 24

  def __init__(self, heart_beat_cb=None):
    self.heart_beat_cb = heart_beat_cb
    self.proxies = self._GetProxies()
    self.base_urls = self._GetBaseURLs()

    # We start checking with this proxy.
    self.last_proxy_index = 0
    self.last_base_url_index = 0

    # If we have connected previously but now suddenly fail to connect, we try
    # the connection a few times (retry_error_limit) before we determine
    # that it is failed.
    self.consecutive_connection_errors = 0

    self.active_base_url = None
    self.error_poll_min = config.CONFIG["Client.error_poll_min"]

  def _GetBaseURLs(self):
    """Gathers a list of base URLs we will try."""
    result = config.CONFIG["Client.server_urls"]
    if not result:
      # Backwards compatibility - deduce server_urls from Client.control_urls.
      for control_url in config.CONFIG["Client.control_urls"]:
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
    result.extend(config.CONFIG["Client.proxy_servers"])

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
                         params=None,
                         headers=None,
                         method="GET",
                         timeout=None):
    """Search through all the base URLs to connect to one that works.

    This is a thin wrapper around requests.request() so most parameters are
    documented there.

    Args:
      path: The URL path to access in this endpoint.
      verify_cb: A callback which should return True if the response is
        reasonable. This is used to detect if we are able to talk to the correct
        endpoint. If not we try a different endpoint/proxy combination.
      data: Parameters to send in POST bodies (See Requests documentation).
      params: Parameters to send in GET URLs (See Requests documentation).
      headers: Additional headers (See Requests documentation)
      method: The HTTP method to use. If not set we select one automatically.
      timeout: See Requests documentation.

    Returns:
      an HTTPObject() instance with the correct error code set.
    """
    tries = 0
    last_error = HTTPObject(code=404)

    while tries < len(self.base_urls):
      base_url_index = self.last_base_url_index % len(self.base_urls)
      active_base_url = self.base_urls[base_url_index]

      result = self.OpenURL(
          self._ConcatenateURL(active_base_url, path),
          data=data,
          params=params,
          headers=headers,
          method=method,
          timeout=timeout,
          verify_cb=verify_cb,
      )

      if not result.Success():
        tries += 1
        self.last_base_url_index += 1
        last_error = result
        continue

      # The URL worked - we record that.
      self.active_base_url = active_base_url

      return result

    # No connection is possible at all.
    logging.info(
        "Could not connect to GRR servers %s, directly or through "
        "these proxies: %s.", self.base_urls, self.proxies)

    return last_error

  def OpenURL(self,
              url,
              verify_cb=lambda x: True,
              data=None,
              params=None,
              headers=None,
              method="GET",
              timeout=None):
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
      data: Parameters to send in POST bodies (See Requests documentation).
      params: Parameters to send in GET URLs (See Requests documentation).
      headers: Additional headers (See Requests documentation)
      method: The HTTP method to use. If not set we select one automatically.
      timeout: See Requests documentation.

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

        headers = (headers or {}).copy()
        headers["Cache-Control"] = "no-cache"

        if data:
          method = "POST"

        duration, handle = self._RetryRequest(
            url=url,
            data=data,
            params=params,
            headers=headers,
            method=method,
            timeout=timeout,
            proxies=proxydict,
        )

        data = handle.content

        result = HTTPObject(
            url=url, data=data, proxy=proxy, code=200, duration=duration)

        if not verify_cb(result):
          raise IOError("Data not verified.")

        # The last connection worked.
        self.consecutive_connection_errors = 0
        return result

      except requests.RequestException as e:
        # Especially trap a 406 error message - it means the client needs to
        # enroll.
        if e.response is not None:
          last_error = e.response.status_code
          if last_error == 406:
            # A 406 is not considered an error as the frontend is reachable. If
            # we considered it as an error the client would be unable to send
            # the enrollment request since connection errors disable message
            # draining.
            self.consecutive_connection_errors = 0
            return HTTPObject(code=406)

        # Try the next proxy
        self.last_proxy_index = proxy_index + 1
        tries += 1

      # Catch any exceptions that dont have a code (e.g. socket.error).
      except IOError:
        # Try the next proxy
        self.last_proxy_index = proxy_index + 1
        tries += 1
        last_error = 500
      # Catch unexpected exceptions. If the error is proxy related it makes
      # sense to cycle the proxy before reraising. One error we have seen here
      # is ProxySchemeUnknown but urllib can raise many different exceptions, it
      # doesn't make sense to enumerate them all.
      except Exception:  # pylint: disable=broad-except
        logging.exception(
            "Got an unexpected exception while connecting to the server.")
        # Try the next proxy
        self.last_proxy_index = proxy_index + 1
        tries += 1
        last_error = 500

    # We failed to connect at all here.
    return HTTPObject(code=last_error)

  def _RetryRequest(self, timeout=None, **request_args):
    """Retry the request a few times before we determine it failed.

    Sometimes the frontend becomes loaded and issues a 500 error to throttle the
    clients. We wait Client.error_poll_min seconds between each attempt to back
    off the frontend. Note that this does not affect any timing algorithm in the
    client itself which is controlled by the Timer() class.

    Args:
      timeout: Timeout for retry.
      **request_args: Args to the requests.request call.

    Returns:
      a tuple of duration, urllib.request.urlopen response.
    """
    while True:
      try:
        now = time.time()
        if not timeout:
          timeout = config.CONFIG["Client.http_timeout"]

        result = requests.request(**request_args)
        # By default requests doesn't raise on HTTP error codes.
        result.raise_for_status()

        # Requests does not always raise an exception when an incorrect response
        # is received. This fixes that behaviour.
        if not result.ok:
          raise requests.RequestException(response=result)

        return time.time() - now, result

      # Catch any exceptions that dont have a code (e.g. socket.error).
      except IOError as e:
        self.consecutive_connection_errors += 1
        # Request failed. If we connected successfully before we attempt a few
        # connections before we determine that it really failed. This might
        # happen if the front end is loaded and returns a few throttling 500
        # messages.
        if self.active_base_url is not None:
          # Propagate 406 immediately without retrying, as 406 is a valid
          # response that indicates a need for enrollment.
          response = getattr(e, "response", None)
          if getattr(response, "status_code", None) == 406:
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
    for _ in range(int(timeout)):
      time.sleep(1)

      if self.heart_beat_cb:
        self.heart_beat_cb()

  def ErrorLimitReached(self):
    return self.consecutive_connection_errors > self.connection_error_limit


class Timer(object):
  """Implements the polling policy.

  External code simply calls our Wait() method without regard to the exact
  timing policy.
  """

  # Slew of poll time.
  poll_slew = 1.15

  def __init__(self):
    self.poll_min = config.CONFIG["Client.poll_min"]
    self.sleep_time = self.poll_max = config.CONFIG["Client.poll_max"]

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
    for _ in range(int(self.sleep_time)):
      time.sleep(1)

    # Back off slowly at first and fast if no answer.
    self.sleep_time = min(self.poll_max,
                          max(self.poll_min, self.sleep_time) * self.poll_slew)


class GRRClientWorker(threading.Thread):
  """This client worker runs the main loop in another thread.

  The client which uses this worker is not blocked while queuing messages to be
  worked on. There is only a single working thread though.

  The overall effect is that the HTTP client is not blocked waiting for actions
  to be executed, and at the same time, the client working thread is not blocked
  waiting on network latency.
  """

  stats_collector = None

  sent_bytes_per_flow = {}

  # Client sends stats notifications at least every 50 minutes.
  STATS_MAX_SEND_INTERVAL = rdfvalue.Duration("50m")

  # Client sends stats notifications at most every 60 seconds.
  STATS_MIN_SEND_INTERVAL = rdfvalue.Duration("60s")

  def __init__(self,
               client=None,
               out_queue=None,
               internal_nanny_monitoring=True,
               heart_beat_cb=None):
    threading.Thread.__init__(self)

    # A reference to the parent client that owns us.
    self.client = client

    self._is_active = False

    self.proc = psutil.Process()

    self.nanny_controller = None

    self.transaction_log = client_utils.TransactionLog()

    if internal_nanny_monitoring:

      self.StartNanny()

      if heart_beat_cb is None:
        heart_beat_cb = self.nanny_controller.Heartbeat

    self.heart_beat_cb = heart_beat_cb

    self.lock = threading.RLock()

    # The worker may communicate over HTTP independently from the comms
    # thread. This way we do not need to synchronize the HTTP manager between
    # the two threads.
    self.http_manager = HTTPManager(heart_beat_cb=heart_beat_cb)

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
          heart_beat_cb=heart_beat_cb)

    # Only start this thread after the _out_queue is ready to send.
    self.StartStatsCollector()

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

  def StartNanny(self):
    # Use this to control the nanny transaction log.
    self.nanny_controller = client_utils.NannyController()
    self.nanny_controller.StartNanny()

  def StartStatsCollector(self):
    if not GRRClientWorker.stats_collector:
      GRRClientWorker.stats_collector = client_stats.ClientStatsCollector(self)
      GRRClientWorker.stats_collector.start()

  def SendReply(self,
                rdf_value=None,
                request_id=None,
                response_id=None,
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

    message = rdf_flows.GrrMessage(
        session_id=session_id,
        task_id=task_id,
        name=name,
        response_id=response_id,
        request_id=request_id,
        require_fastpoll=require_fastpoll,
        ttl=ttl,
        type=message_type)

    if rdf_value is not None:
      message.payload = rdf_value

    serialized_message = message.SerializeToString()

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

  def GetRekallProfile(self, profile_name, version="v1.0"):
    response = self.http_manager.OpenServerEndpoint(
        u"/rekall_profiles/%s/%s" % (version, profile_name))

    if response.code != 200:
      return None

    pb = rdf_rekall_types.RekallProfile.protobuf()
    json_format.Parse(response.data.lstrip(")]}'\n"), pb)
    return rdf_rekall_types.RekallProfile.FromSerializedString(
        pb.SerializeToString())

  @utils.Synchronized
  def ChargeBytesToSession(self, session_id, length, limit=0):
    self.sent_bytes_per_flow.setdefault(session_id, 0)
    self.sent_bytes_per_flow[session_id] += length

    # Check after incrementing so that sent_bytes_per_flow goes over the limit
    # even though we don't send those bytes.  This makes sure flow_runner will
    # die on the flow.
    if limit and self.sent_bytes_per_flow[session_id] > limit:
      self.SendClientAlert("Network limit exceeded.")
      raise actions.NetworkBytesExceededError(
          "Action exceeded network send limit.")

  def HandleMessage(self, message):
    """Entry point for processing jobs.

    Args:
        message: The GrrMessage that was delivered from the server.

    Raises:
        RuntimeError: The client action requested was not found.
    """
    self._is_active = True
    try:
      action_cls = actions.ActionPlugin.classes.get(message.name)
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
      # We want to send ClientStats when client action is complete.
      self.stats_collector.RequestSend()

  def MemoryExceeded(self):
    """Returns True if our memory footprint is too large."""
    rss_size = self.proc.memory_info().rss
    return rss_size // 1024 // 1024 > config.CONFIG["Client.rss_max"]

  def IsActive(self):
    """Returns True if worker is currently handling a message."""
    return self._is_active

  def SendNannyMessage(self):
    # We might be monitored by Fleetspeak.
    if not self.nanny_controller:
      return

    msg = self.nanny_controller.GetNannyMessage()
    if msg:
      self.SendReply(
          rdf_protodict.DataBlob(string=msg),
          session_id=rdfvalue.FlowSessionID(flow_name="NannyMessage"),
          require_fastpoll=False)
      self.nanny_controller.ClearNannyMessage()

  def SendClientAlert(self, msg):
    self.SendReply(
        rdf_protodict.DataBlob(string=msg),
        session_id=rdfvalue.FlowSessionID(flow_name="ClientAlert"),
        require_fastpoll=False)

  def Sleep(self, timeout):
    """Sleeps the calling thread with heartbeat."""
    if self.nanny_controller:
      self.nanny_controller.Heartbeat()

    # Split a long sleep interval into 1 second intervals so we can heartbeat.
    while timeout > 0:
      time.sleep(min(1., timeout))
      timeout -= 1
      # If the output queue is full, we are ready to do a post - no
      # point in waiting.
      if self._out_queue.Full():
        return

      if self.nanny_controller:
        self.nanny_controller.Heartbeat()

  def OnStartup(self):
    """A handler that is called on client startup."""
    # We read the transaction log and fail any requests that are in it. If there
    # is anything in the transaction log we assume its there because we crashed
    # last time and let the server know.

    last_request = self.transaction_log.Get()
    if last_request:
      status = rdf_flows.GrrStatus(
          status=rdf_flows.GrrStatus.ReturnedStatus.CLIENT_KILLED,
          error_message="Client killed during transaction")
      if self.nanny_controller:
        nanny_status = self.nanny_controller.GetNannyStatus()
        if nanny_status:
          status.nanny_status = nanny_status

      self.SendReply(
          status,
          request_id=last_request.request_id,
          response_id=1,
          session_id=last_request.session_id,
          message_type=rdf_flows.GrrMessage.Type.STATUS)

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
    message = message.SerializeToString()

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
        ret.job.append(rdf_flows.GrrMessage.FromSerializedString(message))
        ret_size += len(message)
        if soft_size_limit is not None and ret_size > soft_size_limit:
          break

      return ret

  def Size(self):
    return self._total_size

  def Full(self):
    return self._total_size >= self._maxsize


class GRRHTTPClient(object):
  """A class which abstracts away HTTP communications.

  To create a new GRR HTTP client, instantiate this class and generate
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
      send that. Enrollment requests are throttled to a
      maximum of one every 10 minutes.

    - A status code of 500 is an error, the messages are re-queued and the
      client waits and retries to send them later.
  """

  http_manager_class = HTTPManager

  def __init__(self, ca_cert=None, worker_cls=None, private_key=None):
    """Constructor.

    Args:
      ca_cert: String representation of a CA certificate to use for checking
        server certificate.
      worker_cls: The client worker class to use. Defaults to GRRClientWorker.
      private_key: The private key for this client. Defaults to config
        Client.private_key.
    """
    self.ca_cert = ca_cert
    if private_key is None:
      private_key = config.CONFIG.Get("Client.private_key", default=None)

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
    if worker_cls:
      self.client_worker = worker_cls(client=self)
    else:
      self.client_worker = GRRClientWorker(client=self)
    # TODO(hanuszczak): Maybe we should start the thread in `GRRHTTPClient::Run`
    # method instead? Starting threads in constructor is rarely a good idea, is
    # it guaranteed that we call `GRRHTTPClient::Run` only once?
    self.client_worker.start()

  def FleetspeakEnabled(self):
    return False

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
        server_certificate = rdf_crypto.RDFX509Cert(server_pem)
        self.communicator.LoadServerCertificate(
            server_certificate=server_certificate, ca_certificate=self.ca_cert)

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
    stats_collector_instance.Get().IncrementCounter("grr_client_sent_bytes",
                                                    len(data))

    # Verify the response is as it should be from the control endpoint.
    response = self.http_manager.OpenServerEndpoint(
        path="control?api=%s" % config.CONFIG["Network.api"],
        verify_cb=self.VerifyServerControlResponse,
        data=data,
        headers={"Content-Type": "binary/octet-stream"})

    if response.code == 406:
      self.InitiateEnrolment()
      return response

    if response.code == 200:
      stats_collector_instance.Get().IncrementCounter(
          "grr_client_received_bytes", len(response.data))
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
          max_size=config.CONFIG["Client.max_post_size"])
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
        message.require_fastpoll = False
        message.ttl -= 1
        if message.ttl > 0:
          self.client_worker.QueueResponse(message)
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
    logging.info(
        "%s: Sending %s(%s), Received %s messages in %s sec. "
        "Sleeping for %s sec.", cn, len(message_list), len(payload_data),
        len(response.messages), response.duration, self.timer.sleep_time)

    return response

  def SendForemanRequest(self):
    self.client_worker.SendReply(
        rdf_protodict.DataBlob(),
        session_id=rdfvalue.FlowSessionID(flow_name="Foreman"),
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
    connection_error_limit failures, the method returns and allows the
    client to exit.
    """
    while True:
      if self.http_manager.ErrorLimitReached():
        return

      # Check if there is a message from the nanny to be sent.
      self.client_worker.SendNannyMessage()

      now = time.time()
      # Check with the foreman if we need to
      if (now > self.last_foreman_check +
          config.CONFIG["Client.foreman_check_frequency"]):
        # We must not queue messages from the comms thread with blocking=True
        # or we might deadlock. If the output queue is full, we can't accept
        # more work from the foreman anyways so it's ok to drop the message.
        try:
          self.client_worker.SendReply(
              rdf_protodict.DataBlob(),
              session_id=rdfvalue.FlowSessionID(flow_name="Foreman"),
              require_fastpoll=False,
              blocking=False)
          self.last_foreman_check = now
        except queue.Full:
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
          rdf_crypto.Certificate(
              type=rdf_crypto.Certificate.Type.CSR,
              pem=self.communicator.GetCSRAsPem()),
          session_id=rdfvalue.SessionID(
              queue=queues.ENROLLMENT, flow_name="Enrol"))


class ClientCommunicator(communicator.Communicator):
  """A communicator implementation for clients.

    This extends the generic communicator to include verification of
    server side certificates.
  """

  def __init__(self, certificate=None, private_key=None):
    super(ClientCommunicator, self).__init__(
        certificate=certificate, private_key=private_key)
    self.InitPrivateKey()

  def InitPrivateKey(self):
    """Makes sure this client has a private key set.

    It first tries to load an RSA key from the certificate.

    If no certificate is found, or it is invalid, we make a new random RSA key,
    and store it as our certificate.

    Returns:
      An RSA key - either from the certificate or a new random key.
    """
    if self.private_key:
      try:
        self.common_name = rdf_client.ClientURN.FromPrivateKey(self.private_key)

        logging.info("Starting client %s", self.common_name)

        return self.private_key

      except type_info.TypeValueError:
        pass

    # We either have an invalid key or no key. We just generate a new one.
    key = rdf_crypto.RSAPrivateKey.GenerateKey(
        bits=config.CONFIG["Client.rsa_key_length"])

    self.common_name = rdf_client.ClientURN.FromPrivateKey(key)
    logging.info("Client pending enrolment %s", self.common_name)

    # Save the keys
    self.SavePrivateKey(key)

    return key

  def GetCSR(self):
    """Return our CSR."""
    return rdf_crypto.CertificateSigningRequest(
        common_name=self.common_name, private_key=self.private_key)

  def GetCSRAsPem(self):
    """Return our CSR in PEM format."""
    return self.GetCSR().AsPEM()

  def SavePrivateKey(self, private_key):
    """Store the new private key on disk."""
    self.private_key = private_key
    config.CONFIG.Set("Client.private_key",
                      self.private_key.SerializeToString())
    config.CONFIG.Write()

  def LoadServerCertificate(self, server_certificate=None, ca_certificate=None):
    """Loads and verifies the server certificate."""
    # Check that the server certificate verifies
    try:
      server_certificate.Verify(ca_certificate.GetPublicKey())
    except rdf_crypto.VerificationError as e:
      self.server_name = None
      raise IOError("Server cert is invalid: %s" % e)

    # Make sure that the serial number is higher.
    server_cert_serial = server_certificate.GetSerialNumber()

    if server_cert_serial < config.CONFIG["Client.server_serial_number"]:
      # We can not accept this serial number...
      raise IOError("Server certificate serial number is too old.")
    elif server_cert_serial > config.CONFIG["Client.server_serial_number"]:
      logging.info("Server serial number updated to %s", server_cert_serial)
      config.CONFIG.Set("Client.server_serial_number", server_cert_serial)

      # Save the new data to the config file.
      config.CONFIG.Write()

    self.server_name = server_certificate.GetCN()
    self.server_certificate = server_certificate
    self.ca_certificate = ca_certificate
    self.server_public_key = server_certificate.GetPublicKey()
    # If we still have a cached session key, we need to remove it.
    self._ClearServerCipherCache()

  def EncodeMessages(self, message_list, result, **kwargs):
    # Force the right API to be used
    kwargs["api_version"] = config.CONFIG["Network.api"]
    return super(ClientCommunicator, self).EncodeMessages(
        message_list, result, **kwargs)

  def _GetRemotePublicKey(self, common_name):

    if common_name == self.server_name:
      return self.server_public_key

    raise communicator.UnknownClientCert(
        "Client wants to talk to %s, not %s" % (common_name, self.server_name))
