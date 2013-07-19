#!/usr/bin/env python
"""This file contains common grr jobs."""


import logging
import os
import pdb
import traceback


import psutil

from grr.client import client_utils
from grr.lib import flags
from grr.lib import rdfvalue
# pylint: disable=unused-import
from grr.lib import rdfvalues
# pylint: enable=unused-import
from grr.lib import registry
from grr.lib import utils


# Our first response in the session is this:
INITIAL_RESPONSE_ID = 1


class Error(Exception):
  pass


class CPUExceededError(Error):
  pass


class NetworkBytesExceededError(Error):
  """Exceeded the maximum number of bytes allowed to be sent for this action."""
  pass


class ActionPlugin(object):
  """Baseclass for plugins.

  An action is a plugin abstraction which receives an rdfvalue and
  sends another rdfvalue in response.

  The code is specified in the Run() method, while the data is
  specified in the in_rdfvalue and out_rdfvalue classes.
  """
  # The rdfvalue used to encode this message.
  in_rdfvalue = None

  # TODO(user): The RDFValue instance for the output protobufs. This is
  # required temporarily until the client sends RDFValue instances instead of
  # protobufs.
  out_rdfvalue = None

  # Authentication Required for this Action:
  _authentication_required = True

  __metaclass__ = registry.MetaclassRegistry

  priority = rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY

  require_fastpoll = True

  def __init__(self, message, grr_worker=None):
    """Initializes the action plugin.

    Args:
      message:     The GrrMessage that we are called to process.
      grr_worker:  The grr client worker object which may be used to
                   e.g. send new actions on.
    """
    self.grr_worker = grr_worker
    self.message = message
    self.response_id = INITIAL_RESPONSE_ID
    self.cpu_used = None
    self.nanny_controller = None
    if message:
      self.priority = message.priority

  def Execute(self):
    """This function parses the RDFValue from the server.

    The Run method will be called with the specified RDFValue.

    Returns:
       Upon return a callback will be called on the server to register
       the end of the function and pass back exceptions.
    Raises:
       RuntimeError: The arguments from the server do not match the expected
                     rdf type.

    """
    args = None
    if self.message.args_rdf_name:
      if not self.in_rdfvalue:
        raise RuntimeError("Did not expect arguments, got %s." %
                           self.message.args_rdf_name)
      if self.in_rdfvalue.__name__ != self.message.args_rdf_name:
        raise RuntimeError("Unexpected arg type %s != %s." %
                           self.message.args_rdf_name,
                           self.in_rdfvalue.__name__)

      # TODO(user): should be args = self.message.payload
      args = rdfvalue.GrrMessage(self.message).payload

    self.status = rdfvalue.GrrStatus(
        status=rdfvalue.GrrStatus.ReturnedStatus.OK)

    try:
      # Only allow authenticated messages in the client
      if (self._authentication_required and
          self.message.auth_state !=
          rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED):
        raise RuntimeError("Message for %s was not Authenticated." %
                           self.message.name)

      pid = os.getpid()
      self.proc = psutil.Process(pid)
      user_start, system_start = self.proc.get_cpu_times()
      self.cpu_start = (user_start, system_start)
      self.cpu_limit = self.message.cpu_limit
      self.network_bytes_limit = self.message.network_bytes_limit

      try:
        self.Run(args)

      # Ensure we always add CPU usage even if an exception occured.
      finally:
        user_end, system_end = self.proc.get_cpu_times()

        self.cpu_used = (user_end - user_start, system_end - system_start)

    except NetworkBytesExceededError as e:
      self.SetStatus(rdfvalue.GrrStatus.ReturnedStatus.NETWORK_LIMIT_EXCEEDED,
                     "%r: %s" % (e, e),
                     traceback.format_exc())

    # We want to report back all errors and map Python exceptions to
    # Grr Errors.
    except Exception as e:  # pylint: disable=broad-except
      self.SetStatus(rdfvalue.GrrStatus.ReturnedStatus.GENERIC_ERROR,
                     "%r: %s" % (e, e),
                     traceback.format_exc())
      if flags.FLAGS.debug:
        pdb.post_mortem()

    if self.status.status != rdfvalue.GrrStatus.ReturnedStatus.OK:
      logging.info("Job Error (%s): %s", self.__class__.__name__,
                   self.status.error_message)
      if self.status.backtrace:
        logging.debug(self.status.backtrace)

    if self.cpu_used:
      self.status.cpu_time_used.user_cpu_time = self.cpu_used[0]
      self.status.cpu_time_used.system_cpu_time = self.cpu_used[1]

    # This returns the error status of the Actions to the flow.
    self.SendReply(self.status, message_type=rdfvalue.GrrMessage.Type.STATUS)

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

  def SendReply(self, rdf_value=None,
                message_type=rdfvalue.GrrMessage.Type.MESSAGE, **kw):
    """Send response back to the server."""
    if rdf_value is None:
      rdf_value = self.out_rdfvalue(**kw)  # pylint: disable=not-callable

    self.grr_worker.SendReply(rdf_value,
                              # This is not strictly necessary but adds context
                              # to this response.
                              name=self.__class__.__name__,
                              session_id=self.message.session_id,
                              response_id=self.response_id,
                              request_id=self.message.request_id,
                              message_type=message_type,
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
    # Prevent the machine from sleeping while the action is running.
    client_utils.KeepAlive()

    if self.nanny_controller is None:
      self.nanny_controller = client_utils.NannyController()

    self.nanny_controller.Heartbeat()
    try:
      user_start, system_start = self.cpu_start
      user_end, system_end = self.proc.get_cpu_times()

      used_cpu = user_end - user_start + system_end - system_start

      if used_cpu > self.cpu_limit:
        self.grr_worker.SendClientAlert("Cpu limit exceeded.")
        raise CPUExceededError("Action exceeded cpu limit.")

    except AttributeError:
      pass

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
    self.grr_worker.ChargeBytesToSession(self.message.session_id, length,
                                         limit=self.network_bytes_limit)


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
    request.iterator.client_state = rdfvalue.Dict(client_state)

    # Return the iterator
    self.SendReply(request.iterator,
                   message_type=rdfvalue.GrrMessage.Type.ITERATOR)

  def Iterate(self, request, client_state):
    """Actions should override this."""
