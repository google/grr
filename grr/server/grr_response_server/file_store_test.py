#!/usr/bin/env python
"""Tests for REL_DB-based file store."""

import itertools
from unittest import mock

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server.databases import db
from grr_response_server.models import blobs as models_blobs
from grr_response_server.rdfvalues import mig_objects
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib
from grr.test_lib import vfs_test_lib

POSITIONAL_ARGS = 0
KEYWORD_ARGS = 1


class BlobStreamTest(test_lib.GRRBaseTest):
  """BlobStream tests."""

  def setUp(self):
    super().setUp()

    self.blob_size = 10
    self.blob_data, self.blob_refs = vfs_test_lib.GenerateBlobRefs(
        self.blob_size, "abcde12345"
    )
    blob_ids = [models_blobs.BlobID(ref.blob_id) for ref in self.blob_refs]
    data_store.BLOBS.WriteBlobs(dict(zip(blob_ids, self.blob_data)))

    self.blob_stream = file_store.BlobStream(None, self.blob_refs, None)

  def testRaisesIfBlobIsMissing(self):
    _, missing_blob_refs = vfs_test_lib.GenerateBlobRefs(self.blob_size, "0")
    blob_stream = file_store.BlobStream(None, missing_blob_refs, None)
    with self.assertRaises(file_store.BlobNotFoundError):
      blob_stream.read(1)

  def testReturnsEmptyBytesIfNoBlobs(self):
    blob_stream = file_store.BlobStream(None, [], None)
    self.assertEqual(blob_stream.read(), b"")

  def testReadsFirstByte(self):
    self.assertEqual(self.blob_stream.read(1), b"a")

  def testReadsLastByte(self):
    self.blob_stream.seek(-1, 2)
    self.assertEqual(self.blob_stream.read(1), b"5")

  def testReadsFirstChunkPlusOneByte(self):
    self.assertEqual(
        self.blob_stream.read(self.blob_size + 1), b"a" * self.blob_size + b"b"
    )

  def testReadsLastChunkPlusOneByte(self):
    self.blob_stream.seek(-self.blob_size - 1, 2)
    self.assertEqual(
        self.blob_stream.read(self.blob_size + 1), b"4" + b"5" * self.blob_size
    )

  def testReadsWholeFile(self):
    self.assertEqual(self.blob_stream.read(), b"".join(self.blob_data))

  def testRaisesWhenTryingToReadTooMuchDataAtOnce(self):
    with test_lib.ConfigOverrider({"Server.max_unbound_read_size": 4}):
      # Recreate to make sure the new config option value is applied.
      self.blob_stream = file_store.BlobStream(None, self.blob_refs, None)

      self.blob_stream.read(4)
      with self.assertRaises(file_store.OversizedReadError):
        self.blob_stream.read()  # This would implicitly read 6 bytes.

  def testWhenReadingWholeFileAndWholeFileSizeIsTooBig(self):
    self.blob_stream.read()
    self.blob_stream.seek(0)

    with test_lib.ConfigOverrider(
        {"Server.max_unbound_read_size": self.blob_size * 10 - 1}
    ):
      # Recreate to make sure the new config option value is applied.
      self.blob_stream = file_store.BlobStream(None, self.blob_refs, None)

      with self.assertRaises(file_store.OversizedReadError):
        self.blob_stream.read()

  def testAllowsReadingAboveLimitWhenSpecifiedManually(self):
    with test_lib.ConfigOverrider({"Server.max_unbound_read_size": 1}):
      # Recreate to make sure the new config option value is applied.
      self.blob_stream = file_store.BlobStream(None, self.blob_refs, None)
      self.blob_stream.read(self.blob_size)


class AddFileWithUnknownHashTest(test_lib.GRRBaseTest):
  """Tests for AddFileWithUnknownHash."""

  def setUp(self):
    super().setUp()

    self.blob_size = 10
    self.blob_data, self.blob_refs = vfs_test_lib.GenerateBlobRefs(
        self.blob_size, "abcd"
    )
    blob_ids = [models_blobs.BlobID(ref.blob_id) for ref in self.blob_refs]
    data_store.BLOBS.WriteBlobs(dict(zip(blob_ids, self.blob_data)))

    self.client_id = "C.0000111122223333"
    self.client_path = db.ClientPath.OS(self.client_id, ["foo", "bar"])

  def testAddsFileWithSingleBlob(self):
    hash_id = file_store.AddFileWithUnknownHash(
        self.client_path, self.blob_refs[:1]
    )
    self.assertEqual(hash_id.AsBytes(), self.blob_refs[0].blob_id)

  @mock.patch.object(
      file_store,
      "BLOBS_READ_TIMEOUT",
      rdfvalue.Duration.From(1, rdfvalue.MICROSECONDS),
  )
  def testRaisesIfOneSingleBlobIsNotFound(self):
    blob_ref = rdf_objects.BlobReference(
        offset=0, size=0, blob_id=bytes(models_blobs.BlobID.Of(b""))
    )
    with self.assertRaises(file_store.BlobNotFoundError):
      file_store.AddFileWithUnknownHash(self.client_path, [blob_ref])

  @mock.patch.object(
      file_store,
      "BLOBS_READ_TIMEOUT",
      rdfvalue.Duration.From(1, rdfvalue.MICROSECONDS),
  )
  def testRaisesIfOneOfTwoBlobsIsNotFound(self):
    blob_ref = rdf_objects.BlobReference(
        offset=0, size=0, blob_id=bytes(models_blobs.BlobID.Of(b""))
    )
    with self.assertRaises(file_store.BlobNotFoundError):
      file_store.AddFileWithUnknownHash(
          self.client_path, [self.blob_refs[0], blob_ref]
      )

  def testAddsFileWithTwoBlobs(self):
    hash_id = file_store.AddFileWithUnknownHash(
        self.client_path, self.blob_refs
    )
    self.assertEqual(
        hash_id.AsBytes(),
        rdf_objects.SHA256HashID.FromData(b"".join(self.blob_data)),
    )

  def testFilesWithOneBlobAreStillReadToEnsureBlobExists(self):
    _, long_blob_refs = vfs_test_lib.GenerateBlobRefs(self.blob_size, "cd")
    _, short_blob_refs1 = vfs_test_lib.GenerateBlobRefs(self.blob_size, "a")
    _, short_blob_refs2 = vfs_test_lib.GenerateBlobRefs(self.blob_size, "b")

    path1 = db.ClientPath.OS(self.client_id, ["foo"])
    path2 = db.ClientPath.OS(self.client_id, ["bar"])
    path3 = db.ClientPath.OS(self.client_id, ["baz"])

    # One small file, blob is still read.
    with mock.patch.object(
        data_store.BLOBS, "ReadBlobs", wraps=data_store.BLOBS.ReadBlobs
    ) as p:
      file_store.AddFileWithUnknownHash(path1, short_blob_refs1)
      p.assert_called_once()

    # Same for multiple small files.
    with mock.patch.object(
        data_store.BLOBS, "ReadBlobs", wraps=data_store.BLOBS.ReadBlobs
    ) as p:
      file_store.AddFilesWithUnknownHashes({
          path1: short_blob_refs1,
          path2: short_blob_refs2,
      })
      p.assert_called_once()

    # One large file and two small ones result in a single read for the
    # all three blobs.
    with mock.patch.object(
        data_store.BLOBS, "ReadBlobs", wraps=data_store.BLOBS.ReadBlobs
    ) as p:
      file_store.AddFilesWithUnknownHashes({
          path1: short_blob_refs1,
          path2: short_blob_refs2,
          path3: long_blob_refs,
      })
      p.assert_called_once()
      self.assertLen(p.call_args[POSITIONAL_ARGS], 1)
      self.assertEmpty(p.call_args[KEYWORD_ARGS])
      self.assertCountEqual(
          p.call_args[0][0],
          [
              models_blobs.BlobID(r.blob_id)
              for r in itertools.chain(
                  short_blob_refs1, short_blob_refs2, long_blob_refs
              )
          ],
      )

  @mock.patch.object(file_store.EXTERNAL_FILE_STORE, "AddFiles")
  def testAddsFileToExternalFileStore(self, add_file_mock):
    hash_id = file_store.AddFileWithUnknownHash(
        self.client_path, self.blob_refs
    )

    add_file_mock.assert_called_once()
    args = add_file_mock.call_args_list[0][0]
    self.assertEqual(args[0][hash_id].client_path, self.client_path)
    self.assertEqual(args[0][hash_id].blob_refs, self.blob_refs)


def _BlobRefsFromByteArray(data_array):
  offset = 0
  blob_refs = []
  for data in data_array:
    blob_id = models_blobs.BlobID.Of(data)
    blob_refs.append(
        rdf_objects.BlobReference(
            offset=offset, size=len(data), blob_id=bytes(blob_id)
        )
    )
    offset += len(data)
  return blob_refs


class AddFilesWithUnknownHashesTest(test_lib.GRRBaseTest):

  def testDoesNotFailForEmptyDict(self):
    file_store.AddFilesWithUnknownHashes({})

  def testDoesNotFailForEmptyFiles(self):
    client_id = self.SetupClient(0)

    paths = []
    for idx in range(100):
      components = ("foo", "bar", str(idx))
      paths.append(db.ClientPath.OS(client_id=client_id, components=components))

    hash_ids = file_store.AddFilesWithUnknownHashes(
        {path: [] for path in paths}
    )

    empty_hash_id = rdf_objects.SHA256HashID.FromData(b"")
    for path in paths:
      self.assertEqual(hash_ids[path], empty_hash_id)

  def testSimpleMultiplePaths(self):
    foo_blobs = [b"foo", b"norf", b"thud"]
    foo_blob_refs = _BlobRefsFromByteArray(foo_blobs)
    foo_blob_ids = [models_blobs.BlobID(ref.blob_id) for ref in foo_blob_refs]
    foo_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(foo_blobs))
    data_store.BLOBS.WriteBlobs(dict(zip(foo_blob_ids, foo_blobs)))

    bar_blobs = [b"bar", b"quux", b"blargh"]
    bar_blob_refs = _BlobRefsFromByteArray(bar_blobs)
    bar_blob_ids = [models_blobs.BlobID(ref.blob_id) for ref in bar_blob_refs]
    bar_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(bar_blobs))
    data_store.BLOBS.WriteBlobs(dict(zip(bar_blob_ids, bar_blobs)))

    client_id = self.SetupClient(0)
    foo_path = db.ClientPath.OS(client_id=client_id, components=("foo",))
    bar_path = db.ClientPath.OS(client_id=client_id, components=("bar",))

    hash_ids = file_store.AddFilesWithUnknownHashes({
        foo_path: foo_blob_refs,
        bar_path: bar_blob_refs,
    })

    self.assertLen(hash_ids, 2)
    self.assertEqual(hash_ids[foo_path], foo_hash_id)
    self.assertEqual(hash_ids[bar_path], bar_hash_id)

  def testSimpleOverlappingBlobIds(self):
    foo_blobs = [b"foo", b"norf", b"quux", b"thud"]
    bar_blobs = [b"bar", b"norf", b"blag", b"thud"]

    foo_blob_refs = _BlobRefsFromByteArray(foo_blobs)
    foo_blob_ids = [models_blobs.BlobID(ref.blob_id) for ref in foo_blob_refs]
    foo_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(foo_blobs))

    bar_blob_refs = _BlobRefsFromByteArray(bar_blobs)
    bar_blob_ids = [models_blobs.BlobID(ref.blob_id) for ref in bar_blob_refs]
    bar_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(bar_blobs))

    data_store.BLOBS.WriteBlobs(dict(zip(foo_blob_ids, foo_blobs)))
    data_store.BLOBS.WriteBlobs(dict(zip(bar_blob_ids, bar_blobs)))

    client_id = self.SetupClient(0)
    foo_path = db.ClientPath.OS(client_id=client_id, components=("foo", "quux"))
    bar_path = db.ClientPath.OS(client_id=client_id, components=("bar", "blag"))

    hash_ids = file_store.AddFilesWithUnknownHashes({
        foo_path: foo_blob_refs,
        bar_path: bar_blob_refs,
    })

    self.assertLen(hash_ids, 2)
    self.assertEqual(hash_ids[foo_path], foo_hash_id)
    self.assertEqual(hash_ids[bar_path], bar_hash_id)

  def testLargeNumberOfPaths(self):
    client_id = self.SetupClient(0)

    paths = []
    for idx in range(1337):
      components = ("foo", "bar", str(idx))
      paths.append(db.ClientPath.OS(client_id=client_id, components=components))

    blob_data = [b"foo", b"bar", b"baz"]
    blob_refs = _BlobRefsFromByteArray(blob_data)
    blob_ids = [models_blobs.BlobID(ref.blob_id) for ref in blob_refs]
    data_store.BLOBS.WriteBlobs(dict(zip(blob_ids, blob_data)))

    hash_ids = file_store.AddFilesWithUnknownHashes(
        {path: blob_refs for path in paths}
    )

    expected_hash_id = rdf_objects.SHA256HashID.FromData(b"foobarbaz")
    for path in paths:
      self.assertEqual(hash_ids[path], expected_hash_id)

  def testLargeNumberOfBlobs(self):

    def Blobs(prefix):
      for idx in range(1337):
        yield prefix + str(idx).encode("ascii")

    foo_blobs = list(Blobs(b"foo"))
    foo_blob_refs = _BlobRefsFromByteArray(foo_blobs)
    foo_blob_ids = [models_blobs.BlobID(ref.blob_id) for ref in foo_blob_refs]
    foo_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(foo_blobs))
    data_store.BLOBS.WriteBlobs(dict(zip(foo_blob_ids, foo_blobs)))

    bar_blobs = list(Blobs(b"bar"))
    bar_blob_refs = _BlobRefsFromByteArray(bar_blobs)
    bar_blob_ids = [models_blobs.BlobID(ref.blob_id) for ref in bar_blob_refs]
    bar_hash_id = rdf_objects.SHA256HashID.FromData(b"".join(bar_blobs))
    data_store.BLOBS.WriteBlobs(dict(zip(bar_blob_ids, bar_blobs)))

    client_id = self.SetupClient(0)
    foo_path = db.ClientPath.OS(client_id=client_id, components=("foo",))
    bar_path = db.ClientPath.OS(client_id=client_id, components=("bar",))

    with mock.patch.object(file_store, "_BLOBS_READ_BATCH_SIZE", 42):
      hash_ids = file_store.AddFilesWithUnknownHashes({
          foo_path: foo_blob_refs,
          bar_path: bar_blob_refs,
      })
    self.assertLen(hash_ids, 2)
    self.assertEqual(hash_ids[foo_path], foo_hash_id)
    self.assertEqual(hash_ids[bar_path], bar_hash_id)


class OpenFileTest(test_lib.GRRBaseTest):
  """Tests for OpenFile."""

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))

    blob_size = 10
    blob_data, blob_refs = vfs_test_lib.GenerateBlobRefs(blob_size, "abcdef")
    blob_ids = [models_blobs.BlobID(ref.blob_id) for ref in blob_refs]
    data_store.BLOBS.WriteBlobs(dict(zip(blob_ids, blob_data)))

    blob_data, blob_refs = vfs_test_lib.GenerateBlobRefs(blob_size, "def")
    self.hash_id = file_store.AddFileWithUnknownHash(
        self.client_path, blob_refs
    )
    self.data = b"".join(blob_data)

    _, blob_refs = vfs_test_lib.GenerateBlobRefs(blob_size, "abc")
    self.other_hash_id = file_store.AddFileWithUnknownHash(
        self.client_path, blob_refs
    )

    self.invalid_hash_id = rdf_objects.SHA256HashID.FromData(b"")

  def _PathInfo(self, hash_id=None):
    pi = rdf_objects.PathInfo.OS(components=self.client_path.components)
    if hash_id:
      pi.hash_entry.sha256 = hash_id.AsBytes()
    return pi

  def testOpensFileWithSinglePathInfoWithHash(self):
    data_store.REL_DB.WritePathInfos(
        self.client_id,
        [mig_objects.ToProtoPathInfo(self._PathInfo(self.hash_id))],
    )
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testRaisesForNonExistentFile(self):
    with self.assertRaises(file_store.FileNotFoundError):
      file_store.OpenFile(self.client_path)

  def testRaisesForFileWithSinglePathInfoWithoutHash(self):
    data_store.REL_DB.WritePathInfos(
        self.client_id, [mig_objects.ToProtoPathInfo(self._PathInfo())]
    )
    with self.assertRaises(file_store.FileHasNoContentError):
      file_store.OpenFile(self.client_path)

  def testRaisesForFileWithSinglePathInfoWithUnknownHash(self):
    data_store.REL_DB.WritePathInfos(
        self.client_id,
        [mig_objects.ToProtoPathInfo(self._PathInfo(self.invalid_hash_id))],
    )
    with self.assertRaises(file_store.FileHasNoContentError):
      file_store.OpenFile(self.client_path)

  def testOpensFileWithTwoPathInfosWhereOldestHasHash(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(
        self.client_id,
        [mig_objects.ToProtoPathInfo(self._PathInfo(self.hash_id))],
    )
    # Newest.
    data_store.REL_DB.WritePathInfos(
        self.client_id, [mig_objects.ToProtoPathInfo(self._PathInfo())]
    )
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensFileWithTwoPathInfosWhereNewestHasHash(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(
        self.client_id, [mig_objects.ToProtoPathInfo(self._PathInfo())]
    )
    # Newest.
    data_store.REL_DB.WritePathInfos(
        self.client_id,
        [mig_objects.ToProtoPathInfo(self._PathInfo(self.hash_id))],
    )
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensFileWithTwoPathInfosWhereOldestHashIsUnknown(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(
        self.client_id,
        [mig_objects.ToProtoPathInfo(self._PathInfo(self.invalid_hash_id))],
    )
    # Newest.
    data_store.REL_DB.WritePathInfos(
        self.client_id,
        [mig_objects.ToProtoPathInfo(self._PathInfo(self.hash_id))],
    )
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensFileWithTwoPathInfosWhereNewestHashIsUnknown(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(
        self.client_id,
        [mig_objects.ToProtoPathInfo(self._PathInfo(self.hash_id))],
    )
    # Newest.
    data_store.REL_DB.WritePathInfos(
        self.client_id,
        [mig_objects.ToProtoPathInfo(self._PathInfo(self.invalid_hash_id))],
    )
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)

  def testOpensLatestVersionForPathWithTwoPathInfosWithHashes(self):
    # Oldest.
    data_store.REL_DB.WritePathInfos(
        self.client_id,
        [mig_objects.ToProtoPathInfo(self._PathInfo(self.other_hash_id))],
    )
    # Newest.
    data_store.REL_DB.WritePathInfos(
        self.client_id,
        [mig_objects.ToProtoPathInfo(self._PathInfo(self.hash_id))],
    )
    fd = file_store.OpenFile(self.client_path)
    self.assertEqual(fd.read(), self.data)


class StreamFilesChunksTest(test_lib.GRRBaseTest):
  """Tests for StreamFilesChunks."""

  def _WriteFile(self, client_path, blobs_range=None):
    r_from, r_to = blobs_range or (0, 0)
    blob_data, blob_refs = vfs_test_lib.GenerateBlobRefs(
        self.blob_size, "abcdef"[r_from:r_to]
    )
    vfs_test_lib.CreateFileWithBlobRefsAndData(
        client_path, blob_refs, blob_data
    )

    return blob_data, blob_refs

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)
    self.client_id_other = self.SetupClient(1)

    self.blob_size = 10

  def testStreamsSingleFileWithSingleChunk(self):
    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    blob_data, _ = self._WriteFile(client_path, (0, 1))

    chunks = list(file_store.StreamFilesChunks([client_path]))
    self.assertLen(chunks, 1)
    self.assertEqual(chunks[0].client_path, client_path)
    self.assertEqual(chunks[0].data, blob_data[0])
    self.assertEqual(chunks[0].chunk_index, 0)
    self.assertEqual(chunks[0].total_chunks, 1)
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[0].total_size, self.blob_size)

  def testRaisesIfSingleFileChunkIsMissing(self):
    _, missing_blob_refs = vfs_test_lib.GenerateBlobRefs(self.blob_size, "0")
    missing_blob_refs = list(
        map(mig_objects.ToProtoBlobReference, missing_blob_refs)
    )

    hash_id = rdf_objects.SHA256HashID.FromSerializedBytes(
        missing_blob_refs[0].blob_id
    )
    data_store.REL_DB.WriteHashBlobReferences({hash_id: missing_blob_refs})

    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    path_info = rdf_objects.PathInfo.OS(components=client_path.components)
    path_info.hash_entry.sha256 = hash_id.AsBytes()
    data_store.REL_DB.WritePathInfos(
        client_path.client_id, [mig_objects.ToProtoPathInfo(path_info)]
    )

    # Just getting the generator doesn't raise.
    chunks = file_store.StreamFilesChunks([client_path])
    # Iterating through the generator does actually raise.
    with self.assertRaises(file_store.BlobNotFoundError):
      list(chunks)

  def testStreamsSingleFileWithTwoChunks(self):
    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    blob_data, _ = self._WriteFile(client_path, (0, 2))

    chunks = list(file_store.StreamFilesChunks([client_path]))
    self.assertLen(chunks, 2)

    self.assertEqual(chunks[0].client_path, client_path)
    self.assertEqual(chunks[0].data, blob_data[0])
    self.assertEqual(chunks[0].chunk_index, 0)
    self.assertEqual(chunks[0].total_chunks, 2)
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[0].total_size, self.blob_size * 2)

    self.assertEqual(chunks[1].client_path, client_path)
    self.assertEqual(chunks[1].data, blob_data[1])
    self.assertEqual(chunks[1].chunk_index, 1)
    self.assertEqual(chunks[1].total_chunks, 2)
    self.assertEqual(chunks[1].offset, self.blob_size)
    self.assertEqual(chunks[1].total_size, self.blob_size * 2)

  def testStreamsTwoFilesWithTwoChunksInEach(self):
    client_path_1 = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    blob_data_1, _ = self._WriteFile(client_path_1, (0, 2))

    client_path_2 = db.ClientPath.OS(self.client_id_other, ("foo", "bar"))
    blob_data_2, _ = self._WriteFile(client_path_2, (2, 4))

    chunks = list(file_store.StreamFilesChunks([client_path_1, client_path_2]))
    self.assertLen(chunks, 4)

    self.assertEqual(chunks[0].client_path, client_path_1)
    self.assertEqual(chunks[0].data, blob_data_1[0])
    self.assertEqual(chunks[0].chunk_index, 0)
    self.assertEqual(chunks[0].total_chunks, 2)
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[0].total_size, self.blob_size * 2)

    self.assertEqual(chunks[1].client_path, client_path_1)
    self.assertEqual(chunks[1].data, blob_data_1[1])
    self.assertEqual(chunks[1].chunk_index, 1)
    self.assertEqual(chunks[1].total_chunks, 2)
    self.assertEqual(chunks[1].offset, self.blob_size)
    self.assertEqual(chunks[1].total_size, self.blob_size * 2)

    self.assertEqual(chunks[2].client_path, client_path_2)
    self.assertEqual(chunks[2].data, blob_data_2[0])
    self.assertEqual(chunks[2].chunk_index, 0)
    self.assertEqual(chunks[2].total_chunks, 2)
    self.assertEqual(chunks[2].offset, 0)
    self.assertEqual(chunks[2].total_size, self.blob_size * 2)

    self.assertEqual(chunks[3].client_path, client_path_2)
    self.assertEqual(chunks[3].data, blob_data_2[1])
    self.assertEqual(chunks[3].chunk_index, 1)
    self.assertEqual(chunks[3].total_chunks, 2)
    self.assertEqual(chunks[3].offset, self.blob_size)
    self.assertEqual(chunks[3].total_size, self.blob_size * 2)

  def testIgnoresFileWithoutChunks(self):
    client_path_1 = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    self._WriteFile(client_path_1, None)

    client_path_2 = db.ClientPath.OS(self.client_id_other, ("foo", "bar"))
    blob_data_2, _ = self._WriteFile(client_path_2, (2, 4))

    chunks = list(file_store.StreamFilesChunks([client_path_1, client_path_2]))
    self.assertLen(chunks, 2)

    self.assertEqual(chunks[0].client_path, client_path_2)
    self.assertEqual(chunks[0].data, blob_data_2[0])
    self.assertEqual(chunks[0].chunk_index, 0)
    self.assertEqual(chunks[0].total_chunks, 2)
    self.assertEqual(chunks[0].offset, 0)
    self.assertEqual(chunks[0].total_size, self.blob_size * 2)

    self.assertEqual(chunks[1].client_path, client_path_2)
    self.assertEqual(chunks[1].data, blob_data_2[1])
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

    blob_data_1, _ = self._WriteFile(client_path, (0, 1))
    blob_data_2, _ = self._WriteFile(client_path, (1, 2))

    chunks = list(file_store.StreamFilesChunks([client_path]))
    self.assertLen(chunks, 1)
    self.assertEqual(chunks[0].client_path, client_path)
    self.assertNotEqual(chunks[0].data, blob_data_1[0])
    self.assertEqual(chunks[0].data, blob_data_2[0])

  def testRespectsMaxTimestampWhenStreamingSingleFile(self):
    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))

    blob_data_1, _ = self._WriteFile(client_path, (0, 1))
    timestamp_1 = rdfvalue.RDFDatetime.Now()
    blob_data_2, _ = self._WriteFile(client_path, (1, 2))
    timestamp_2 = rdfvalue.RDFDatetime.Now()

    chunks = list(
        file_store.StreamFilesChunks([client_path], max_timestamp=timestamp_2)
    )
    self.assertLen(chunks, 1)
    self.assertEqual(chunks[0].client_path, client_path)
    self.assertNotEqual(chunks[0].data, blob_data_1[0])
    self.assertEqual(chunks[0].data, blob_data_2[0])

    chunks = list(
        file_store.StreamFilesChunks([client_path], max_timestamp=timestamp_1)
    )
    self.assertLen(chunks, 1)
    self.assertEqual(chunks[0].client_path, client_path)
    self.assertEqual(chunks[0].data, blob_data_1[0])
    self.assertNotEqual(chunks[0].data, blob_data_2[0])

  def testRespectsMaxSizeEqualToOneChunkWhenStreamingSingleFile(self):
    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    blob_data, _ = self._WriteFile(client_path, (0, 2))

    chunks = list(
        file_store.StreamFilesChunks([client_path], max_size=self.blob_size)
    )
    self.assertLen(chunks, 1)
    self.assertEqual(chunks[0].data, blob_data[0])

  def testRespectsMaxSizeGreaterThanOneChunkWhenStreamingSingleFile(self):
    client_path = db.ClientPath.OS(self.client_id, ("foo", "bar"))
    blob_data, _ = self._WriteFile(client_path, (0, 2))

    chunks = list(
        file_store.StreamFilesChunks([client_path], max_size=self.blob_size + 1)
    )
    self.assertLen(chunks, 2)
    self.assertEqual(chunks[0].data, blob_data[0])
    self.assertEqual(chunks[1].data, blob_data[1])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
