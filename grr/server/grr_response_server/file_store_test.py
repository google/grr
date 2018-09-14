#!/usr/bin/env python
"""Tests for REL_DB-based file store."""
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_server import data_store
from grr_response_server import db
from grr_response_server import file_store
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib


class BlobStreamTest(test_lib.GRRBaseTest):
  """BlobStream tests."""

  def setUp(self):
    super(BlobStreamTest, self).setUp()

    self.blob_size = 10
    self.blob_data = [c * self.blob_size for c in b"abcde12345"]
    self.blob_ids = [
        rdf_objects.BlobID.FromBlobData(bd) for bd in self.blob_data
    ]
    self.blob_refs = [
        rdf_objects.BlobReference(
            offset=i * self.blob_size, size=self.blob_size, blob_id=blob_id)
        for i, blob_id in enumerate(self.blob_ids)
    ]
    data_store.REL_DB.WriteBlobs(dict(zip(self.blob_ids, self.blob_data)))

    self.blob_stream = file_store.BlobStream(self.blob_refs, None)

  def testReadsFirstByte(self):
    self.assertEqual(self.blob_stream.read(1), b"a")

  def testReadsLastByte(self):
    self.blob_stream.seek(-1, 2)
    self.assertEqual(self.blob_stream.read(1), b"5")

  def testReadsFirstChunkPlusOneByte(self):
    self.assertEqual(
        self.blob_stream.read(self.blob_size + 1), b"a" * self.blob_size + b"b")

  def testReadsLastChunkPlusOneByte(self):
    self.blob_stream.seek(-self.blob_size - 1, 2)
    self.assertEqual(
        self.blob_stream.read(self.blob_size + 1), b"4" + b"5" * self.blob_size)

  def testReadsWholeFile(self):
    self.assertEqual(self.blob_stream.read(), b"".join(self.blob_data))

  def testRaisesWhenTryingToReadTooMuchDataAtOnce(self):
    with test_lib.ConfigOverrider({
        "Server.max_unbound_read_size": self.blob_size
    }):
      # Recreate to make sure the new config option value is applied.
      self.blob_stream = file_store.BlobStream(self.blob_refs, None)

      self.blob_stream.read(self.blob_size)
      with self.assertRaises(file_store.OversizedRead):
        self.blob_stream.read(self.blob_size + 1)

  def testWhenReadingWholeFileAndWholeFileSizeIsTooBig(self):
    self.blob_stream.read()
    self.blob_stream.seek(0)

    with test_lib.ConfigOverrider({
        "Server.max_unbound_read_size": self.blob_size * 10 - 1
    }):
      # Recreate to make sure the new config option value is applied.
      self.blob_stream = file_store.BlobStream(self.blob_refs, None)

      with self.assertRaises(file_store.OversizedRead):
        self.blob_stream.read()


class AddFileWithUnknownHashTest(test_lib.GRRBaseTest):
  """Tests for AddFileWithUnknownHash."""

  def setUp(self):
    super(AddFileWithUnknownHashTest, self).setUp()

    self.blob_size = 10
    self.blob_data = [c * self.blob_size for c in b"ab"]
    self.blob_ids = [
        rdf_objects.BlobID.FromBlobData(bd) for bd in self.blob_data
    ]
    data_store.REL_DB.WriteBlobs(dict(zip(self.blob_ids, self.blob_data)))

  def testRaisesIfSingleBlobIsNotFound(self):
    blob_id = rdf_objects.BlobID.FromBlobData("")
    with self.assertRaises(file_store.BlobNotFound):
      file_store.AddFileWithUnknownHash([blob_id])

  def testAddsFileWithSingleBlob(self):
    hash_id = file_store.AddFileWithUnknownHash(self.blob_ids[:1])
    self.assertEqual(hash_id.AsBytes(), self.blob_ids[0].AsBytes())

  def testRaisesIfOneOfTwoBlobsIsNotFound(self):
    blob_id = rdf_objects.BlobID.FromBlobData("")
    with self.assertRaises(file_store.BlobNotFound):
      file_store.AddFileWithUnknownHash([self.blob_ids[0], blob_id])

  def testAddsFileWithTwoBlobs(self):
    hash_id = file_store.AddFileWithUnknownHash(self.blob_ids)
    self.assertEqual(
        hash_id.AsBytes(),
        rdf_objects.SHA256HashID.FromData(b"".join(self.blob_data)))


class OpenLatestFileVersionTest(test_lib.GRRBaseTest):
  """Tests for OpenLatestFileVersion."""

  def setUp(self):
    super(OpenLatestFileVersionTest, self).setUp()
    self.client_id = self.SetupClient(0).Basename()
    self.client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))

    self.blob_size = 10
    self.blob_data = [c * self.blob_size for c in b"abcdef"]
    self.blob_ids = [
        rdf_objects.BlobID.FromBlobData(bd) for bd in self.blob_data
    ]
    data_store.REL_DB.WriteBlobs(dict(zip(self.blob_ids, self.blob_data)))

    self.hash_id = file_store.AddFileWithUnknownHash(self.blob_ids[:3])
    self.data = b"".join(self.blob_data[:3])

    self.other_hash_id = file_store.AddFileWithUnknownHash(self.blob_ids[3:])
    self.invalid_hash_id = rdf_objects.SHA256HashID.FromData(b"")

  def _PathInfo(self, hash_id=None):
    pi = rdf_objects.PathInfo.OS(components=self.client_path.components)
    if hash_id:
      pi.hash_entry.sha256 = hash_id.AsBytes()
    return pi

  def testOpensFileWithSinglePathInfoWithHash(self):
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.hash_id)])
    fd = file_store.OpenLatestFileVersion(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testRaisesForFileWithSinglePathInfoWithoutHash(self):
    data_store.REL_DB.WritePathInfos(self.client_id, [self._PathInfo()])
    with self.assertRaises(file_store.FileHasNoContent):
      file_store.OpenLatestFileVersion(self.client_path)

  def testRaisesForFileWithSinglePathInfoWithUnknownHash(self):
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.invalid_hash_id)])
    with self.assertRaises(file_store.FileHasNoContent):
      file_store.OpenLatestFileVersion(self.client_path)

  def testOpensFileWithTwoPathInfosWhereOldestHasHash(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.hash_id)])
    # Newest.
    data_store.REL_DB.WritePathInfos(self.client_id, [self._PathInfo()])
    fd = file_store.OpenLatestFileVersion(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensFileWithTwoPathInfosWhereNewestHasHash(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(self.client_id, [self._PathInfo()])
    # Newest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.hash_id)])
    fd = file_store.OpenLatestFileVersion(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensFileWithTwoPathInfosWhereOldestHashIsUnknown(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.invalid_hash_id)])
    # Newest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.hash_id)])
    fd = file_store.OpenLatestFileVersion(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensFileWithTwoPathInfosWhereNewestHashIsUnknown(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.hash_id)])
    # Newest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.invalid_hash_id)])
    fd = file_store.OpenLatestFileVersion(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensLatestVersionForPathWithTwoPathInfosWithHashes(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.other_hash_id)])
    # Newest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.hash_id)])
    fd = file_store.OpenLatestFileVersion(self.client_path)
    self.assertEqual(fd.read(), self.data)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
