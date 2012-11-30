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


"""This file contains common grr jobs."""


import logging
import os
import pdb
import traceback


import psutil

from grr.client import conf as flags
from grr.client import client_utils
from grr.lib import registry
from grr.lib import utils
from grr.proto import jobs_pb2

FLAGS = flags.FLAGS

# Our first response in the session is this:
INITIAL_RESPONSE_ID = 1


class Error(Exception):
  pass


class CPUExceededError(Error):
  pass


class ActionPlugin(object):
  """Baseclass for plugins.

  An action is a plugin abstraction which receives a protobuf and
  sends a protobuf in response.

  The code is specified in the Run() method, while the data is
  specified in the in_protobuf and out_protobuf classes.
  """
  # The protobuf that will be used to encode this message
  in_protobuf = None

  # The protobuf type we send
  out_protobuf = None

  # Authentication Required for this Action:
  _authentication_required = True

  __metaclass__ = registry.MetaclassRegistry

  priority = jobs_pb2.GrrMessage.MEDIUM_PRIORITY

  require_fastpoll = True

  def __init__(self, message, grr_worker=None, **proto_args):
    """Initialises our protobuf from the keywords passed.

    Args:
      message:     The GrrMessage that we are called to process.
      grr_worker:  The grr client worker object which may be used to
                   e.g. send new actions on.
      **proto_args:  Field initializers for the protobuf in self._protobuf.
    """
    self.grr_worker = grr_worker
    self.message = message
    self.response_id = INITIAL_RESPONSE_ID
    self.cpu_used = None
    self.nanny_controller = None
    if message:
      self.priority = message.priority

    if self.in_protobuf:
      self.buff = self.in_protobuf()  # pylint: disable=E1102

      for k, v in proto_args.items():
        setattr(self.buff, k, v)

  def Execute(self, message):
    """This function parses the protobuf from the server.

    The Run method will be called with the unserialised protobuf.

    Args:
       message: The encoded protobuf which will be decoded
       by the plugin.

    Returns:
       Upon return a callback will be called on the server to register
       the end of the function and pass back exceptions.
    """
    if self.in_protobuf:
      args = self.in_protobuf()  # pylint: disable=E1102
      args.ParseFromString(message.args)
    else:
      args = None

    self.status = jobs_pb2.GrrStatus()
    self.status.status = jobs_pb2.GrrStatus.OK  # Default status.

    try:
      # Only allow authenticated messages in the client
      if (self._authentication_required and
          message.auth_state != jobs_pb2.GrrMessage.AUTHENTICATED):
        raise RuntimeError("Message for %s was not Authenticated." %
                           message.name)

      pid = os.getpid()
      self.proc = psutil.Process(pid)
      user_start, system_start = self.proc.get_cpu_times()
      self.cpu_start = (user_start, system_start)
      self.cpu_limit = message.cpu_limit
      self.Run(args)
      user_end, system_end = self.proc.get_cpu_times()

      self.cpu_used = (user_end - user_start, system_end - system_start)

    # We want to report back all errors and map Python exceptions to
    # Grr Errors.
    except Exception, e:  # pylint: disable=W0703
      self.SetStatus(jobs_pb2.GrrStatus.GENERIC_ERROR, "%r: %s" % (e, e),
                     traceback.format_exc())
      if FLAGS.debug:
        pdb.post_mortem()

    if self.status.status != jobs_pb2.GrrStatus.OK:
      logging.info("Job Error (%s): %s", self.__class__.__name__,
                   self.status.error_message)
      if self.status.backtrace:
        logging.debug(self.status.backtrace)

    if self.cpu_used:
      self.status.cpu_time_used.user_cpu_time = self.cpu_used[0]
      self.status.cpu_time_used.system_cpu_time = self.cpu_used[1]

    # This returns the error status of the Actions to the flow.
    self.SendReply(self.status, message_type=jobs_pb2.GrrMessage.STATUS)

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

  def SendReply(self, protobuf=None, message_type=jobs_pb2.GrrMessage.MESSAGE,
                **kw):
    """Send response back to the server."""
    if protobuf is None:
      protobuf = self.out_protobuf(**kw)  # pylint: disable=E1102

    self.grr_worker.SendReply(protobuf,
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
      used_user_cpu = self.proc.get_cpu_times()[0] - self.cpu_start[0]
      if used_user_cpu > self.cpu_limit:
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


class IteratedAction(ActionPlugin):
  """An action which can restore its state from an iterator.

  Implement iterating actions by extending this class and overriding the
  Iterate() method.
  """

  def Run(self, request):
    """Munge the iterator to the server and abstract it away."""
    # Pass the client_state as a dict to the action. This is often more
    # efficient than manipulating a protobuf.
    client_state = utils.ProtoDict(request.iterator.client_state).ToDict()

    # Derived classes should implement this.
    self.Iterate(request, client_state)

    # Update the iterator client_state from the dict.
    request.iterator.client_state.CopyFrom(
        utils.ProtoDict(client_state).ToProto())

    # Return the iterator
    self.SendReply(request.iterator, message_type=jobs_pb2.GrrMessage.ITERATOR)

  def Iterate(self, request, client_state):
    """Actions should override this."""
