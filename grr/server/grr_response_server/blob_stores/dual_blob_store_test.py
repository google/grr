#!/usr/bin/env python
"""Tests for the legacy AFF4-based blob store."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from future.moves import queue
import mock

from grr_response_core.lib.util import compatibility
from grr_response_server import blob_store
from grr_response_server import blob_store_test_mixin
from grr_response_server.blob_stores import dual_blob_store
from grr_response_server.blob_stores import registry_init
from grr_response_server.databases import mem_blobs
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


def _StopBackgroundThread(dual_bs):
  """Stops the background thread that writes to the secondary."""

  # First, indicate that the Thread should get stopped in the next loop cycle.
  dual_bs._thread_running = False

  # Then, unblock _queue.get() to recheck loop condition.
  try:
    dual_bs._queue.put_nowait({})
  except queue.Full:
    pass  # At least one entry is in the queue, which triggers the loop cycle.

  # Wait for the background thread to terminate.
  dual_bs._thread.join(timeout=1)

  # In the unlikely case that the background thread exited before entering the
  # loop even once, there is still {} in the queue. Remove all entries in the
  # queue.
  while True:
    try:
      dual_bs._queue.get_nowait()
    except queue.Empty:
      break


class ArtificialError(Exception):
  pass


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
  def primary(self):
    return self.blob_store.delegate._primary

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
    self.assertEqual(self.blob_store.delegate._queue.qsize(), 0)

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

  def testFailingPrimaryWrites(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)

    with mock.patch.object(
        self.primary, "WriteBlobs", side_effect=ArtificialError):
      with self.assertStatsCounterDelta(
          1,
          "dual_blob_store_error_count",
          fields=["primary", "InMemoryBlobStore"]):
        with self.assertRaises(ArtificialError):

          self.blob_store.WriteBlobs({blob_id: b"a"})
    _WaitUntilQueueIsEmpty(self.blob_store.delegate)
    self.assertIsNone(self.blob_store.ReadBlob(blob_id))
    self.assertEqual(self.secondary.ReadBlob(blob_id), b"a")

  def testFailingSecondaryWrites(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)

    with mock.patch.object(
        self.secondary, "WriteBlobs", side_effect=ArtificialError):
      with self.assertStatsCounterDelta(
          1,
          "dual_blob_store_error_count",
          fields=["secondary", "InMemoryBlobStore"]):
        self.blob_store.WriteBlobs({blob_id: b"a"})
        _WaitUntilQueueIsEmpty(self.blob_store.delegate)
    self.assertEqual(self.blob_store.ReadBlob(blob_id), b"a")
    self.assertIsNone(self.secondary.ReadBlob(blob_id))

  def testBlobStoreLoadsClassNamesFromConfig(self):

    class PrimaryBlobStore(mem_blobs.InMemoryDBBlobsMixin):
      pass

    class SecondaryBlobStore(mem_blobs.InMemoryDBBlobsMixin):
      pass

    with mock.patch.object(
        blob_store, "REGISTRY", {
            "PrimaryBlobStore": PrimaryBlobStore,
            "SecondaryBlobStore": SecondaryBlobStore
        }):
      with test_lib.ConfigOverrider({
          "DualBlobStore.primary_implementation": "PrimaryBlobStore",
          "DualBlobStore.secondary_implementation": "SecondaryBlobStore"
      }):
        bs = dual_blob_store.DualBlobStore()
      self.assertIsInstance(bs._primary, PrimaryBlobStore)
      self.assertIsInstance(bs._secondary, SecondaryBlobStore)
      _StopBackgroundThread(bs)

  def testBlobStoreRaisesForMissingConfig(self):
    with test_lib.ConfigOverrider(
        {"DualBlobStore.primary_implementation": "InMemoryDBBlobsMixin"}):
      with self.assertRaises(ValueError):
        dual_blob_store.DualBlobStore()

    with test_lib.ConfigOverrider(
        {"DualBlobStore.secondary_implementation": "InMemoryDBBlobsMixin"}):
      with self.assertRaises(ValueError):
        dual_blob_store.DualBlobStore()

  def testBlobStoreRaisesForInvalidConfig(self):
    with test_lib.ConfigOverrider({
        "DualBlobStore.primary_implementation": "InMemoryDBBlobsMixin",
        "DualBlobStore.secondary_implementation": "invalid"
    }):
      with self.assertRaises(ValueError):
        dual_blob_store.DualBlobStore()

    with test_lib.ConfigOverrider({
        "DualBlobStore.primary_implementation": "invalid",
        "DualBlobStore.secondary_implementation": "InMemoryDBBlobsMixin"
    }):
      with self.assertRaises(ValueError):
        dual_blob_store.DualBlobStore()


if __name__ == "__main__":
  app.run(test_lib.main)
