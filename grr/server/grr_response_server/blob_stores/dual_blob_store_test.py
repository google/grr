#!/usr/bin/env python
"""Tests for the legacy AFF4-based blob store."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from future.moves import queue

from grr_response_core.lib.util import compatibility
from grr_response_server import blob_store_test_mixin
from grr_response_server.blob_stores import dual_blob_store
from grr_response_server.blob_stores import registry_init
from grr_response_server.databases import mem_blobs
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


def _StopBackgroundThread(dual_bs):
  """Stops the background thread that writes to the secondary."""
  dual_bs._thread_running = False
  # Unblock _queue.get() to recheck loop condition.
  try:
    dual_bs._queue.put_nowait({})
  except queue.Full:
    pass  # At least one entry is in the queue, which works as well.
  dual_bs._thread.join(timeout=1)


def _WaitUntilQueueIsEmpty(dual_bs):
  dual_bs._queue.join()


class DualBlobStoreTest(
    blob_store_test_mixin.BlobStoreTestMixin,
    test_lib.GRRBaseTest,
):

  @classmethod
  def setUpClass(cls):
    registry_init.RegisterBlobStores()

  def CreateBlobStore(self):
    backing_store_name = compatibility.GetName(mem_blobs.InMemoryBlobStore)
    bs = dual_blob_store.DualBlobStore(backing_store_name, backing_store_name)
    return bs, lambda: _StopBackgroundThread(bs)

  @property
  def secondary(self):
    return self.blob_store.delegate._secondary

  def testSingleBlobIsWrittenToSecondary(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    blob_data = b"abcdef"

    self.blob_store.WriteBlobs({blob_id: blob_data})
    _WaitUntilQueueIsEmpty(self.blob_store.delegate)

    result = self.secondary.ReadBlob(blob_id)
    self.assertEqual(result, blob_data)

  def testMultipleBlobsAreWrittenToSecondary(self):
    blob_ids = [rdf_objects.BlobID((b"%d1234567" % i) * 4) for i in range(10)]
    blob_data = [b"a" * i for i in range(10)]

    self.blob_store.WriteBlobs(dict(zip(blob_ids, blob_data)))
    _WaitUntilQueueIsEmpty(self.blob_store.delegate)

    result = self.secondary.ReadBlobs(blob_ids)
    self.assertEqual(result, dict(zip(blob_ids, blob_data)))

  def testWritesToPrimaryAreNotBlockedBySecondary(self):
    _StopBackgroundThread(self.blob_store.delegate)

    limit = dual_blob_store._SECONDARY_WRITE_QUEUE_MAX_LENGTH + 1
    blob_ids = [
        rdf_objects.BlobID((b"%02d234567" % i) * 4) for i in range(limit)
    ]
    blob_data = [b"a" * i for i in range(limit)]

    self.blob_store.WriteBlobs(dict(zip(blob_ids, blob_data)))
    result = self.blob_store.ReadBlobs(blob_ids)
    self.assertEqual(result, dict(zip(blob_ids, blob_data)))

  def testDiscardedSecondaryWritesAreMeasured(self):
    _StopBackgroundThread(self.blob_store.delegate)

    with self.assertStatsCounterDelta(
        0,
        "dual_blob_store_discard_count",
        fields=["secondary", "InMemoryBlobStore"]):
      for i in range(dual_blob_store._SECONDARY_WRITE_QUEUE_MAX_LENGTH):
        blob_id = rdf_objects.BlobID((b"%02d234567" % i) * 4)
        blob = b"a" * i
        self.blob_store.WriteBlobs({blob_id: blob})

    self.assertEqual(self.blob_store.delegate._queue.qsize(),
                     dual_blob_store._SECONDARY_WRITE_QUEUE_MAX_LENGTH)
    with self.assertStatsCounterDelta(
        3,
        "dual_blob_store_discard_count",
        fields=["secondary", "InMemoryBlobStore"]):
      for i in range(3, 6):
        blob_id = rdf_objects.BlobID((b"%02d234567" % i) * 4)
        blob = b"a" * i
        self.blob_store.WriteBlobs({blob_id: blob})


if __name__ == "__main__":
  app.run(test_lib.main)
