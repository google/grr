#!/usr/bin/env python
"""Tests for REL_DB-based file store."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
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
    data_store.BLOBS.WriteBlobs(dict(zip(self.blob_ids, self.blob_data)))

    self.blob_stream = file_store.BlobStream(None, self.blob_refs, None)

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
    with test_lib.ConfigOverrider(
        {"Server.max_unbound_read_size": self.blob_size}):
      # Recreate to make sure the new config option value is applied.
      self.blob_stream = file_store.BlobStream(None, self.blob_refs, None)

      self.blob_stream.read(self.blob_size)
      with self.assertRaises(file_store.OversizedReadError):
        self.blob_stream.read(self.blob_size + 1)

  def testWhenReadingWholeFileAndWholeFileSizeIsTooBig(self):
    self.blob_stream.read()
    self.blob_stream.seek(0)

    with test_lib.ConfigOverrider(
        {"Server.max_unbound_read_size": self.blob_size * 10 - 1}):
      # Recreate to make sure the new config option value is applied.
      self.blob_stream = file_store.BlobStream(None, self.blob_refs, None)

      with self.assertRaises(file_store.OversizedReadError):
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
    data_store.BLOBS.WriteBlobs(dict(zip(self.blob_ids, self.blob_data)))

  def testRaisesIfSingleBlobIsNotFound(self):
    blob_id = rdf_objects.BlobID.FromBlobData("")
    with self.assertRaises(file_store.BlobNotFoundError):
      file_store.AddFileWithUnknownHash([blob_id])

  def testAddsFileWithSingleBlob(self):
    hash_id = file_store.AddFileWithUnknownHash(self.blob_ids[:1])
    self.assertEqual(hash_id.AsBytes(), self.blob_ids[0].AsBytes())

  def testRaisesIfOneOfTwoBlobsIsNotFound(self):
    blob_id = rdf_objects.BlobID.FromBlobData("")
    with self.assertRaises(file_store.BlobNotFoundError):
      file_store.AddFileWithUnknownHash([self.blob_ids[0], blob_id])

  def testAddsFileWithTwoBlobs(self):
    hash_id = file_store.AddFileWithUnknownHash(self.blob_ids)
    self.assertEqual(
        hash_id.AsBytes(),
        rdf_objects.SHA256HashID.FromData(b"".join(self.blob_data)))


class OpenFileTest(test_lib.GRRBaseTest):
  """Tests for OpenFile."""

  def setUp(self):
    super(OpenFileTest, self).setUp()
    self.client_id = self.SetupClient(0).Basename()
    self.client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))

    self.blob_size = 10
    self.blob_data = [c * self.blob_size for c in b"abcdef"]
    self.blob_ids = [
        rdf_objects.BlobID.FromBlobData(bd) for bd in self.blob_data
    ]
    data_store.BLOBS.WriteBlobs(dict(zip(self.blob_ids, self.blob_data)))

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
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testRaisesForFileWithSinglePathInfoWithoutHash(self):
    data_store.REL_DB.WritePathInfos(self.client_id, [self._PathInfo()])
    with self.assertRaises(file_store.FileHasNoContentError):
      file_store.OpenFile(self.client_path)

  def testRaisesForFileWithSinglePathInfoWithUnknownHash(self):
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.invalid_hash_id)])
    with self.assertRaises(file_store.FileHasNoContentError):
      file_store.OpenFile(self.client_path)

  def testOpensFileWithTwoPathInfosWhereOldestHasHash(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.hash_id)])
    # Newest.
    data_store.REL_DB.WritePathInfos(self.client_id, [self._PathInfo()])
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensFileWithTwoPathInfosWhereNewestHasHash(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(self.client_id, [self._PathInfo()])
    # Newest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.hash_id)])
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensFileWithTwoPathInfosWhereOldestHashIsUnknown(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.invalid_hash_id)])
    # Newest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.hash_id)])
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensFileWithTwoPathInfosWhereNewestHashIsUnknown(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.hash_id)])
    # Newest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.invalid_hash_id)])
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensLatestVersionForPathWithTwoPathInfosWithHashes(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.other_hash_id)])
    # Newest.
    data_store.REL_DB.WritePathInfos(self.client_id,
                                     [self._PathInfo(self.hash_id)])
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)


class StreamFilesChunksTest(test_lib.GRRBaseTest):
  """Tests for StreamFilesChunks."""

  def _WriteFile(self, client_path, blobs_range=None):
    path_info = rdf_objects.PathInfo.OS(components=client_path.components)

    if blobs_range:
      hash_id = file_store.AddFileWithUnknownHash(
          self.blob_ids[blobs_range[0]:blobs_range[1]])
      path_info.hash_entry.sha256 = hash_id.AsBytes()

    data_store.REL_DB.WritePathInfos(client_path.client_id, [path_info])

  def setUp(self):
    super(StreamFilesChunksTest, self).setUp()
    self.client_id = self.SetupClient(0).Basename()
    self.client_id_other = self.SetupClient(1).Basename()

    self.blob_size = 10
    self.blob_data = [c * self.blob_size for c in b"abcdef"]
    self.blob_ids = [
        rdf_objects.BlobID.FromBlobData(bd) for bd in self.blob_data
    ]
    data_store.BLOBS.WriteBlobs(dict(zip(self.blob_ids, self.blob_data)))

  def testStreamsSingleFileWithSingleChunk(self):
    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    self._WriteFile(client_path, (0, 1))

    chunks = list(file_store.StreamFilesChunks([client_path]))
    self.assertLen(chunks, 1)
    self.assertEqual(chunks[0].client_path, client_path)
    self.assertEqual(chunks[0].data, self.blob_data[0])
    self.assertEqual(chunks[0].chunk_index, 0)
    self.assertEqual(chunks[0].total_chunks, 1)
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[0].total_size, self.blob_size)

  def testStreamsSingleFileWithTwoChunks(self):
    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    self._WriteFile(client_path, (0, 2))

    chunks = list(file_store.StreamFilesChunks([client_path]))
    self.assertLen(chunks, 2)

    self.assertEqual(chunks[0].client_path, client_path)
    self.assertEqual(chunks[0].data, self.blob_data[0])
    self.assertEqual(chunks[0].chunk_index, 0)
    self.assertEqual(chunks[0].total_chunks, 2)
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[0].total_size, self.blob_size * 2)

    self.assertEqual(chunks[1].client_path, client_path)
    self.assertEqual(chunks[1].data, self.blob_data[1])
    self.assertEqual(chunks[1].chunk_index, 1)
    self.assertEqual(chunks[1].total_chunks, 2)
    self.assertEqual(chunks[1].offset, self.blob_size)
    self.assertEqual(chunks[1].total_size, self.blob_size * 2)

  def testStreamsTwoFilesWithTwoChunksInEach(self):
    client_path_1 = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    self._WriteFile(client_path_1, (0, 2))

    client_path_2 = db.ClientPath.OS(self.client_id_other, ("foo", "bar"))
    self._WriteFile(client_path_2, (2, 4))

    chunks = list(file_store.StreamFilesChunks([client_path_1, client_path_2]))
    self.assertLen(chunks, 4)

    self.assertEqual(chunks[0].client_path, client_path_1)
    self.assertEqual(chunks[0].data, self.blob_data[0])
    self.assertEqual(chunks[0].chunk_index, 0)
    self.assertEqual(chunks[0].total_chunks, 2)
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[0].total_size, self.blob_size * 2)

    self.assertEqual(chunks[1].client_path, client_path_1)
    self.assertEqual(chunks[1].data, self.blob_data[1])
    self.assertEqual(chunks[1].chunk_index, 1)
    self.assertEqual(chunks[1].total_chunks, 2)
    self.assertEqual(chunks[1].offset, self.blob_size)
    self.assertEqual(chunks[1].total_size, self.blob_size * 2)

    self.assertEqual(chunks[2].client_path, client_path_2)
    self.assertEqual(chunks[2].data, self.blob_data[2])
    self.assertEqual(chunks[2].chunk_index, 0)
    self.assertEqual(chunks[2].total_chunks, 2)
    self.assertEqual(chunks[2].offset, 0)
    self.assertEqual(chunks[2].total_size, self.blob_size * 2)

    self.assertEqual(chunks[3].client_path, client_path_2)
    self.assertEqual(chunks[3].data, self.blob_data[3])
    self.assertEqual(chunks[3].chunk_index, 1)
    self.assertEqual(chunks[3].total_chunks, 2)
    self.assertEqual(chunks[3].offset, self.blob_size)
    self.assertEqual(chunks[3].total_size, self.blob_size * 2)

  def testIgnoresFileWithoutChunks(self):
    client_path_1 = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    self._WriteFile(client_path_1, None)

    client_path_2 = db.ClientPath.OS(self.client_id_other, ("foo", "bar"))
    self._WriteFile(client_path_2, (2, 4))

    chunks = list(file_store.StreamFilesChunks([client_path_1, client_path_2]))
    self.assertLen(chunks, 2)

    self.assertEqual(chunks[0].client_path, client_path_2)
    self.assertEqual(chunks[0].data, self.blob_data[2])
    self.assertEqual(chunks[0].chunk_index, 0)
    self.assertEqual(chunks[0].total_chunks, 2)
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[0].total_size, self.blob_size * 2)

    self.assertEqual(chunks[1].client_path, client_path_2)
    self.assertEqual(chunks[1].data, self.blob_data[3])
    self.assertEqual(chunks[1].chunk_index, 1)
    self.assertEqual(chunks[1].total_chunks, 2)
    self.assertEqual(chunks[1].offset, self.blob_size)
    self.assertEqual(chunks[1].total_size, self.blob_size * 2)

  def testRespectsClientPathsOrder(self):
    client_path_1 = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    self._WriteFile(client_path_1, (0, 1))

    client_path_2 = db.ClientPath.OS(self.client_id_other, ("foo", "bar"))
    self._WriteFile(client_path_2, (0, 1))

    chunks = list(file_store.StreamFilesChunks([client_path_1, client_path_2]))
    self.assertLen(chunks, 2)
    self.assertEqual(chunks[0].client_path, client_path_1)
    self.assertEqual(chunks[1].client_path, client_path_2)

    # Check that reversing the list of requested client paths reverses the
    # result.
    chunks = list(file_store.StreamFilesChunks([client_path_2, client_path_1]))
    self.assertLen(chunks, 2)
    self.assertEqual(chunks[0].client_path, client_path_2)
    self.assertEqual(chunks[1].client_path, client_path_1)

  def testReadsLatestVersionWhenStreamingWithoutSpecifiedTimestamp(self):
    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))

    self._WriteFile(client_path, (0, 1))
    self._WriteFile(client_path, (1, 2))

    chunks = list(file_store.StreamFilesChunks([client_path]))
    self.assertLen(chunks, 1)
    self.assertEqual(chunks[0].client_path, client_path)
    self.assertEqual(chunks[0].data, self.blob_data[1])

  def testRespectsMaxTimestampWhenStreamingSingleFile(self):
    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))

    self._WriteFile(client_path, (0, 1))
    timestamp_1 = rdfvalue.RDFDatetime.Now()
    self._WriteFile(client_path, (1, 2))
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    chunks = list(
        file_store.StreamFilesChunks([client_path], max_timestamp=timestamp_2))
    self.assertLen(chunks, 1)
    self.assertEqual(chunks[0].client_path, client_path)
    self.assertEqual(chunks[0].data, self.blob_data[1])

    chunks = list(
        file_store.StreamFilesChunks([client_path], max_timestamp=timestamp_1))
    self.assertLen(chunks, 1)
    self.assertEqual(chunks[0].client_path, client_path)
    self.assertEqual(chunks[0].data, self.blob_data[0])

  def testRespectsMaxSizeEqualToOneChunkWhenStreamingSingleFile(self):
    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    self._WriteFile(client_path, (0, 2))

    chunks = list(
        file_store.StreamFilesChunks([client_path], max_size=self.blob_size))
    self.assertLen(chunks, 1)
    self.assertEqual(chunks[0].data, self.blob_data[0])

  def testRespectsMaxSizeGreaterThanOneChunkWhenStreamingSingleFile(self):
    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    self._WriteFile(client_path, (0, 2))

    chunks = list(
        file_store.StreamFilesChunks([client_path],
                                     max_size=self.blob_size + 1))
    self.assertLen(chunks, 2)
    self.assertEqual(chunks[0].data, self.blob_data[0])
    self.assertEqual(chunks[1].data, self.blob_data[1])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
