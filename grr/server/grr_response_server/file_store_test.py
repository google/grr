#!/usr/bin/env python
"""Tests for REL_DB-based file store."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future.builtins import map
from future.builtins import range
from future.builtins import str

import mock

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

    self.client_id = "C.0000111122223333"
    self.client_path = db.ClientPath.OS(self.client_id, ["foo", "bar"])

  def testRaisesIfSingleBlobIsNotFound(self):
    blob_id = rdf_objects.BlobID.FromBlobData("")
    with self.assertRaises(file_store.BlobNotFoundError):
      file_store.AddFileWithUnknownHash(self.client_path, [blob_id])

  def testAddsFileWithSingleBlob(self):
    hash_id = file_store.AddFileWithUnknownHash(self.client_path,
                                                self.blob_ids[:1])
    self.assertEqual(hash_id.AsBytes(), self.blob_ids[0].AsBytes())

  def testRaisesIfOneOfTwoBlobsIsNotFound(self):
    blob_id = rdf_objects.BlobID.FromBlobData("")
    with self.assertRaises(file_store.BlobNotFoundError):
      file_store.AddFileWithUnknownHash(self.client_path,
                                        [self.blob_ids[0], blob_id])

  def testAddsFileWithTwoBlobs(self):
    hash_id = file_store.AddFileWithUnknownHash(self.client_path, self.blob_ids)
    self.assertEqual(
        hash_id.AsBytes(),
        rdf_objects.SHA256HashID.FromData(b"".join(self.blob_data)))

  @mock.patch.object(file_store.EXTERNAL_FILE_STORE, "AddFiles")
  def testAddsFileToExternalFileStore(self, add_file_mock):
    hash_id = file_store.AddFileWithUnknownHash(self.client_path, self.blob_ids)

    add_file_mock.assert_called_once()
    args = add_file_mock.call_args_list[0][0]
    self.assertEqual(args[0][hash_id].client_path, self.client_path)
    blob_ids = [ref.blob_id for ref in args[0][hash_id].blob_refs]
    self.assertEqual(blob_ids, self.blob_ids)


class AddFilesWithUnknownHashesTest(test_lib.GRRBaseTest):

  def testDoesNotFailForEmptyDict(self):
    file_store.AddFilesWithUnknownHashes({})

  def testDoesNotFailForEmptyFiles(self):
    client_id = self.SetupClient(0).Basename()

    paths = []
    for idx in range(100):
      components = ("foo", "bar", str(idx))
      paths.append(db.ClientPath.OS(client_id=client_id, components=components))

    hash_ids = file_store.AddFilesWithUnknownHashes(
        {path: [] for path in paths})

    empty_hash_id = rdf_objects.SHA256HashID.FromData(b"")
    for path in paths:
      self.assertEqual(hash_ids[path], empty_hash_id)

  def testSimpleMultiplePaths(self):
    foo_blobs = [b"foo", b"norf", b"thud"]
    foo_blob_ids = list(map(rdf_objects.BlobID.FromBlobData, foo_blobs))
    foo_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(foo_blobs))
    data_store.BLOBS.WriteBlobs(dict(zip(foo_blob_ids, foo_blobs)))

    bar_blobs = [b"bar", b"quux", b"blargh"]
    bar_blob_ids = list(map(rdf_objects.BlobID.FromBlobData, bar_blobs))
    bar_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(bar_blobs))
    data_store.BLOBS.WriteBlobs(dict(zip(bar_blob_ids, bar_blobs)))

    client_id = self.SetupClient(0).Basename()
    foo_path = db.ClientPath.OS(client_id=client_id, components=("foo",))
    bar_path = db.ClientPath.OS(client_id=client_id, components=("bar",))

    hash_ids = file_store.AddFilesWithUnknownHashes({
        foo_path: foo_blob_ids,
        bar_path: bar_blob_ids,
    })

    self.assertLen(hash_ids, 2)
    self.assertEqual(hash_ids[foo_path], foo_hash_id)
    self.assertEqual(hash_ids[bar_path], bar_hash_id)

  def testSimpleOverlappingBlobIds(self):
    foo_blobs = [b"foo", b"norf", b"quux", b"thud"]
    bar_blobs = [b"bar", b"norf", b"blag", b"thud"]

    foo_blob_ids = list(map(rdf_objects.BlobID.FromBlobData, foo_blobs))
    foo_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(foo_blobs))

    bar_blob_ids = list(map(rdf_objects.BlobID.FromBlobData, bar_blobs))
    bar_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(bar_blobs))

    data_store.BLOBS.WriteBlobs(dict(zip(foo_blob_ids, foo_blobs)))
    data_store.BLOBS.WriteBlobs(dict(zip(bar_blob_ids, bar_blobs)))

    client_id = self.SetupClient(0).Basename()
    foo_path = db.ClientPath.OS(client_id=client_id, components=("foo", "quux"))
    bar_path = db.ClientPath.OS(client_id=client_id, components=("bar", "blag"))

    hash_ids = file_store.AddFilesWithUnknownHashes({
        foo_path: foo_blob_ids,
        bar_path: bar_blob_ids,
    })

    self.assertLen(hash_ids, 2)
    self.assertEqual(hash_ids[foo_path], foo_hash_id)
    self.assertEqual(hash_ids[bar_path], bar_hash_id)

  def testLargeNumberOfPaths(self):
    client_id = self.SetupClient(0).Basename()

    paths = []
    for idx in range(1337):
      components = ("foo", "bar", str(idx))
      paths.append(db.ClientPath.OS(client_id=client_id, components=components))

    blobs = [b"foo", b"bar", b"baz"]
    blob_ids = list(map(rdf_objects.BlobID.FromBlobData, blobs))
    data_store.BLOBS.WriteBlobs(dict(zip(blob_ids, blobs)))

    hash_ids = file_store.AddFilesWithUnknownHashes(
        {path: blob_ids for path in paths})

    expected_hash_id = rdf_objects.SHA256HashID.FromData(b"foobarbaz")
    for path in paths:
      self.assertEqual(hash_ids[path], expected_hash_id)

  def testLargeNumberOfBlobs(self):

    def Blobs(prefix):
      for idx in range(1337):
        yield prefix + str(idx).encode("ascii")

    foo_blobs = list(Blobs(b"foo"))
    foo_blob_ids = list(map(rdf_objects.BlobID.FromBlobData, foo_blobs))
    foo_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(foo_blobs))
    data_store.BLOBS.WriteBlobs(dict(zip(foo_blob_ids, foo_blobs)))

    bar_blobs = list(Blobs(b"bar"))
    bar_blob_ids = list(map(rdf_objects.BlobID.FromBlobData, bar_blobs))
    bar_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(bar_blobs))
    data_store.BLOBS.WriteBlobs(dict(zip(bar_blob_ids, bar_blobs)))

    client_id = self.SetupClient(0).Basename()
    foo_path = db.ClientPath.OS(client_id=client_id, components=("foo",))
    bar_path = db.ClientPath.OS(client_id=client_id, components=("bar",))

    with mock.patch.object(file_store, "_BLOBS_READ_BATCH_SIZE", 42):
      hash_ids = file_store.AddFilesWithUnknownHashes({
          foo_path: foo_blob_ids,
          bar_path: bar_blob_ids,
      })
    self.assertLen(hash_ids, 2)
    self.assertEqual(hash_ids[foo_path], foo_hash_id)
    self.assertEqual(hash_ids[bar_path], bar_hash_id)


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

    self.hash_id = file_store.AddFileWithUnknownHash(self.client_path,
                                                     self.blob_ids[:3])
    self.data = b"".join(self.blob_data[:3])

    self.other_hash_id = file_store.AddFileWithUnknownHash(
        self.client_path, self.blob_ids[3:])
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
          client_path, self.blob_ids[blobs_range[0]:blobs_range[1]])
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
