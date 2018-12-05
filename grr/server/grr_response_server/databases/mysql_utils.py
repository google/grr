#!/usr/bin/env python
"""Utilities used by the MySQL database."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import contextlib
import functools
import inspect

from grr_response_core.lib import rdfvalue
from grr_response_server import db_utils


# GRR Client IDs are strings of the form "C.<16 hex digits>", our MySQL schema
# uses uint64 values.
def ClientIDToInt(client_id):
  return int(client_id[2:], 16)


def IntToClientID(client_id):
  return "C.%016x" % client_id


def FlowIDToInt(flow_id):
  return int(flow_id or "0", 16)


def IntToFlowID(flow_id):
  return "%08X" % flow_id


def StringToRDFProto(proto_type, value):
  return value if value is None else proto_type.FromSerializedString(value)


# The MySQL driver accepts and returns Python datetime objects.
def MysqlToRDFDatetime(dt):
  return dt if dt is None else rdfvalue.RDFDatetime.FromDatetime(dt)


def RDFDatetimeToMysqlString(rdf):
  if rdf is None:
    return None
  if not isinstance(rdf, rdfvalue.RDFDatetime):
    raise ValueError(
        "time value must be rdfvalue.RDFDatetime, got: %s" % type(rdf))
  return "%s.%06d" % (rdf, rdf.AsMicrosecondsSinceEpoch() % 1000000)


class WithTransaction(object):
  """Decorator that provides a connection or cursor with transaction management.

  Every function decorated @WithTransaction will receive a named 'connection' or
  'cursor' argument.

  If the caller provides a value for the needed parameter, it will be passed
  through without change.

  Otherwise, a connection will be reserved from the pool, a transaction started,
  the decorated function will be called with the missing argument.

  Afterward, the transaction will be committed and the connection returned to
  the pool. Furthermore, if a retryable database error is raised during this
  process, the decorated function may be called again after a short delay.
  """

  def __init__(self, readonly=False):
    """Constructs a decorator.

    Args:
      readonly: Whether the decorated function only requires a readonly
        transaction. Has no effect when a connection is provided.
    """
    self.readonly = readonly

  def __call__(self, func):
    readonly = self.readonly

    takes_args = inspect.getargspec(func).args
    takes_connection = "connection" in takes_args
    takes_cursor = "cursor" in takes_args

    if takes_connection == takes_cursor:
      raise TypeError(
          "@mysql_utils.WithTransaction requires a function to take exactly "
          "one of 'connection', 'cursor', got: %s" % str(takes_args))

    if takes_connection:

      @functools.wraps(func)
      def Decorated(self, *args, **kw):
        """A function decorated by WithTransaction to receive a connection."""
        connection = kw.get("connection", None)
        if connection:
          return func(self, *args, **kw)

        def Closure(connection):
          new_kw = kw.copy()
          new_kw["connection"] = connection
          return func(self, *args, **new_kw)

        return self._RunInTransaction(Closure, readonly)

      return Decorated

    @functools.wraps(func)
    def Decorated(self, *args, **kw):  # pylint: disable=function-redefined
      """A function decorated by WithTransaction to receive a cursor."""
      cursor = kw.get("cursor", None)
      if cursor:
        return func(self, *args, **kw)

      def Closure(connection):
        with contextlib.closing(connection.cursor()) as cursor:
          new_kw = kw.copy()
          new_kw["cursor"] = cursor
          return func(self, *args, **new_kw)

      return self._RunInTransaction(Closure, readonly)

    return db_utils.CallLoggedAndAccounted(Decorated)
