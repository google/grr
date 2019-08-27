#!/usr/bin/env python
"""Tests for the legacy AFF4-based blob store."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from absl import app
from future.moves import queue
import mock

from grr_response_server import blob_store
from grr_response_server import blob_store_test_mixin
from grr_response_server.blob_stores import dual_blob_store
from grr_response_server.databases import mem_blobs
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


def _NoOp(arg):
  del arg  # Unused.


_NOOP_ITEM = None, _NoOp, None


def _StopBackgroundThreads(dual_bs):
  """Stops the background thread that writes to the secondary."""

  # First, indicate that the Thread should get stopped in the next loop cycle.
  dual_bs._thread_running = False

  # Then, unblock _queue.get() to recheck loop condition.
  dual_bs._read_queue.put(_NOOP_ITEM)
  try:
    dual_bs._write_queue.put_nowait(_NOOP_ITEM)
  except queue.Full:
    pass  # At least one entry is in the queue, which triggers the loop cycle.

  # Wait for the background thread to terminate.
  for thread in dual_bs._threads:
    thread.join(timeout=1)

  # In the unlikely case that the background thread exited before entering the
  # loop even once, there is still {} in the queue. Remove all entries in the
  # queue.
  while True:
    try:
      dual_bs._read_queue.get_nowait()
    except queue.Empty:
      break

  while True:
    try:
      dual_bs._write_queue.get_nowait()
    except queue.Empty:
      break


class ArtificialError(Exception):
  pass


def _WaitUntilQueueIsEmpty(dual_bs):
  dual_bs._read_queue.join()
  dual_bs._write_queue.join()


class PrimaryBlobStore(mem_blobs.InMemoryBlobStore):
  pass


class SecondaryBlobStore(mem_blobs.InMemoryBlobStore):
  pass


class DualBlobStoreTest(
    blob_store_test_mixin.BlobStoreTestMixin,
    test_lib.GRRBaseTest,
):

  def CreateBlobStore(self):
    with mock.patch.object(
        blob_store, "REGISTRY", {
            "PrimaryBlobStore": PrimaryBlobStore,
            "SecondaryBlobStore": SecondaryBlobStore
        }):
      bs = dual_blob_store.DualBlobStore("PrimaryBlobStore",
                                         "SecondaryBlobStore")
    return bs, lambda: _StopBackgroundThreads(bs)

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

    self.assertTrue(self.secondary.CheckBlobExists(blob_id))
    self.assertEqual(self.secondary.ReadBlob(blob_id), blob_data)

  def testMultipleBlobsAreWrittenToSecondary(self):
    blob_ids = [rdf_objects.BlobID((b"%d1234567" % i) * 4) for i in range(10)]
    blob_data = [b"a" * i for i in range(10)]

    self.blob_store.WriteBlobs(dict(zip(blob_ids, blob_data)))
    _WaitUntilQueueIsEmpty(self.blob_store.delegate)

    self.assertEqual(
        self.secondary.CheckBlobsExist(blob_ids),
        {blob_id: True for blob_id in blob_ids})
    self.assertEqual(
        self.secondary.ReadBlobs(blob_ids), dict(zip(blob_ids, blob_data)))

  def testWritesToPrimaryAreNotBlockedBySecondary(self):
    _StopBackgroundThreads(self.blob_store.delegate)

    limit = dual_blob_store._SECONDARY_WRITE_QUEUE_MAX_LENGTH + 1
    blob_ids = [
        rdf_objects.BlobID((b"%02d234567" % i) * 4) for i in range(limit)
    ]
    blob_data = [b"a" * i for i in range(limit)]

    self.blob_store.WriteBlobs(dict(zip(blob_ids, blob_data)))
    result = self.blob_store.ReadBlobs(blob_ids)
    self.assertEqual(result, dict(zip(blob_ids, blob_data)))

  def testDiscardedSecondaryWritesAreMeasured(self):
    _StopBackgroundThreads(self.blob_store.delegate)
    self.assertEqual(self.blob_store.delegate._write_queue.qsize(), 0)

    with self.assertStatsCounterDelta(
        0,
        dual_blob_store.DUAL_BLOB_STORE_DISCARD_COUNT,
        fields=["SecondaryBlobStore", "WriteBlobs"]):
      for i in range(dual_blob_store._SECONDARY_WRITE_QUEUE_MAX_LENGTH):
        blob_id = rdf_objects.BlobID((b"%02d234567" % i) * 4)
        blob = b"a" * i
        self.blob_store.WriteBlobs({blob_id: blob})

    self.assertEqual(self.blob_store.delegate._write_queue.qsize(),
                     dual_blob_store._SECONDARY_WRITE_QUEUE_MAX_LENGTH)
    with self.assertStatsCounterDelta(
        3,
        dual_blob_store.DUAL_BLOB_STORE_DISCARD_COUNT,
        fields=["SecondaryBlobStore", "WriteBlobs"]):
      for i in range(3, 6):
        blob_id = rdf_objects.BlobID((b"%02d234567" % i) * 4)
        blob = b"a" * i
        self.blob_store.WriteBlobs({blob_id: blob})

  def testFailingPrimaryWrites(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)

    with mock.patch.object(
        self.primary, "WriteBlobs", autospec=True, side_effect=ArtificialError):
      with self.assertStatsCounterDelta(
          1,
          dual_blob_store.DUAL_BLOB_STORE_ERROR_COUNT,
          fields=["PrimaryBlobStore", "WriteBlobs"]):
        with self.assertRaises(ArtificialError):
          self.blob_store.WriteBlobs({blob_id: b"a"})
    _WaitUntilQueueIsEmpty(self.blob_store.delegate)
    self.assertIsNone(self.blob_store.ReadBlob(blob_id))
    self.assertEqual(self.secondary.ReadBlob(blob_id), b"a")

  def testFailingSecondaryWrites(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)

    with mock.patch.object(
        self.secondary,
        "WriteBlobs",
        autospec=True,
        side_effect=ArtificialError):
      with self.assertStatsCounterDelta(
          1,
          dual_blob_store.DUAL_BLOB_STORE_ERROR_COUNT,
          fields=["SecondaryBlobStore", "WriteBlobs"]):
        self.blob_store.WriteBlobs({blob_id: b"a"})
        _WaitUntilQueueIsEmpty(self.blob_store.delegate)
    self.assertEqual(self.blob_store.ReadBlob(blob_id), b"a")
    self.assertIsNone(self.secondary.ReadBlob(blob_id))

  def assertMethodIsMeasured(self, method, arg):
    latency = dual_blob_store.DUAL_BLOB_STORE_LATENCY
    successes = dual_blob_store.DUAL_BLOB_STORE_SUCCESS_COUNT
    op_size = dual_blob_store.DUAL_BLOB_STORE_OP_SIZE
    primary = ["PrimaryBlobStore", method]
    secondary = ["SecondaryBlobStore", method]
    with self.assertStatsCounterDelta(1, latency, primary), \
         self.assertStatsCounterDelta(1, latency, secondary), \
         self.assertStatsCounterDelta(1, successes, primary), \
         self.assertStatsCounterDelta(1, successes, secondary), \
         self.assertStatsCounterDelta(1, op_size, primary), \
         self.assertStatsCounterDelta(1, op_size, secondary):
      getattr(self.blob_store, method)(arg)
      _WaitUntilQueueIsEmpty(self.blob_store.delegate)

  def testCheckBlobExistsIsMeasured(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    self.assertMethodIsMeasured("CheckBlobExists", blob_id)

  def testCheckBlobsExistIsMeasured(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    self.assertMethodIsMeasured("CheckBlobsExist", [blob_id])

  def testReadBlobsIsMeasured(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    self.assertMethodIsMeasured("ReadBlobs", [blob_id])

  def testReadBlobIsMeasured(self):
    blob_id = rdf_objects.BlobID(b"01234567" * 4)
    self.assertMethodIsMeasured("ReadBlob", blob_id)

  def testBlobStoreLoadsClassNamesFromConfig(self):
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
      _StopBackgroundThreads(bs)

  @mock.patch.object(blob_store, "REGISTRY", {
      "InMemoryBlobStore": mem_blobs.InMemoryBlobStore,
  })
  def testBlobStoreRaisesForMissingConfig(self):
    with test_lib.ConfigOverrider(
        {"DualBlobStore.primary_implementation": "InMemoryBlobStore"}):
      with self.assertRaises(ValueError):
        dual_blob_store.DualBlobStore()

    with test_lib.ConfigOverrider(
        {"DualBlobStore.secondary_implementation": "InMemoryBlobStore"}):
      with self.assertRaises(ValueError):
        dual_blob_store.DualBlobStore()

  @mock.patch.object(blob_store, "REGISTRY", {
      "InMemoryBlobStore": mem_blobs.InMemoryBlobStore,
  })
  def testBlobStoreRaisesForInvalidConfig(self):
    with test_lib.ConfigOverrider({
        "DualBlobStore.primary_implementation": "InMemoryBlobStore",
        "DualBlobStore.secondary_implementation": "invalid"
    }):
      with self.assertRaises(ValueError):
        dual_blob_store.DualBlobStore()

    with test_lib.ConfigOverrider({
        "DualBlobStore.primary_implementation": "invalid",
        "DualBlobStore.secondary_implementation": "InMemoryBlobStore"
    }):
      with self.assertRaises(ValueError):
        dual_blob_store.DualBlobStore()


if __name__ == "__main__":
  app.run(test_lib.main)
