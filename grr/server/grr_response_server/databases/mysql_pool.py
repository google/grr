#!/usr/bin/env python
"""Connection pooling for MySQLdb connections."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import threading

import MySQLdb


class Error(Exception):
  pass


class PoolAlreadyClosedError(Error):
  pass


class Pool(object):
  """A Pool of database connections.

  A simple pool, with a maximum number of simultaneous connections. Primary goal
  is to do the right thing when using MySQLdb in obvious ways (our use case),
  but we also try to stay loosely within the PEP-249 standard.

  Intends to be thread safe in that multiple connections can be requested and
  used by multiple threads without synchronization, but operations on each
  connection (and its associated cursors) are assumed to be serial.
  """

  def __init__(self, connect_func, max_size=10):
    """Creates a ConnectionPool.

    Args:
     connect_func: A closure which returns a new connection to the underlying
       database, i.e. a MySQLdb.Connection. Should raise or block if the
       database is unavailable.
     max_size: The maximum number of simultaneous connections.
    """
    self.connect_func = connect_func
    self.limiter = threading.BoundedSemaphore(max_size)
    self.idle_conns = []  # Atomic access only!!
    self.closed = False

  def get(self, blocking=True):
    """Gets a connection.

    Args:
      blocking: Whether to block when max_size connections are already in
        use. If false, may return None.

    Returns:
      A connection to the database.

    Raises:
      PoolAlreadyClosedError: if close() method was already called on
      this pool.
    """
    if self.closed:
      raise PoolAlreadyClosedError("Connection pool is already closed.")

    # NOTE: Once we acquire capacity from the semaphore, it is essential that we
    # return it eventually. On success, this responsibility is delegated to
    # _ConnectionProxy.
    if not self.limiter.acquire(blocking=blocking):
      return None
    c = None
    # pop is atomic, but if we did a check first, it would not be atomic with
    # the pop.
    try:
      c = self.idle_conns.pop()
    except IndexError:
      # Create a connection, release the pool allocation if it fails.
      try:
        c = self.connect_func()
      except Exception:
        self.limiter.release()
        raise
    return _ConnectionProxy(self, c)

  def close(self):
    self.closed = True
    for conn in self.idle_conns:
      conn.close()


class _ConnectionProxy(object):
  """A proxy/wrapper of the underlying database connection object.

  This class exists to return the underlying connection to the pool instead of
  closing it. With the help of _CursorProxy, it does close the underlying
  connection when it may be in an errored state.
  """

  def __init__(self, pool, con):
    self.con = con
    self.pool = pool
    self.errored = False

  def __del__(self):
    if self.con:
      logging.warn("Connection deleted without closing.")
      self.close()

  def close(self):
    if self.con:
      try:
        if not self.errored and not self.pool.closed:
          try:
            self.con.rollback()
            # append is atomic.
            self.pool.idle_conns.append(self.con)
          except Exception:
            # rollback raised and the connection didn't make it into the idle
            # list, so close it.
            self.con.close()
            raise
        else:
          self.con.close()
      finally:
        self.con = None
        self.pool.limiter.release()

  def commit(self):
    self.con.commit()

  def rollback(self):
    self.con.rollback()

  def cursor(self):
    return _CursorProxy(self, self.con.cursor())


class _CursorProxy(object):
  """A proxy/wrapper of an underlying database cursor object.

  This class exists to mark the connection to be closed, instead of returned to
  the pool, when the connection may be broken.
  """

  def __init__(self, con, cursor):
    self.con = con
    self.cursor = cursor

  @property
  def description(self):
    return self.cursor.description

  @property
  def rowcount(self):
    return self.cursor.rowcount

  def close(self):
    self.cursor.close()

  def _forward(self, method, *args, **kwargs):
    try:
      return method(*args, **kwargs)
    except MySQLdb.OperationalError:
      self.con.errored = True
      raise

  def callproc(self, procname, args=()):
    return self._forward(self.cursor.callproc, procname, args=args)

  def execute(self, query, args=None):
    return self._forward(self.cursor.execute, query, args=args)

  def executemany(self, query, args):
    return self._forward(self.cursor.executemany, query, args)

  def fetchone(self):
    return self._forward(self.cursor.fetchone)

  def fetchmany(self, size=None):
    return self._forward(self.cursor.fetchmany, size=size)

  def fetchall(self):
    return self._forward(self.cursor.fetchall)

  @property
  def arraysize(self):
    return self.cursor.arraysize

  @arraysize.setter
  def arraysize(self, size):
    self.cursor.arraysize = size

  def setinputsizes(self, sizes):
    self.cursor.setinputsizes(sizes)

  def setoutputsize(self, size):
    self.cursor.setoutputsize(size)
