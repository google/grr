#!/usr/bin/env python
import os
from typing import Callable
from typing import Optional

from absl.testing import absltest

from grr_response_core.stats import default_stats_collector
from grr_response_core.stats import stats_collector_instance
from grr_response_server import blob_store
from grr_response_server import blob_store_test_mixin
from grr_response_server.blob_stores import encrypted_blob_store
from grr_response_server.databases import mem as mem_db
from grr_response_server.keystore import mem as mem_ks
from grr_response_server.rdfvalues import objects as rdf_objects


def setUpModule() -> None:
  # TODO(hanuszczak): We should have a generic utility for tests that depend on
  # it (and perhaps make it more explicit). Note that we cannot restore the
  # original stats collector in cases there was any set before as it can be set
  # only once in the process lifecycle.
  stats_collector_instance.Set(default_stats_collector.DefaultStatsCollector())


class EncryptedBlobStoreTest(
    blob_store_test_mixin.BlobStoreTestMixin,
    absltest.TestCase,
):
  # Test methods are defined in the base mixin class.

  def CreateBlobStore(
      self) -> tuple[blob_store.BlobStore, Optional[Callable[[], None]]]:
    db = mem_db.InMemoryDB()
    bs = db
    ks = mem_ks.MemKeystore(["foo"])
    return encrypted_blob_store.EncryptedBlobStore(bs, db, ks, "foo"), None

  def testReadBlobUnencrypted(self):
    blob = os.urandom(1024)
    blob_id = rdf_objects.BlobID.FromBlobData(blob)

    db = mem_db.InMemoryDB()
    db.WriteBlobs({blob_id: blob})

    ks = mem_ks.MemKeystore(["foo"])
    bs = encrypted_blob_store.EncryptedBlobStore(db, db, ks, "foo")

    self.assertEqual(bs.ReadBlob(blob_id), blob)

  def testReadBlobEncryptedWithoutKeysRecent(self):
    blob = os.urandom(1024)
    blob_id = rdf_objects.BlobID.FromBlobData(blob)

    db = mem_db.InMemoryDB()
    ks = mem_ks.MemKeystore(["foo"])
    bs = encrypted_blob_store.EncryptedBlobStore(db, db, ks, "foo")

    bs.WriteBlobs({blob_id: blob})
    del db.blob_keys[blob_id]

    # We deleted the key from the database, but blobstore should attempt to
    # decrypt it with the current key.
    self.assertEqual(bs.ReadBlob(blob_id), blob)

  def testReadBlobEncryptedWithoutKeysOutdated(self):
    blob = os.urandom(1024)
    blob_id = rdf_objects.BlobID.FromBlobData(blob)

    db = mem_db.InMemoryDB()
    ks = mem_ks.MemKeystore(["foo", "bar"])

    # First we write blob using the key `foo`.
    bs = encrypted_blob_store.EncryptedBlobStore(db, db, ks, "foo")
    bs.WriteBlobs({blob_id: blob})

    # We swap the active key to be `bar` and delete associated with `foo`.
    bs = encrypted_blob_store.EncryptedBlobStore(db, db, ks, "bar")
    del db.blob_keys[blob_id]

    with self.assertRaises(
        encrypted_blob_store.EncryptedBlobWithoutKeysError) as context:
      bs.ReadBlob(blob_id)

    self.assertEqual(context.exception.blob_id, blob_id)


if __name__ == "__main__":
  absltest.main()
