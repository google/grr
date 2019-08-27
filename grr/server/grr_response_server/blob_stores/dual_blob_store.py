#!/usr/bin/env python
"""A BlobStore proxy that writes to two BlobStores."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import logging
import threading
import time

from future.builtins import str
from future.moves import queue
from typing import Callable, Dict, Iterable, Optional, Text, TypeVar

from grr_response_core import config
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr_response_core.stats import metrics
from grr_response_server import blob_store
from grr_response_server.rdfvalues import objects as rdf_objects

# Maximum queue length, where each queue entry can consist of multiple blobs.
# Thus the number of enqueued blobs can be considerably bigger. This only
# serves as a basic measure to prevent unbounded memory growth.
_SECONDARY_WRITE_QUEUE_MAX_LENGTH = 30


DUAL_BLOB_STORE_LATENCY = metrics.Event(
    "dual_blob_store_latency",
    fields=[("backend_class", str), ("method", str)],
    bins=[0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50])
DUAL_BLOB_STORE_OP_SIZE = metrics.Event(
    "dual_blob_store_op_size",
    fields=[("backend_class", str), ("method", str)],
    bins=[0, 1, 2, 5, 10, 20, 50, 100, 200, 500])
DUAL_BLOB_STORE_SUCCESS_COUNT = metrics.Counter(
    "dual_blob_store_success_count",
    fields=[("backend_class", str), ("method", str)])
DUAL_BLOB_STORE_ERROR_COUNT = metrics.Counter(
    "dual_blob_store_error_count",
    fields=[("backend_class", str), ("method", str)])
DUAL_BLOB_STORE_DISCARD_COUNT = metrics.Counter(
    "dual_blob_store_discard_count",
    fields=[("backend_class", str), ("method", str)])


def _InstantiateBlobStore(name):
  try:
    cls = blob_store.REGISTRY[name]
  except KeyError:
    raise ValueError("No blob store %s found." % name)
  return cls()


I = TypeVar("I")
O = TypeVar("O")


def _MeasureFn(bs, fn, arg):
  """Runs fn(arg) and tracks latency and error metrics."""
  start_time = time.time()
  cls_name = compatibility.GetName(type(bs))
  fn_name = compatibility.GetName(fn)

  # Record the number of BlobIDs given to the current operation, which is either
  # 1 for a single BlobID or the length of the given Sequence/Mapping.
  if isinstance(arg, rdf_objects.BlobID):
    op_size = 1
  else:
    op_size = len(arg)
  DUAL_BLOB_STORE_OP_SIZE.RecordEvent(op_size, fields=[cls_name, fn_name])

  try:
    result = fn(arg)
  except Exception:  # pylint: disable=broad-except
    DUAL_BLOB_STORE_ERROR_COUNT.Increment(fields=[cls_name, fn_name])
    raise

  DUAL_BLOB_STORE_LATENCY.RecordEvent(
      time.time() - start_time, fields=[cls_name, fn_name])
  DUAL_BLOB_STORE_SUCCESS_COUNT.Increment(fields=[cls_name, fn_name])

  return result


def _Enqueue(item_queue, bs, fn, arg):
  try:
    item_queue.put_nowait((bs, fn, arg))
  except queue.Full:
    DUAL_BLOB_STORE_DISCARD_COUNT.Increment(
        fields=[compatibility.GetName(type(bs)),
                compatibility.GetName(fn)])


class DualBlobStore(blob_store.BlobStore):
  """A BlobStore proxy that writes to two BlobStores.

  This class is backed by both a primary and secondary BlobStore. Requests to
  read and write blobs are immediately processed by the primary, return as soon
  as the primary has finished processing, and only raise if the primary raises.

  Additionally, blobs are concurrently, non-blockingly written to the secondary
  from a background thread. If the secondary processes blobs slower than the
  primary, writes are queued and delayed. Writes to the secondary can be
  discarded, if the number of queued writes is too high. Writes to the primary
  are never discarded or delayed.
  """

  def __init__(self,
               primary = None,
               secondary = None):
    """Instantiates a new DualBlobStore and its primary and secondary BlobStore.

    Args:
      primary: The class name of the primary blob store implementation
      secondary: The class name of the secondary blob store implementation
    """
    if primary is None:
      primary = config.CONFIG["DualBlobStore.primary_implementation"]

    if secondary is None:
      secondary = config.CONFIG["DualBlobStore.secondary_implementation"]

    precondition.AssertType(primary, Text)
    precondition.AssertType(secondary, Text)

    self._primary = _InstantiateBlobStore(primary)
    self._secondary = _InstantiateBlobStore(secondary)

    self._write_queue = queue.Queue(_SECONDARY_WRITE_QUEUE_MAX_LENGTH)
    self._read_queue = queue.Queue()

    # Signal that can be set to False from tests to stop the background
    # processing threads.
    self._thread_running = True
    self._threads = []

    self._StartBackgroundThread("DualBlobStore_WriteThread", self._write_queue)
    self._StartBackgroundThread("DualBlobStore_ReadThread", self._read_queue)

  def WriteBlobs(self,
                 blob_id_data_map):
    """Creates or overwrites blobs."""
    _Enqueue(self._write_queue, self._secondary, self._secondary.WriteBlobs,
             dict(blob_id_data_map))
    _MeasureFn(self._primary, self._primary.WriteBlobs, blob_id_data_map)

  def ReadBlobs(self, blob_ids
               ):
    """Reads all blobs, specified by blob_ids, returning their contents."""
    _Enqueue(self._read_queue, self._secondary, self._secondary.ReadBlobs,
             list(blob_ids))
    return _MeasureFn(self._primary, self._primary.ReadBlobs, blob_ids)

  def ReadBlob(self, blob_id):
    """Reads the blob contents, identified by the given BlobID."""
    _Enqueue(self._read_queue, self._secondary, self._secondary.ReadBlob,
             blob_id)
    return _MeasureFn(self._primary, self._primary.ReadBlob, blob_id)

  def CheckBlobExists(self, blob_id):
    """Checks if a blob with a given BlobID exists."""
    _Enqueue(self._read_queue, self._secondary, self._secondary.CheckBlobExists,
             blob_id)
    return _MeasureFn(self._primary, self._primary.CheckBlobExists, blob_id)

  def CheckBlobsExist(self, blob_ids
                     ):
    """Checks if blobs for the given identifiers already exist."""
    _Enqueue(self._read_queue, self._secondary, self._secondary.CheckBlobsExist,
             list(blob_ids))
    return _MeasureFn(self._primary, self._primary.CheckBlobsExist, blob_ids)

  def _StartBackgroundThread(self, thread_name, item_queue):

    def _ThreadLoop():
      while self._thread_running:
        bs, fn, arg = item_queue.get()
        try:
          _MeasureFn(bs, fn, arg)
        except Exception as e:  # pylint: disable=broad-except
          logging.exception(e)
        item_queue.task_done()

    thread = threading.Thread(target=_ThreadLoop, name=thread_name)
    thread.daemon = True
    thread.start()
    self._threads.append(thread)
