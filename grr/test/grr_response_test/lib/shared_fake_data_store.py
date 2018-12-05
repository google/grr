#!/usr/bin/env python
"""An implementation of an file-based data store for testing."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import logging
import pickle
import socket
import time

import socketserver

from grr_response_core import config
from grr_response_server import data_store
from grr_response_server.data_stores import fake_data_store


def ConvertToListIfIterator(obj):
  if isinstance(obj, collections.Iterator):
    return list(obj)
  else:
    return obj


class SharedFakeDataStoreTCPHandler(socketserver.StreamRequestHandler):
  """TCP connections handler for SharedFakeDataStore server."""

  @property
  def delegate(self):
    return self.server.delegate

  def AcquireDBSubjectLock(self, subject, new_expires):
    with self.delegate.lock:
      expires = self.delegate.transactions.get(subject)
      if expires and (time.time() * 1e6) < expires:
        raise data_store.DBSubjectLockError("Subject is locked")
      self.delegate.transactions[subject] = new_expires

  def UpdateDBSubjectLockLease(self, subject, expires):
    with self.delegate.lock:
      self.delegate.transactions[subject] = expires

  def ReleaseDBSubjectLock(self, subject):
    with self.delegate.lock:
      self.delegate.transactions.pop(subject, None)

  def handle(self):
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
      # If the delegate FakeDataStore has requested method - call it.
      # Otherwise search for the requested method in the handler itself.
      if hasattr(self.delegate, function_name):
        result = getattr(self.delegate, function_name)(*args, **kwargs)
      else:
        result = getattr(self, function_name)(*args, **kwargs)

    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Exception in the delegated call: %s (args: %s)",
                        function_name, args)
      result = e

    # If a generator or an iterator is returned, convert it to list, so that
    # it's pickleable.
    pickle.dump(ConvertToListIfIterator(result), self.wfile)


class TCPServerV6(socketserver.TCPServer):
  address_family = socket.AF_INET6


def SharedFakeDataStoreServer(port):
  """Initializes SharedFakeDataStore server object."""

  server = TCPServerV6(("::", port), SharedFakeDataStoreTCPHandler)
  server.delegate = fake_data_store.FakeDataStore()
  return server


_FILE_READ_CHUNK_SIZE = 4096


def DelegatedMethod(mname):
  """Class decorator delegating given method to a remote data store server."""

  def Impl(self, *src_args, **src_kwargs):
    """Method implementation to add."""
    del self  # unused

    # Make sure positional arguments are pickleable (i.e. have no generators
    # or iterators).
    args = []
    for a in src_args:
      args.append(ConvertToListIfIterator(a))

    # Make sure keyword arguments are pickleable (i.e. have no generators
    # or iterators).
    kwargs = {}
    for n, a in src_kwargs.items():
      kwargs[n] = ConvertToListIfIterator(a)

    port = config.CONFIG["SharedFakeDataStore.port"]
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


@DelegatedMethod("DeleteSubject")
@DelegatedMethod("ClearTestDB")
@DelegatedMethod("MultiSet")
@DelegatedMethod("DeleteAttributes")
@DelegatedMethod("ScanAttributes")
@DelegatedMethod("MultiResolvePrefix")
@DelegatedMethod("ResolveMulti")
@DelegatedMethod("Flush")
# Methods below do not belong to the DataStore abstract interface. They're
# used by SharedFakeDBSubjectLock implementation to implement subject
# locking logic in a thread-safe way.
@DelegatedMethod("AcquireDBSubjectLock")
@DelegatedMethod("UpdateDBSubjectLockLease")
@DelegatedMethod("ReleaseDBSubjectLock")
class SharedFakeDataStoreMixin(object):
  """Mixin containing auto-generated delegated method.

  While it's technically possible to apply @DelegatedMethod decorators to
  the SharedFakeDataStore class itself, registering new methods this way
  doesn't play nicely with inheriting from an abstract class.

  @DelegatedMethod uses setattr to define new methods. However, effectively,
  using setattr to declare an implementation of a method
  marked as @abc.abstractmethod doesn't play nicely with the abc
  library. On the other hand, inheriting from a mixin where
  methods are defined with setattr works fine.
  """


class SharedFakeDBSubjectLock(data_store.DBSubjectLock):
  """A fake transaction object for testing."""

  def _Acquire(self, lease_time):
    self.expires = int((time.time() + lease_time) * 1e6)
    self.store.AcquireDBSubjectLock(self.subject, self.expires)
    self.locked = True

  def UpdateLease(self, duration):
    self.expires = int((time.time() + duration) * 1e6)
    self.store.UpdateDBSubjectLockLease(self.subject, self.expires)

  def Release(self):
    if self.locked:
      self.store.ReleaseDBSubjectLock(self.subject)
      self.locked = False


class SharedFakeDataStore(SharedFakeDataStoreMixin, data_store.DataStore):
  """Implementation that forwards requests to remote FakeDataStore server."""

  enable_flusher_thread = False

  def DBSubjectLock(self, subject, lease_time=None):
    return SharedFakeDBSubjectLock(self, subject, lease_time=lease_time)
