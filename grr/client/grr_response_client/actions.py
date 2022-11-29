#!/usr/bin/env python
"""This file contains common grr jobs."""

import gc
import logging
import pdb
import traceback
from typing import NamedTuple

from absl import flags

import psutil

from grr_response_client import client_utils
from grr_response_client.unprivileged import communication
from grr_response_core import config
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.util import compatibility

# Our first response in the session is this:
INITIAL_RESPONSE_ID = 1


class Error(Exception):
  pass


class CPUExceededError(Error):
  pass


class NetworkBytesExceededError(Error):
  """Exceeded the maximum number of bytes allowed to be sent for this action."""


class RuntimeExceededError(Error):
  """Exceeded the maximum allowed runtime."""


class _CpuUsed(NamedTuple):
  cpu_time: float
  sys_time: float


class _CpuTimes:
  """Accounting of used CPU time."""

  def __init__(self):
    self.proc = psutil.Process()
    self.cpu_start = self.proc.cpu_times()
    self.unprivileged_cpu_start = communication.TotalServerCpuTime()
    self.unprivileged_sys_start = communication.TotalServerSysTime()

  @property
  def cpu_used(self) -> _CpuUsed:
    end = self.proc.cpu_times()
    unprivileged_cpu_end = communication.TotalServerCpuTime()
    unprivileged_sys_end = communication.TotalServerSysTime()
    return _CpuUsed((end.user - self.cpu_start.user + unprivileged_cpu_end -
                     self.unprivileged_cpu_start),
                    (end.system - self.cpu_start.system + unprivileged_sys_end -
                     self.unprivileged_sys_start))

  @property
  def total_cpu_used(self) -> float:
    return sum(self.cpu_used)


class ActionPlugin(object):
  """Baseclass for plugins.

  An action is a plugin abstraction which receives an rdfvalue and
  sends another rdfvalue in response.

  The code is specified in the Run() method, while the data is
  specified in the in_rdfvalue and out_rdfvalues classes.

  Windows and OS X client actions cannot be imported on the linux server since
  they require OS-specific libraries. If you are adding a client action that
  doesn't have a linux implementation, you will need to register it in
  libs/server_stubs.py

  Windows and OS X implementations of client actions with the same name (e.g.
  EnumerateInterfaces) as linux actions must accept and return the same rdfvalue
  types as their linux counterparts.
  """
  # The rdfvalue used to encode this message.
  in_rdfvalue = None

  # TODO(user): The RDFValue instance for the output protobufs. This is
  # required temporarily until the client sends RDFValue instances instead of
  # protobufs.
  out_rdfvalues = [None]

  # Authentication Required for this Action:
  _authentication_required = True

  __abstract = True  # pylint: disable=invalid-name

  require_fastpoll = True

  _PROGRESS_THROTTLE_INTERVAL = rdfvalue.Duration.From(2, rdfvalue.SECONDS)

  last_progress_time = rdfvalue.RDFDatetime.FromSecondsSinceEpoch(0)

  def __init__(self, grr_worker=None):
    """Initializes the action plugin.

    Args:
      grr_worker:  The grr client worker object which may be used to e.g. send
        new actions on.
    """
    self.grr_worker = grr_worker
    self.response_id = INITIAL_RESPONSE_ID
    self.cpu_used = None
    self.status = rdf_flows.GrrStatus(
        status=rdf_flows.GrrStatus.ReturnedStatus.OK)
    self._last_gc_run = rdfvalue.RDFDatetime.Now()
    self._gc_frequency = rdfvalue.Duration.From(
        config.CONFIG["Client.gc_frequency"], rdfvalue.SECONDS)
    self.cpu_times = _CpuTimes()
    self.cpu_limit = rdf_flows.GrrMessage().cpu_limit
    self.start_time = None
    self.runtime_limit = None

  def Execute(self, message):
    """This function parses the RDFValue from the server.

    The Run method will be called with the specified RDFValue.

    Args:
      message:     The GrrMessage that we are called to process.

    Returns:
       Upon return a callback will be called on the server to register
       the end of the function and pass back exceptions.
    Raises:
       RuntimeError: The arguments from the server do not match the expected
                     rdf type.
    """
    self.message = message
    if message:
      self.require_fastpoll = message.require_fastpoll

    args = None
    try:
      if self.message.args_rdf_name:
        if not self.in_rdfvalue:
          raise RuntimeError("Did not expect arguments, got %s." %
                             self.message.args_rdf_name)

        if self.in_rdfvalue.__name__ != self.message.args_rdf_name:
          raise RuntimeError(
              "Unexpected arg type %s != %s." %
              (self.message.args_rdf_name, self.in_rdfvalue.__name__))

        args = self.message.payload

      # Only allow authenticated messages in the client
      if self._authentication_required and (
          self.message.auth_state !=
          rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED):
        raise RuntimeError("Message for %s was not Authenticated." %
                           self.message.name)

      self.cpu_times = _CpuTimes()
      self.cpu_limit = self.message.cpu_limit

      if getattr(flags.FLAGS, "debug_client_actions", False):
        pdb.set_trace()

      self.start_time = rdfvalue.RDFDatetime.Now()
      self.runtime_limit = self.message.runtime_limit_us

      try:
        self.Run(args)

      # Ensure we always add CPU usage even if an exception occurred.
      finally:
        self.cpu_used = self.cpu_times.cpu_used
        self.status.runtime_us = rdfvalue.RDFDatetime.Now() - self.start_time

    except NetworkBytesExceededError as e:
      self.grr_worker.SendClientAlert("Network limit exceeded.")
      self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.NETWORK_LIMIT_EXCEEDED,
                     "%r: %s" % (e, e), traceback.format_exc())

    except RuntimeExceededError as e:
      self.grr_worker.SendClientAlert("Runtime limit exceeded.")
      self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.RUNTIME_LIMIT_EXCEEDED,
                     "%r: %s" % (e, e), traceback.format_exc())

    except CPUExceededError as e:
      self.grr_worker.SendClientAlert("Cpu limit exceeded.")
      self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.CPU_LIMIT_EXCEEDED,
                     "%r: %s" % (e, e), traceback.format_exc())

    # We want to report back all errors and map Python exceptions to
    # Grr Errors.
    except Exception as e:  # pylint: disable=broad-except
      self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR,
                     "%r: %s" % (e, e), traceback.format_exc())

      if flags.FLAGS.pdb_post_mortem:
        pdb.post_mortem()

    if self.status.status != rdf_flows.GrrStatus.ReturnedStatus.OK:
      logging.info("Job Error (%s): %s", self.__class__.__name__,
                   self.status.error_message)

      if self.status.backtrace:
        logging.debug(self.status.backtrace)

    if self.cpu_used:
      self.status.cpu_time_used.user_cpu_time = self.cpu_used[0]
      self.status.cpu_time_used.system_cpu_time = self.cpu_used[1]

    # This returns the error status of the Actions to the flow.
    self.SendReply(self.status, message_type=rdf_flows.GrrMessage.Type.STATUS)

    self._RunGC()

  def _RunGC(self):
    # After each action we can run the garbage collection to reduce our memory
    # footprint a bit. We don't do it too frequently though since this is
    # a bit expensive.
    now = rdfvalue.RDFDatetime.Now()
    if now - self._last_gc_run > self._gc_frequency:
      gc.collect()
      self._last_gc_run = now

  def ForceGC(self):
    self._last_gc_run = rdfvalue.RDFDatetime(0)
    self._RunGC()

  def Run(self, unused_args):
    """Main plugin entry point.

    This function will always be overridden by real plugins.

    Args:
      unused_args: An already initialised protobuf object.

    Raises:
      KeyError: if not implemented.
    """
    raise KeyError("Action %s not available on this platform." %
                   self.message.name)

  def SetStatus(self, status, message="", backtrace=None):
    """Set a status to report back to the server."""
    self.status.status = status
    self.status.error_message = utils.SmartUnicode(message)
    if backtrace:
      self.status.backtrace = utils.SmartUnicode(backtrace)

  # TODO(hanuszczak): It feels like this function is doing too much. `SendReply`
  # should be able to send replies only to the parent flow and there should be
  # some other method to communicate with well-known flows. The naming is also
  # confusing since sending messages to well-knows flows is not really replying
  # to anything.
  def SendReply(self,
                rdf_value=None,
                session_id=None,
                message_type=rdf_flows.GrrMessage.Type.MESSAGE):
    """Send response back to the server."""
    # TODO(hanuszczak): This is pretty bad. Here we assume that if the session
    # id is not none we are "replying" to a well-known flow. If we are replying
    # to a well-known flow we cannot increment the response id (since these are
    # not really responses) because otherwise the parent flow will think it is
    # missing some responses.
    #
    # Moreover, the message queue (at least in the flow test helper workflow)
    # expects flow messages to have request id equal to 0. This is rather
    # convoluted and should be untangled in the future.
    #
    # Once we have a separate method for communicating with well-known flows
    # this if-statement should no longer be relevant (since setting custom
    # session ids would become illegal).
    if session_id is None:
      response_id = self.response_id
      request_id = self.message.request_id
      session_id = self.message.session_id
      self.response_id += 1
    else:
      response_id = 0
      request_id = 0

    self.grr_worker.SendReply(
        rdf_value,
        # This is not strictly necessary but adds context
        # to this response.
        name=self.__class__.__name__,
        session_id=session_id,
        response_id=response_id,
        request_id=request_id,
        message_type=message_type,
        task_id=self.message.Get("task_id") or None,
        require_fastpoll=self.require_fastpoll)

  def Progress(self):
    """Indicate progress of the client action.

    This function should be called periodically during client actions that do
    not finish instantly. It will notify the nanny that the action is not stuck
    and avoid the timeout and it will also check if the action has reached its
    cpu limit.

    Raises:
      CPUExceededError: CPU limit exceeded.
      RuntimeExceededError: Runtime limit exceeded.
    """
    now = rdfvalue.RDFDatetime.Now()
    time_since_last_progress = now - ActionPlugin.last_progress_time

    if time_since_last_progress <= self._PROGRESS_THROTTLE_INTERVAL:
      return

    if self.runtime_limit and now - self.start_time > self.runtime_limit:
      raise RuntimeExceededError("{} exceeded runtime limit of {}.".format(
          compatibility.GetName(type(self)), self.runtime_limit))

    ActionPlugin.last_progress_time = now

    # Prevent the machine from sleeping while the action is running.
    client_utils.KeepAlive()

    self.grr_worker.Heartbeat()

    used_cpu = self.cpu_times.total_cpu_used

    if used_cpu > self.cpu_limit:
      raise CPUExceededError("Action exceeded cpu limit.")

  def SyncTransactionLog(self):
    """This flushes the transaction log.

    This function should be called by the client before performing
    potential dangerous actions so the server can get notified in case
    the whole machine crashes.
    """
    self.grr_worker.SyncTransactionLog()

  def ChargeBytesToSession(self, length):
    self.grr_worker.ChargeBytesToSession(
        self.message.session_id, length, limit=self.network_bytes_limit)

  @property
  def session_id(self):
    try:
      return self.message.session_id
    except AttributeError:
      return None

  @property
  def network_bytes_limit(self):
    try:
      return self.message.network_bytes_limit
    except AttributeError:
      return None
