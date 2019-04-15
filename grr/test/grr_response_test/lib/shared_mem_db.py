#!/usr/bin/env python
"""An implementation of an file-based data store for testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import inspect
import logging
import pickle
import socket
import threading
import time

import socketserver

from grr_response_core import config
from grr_response_core.lib import utils
from grr_response_server import blob_store
from grr_response_server.databases import db
from grr_response_server.databases import mem


def ConvertToListIfIterator(obj):
  if isinstance(obj, collections.Iterator):
    return list(obj)
  else:
    return obj


class SharedMemoryDBTCPHandler(socketserver.StreamRequestHandler):
  """TCP connections handler for SharedMemoryDB server."""

  @property
  def delegate(self):
    return self.server.delegate

  def _handle(self):
    try:
      function_name, args, kwargs = pickle.load(self.rfile)
    except EOFError:
      # Client has closed the connection. Just return then.
      # This logic is useful when detecting if the data store server is up or
      # not by opening a socket connection and then immediately closing it.
      # Ingoring EOFError errors here means that we're not going to spam
      # stderr with tracebacks.
      return

    try:
      # If the handler class has a method with a name corresponding to
      # function_name, invoke it.
      # Otherwise try the delegate.
      if hasattr(self, function_name):
        method = getattr(self, function_name)
      else:
        method = getattr(self.delegate, function_name)
    except AttributeError as e:
      logging.exception("Function %s not found in the delegate %s.",
                        function_name, self.delegate)
      pickle.dump(e, self.wfile)
      return

    try:
      result = method(*args, **kwargs)
      pickle.dump(ConvertToListIfIterator(result), self.wfile)
    except Exception as e:  # pylint: disable=broad-except
      # Any error has to be pickled and sent back so that DB-related
      # exceptions handling code behaves correctly.
      # Only log exceptions that don't inherit from db.Error. db.Error-based
      # exceptions are considered operational.
      if not isinstance(e, db.Error):
        logging.exception("Exception in the delegated call: %s (args: %s)",
                          function_name, args)
      pickle.dump(e, self.wfile)

  def handle(self):
    with self.server.lock:
      self._handle()

  def __FlowProcessingHandler(self, requests):
    """Stores flow processing request together with the current time."""
    self.server.flow_processing_requests.append((time.time(), requests))

  # Called by SharedMemoryDB implementation.
  def _SMDBGetFlowProcessingRequests(self, after_timestamp, before_timestamp):
    """Returns flow processing requests received within a given time range."""
    result = []
    for timestamp, requests in self.server.flow_processing_requests:
      if timestamp >= after_timestamp and timestamp < before_timestamp:
        result.append(requests)

    return result

  # Called by SharedMemoryDB implementation.
  def _SMDBRegisterFlowProcessingHandler(self):
    """Used by clients to notify about local processing handler registration.

    This is an optimization. There's no point to register a flow processing
    handler and later deregister it in SharedMemoryDB server if there's no
    client to use it.
    """
    if self.server.num_fpr_handlers == 0:
      self.delegate.RegisterFlowProcessingHandler(self.__FlowProcessingHandler)
    self.server.num_fpr_handlers += 1

  # Called by SharedMemoryDB implementation.
  def _SMDBUnregisterFlowProcessingHandler(self):
    """Used by clients to notify about requests handler deregistration."""
    self.server.num_fpr_handlers -= 1
    if self.server.num_fpr_handlers == 0:
      self.delegate.UnregisterFlowProcessingHandler()
      self.server.flow_processing_requests = []

  def __MessageHandler(self, messages):
    """Stores messages together with timestamps."""
    self.server.messages.append((time.time(), messages))

  # Called by SharedMemoryDB implementation.
  def _SMDBGetMessages(self, after_timestamp, before_timestamp):
    """Returns messages received within a given time range."""
    result = []
    for timestamp, messages in self.server.messages:
      if timestamp >= after_timestamp and timestamp < before_timestamp:
        result.append(messages)

    return result

  # Called by SharedMemoryDB implementation.
  def _SMDBRegisterMessageHandler(self, lease_time, limit):
    """Used by clients to notify about local messages handler registration.

    This is an optimization. There's no point to register a message
    handler and later deregister it in SharedMemoryDB server if there's no
    client to use it.

    Args:
      lease_time: Message lease time.
      limit: Max number of messages to be handled by a single handler call.
    """
    if self.server.num_msg_handlers == 0:
      self.delegate.RegisterMessageHandler(
          self.__MessageHandler, lease_time=lease_time, limit=limit)
    self.server.num_msg_handlers += 1

  # Called by SharedMemoryDB implementation.
  def _SMDBUnregisterMessageHandler(self):
    """Used by clients to notify about message handler deregistration."""
    self.server.num_msg_handlers -= 1
    if self.server.num_msg_handlers == 0:
      self.delegate.UnregisterMessageHandler()
      self.server.messages = []


class TCPServerV6(socketserver.TCPServer):
  address_family = socket.AF_INET6


def SharedMemoryDBServer(port):
  """Initializes SharedMemoryDB server object."""

  server = TCPServerV6(("::", port), SharedMemoryDBTCPHandler)
  server.port = port
  server.lock = threading.RLock()

  server.flow_processing_requests = []
  server.num_fpr_handlers = 0
  server.messages = []
  server.num_msg_handlers = 0

  server.delegate = mem.InMemoryDB()

  def Reset():
    server.delegate = mem.InMemoryDB()

  server.Reset = Reset  # pylint: disable=invalid-name

  return server


_FILE_READ_CHUNK_SIZE = 1024 * 1024


def DelegatedMethod(mname):
  """Class decorator delegating a single given method to a remote DB server."""

  def Impl(self, *args, **kwargs):
    """Method implementation to add."""
    del self  # unused

    port = config.CONFIG["SharedMemoryDB.port"]
    sock = socket.create_connection(("localhost", port))
    sock.settimeout(30.0)
    try:
      # Send pickled request.
      sock.sendall(pickle.dumps((mname, args, kwargs)))

      # Read pickled response.
      data = []
      while True:
        chunk = sock.recv(_FILE_READ_CHUNK_SIZE)
        if not chunk:
          break
        data.append(chunk)

      # Unpickle the response combined from read chunks.
      result = pickle.loads(b"".join(data))
    finally:
      sock.close()

    # If returned object is an exception, simply raise it.
    if isinstance(result, Exception):
      raise result

    return result

  def MethodAdder(cls):
    setattr(cls, mname, Impl)
    return cls

  return MethodAdder


def DelegatedMethods(mnames):
  """Class decorator delegating a set of methdos to a remote DB server."""

  def MethodsAdder(cls):
    for mname in mnames:
      cls = DelegatedMethod(mname)(cls)

    return cls

  return MethodsAdder


def GetAbstractDBMethodNames(cls):

  def Predicate(m):
    return inspect.ismethod(m) and "__isabstractmethod__" in m.im_func.func_dict

  members = inspect.getmembers(cls, Predicate)
  return [method_name for method_name, _ in members]


@DelegatedMethods(GetAbstractDBMethodNames(db.Database))
@DelegatedMethods(GetAbstractDBMethodNames(blob_store.BlobStore))
# Methods below are SharedMemoryDB-specific:
@DelegatedMethod("_SMDBGetFlowProcessingRequests")
@DelegatedMethod("_SMDBRegisterFlowProcessingHandler")
@DelegatedMethod("_SMDBUnregisterFlowProcessingHandler")
@DelegatedMethod("_SMDBGetMessages")
@DelegatedMethod("_SMDBRegisterMessageHandler")
@DelegatedMethod("_SMDBUnregisterMessageHandler")
class SharedMemoryDBMixin(object):
  """Mixin containing auto-generated delegated method.

  While it's technically possible to apply @DelegatedMethod decorators to
  the SharedMemoryDB class itself, registering new methods this way
  doesn't play nicely with inheriting from an abstract class.

  @DelegatedMethod uses setattr to define new methods. However, effectively,
  using setattr to declare an implementation of a method
  marked as @abc.abstractmethod doesn't play nicely with the abc
  library. On the other hand, inheriting from a mixin where
  methods are defined with setattr works fine.
  """


class SharedMemoryDB(SharedMemoryDBMixin, db.Database):
  """Implementation that forwards requests to remote memory DB server."""

  def __init__(self):
    super(SharedMemoryDB, self).__init__()

    self.flow_handler_stop = False
    self.flow_handler_target = None
    self.flow_handler_thread = None

    self.handler_stop = False
    self.handler_target = None
    self.handler_thread = None

    self.lock = threading.RLock()

  @utils.Synchronized
  def RegisterFlowProcessingHandler(self, handler):
    """Registers a message handler to receive flow processing messages."""
    self.UnregisterFlowProcessingHandler()

    # A simple (though expensive) way to implement callbacks in SharedMemoryDB
    # is to make server always collect everything and let clients simply
    # poll for incoming messages. This approach is implemented in SharedMemoryDB
    # for both flow processing requests and messages.
    self._SMDBRegisterFlowProcessingHandler()
    self.flow_handler_stop = False
    self.flow_handler_thread = threading.Thread(
        name="flow_processing_handler",
        target=self._HandleFlowProcessingRequestLoop,
        args=(handler,))
    self.flow_handler_thread.daemon = True
    self.flow_handler_thread.start()

  @utils.Synchronized
  def UnregisterFlowProcessingHandler(self, timeout=None):
    """Unregisters any registered flow processing handler."""
    self.flow_handler_target = None

    if self.flow_handler_thread:
      self._SMDBUnregisterFlowProcessingHandler()
      self.flow_handler_stop = True
      self.flow_handler_thread.join(timeout)
      if self.flow_handler_thread.isAlive():
        raise RuntimeError("Flow processing handler did not join in time.")
      self.flow_handler_thread = None

  def _HandleFlowProcessingRequestLoop(self, handler):
    """Handler thread for the FlowProcessingRequest queue."""
    last_time = time.time()
    while not self.flow_handler_stop:
      new_time = time.time()
      todo = self._SMDBGetFlowProcessingRequests(last_time, new_time)
      last_time = new_time

      for request in todo:
        handler(request)

      time.sleep(0.2)

  @utils.Synchronized
  def RegisterMessageHandler(self, handler, lease_time, limit=1000):
    """Leases a number of message handler requests up to the indicated limit."""
    self.UnregisterMessageHandler()

    # A simple (though expensive) way to implement callbacks in SharedMemoryDB
    # is to make server always collect everything and let clients simply
    # poll for incoming messages. This approach is implemented in SharedMemoryDB
    # for both flow processing requests and messages.
    self._SMDBRegisterMessageHandler(lease_time, limit)
    self.handler_stop = False
    self.handler_thread = threading.Thread(
        name="message_handler",
        target=self._MessageHandlerLoop,
        args=(handler, lease_time, limit))
    self.handler_thread.daemon = True
    self.handler_thread.start()

  @utils.Synchronized
  def UnregisterMessageHandler(self, timeout=None):
    """Unregisters any registered message handler."""
    if self.handler_thread:
      self._SMDBUnregisterMessageHandler()

      self.handler_stop = True
      self.handler_thread.join(timeout)
      if self.handler_thread.isAlive():
        raise RuntimeError("Message handler thread did not join in time.")
      self.handler_thread = None

  def _MessageHandlerLoop(self, handler, lease_time, limit):
    last_time = time.time()
    while not self.handler_stop:
      new_time = time.time()
      todo = self._SMDBGetMessages(last_time, new_time)
      last_time = new_time

      for request in todo:
        handler(request)

      time.sleep(0.2)
