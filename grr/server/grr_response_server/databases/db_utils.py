#!/usr/bin/env python
"""Utility functions/decorators for DB implementations."""
import functools
import logging
import time

from typing import Generic
from typing import List
from typing import Sequence
from typing import Text
from typing import Tuple
from typing import TypeVar

from google.protobuf import any_pb2
from google.protobuf import wrappers_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import precondition
from grr_response_core.stats import metrics
from grr_response_server.databases import db
from grr_response_server.rdfvalues import objects as rdf_objects


_T = TypeVar("_T")


DB_REQUEST_LATENCY = metrics.Event(
    "db_request_latency",
    fields=[("call", str)],
    bins=[0.05 * 1.2**x for x in range(30)])  # 50ms to ~10 secs
DB_REQUEST_ERRORS = metrics.Counter(
    "db_request_errors", fields=[("call", str), ("type", str)])


class Error(Exception):
  pass


class FlowIDIsNotAnIntegerError(Error):
  pass


class OutputPluginIDIsNotAnIntegerError(Error):
  pass


class HuntIDIsNotAnIntegerError(Error):
  pass


def CallLoggedAndAccounted(f):
  """Decorator to log and account for a DB call."""

  @functools.wraps(f)
  def Decorator(*args, **kwargs):
    try:
      start_time = time.time()
      result = f(*args, **kwargs)
      latency = time.time() - start_time

      DB_REQUEST_LATENCY.RecordEvent(latency, fields=[f.__name__])
      logging.debug("DB request %s SUCCESS (%.3fs)", f.__name__, latency)

      return result
    except db.Error as e:
      DB_REQUEST_ERRORS.Increment(fields=[f.__name__, "grr"])
      logging.debug("DB request %s GRR ERROR: %s", f.__name__,
                    utils.SmartUnicode(e))
      raise
    except Exception as e:
      DB_REQUEST_ERRORS.Increment(fields=[f.__name__, "db"])
      logging.debug("DB request %s INTERNAL DB ERROR : %s", f.__name__,
                    utils.SmartUnicode(e))
      raise

  return Decorator


def EscapeWildcards(string: Text) -> Text:
  """Escapes wildcard characters for strings intended to be used with `LIKE`.

  Databases don't automatically escape wildcard characters ('%', '_'), so any
  non-literal string that is passed to `LIKE` and is expected to match literally
  has to be manually escaped.

  Args:
    string: A string to escape.

  Returns:
    An escaped string.
  """
  precondition.AssertType(string, Text)
  return string.replace("%", r"\%").replace("_", r"\_")


def EscapeBackslashes(string: Text) -> Text:
  """Escapes backslash characters for strings intended to be used with `LIKE`.

  Backslashes work in mysterious ways: sometimes they do need to be escaped,
  sometimes this is being done automatically when passing values. Combined with
  unclear rules of `LIKE`, this can be very confusing.

  https://what.thedailywtf.com/topic/13989/mysql-backslash-escaping

  Args:
    string: A string to escape.

  Returns:
    An escaped string.
  """
  precondition.AssertType(string, Text)
  return string.replace("\\", "\\\\")


def ClientIdFromGrrMessage(m):
  if m.queue:
    return m.queue.Split()[0]
  if m.source:
    return m.source.Basename()


# GRR Client IDs are strings of the form "C.<16 hex digits>", our F1 schema
# uses uint64 values.
def ClientIDToInt(client_id):
  if client_id[:2] != "C.":
    raise ValueError("Malformed client id received: %s" % client_id)
  return int(client_id[2:], 16)


def IntToClientID(client_id):
  return "C.%016x" % client_id


def FlowIDToInt(flow_id):
  try:
    return int(flow_id or "0", 16)
  except ValueError as e:
    raise FlowIDIsNotAnIntegerError(e)


def IntToFlowID(flow_id):
  # Stringify legacy IDs (32-bit) to 8 characters to allow string equality
  # comparison, otherwise "11111111" would be != "0000000011111111", but both
  # represent the same actual number 0x11111111.
  if flow_id <= 0xFFFFFFFF:
    return "{:08X}".format(flow_id)
  else:
    return "{:016X}".format(flow_id)


def HuntIDToInt(hunt_id):
  """Convert hunt id string to an integer."""
  # TODO(user): This code is only needed for a brief period of time when we
  # allow running new rel-db flows with old aff4-based hunts. In this scenario
  # parent_hunt_id is effectively not used, but it has to be an
  # integer. Stripping "H:" from hunt ids then makes the rel-db happy. Remove
  # this code when hunts are rel-db only.
  if hunt_id.startswith("H:"):
    hunt_id = hunt_id[2:]

  try:
    return int(hunt_id or "0", 16)
  except ValueError as e:
    raise HuntIDIsNotAnIntegerError(e)


def IntToHuntID(hunt_id):
  return IntToFlowID(hunt_id)


def OutputPluginIDToInt(output_plugin_id):
  try:
    return int(output_plugin_id or "0", 16)
  except ValueError as e:
    raise OutputPluginIDIsNotAnIntegerError(e)


def IntToOutputPluginID(output_plugin_id):
  return "%08X" % output_plugin_id


def CronJobRunIDToInt(cron_job_run_id):
  if cron_job_run_id is None:
    return None
  else:
    return int(cron_job_run_id, 16)


def IntToCronJobRunID(cron_job_run_id):
  if cron_job_run_id is None:
    return None
  else:
    return "%08X" % cron_job_run_id


def SecondsToMicros(seconds):
  return int(seconds * 1e6)


def MicrosToSeconds(ms):
  return ms / 1e6


def ParseAndUnpackAny(payload_type: str,
                      payload_bytes: bytes) -> rdf_structs.RDFProtoStruct:
  """Parses a google.protobuf.Any payload and unpack it into RDFProtoStruct.

  Args:
    payload_type: RDF type of the value to unpack.
    payload_bytes: serialized google.protobuf.Any proto.

  Returns:
    An instance of RDFProtoStruct unpacked from the given payload or,
    if payload type is not recognized, an instance of
    SerializedValueOfUnrecognizedType.
  """
  any_proto = any_pb2.Any.FromString(payload_bytes)

  if any_proto.type_url == _BYTES_VALUE_TYPE_URL:
    bytes_value_proto = wrappers_pb2.BytesValue()
    any_proto.Unpack(bytes_value_proto)

    payload_value_bytes = bytes_value_proto.value
  else:
    payload_value_bytes = any_proto.value

  if payload_type not in rdfvalue.RDFValue.classes:
    return rdf_objects.SerializedValueOfUnrecognizedType(
        type_name=payload_type, value=payload_value_bytes)

  rdf_class = rdfvalue.RDFValue.classes[payload_type]
  return rdf_class.FromSerializedBytes(payload_value_bytes)


class BatchPlanner(Generic[_T]):
  """Helper class to batch operations based on affected rows limit.

  Typical example: batching delete operations. Database backends
  often have limits on number of rows to be modified within
  a single transaction. These can be hard limits imposed by the DB
  design or practical limits that have to be respected for optimal
  performance. In order to work around such a limit, we want
  to batch multiple delete operations (each affecting a certain number
  of rows) into batches in such a way so that every batch will
  affect less total rows than the limit.
  """

  # TODO: as soon as GRR is fully Python 3.7, this should
  # be replaced with a generic NamedTuple. Unfortunately, Python 3.6
  # has issues with NamedTuples and generics. See:
  # https://stackoverflow.com/questions/50530959/generic-namedtuple-in-python-3-6
  BatchPart = Tuple[_T, int, int]  # pylint: disable=invalid-name
  Batch = Sequence[BatchPart]  # pylint: disable=invalid-name

  def __init__(self, limit: int):
    """Constructor.

    Args:
      limit: Maximum limit of rows that an operation can be performed on in a
        single batch.
    """
    self._limit = limit

    self._current_batch: List[BatchPlanner[_T].BatchPart] = []
    self._current_batch_size = 0

    self._batches: List[BatchPlanner[_T].Batch] = []

  def _PlanOperation(self, key: _T, offset: int, count: int) -> int:
    """An utility method to plan a single operation.

    Args:
      key: Any value identifying a group of rows that an operation should be be
        performed on.
      offset: How many entities were previously planned for this operation.
      count: Total number of entities that will be planend for this operation.

    Returns:
      offset + [number of newly planned] entities.
    """

    # _current_batch is used as a rolling buffer.
    #
    # If the operation is going to overflow the _current_batch, we effectively
    # split the operation in two, finalize the _current_batch and add it to the
    # list of planned batches.
    #
    # What's left from the operation will then be passed to _PlanOperation
    # again by the PlanOperation() code.
    if self._current_batch_size + count > self._limit:
      delta = self._limit - self._current_batch_size
      self._current_batch.append((key, offset, delta))

      self._batches.append(self._current_batch)
      self._current_batch = []
      self._current_batch_size = 0

      return offset + delta
    else:
      # If the _current_batch has capacity for all the elements in the
      # operation, add it to _current_batch.
      self._current_batch.append((key, offset, count))
      self._current_batch_size += count
      return offset + count

  def PlanOperation(self, key: _T, count: int) -> None:
    """Plans an operation on a given number of entities identified by a key.

    After all operations are planned, "batches" property can be used to
    get a sequence of batches of operations where every batch would be
    within the limit passed to the contstructor.

    Args:
      key: Any value identifying a group of rows that an operation should be be
        performed on. For example, when deleting responses, a key may be
        (client_id, flow_id, request_id).
      count: Number of entities that the operation should be performed on.
    """
    offset = 0
    while offset < count:
      offset = self._PlanOperation(key, offset, count - offset)

  @property
  def batches(self) -> Sequence[Batch]:
    """Returns a list of batches built to stay within the operation limit.

    Each batch is made of tuples (key, offset, count) where key identifies
    the group of rows for an operation to be performed on and matches
    a key passed via one of PlanOperation() calls. Offset and count
    identify the range of items corresponding to the key to be
    affected by the operation.

    Total number of rows in a single batch is guaranteed to be less
    than a limit (passed as a constructor argument).
    """

    if self._current_batch:
      result = self._batches[:]
      result.append(self._current_batch)
      return result

    return self._batches


_BYTES_VALUE_TYPE_URL = f"type.googleapis.com/{wrappers_pb2.BytesValue.DESCRIPTOR.full_name}"
