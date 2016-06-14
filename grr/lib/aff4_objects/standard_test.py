#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.standard."""

import StringIO


import mock

from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import standard as aff4_standard
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths


class BlobImageTest(test_lib.AFF4ObjectTest):
  """Tests for cron functionality."""

  def testAppendContentError(self):
    src_content = "ABCD" * 10
    src_fd = StringIO.StringIO(src_content)

    dest_fd = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("temp"),
        aff4_standard.BlobImage,
        token=self.token,
        mode="rw")
    dest_fd.SetChunksize(7)
    dest_fd.AppendContent(src_fd)
    dest_fd.Seek(0)
    self.assertEqual(dest_fd.Read(5000), src_content)

    src_fd.seek(0)
    self.assertRaises(IOError, dest_fd.AppendContent, src_fd)

  def testAppendContent(self):
    """Test writing content where content length % chunksize == 0."""
    src_content = "ABCDEFG" * 10  # 10 chunksize blobs
    src_fd = StringIO.StringIO(src_content)

    dest_fd = aff4.FACTORY.Create(
        aff4.ROOT_URN.Add("temp"),
        aff4_standard.BlobImage,
        token=self.token,
        mode="rw")
    self.assertEqual(dest_fd.Get(dest_fd.Schema.HASHES), None)

    dest_fd.SetChunksize(7)
    dest_fd.AppendContent(src_fd)

    self.assertEqual(int(dest_fd.Get(dest_fd.Schema.SIZE)), len(src_content))
    self.assertTrue(dest_fd.Get(dest_fd.Schema.HASHES))

    dest_fd.Seek(0)
    self.assertEqual(dest_fd.Read(5000), src_content)

    src_fd.seek(0)
    dest_fd.AppendContent(src_fd)
    self.assertEqual(dest_fd.size, 2 * len(src_content))
    self.assertEqual(
        int(dest_fd.Get(dest_fd.Schema.SIZE)), 2 * len(src_content))
    dest_fd.Seek(0)
    self.assertEqual(dest_fd.Read(5000), src_content + src_content)

  def testMultiStreamStreamsSingleFileWithSingleChunk(self):
    with aff4.FACTORY.Create("aff4:/foo",
                             aff4_type=aff4_standard.BlobImage,
                             token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(StringIO.StringIO("123456789"))

    fd = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    chunks_fds = list(aff4.AFF4Stream.MultiStream([fd]))

    self.assertEqual(len(chunks_fds), 1)
    self.assertEqual(chunks_fds[0][1], "123456789")
    self.assertIs(chunks_fds[0][0], fd)

  def testMultiStreamStreamsSinglfeFileWithTwoChunks(self):
    with aff4.FACTORY.Create("aff4:/foo",
                             aff4_type=aff4_standard.BlobImage,
                             token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(StringIO.StringIO("123456789"))

    with aff4.FACTORY.Create("aff4:/bar",
                             aff4_type=aff4_standard.BlobImage,
                             token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(StringIO.StringIO("abcd"))

    fd1 = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    fd2 = aff4.FACTORY.Open("aff4:/bar", token=self.token)
    chunks_fds = list(aff4.AFF4Stream.MultiStream([fd1, fd2]))

    self.assertEqual(len(chunks_fds), 2)

    self.assertEqual(chunks_fds[0][1], "123456789")
    self.assertIs(chunks_fds[0][0], fd1)

    self.assertEqual(chunks_fds[1][1], "abcd")
    self.assertIs(chunks_fds[1][0], fd2)

  def testMultiStreamStreamsTwoFilesWithTwoChunksInEach(self):
    with aff4.FACTORY.Create("aff4:/foo",
                             aff4_type=aff4_standard.BlobImage,
                             token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(StringIO.StringIO("*" * 10 + "123456789"))

    with aff4.FACTORY.Create("aff4:/bar",
                             aff4_type=aff4_standard.BlobImage,
                             token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(StringIO.StringIO("*" * 10 + "abcd"))

    fd1 = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    fd2 = aff4.FACTORY.Open("aff4:/bar", token=self.token)
    chunks_fds = list(aff4.AFF4Stream.MultiStream([fd1, fd2]))

    self.assertEqual(len(chunks_fds), 4)

    self.assertEqual(chunks_fds[0][1], "*" * 10)
    self.assertIs(chunks_fds[0][0], fd1)

    self.assertEqual(chunks_fds[1][1], "123456789")
    self.assertIs(chunks_fds[1][0], fd1)

    self.assertEqual(chunks_fds[2][1], "*" * 10)
    self.assertIs(chunks_fds[2][0], fd2)

    self.assertEqual(chunks_fds[3][1], "abcd")
    self.assertIs(chunks_fds[3][0], fd2)

  def testMultiStreamReturnsExceptionIfChunkIsMissing(self):
    with aff4.FACTORY.Create("aff4:/foo",
                             aff4_type=aff4_standard.BlobImage,
                             token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(StringIO.StringIO("123456789"))

      fd.index.seek(0)
      blob_id = fd.index.read(fd._HASH_SIZE).encode("hex")

    # TODO(user): here we assume that MemoryStreamBlobstore is
    # used in tests. DeleteBlobs method should be introduced to the
    # BlobStore interface and used here.
    aff4.FACTORY.Delete("aff4:/blobs/" + blob_id, token=self.token)

    fd = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    returned_fd, _, e = list(aff4.AFF4Stream.MultiStream([fd]))[0]
    self.assertNotEqual(e, None)
    self.assertEqual(returned_fd, fd)
    self.assertEqual(e.missing_chunks, [blob_id])

  def testMultiStreamIgnoresTheFileIfAnyChunkIsMissingInReadAheadChunks(self):
    with aff4.FACTORY.Create("aff4:/foo",
                             aff4_type=aff4_standard.BlobImage,
                             token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(StringIO.StringIO("*" * 10 + "123456789"))

      fd.index.seek(0)
      unused_blob_id_1 = fd.index.read(fd._HASH_SIZE).encode("hex")
      blob_id_2 = fd.index.read(fd._HASH_SIZE).encode("hex")

    # TODO(user): here we assume that MemoryStreamBlobstore is
    # used in tests. DeleteBlobs method should be introduced to the
    # BlobStore interface and used here.
    aff4.FACTORY.Delete("aff4:/blobs/" + blob_id_2, token=self.token)

    fd = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    count = 0
    for _, _, e in aff4.AFF4Stream.MultiStream([fd]):
      if not e:
        count += 1

    self.assertEqual(count, 0)

  @mock.patch.object(aff4_standard.BlobImage, "MULTI_STREAM_CHUNKS_READ_AHEAD",
                     1)
  def testMultiStreamTruncatesBigFileIfLastChunkIsMissing(self):
    # If the file is split between 2 batches of chunks, and the missing
    # chunk is in the second batch, the first batch will be succesfully
    # yielded.
    with aff4.FACTORY.Create("aff4:/foo",
                             aff4_type=aff4_standard.BlobImage,
                             token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(StringIO.StringIO("*" * 10 + "123456789"))

      fd.index.seek(0)
      unused_blob_id_1 = fd.index.read(fd._HASH_SIZE).encode("hex")
      blob_id_2 = fd.index.read(fd._HASH_SIZE).encode("hex")

    # TODO(user): here we assume that MemoryStreamBlobstore is
    # used in tests. DeleteBlobs method should be introduced to the
    # BlobStore interface and used here.
    aff4.FACTORY.Delete("aff4:/blobs/" + blob_id_2, token=self.token)

    fd = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    content = []
    error_detected = False
    for fd, chunk, e in aff4.AFF4Stream.MultiStream([fd]):
      if not e:
        content.append(chunk)
      else:
        error_detected = True

    self.assertEqual(content, ["*" * 10])
    self.assertTrue(error_detected)

  @mock.patch.object(aff4_standard.BlobImage, "MULTI_STREAM_CHUNKS_READ_AHEAD",
                     1)
  def testMultiStreamSkipsBigFileIfFirstChunkIsMissing(self):
    # If the file is split between 2 batches of chunks, and the missing
    # chunk is in the first batch, the file will be skipped entirely.
    with aff4.FACTORY.Create("aff4:/foo",
                             aff4_type=aff4_standard.BlobImage,
                             token=self.token) as fd:
      fd.SetChunksize(10)
      fd.AppendContent(StringIO.StringIO("*" * 10 + "123456789"))

      fd.index.seek(0)
      blob_id_1 = fd.index.read(fd._HASH_SIZE).encode("hex")

    # TODO(user): here we assume that MemoryStreamBlobstore is
    # used in tests. DeleteBlobs method should be introduced to the
    # BlobStore interface and used here.
    aff4.FACTORY.Delete("aff4:/blobs/" + blob_id_1, token=self.token)

    fd = aff4.FACTORY.Open("aff4:/foo", token=self.token)
    count = 0
    for _, _, e in aff4.AFF4Stream.MultiStream([fd]):
      if not e:
        count += 1

    self.assertEqual(count, 0)


class LabelSetTest(test_lib.AFF4ObjectTest):

  def testAddListRemoveLabels(self):
    index = aff4.FACTORY.Create("aff4:/index/labels/client_set_test",
                                aff4_standard.LabelSet,
                                mode="rw",
                                token=self.token)
    self.assertListEqual([], index.ListLabels())
    index.Add("label1")
    index.Add("label2")
    self.assertListEqual(["label1", "label2"], sorted(index.ListLabels()))
    index.Remove("label2")
    index.Add("label3")
    self.assertListEqual(["label1", "label3"], sorted(index.ListLabels()))


class AFF4SparseImageTest(test_lib.AFF4ObjectTest):

  def AddBlobToBlobStore(self, blob_contents):
    return data_store.DB.StoreBlob(blob_contents, token=self.token)

  def assertChunkEqual(self, fd, chunk, contents):
    fd.Seek(chunk * fd.chunksize)

    self.assertEqual(fd.Read(len(contents)), contents)

  def testAddChunk(self):
    """Makes sure we can add a chunk and modify it."""

    urn = aff4.ROOT_URN.Add("temp_sparse_image.dd")
    fd = aff4.FACTORY.Create(urn,
                             aff4_type=aff4_standard.AFF4SparseImage,
                             token=self.token,
                             mode="rw")
    fd.Set(fd.Schema._CHUNKSIZE, rdfvalue.RDFInteger(1024))
    fd.chunksize = 1024
    fd.Flush()

    chunk_number = 0
    # 1024 characters.
    blob_contents = "A" * fd.chunksize
    blob_hash = self.AddBlobToBlobStore(blob_contents).decode("hex")

    fd.AddBlob(blob_hash=blob_hash,
               length=len(blob_contents),
               chunk_number=chunk_number)
    fd.Flush()

    # Make sure the size is correct.
    self.assertEqual(fd.size, len(blob_contents))

    self.assertChunkEqual(fd, chunk_number, blob_contents)

    # Change the contents of the blob.
    blob_contents = "B" * fd.chunksize
    blob_hash = self.AddBlobToBlobStore(blob_contents).decode("hex")

    # This time we're updating the blob.
    fd.AddBlob(blob_hash, len(blob_contents), chunk_number=chunk_number)
    # The size shouldn't get any bigger, since we got rid of the old blob.
    self.assertEqual(fd.size, len(blob_contents))

    self.assertChunkEqual(fd, chunk_number, blob_contents)

  def testReadAhead(self):
    """Read a chunk, and test that the next few are in cache."""

    urn = aff4.ROOT_URN.Add("temp_sparse_image.dd")
    fd = aff4.FACTORY.Create(urn,
                             aff4_type=aff4_standard.AFF4SparseImage,
                             token=self.token,
                             mode="rw")
    fd.Set(fd.Schema._CHUNKSIZE, rdfvalue.RDFInteger(1024))
    fd.chunksize = 1024
    fd.Flush()

    start_chunk = 1000
    blob_hashes = []
    blobs = []
    num_chunks = 5
    for chunk in xrange(start_chunk, start_chunk + num_chunks):
      # Make sure the blobs have unique content.
      blob_contents = str(chunk % 10) * fd.chunksize
      blobs.append(blob_contents)
      blob_hash = self.AddBlobToBlobStore(blob_contents).decode("hex")
      fd.AddBlob(blob_hash=blob_hash,
                 length=len(blob_contents),
                 chunk_number=chunk)
      blob_hashes.append(blob_hash)

    self.assertEqual(fd.size, fd.chunksize * num_chunks)

    # Read the first chunk.
    fd.Seek(start_chunk * fd.chunksize)
    fd.Read(fd.chunksize)

    self.assertEqual(len(fd.chunk_cache._hash), num_chunks)

    fd.Flush()
    # They shouldn't be in cache anymore, so the chunk_cache should be empty.
    self.assertFalse(fd.chunk_cache._hash.keys())

    # Make sure the contents of the file are what we put into it.
    fd.Seek(start_chunk * fd.chunksize)
    self.assertEqual(fd.Read(fd.chunksize * num_chunks), "".join(blobs))

  def testReadingAfterLastChunk(self):
    urn = aff4.ROOT_URN.Add("temp_sparse_image.dd")
    fd = aff4.FACTORY.Create(urn,
                             aff4_type=aff4_standard.AFF4SparseImage,
                             token=self.token,
                             mode="rw")
    fd.Set(fd.Schema._CHUNKSIZE, rdfvalue.RDFInteger(1024))
    fd.chunksize = 1024
    fd.Flush()

    # We shouldn't be able to get any chunks yet.
    self.assertFalse(fd.Read(10000))

    start_chunk = 1000
    num_chunks = 5
    for chunk in xrange(start_chunk, start_chunk + num_chunks):
      # Make sure the blobs have unique content.
      blob_contents = str(chunk % 10) * fd.chunksize
      blob_hash = self.AddBlobToBlobStore(blob_contents).decode("hex")
      fd.AddBlob(blob_hash=blob_hash,
                 length=len(blob_contents),
                 chunk_number=chunk)

    # Make sure we can read the chunks we just wrote without error.
    fd.Seek(start_chunk * fd.chunksize)
    fd.Read(num_chunks * fd.chunksize)
    # Seek past the end of our chunks.
    fd.Seek((start_chunk + num_chunks) * fd.chunksize)
    # We should get the empty string back.

    self.assertEqual(fd.Read(10000), "")

    # Seek to before our chunks start.
    fd.Seek((start_chunk - 1) * fd.chunksize)

    # There should be no chunk there and we should raise.
    with self.assertRaises(aff4.ChunkNotFoundError):
      fd.Read(fd.chunksize)


class VFSDirectoryTest(test_lib.AFF4ObjectTest):

  def testRealPathspec(self):

    client_id = rdf_client.ClientURN("C.%016X" % 1234)
    for path in ["a/b", "a/b/c/d"]:
      d = aff4.FACTORY.Create(
          client_id.Add("fs/os").Add(path),
          aff4_type=aff4_standard.VFSDirectory,
          token=self.token)
      pathspec = rdf_paths.PathSpec(path=path,
                                    pathtype=rdf_paths.PathSpec.PathType.OS)
      d.Set(d.Schema.PATHSPEC, pathspec)
      d.Close()

    d = aff4.FACTORY.Create(
        client_id.Add("fs/os").Add("a/b/c"),
        aff4_type=aff4_standard.VFSDirectory,
        mode="rw",
        token=self.token)
    self.assertEqual(d.real_pathspec.CollapsePath(), "a/b/c")


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
