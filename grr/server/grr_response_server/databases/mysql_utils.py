#!/usr/bin/env python
"""Utilities used by the MySQL database."""

from collections.abc import Iterable, Sequence
import contextlib
import functools
import hashlib
from typing import Optional, overload

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import precondition
from grr_response_server.databases import db as db_module


def StringToRDFProto(proto_type, value):
  return value if value is None else proto_type.FromSerializedBytes(value)


def Hash(value: str) -> bytes:
  """Calculate a 32 byte cryptographic hash of a unicode string using SHA-256.

  This function allows using arbitrary length strings as primary keys in MySQL.
  Because InnoDB has a 767 bytes size limit, this would not be possible
  otherwise. To keep the result deterministic, do not change the underlying hash
  function.

  Args:
    value: the value to hash.

  Returns:
    32 byte cryptographic hash as bytes.
  """
  encoded = value.encode("utf-8")
  return hashlib.sha256(encoded).digest()


def Placeholders(num: int, values: int = 1) -> str:
  """Returns a string of placeholders for MySQL INSERTs.

  Examples:
    >>> Placeholders(3)
    '(%s, %s, %s)'

    >>> Placeholders(num=3, values=2)
    '(%s, %s, %s), (%s, %s, %s)'

  Args:
    num: The number of %s placeholders for each value.
    values: The number of values to be INSERTed

  Returns:
    a string with `values` comma-separated tuples containing `num`
    comma-separated placeholders each.
  """
  value = "(" + ", ".join(["%s"] * num) + ")"
  return ", ".join([value] * values)


def NamedPlaceholders(iterable: Iterable[str]) -> str:
  """Returns named placeholders from all elements of the given iterable.

  Use this function for VALUES of MySQL INSERTs.

  To account for Iterables with undefined order (dicts before Python 3.6),
  this function sorts column names.

  Examples:
    >>> NamedPlaceholders({"password": "foo", "name": "bar"})
    '(%(name)s, %(password)s)'

  Args:
    iterable: The iterable of strings to be used as placeholder keys.

  Returns:
    A string containing a tuple of comma-separated, sorted, named, placeholders.
  """
  placeholders = ", ".join("%({})s".format(key) for key in sorted(iterable))
  return "({})".format(placeholders)


def Columns(iterable: Iterable[str]) -> str:
  """Returns a string of column names for MySQL INSERTs.

  To account for Iterables with undefined order (dicts before Python 3.6),
  this function sorts column names.

  Examples:
    >>> Columns({"password": "foo", "name": "bar"})
    '(`name`, `password`)'

  Args:
    iterable: The iterable of strings to be used as column names.

  Returns: A string containing a tuple of sorted comma-separated column names.
  """
  columns = sorted(iterable)
  return "({})".format(", ".join("`{}`".format(col) for col in columns))


@overload
def TimestampToRDFDatetime(
    timestamp: int,
) -> rdfvalue.RDFDatetime:
  ...


@overload
def TimestampToRDFDatetime(
    timestamp: None,
) -> None:
  ...


def TimestampToRDFDatetime(timestamp) -> Optional[rdfvalue.RDFDatetime]:
  """Converts MySQL `TIMESTAMP(6)` columns to datetime objects."""
  # TODO(hanuszczak): `timestamp` should be of MySQL type `Decimal`. However,
  # it is unclear where this type is actually defined and how to import it in
  # order to have a type assertion.
  if timestamp is None:
    return None
  else:
    micros = int(1000000 * timestamp)
    return rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(micros)


@overload
def RDFDatetimeToTimestamp(
    datetime: rdfvalue.RDFDatetime,
) -> str:
  ...


@overload
def RDFDatetimeToTimestamp(
    datetime: None,
) -> None:
  ...


def RDFDatetimeToTimestamp(datetime):
  """Converts a datetime object to MySQL `TIMESTAMP(6)` column."""
  if datetime is None:
    return None
  else:
    return "%.6f" % (datetime.AsMicrosecondsSinceEpoch() / 1000000)


def MicrosecondsSinceEpochToTimestamp(microseconds: int) -> str:
  return "%.6f" % (microseconds / 1000000)


def TimestampToMicrosecondsSinceEpoch(timestamp: float) -> int:
  return int(1000000 * timestamp)


def ComponentsToPath(components: Sequence[str]) -> str:
  """Converts a list of path components to a canonical path representation.

  Args:
    components: A sequence of path components.

  Returns:
    A canonical MySQL path representation.
  """
  precondition.AssertIterableType(components, str)
  for component in components:
    if not component:
      raise ValueError("Empty path component in: {}".format(components))

    if "/" in component:
      raise ValueError("Path component with '/' in: {}".format(components))

  if components:
    return "/" + "/".join(components)
  else:
    return ""


def PathToComponents(path: str) -> tuple[str, ...]:
  """Converts a canonical path representation to a list of components.

  Args:
    path: A canonical MySQL path representation.

  Returns:
    A sequence of path components.
  """
  precondition.AssertType(path, str)
  if path and not path.startswith("/"):
    raise ValueError("Path '{}' is not absolute".format(path))

  if path:
    return tuple(path.split("/")[1:])
  else:
    return ()


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

    return Decorated


class RetryableError(db_module.Error):
  """Indicates that a transaction can be retried."""
