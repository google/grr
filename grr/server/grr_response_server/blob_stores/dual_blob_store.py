#!/usr/bin/env python
"""A BlobStore proxy that writes to two BlobStores."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import logging
import threading
import time

from future.moves import queue
from typing import Dict, Iterable, Optional, Text

from grr_response_core import config
from grr_response_core.lib.util import compatibility
from grr_response_core.lib.util import precondition
from grr_response_core.stats import stats_collector_instance
from grr_response_server import blob_store
from grr_response_server.rdfvalues import objects as rdf_objects

# Maximum queue length, where each queue entry can consist of multiple blobs.
# Thus the number of enqueued blobs can be considerably bigger. This only
# serves as a basic measure to prevent unbounded memory growth.
_SECONDARY_WRITE_QUEUE_MAX_LENGTH = 10


def _InstantiateBlobStore(name):
  try:
    cls = blob_store.REGISTRY[name]
  except KeyError:
    raise ValueError("No blob store %s found." % name)
  return cls()


def _WriteBlobs(bs,
                blobs, name):
  """Writes blobs into blob_store and tracks latency and error metrics."""
  start_time = time.time()
  cls_name = compatibility.GetName(type(bs))

  try:
    bs.WriteBlobs(blobs)
  except Exception:  # pylint: disable=broad-except
    stats_collector_instance.Get().IncrementCounter(
        "dual_blob_store_error_count",
        delta=len(blobs),
        fields=[name, cls_name])
    raise

  stats_collector_instance.Get().RecordEvent(
      "dual_blob_store_write_latency",
      time.time() - start_time,
      fields=[name, cls_name])
  stats_collector_instance.Get().IncrementCounter(
      "dual_blob_store_success_count",
      delta=len(blobs),
      fields=[name, cls_name])


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
    self._queue = queue.Queue(_SECONDARY_WRITE_QUEUE_MAX_LENGTH)
    self._thread_running = True
    self._thread = threading.Thread(target=self._WriteBlobsIntoSecondary)
    self._thread.daemon = True
    self._thread.start()

  def WriteBlobs(self,
                 blob_id_data_map):
    """Creates or overwrites blobs."""
    try:
      self._queue.put_nowait(dict(blob_id_data_map))
    except queue.Full:
      stats_collector_instance.Get().IncrementCounter(
          "dual_blob_store_discard_count",
          delta=len(blob_id_data_map),
          fields=["secondary",
                  compatibility.GetName(type(self._secondary))])

    _WriteBlobs(self._primary, blob_id_data_map, "primary")

  def ReadBlobs(self, blob_ids
               ):
    """Reads all blobs, specified by blob_ids, returning their contents."""
    return self._primary.ReadBlobs(blob_ids)

  def ReadBlob(self, blob_id):
    """Reads the blob contents, identified by the given BlobID."""
    return self._primary.ReadBlob(blob_id)

  def CheckBlobExists(self, blob_id):
    """Checks if a blob with a given BlobID exists."""
    return self._primary.CheckBlobExists(blob_id)

  def CheckBlobsExist(self, blob_ids
                     ):
    """Checks if blobs for the given identifiers already exist."""
    return self._primary.CheckBlobsExist(blob_ids)

  def _WriteBlobsIntoSecondary(self):
    """Loops endlessly, writing queued blobs to the secondary."""
    while self._thread_running:
      blobs = self._queue.get()
      try:
        _WriteBlobs(self._secondary, blobs, "secondary")
      except Exception as e:  # pylint: disable=broad-except
        # Failed writes to secondary are not critical, because primary is read
        # from.
        logging.warn(e)
      self._queue.task_done()
