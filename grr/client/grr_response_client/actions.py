#!/usr/bin/env python
"""This file contains common grr jobs."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import gc
import logging
import pdb
import time
import traceback


from future.utils import with_metaclass

import psutil

from grr_response_client import client_utils
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import registry
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import flows as rdf_flows

# Our first response in the session is this:
INITIAL_RESPONSE_ID = 1


class Error(Exception):
  pass


class CPUExceededError(Error):
  pass


class NetworkBytesExceededError(Error):
  """Exceeded the maximum number of bytes allowed to be sent for this action."""


class ActionPlugin(with_metaclass(registry.MetaclassRegistry, object)):
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

  last_progress_time = 0

  def __init__(self, grr_worker=None):
    """Initializes the action plugin.

    Args:
      grr_worker:  The grr client worker object which may be used to
                   e.g. send new actions on.
    """
    self.grr_worker = grr_worker
    self.response_id = INITIAL_RESPONSE_ID
    self.cpu_used = None
    self.nanny_controller = None
    self.status = rdf_flows.GrrStatus(
        status=rdf_flows.GrrStatus.ReturnedStatus.OK)
    self._last_gc_run = rdfvalue.RDFDatetime.Now()
    self._gc_frequency = config.CONFIG["Client.gc_frequency"]
    self.proc = psutil.Process()
    self.cpu_start = self.proc.cpu_times()
    self.cpu_limit = rdf_flows.GrrMessage().cpu_limit

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
          raise RuntimeError(
              "Did not expect arguments, got %s." % self.message.args_rdf_name)

        if self.in_rdfvalue.__name__ != self.message.args_rdf_name:
          raise RuntimeError(
              "Unexpected arg type %s != %s." % (self.message.args_rdf_name,
                                                 self.in_rdfvalue.__name__))

        args = self.message.payload

      # Only allow authenticated messages in the client
      if self._authentication_required and (
          self.message.auth_state !=
          rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED):
        raise RuntimeError(
            "Message for %s was not Authenticated." % self.message.name)

      self.cpu_start = self.proc.cpu_times()
      self.cpu_limit = self.message.cpu_limit

      if getattr(flags.FLAGS, "debug_client_actions", False):
        pdb.set_trace()

      try:
        self.Run(args)

      # Ensure we always add CPU usage even if an exception occurred.
      finally:
        used = self.proc.cpu_times()
        self.cpu_used = (used.user - self.cpu_start.user,
                         used.system - self.cpu_start.system)

    except NetworkBytesExceededError as e:
      self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.NETWORK_LIMIT_EXCEEDED,
                     "%r: %s" % (e, e), traceback.format_exc())

    # We want to report back all errors and map Python exceptions to
    # Grr Errors.
    except Exception as e:  # pylint: disable=broad-except
      self.SetStatus(rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR,
                     "%r: %s" % (e, e), traceback.format_exc())

      if flags.FLAGS.debug:
        self.DisableNanny()
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
    raise KeyError(
        "Action %s not available on this platform." % self.message.name)

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
        task_id=self.message.task_id,
        require_fastpoll=self.require_fastpoll)

  def Progress(self):
    """Indicate progress of the client action.

    This function should be called periodically during client actions that do
    not finish instantly. It will notify the nanny that the action is not stuck
    and avoid the timeout and it will also check if the action has reached its
    cpu limit.

    Raises:
      CPUExceededError: CPU limit exceeded.
    """
    now = time.time()
    if now - self.last_progress_time <= 2:
      return

    self.last_progress_time = now

    # Prevent the machine from sleeping while the action is running.
    client_utils.KeepAlive()

    self.grr_worker.Heartbeat()

    user_start = self.cpu_start.user
    system_start = self.cpu_start.system
    cpu_times = self.proc.cpu_times()
    user_end = cpu_times.user
    system_end = cpu_times.system

    used_cpu = user_end - user_start + system_end - system_start

    if used_cpu > self.cpu_limit:
      self.grr_worker.SendClientAlert("Cpu limit exceeded.")
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

  def DisableNanny(self):
    try:
      self.nanny_controller.nanny.Stop()
    except AttributeError:
      logging.info("Can't disable Nanny on this OS.")

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


class IteratedAction(ActionPlugin):
  """An action which can restore its state from an iterator.

  Implement iterating actions by extending this class and overriding the
  Iterate() method.
  """

  __abstract = True  # pylint: disable=invalid-name

  def Run(self, request):
    """Munge the iterator to the server and abstract it away."""
    # Pass the client_state as a dict to the action. This is often more
    # efficient than manipulating a protobuf.
    client_state = request.iterator.client_state.ToDict()

    # Derived classes should implement this.
    self.Iterate(request, client_state)

    # Update the iterator client_state from the dict.
    request.iterator.client_state = client_state

    # Return the iterator
    self.SendReply(
        request.iterator, message_type=rdf_flows.GrrMessage.Type.ITERATOR)

  def Iterate(self, request, client_state):
    """Actions should override this."""
