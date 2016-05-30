#!/usr/bin/env python
"""This file contains common grr jobs."""


import gc
import logging
import pdb
import threading
import time
import traceback


import psutil

from grr.client import client_utils
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib import utils
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import protodict as rdf_protodict

# Our first response in the session is this:
INITIAL_RESPONSE_ID = 1


class Error(Exception):
  pass


class CPUExceededError(Error):
  pass


class NetworkBytesExceededError(Error):
  """Exceeded the maximum number of bytes allowed to be sent for this action."""


class ThreadNotFoundError(Error):
  """A suspended thread was requested that doesn't exist on the client."""


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

  __metaclass__ = registry.MetaclassRegistry

  priority = rdf_flows.GrrMessage.Priority.MEDIUM_PRIORITY

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
    self._last_gc_run = rdfvalue.RDFDatetime().Now()
    self._gc_frequency = config_lib.CONFIG["Client.gc_frequency"]
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
      self.priority = message.priority
      self.require_fastpoll = message.require_fastpoll

    args = None
    try:
      if self.message.args_rdf_name:
        if not self.in_rdfvalue:
          raise RuntimeError("Did not expect arguments, got %s." %
                             self.message.args_rdf_name)

        if self.in_rdfvalue.__name__ != self.message.args_rdf_name:
          raise RuntimeError("Unexpected arg type %s != %s." %
                             (self.message.args_rdf_name,
                              self.in_rdfvalue.__name__))

        args = self.message.payload

      # Only allow authenticated messages in the client
      if self._authentication_required and (
          self.message.auth_state !=
          rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED):
        raise RuntimeError("Message for %s was not Authenticated." %
                           self.message.name)

      self.cpu_start = self.proc.cpu_times()
      self.cpu_limit = self.message.cpu_limit
      self.network_bytes_limit = self.message.network_bytes_limit

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
    now = rdfvalue.RDFDatetime().Now()
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

  def SendReply(self,
                rdf_value=None,
                message_type=rdf_flows.GrrMessage.Type.MESSAGE,
                **kw):
    """Send response back to the server."""
    if rdf_value is None:
      # The only client actions with multiple out_rdfvalues have them for
      # server-side checks that allow for backwards compatibility. In the future
      # if an action genuinely returns multiple rdfvalues it should pass them in
      # using the rdf_value keyword.
      rdf_value = self.out_rdfvalues[0](**kw)  # pylint: disable=not-callable

    self.grr_worker.SendReply(
        rdf_value,
        # This is not strictly necessary but adds context
        # to this response.
        name=self.__class__.__name__,
        session_id=self.message.session_id,
        response_id=self.response_id,
        request_id=self.message.request_id,
        message_type=message_type,
        task_id=self.message.task_id,
        priority=self.priority,
        require_fastpoll=self.require_fastpoll)

    self.response_id += 1

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

    if self.nanny_controller is None:
      self.nanny_controller = client_utils.NannyController()

    self.nanny_controller.Heartbeat()

    user_start, system_start = self.cpu_start
    user_end, system_end = self.proc.cpu_times()

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

    if self.nanny_controller is None:
      self.nanny_controller = client_utils.NannyController()
    self.nanny_controller.SyncTransactionLog()

  def ChargeBytesToSession(self, length):
    self.grr_worker.ChargeBytesToSession(self.message.session_id,
                                         length,
                                         limit=self.network_bytes_limit)

  def DisableNanny(self):
    try:
      self.nanny_controller.nanny.Stop()
    except AttributeError:
      logging.info("Can't disable Nanny on this OS.")


class IteratedAction(ActionPlugin):
  """An action which can restore its state from an iterator.

  Implement iterating actions by extending this class and overriding the
  Iterate() method.
  """

  def Run(self, request):
    """Munge the iterator to the server and abstract it away."""
    # Pass the client_state as a dict to the action. This is often more
    # efficient than manipulating a protobuf.
    client_state = request.iterator.client_state.ToDict()

    # Derived classes should implement this.
    self.Iterate(request, client_state)

    # Update the iterator client_state from the dict.
    request.iterator.client_state = rdf_protodict.Dict(client_state)

    # Return the iterator
    self.SendReply(request.iterator,
                   message_type=rdf_flows.GrrMessage.Type.ITERATOR)

  def Iterate(self, request, client_state):
    """Actions should override this."""


class ClientActionWorker(threading.Thread):
  """A worker thread for the suspendable client action."""

  daemon = True

  def __init__(self, action=None, *args, **kw):
    super(ClientActionWorker, self).__init__(*args, **kw)
    self.cond = threading.Condition(lock=threading.RLock())
    self.id = None
    self.action_obj = action
    self.exception_status = None

  def Resume(self):
    with self.cond:
      self.cond.notify()
      self.cond.wait()

  def Suspend(self):
    with self.cond:
      self.cond.notify()
      self.cond.wait()

  def run(self):
    # Suspend right after starting.
    self.Suspend()
    try:
      # Do the actual work.
      self.action_obj.Iterate()

    except Exception:  # pylint: disable=broad-except
      if flags.FLAGS.debug:
        pdb.post_mortem()

      # Record the exception status so the main thread can propagate it to the
      # server.
      self.exception_status = traceback.format_exc()
      raise

    finally:
      # Notify the action that we are about to exit. This always has to happen
      # or the main thread will stop.
      self.action_obj.Done()
      with self.cond:
        self.cond.notify()


class SuspendableAction(ActionPlugin):
  """An action that can be suspended on the client.

  How suspended client actions work?

  The GRRClientWorker maintains a store of suspended client actions. A suspended
  client action is one where the thread of execution can be suspended by the
  client at any time, and control is passed back to the server flow. The server
  flow then can resume the client action.

  Since only a single thread can run on the client worker at the same time, the
  suspendable client action and the worker thread are exclusively blocked.

  1) Initially the server issues a regular request to this suspendable action.

  2) Since the Iterator field in the request is initially empty, the
     GRRClientWorker() will instantiate a new ActionPlugin() instance.

  3) The SuspendableAction() instance is then added to the GRRClientWorker's
     suspended_actions store using a unique ID. The unique ID is also copied to
     the request's Iterator.client_state dict.

  4) We then call the client action's Execute method.

  5) The suspendable client action does all its work in a secondary thread, in
     order to allow it to be suspended arbitrarily. We therefore create a
     ClientActionWorker() thread, and pass control it - while the main thread is
     waiting for it.

  6) The ClientActionWorker() thread calls back into the Iterate() method of the
     SuspendableAction() - this is where all the work is done.

  7) When the client action wants to suspend it called its Suspend()
     method. This will block the ClientActionWorker() thread and release the
     main GRRClientWorker() thread. The request is then completed by sending the
     server an ITERATOR and a STATUS message. The corresponding thread is now
     allowed to process all replies so far. The SuspendableAction() is blocked
     until further notice.

  8) The server processes the responses, and then sends a new request,
     containing the same Iterator object that the client gave it. The Iterator
     contains an opaque client_state dict.

  9) The client finds the unique key in the Iterator.client_state dict, which
     allows it to retrieve the SuspendableAction() from the GRRClientWorker()'s
     suspended_actions store. We then call the Run method, which switched
     execution to the ClientActionWorker() thread.
  """

  def __init__(self, *args, **kw):
    # We allow specifying the worker class.
    self.worker_cls = kw.pop("action_worker_cls", None)

    super(SuspendableAction, self).__init__(*args, **kw)
    self.exceptions = []

    # A SuspendableAction does all its main work in a subthread controlled
    # through a condition variable.
    self.worker = None

  def Run(self, request):
    """Process a server request."""
    # This method will be called multiple times for each new client request,
    # therefore we need to resent the response_id each time.
    self.response_id = INITIAL_RESPONSE_ID
    self.request = request

    # We need to start a new worker thread.
    if not self.worker:
      worker_cls = self.worker_cls or ClientActionWorker
      self.worker = worker_cls(action=self)

      # Grab the lock before the thread is started.
      self.worker.cond.acquire()
      self.worker.start()

      # The worker will be blocked trying to get the lock that we are already
      # holding it so we call Resume() and enter a state where the main thread
      # waits for the condition variable and, at the same time, releases the
      # lock. Next the worker will notify the condition variable and suspend
      # itself. This guarantees that we are now in a defined state where the
      # worker is suspended and waiting on the condition variable and the main
      # thread is running. After the next call to Resume() below, the worker
      # will wake up and actually begin running the client action.
      self.worker.Resume()

      # Store ourselves in the worker thread's suspended_actions store.
      self.grr_worker.suspended_actions[id(self)] = self

      # Mark our ID in the iterator's client_state area. The server will return
      # this (opaque) client_state to us on subsequent calls. The client worker
      # thread will be able to retrieve us in this case.
      self.request.iterator.suspended_action = id(self)

    # We stop running, and let the worker run instead.
    self.worker.Resume()

    # An exception occured in the worker thread and it was terminated. We
    # re-raise it here.
    if self.worker.exception_status:
      raise RuntimeError("Exception in child thread: %s" %
                         (self.worker.exception_status))

    # Return the iterator
    self.SendReply(self.request.iterator,
                   message_type=rdf_flows.GrrMessage.Type.ITERATOR)

  def Done(self):
    # Let the server know we finished.
    self.request.iterator.state = self.request.iterator.State.FINISHED

    # Remove the action from the suspended_actions store.
    del self.grr_worker.suspended_actions[id(self)]

  def Suspend(self):
    self.worker.Suspend()

  def Iterate(self):
    """Actions should override this."""
