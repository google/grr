#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.standard."""

import hashlib
import StringIO
import zlib


from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib


class BlobImageTest(test_lib.GRRBaseTest):
  """Tests for cron functionality."""

  def testAppendContentError(self):
    src_content = "ABCD" * 10
    src_fd = StringIO.StringIO(src_content)

    dest_fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("temp"),
                                  "BlobImage", token=self.token, mode="rw")
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

    dest_fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("temp"),
                                  "BlobImage", token=self.token, mode="rw")
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
    self.assertEqual(int(dest_fd.Get(dest_fd.Schema.SIZE)),
                     2 * len(src_content))
    dest_fd.Seek(0)
    self.assertEqual(dest_fd.Read(5000), src_content+src_content)


class IndexTest(test_lib.AFF4ObjectTest):

  def testIndexesCreation(self):
    """Check indexes can be created and queried."""
    client1 = aff4.FACTORY.Create("C.0000000000000001", "VFSGRRClient",
                                  mode="w", token=self.token)
    client2 = aff4.FACTORY.Create("C.0000000000000002", "VFSGRRClient",
                                  mode="w", token=self.token)
    client_schema = client1.Schema
    client1.Set(client_schema.HOSTNAME("client1"))
    client1.Flush()
    client2.Set(client_schema.HOSTNAME("client2"))
    client2.Flush()

    index = aff4.FACTORY.Create("aff4:/index/myfirstindex", "AFF4Index",
                                mode="w", token=self.token)
    index.Add(client1.urn, client_schema.LABEL, "test1")
    index.Add(client1.urn, client_schema.LABEL, "test2")
    index.Add(client2.urn, client_schema.LABEL, "extra-test1-extra")
    index.Add(client2.urn, client_schema.LABEL, "test2")
    index.Flush(sync=True)
    index.Close(sync=True)

    # Reopen for querying.
    index = aff4.FACTORY.Open("aff4:/index/myfirstindex", aff4_type="AFF4Index",
                              token=self.token)
    results = list(index.Query([client_schema.LABEL], "test1"))
    self.assertEquals(len(results), 1)

    results = list(index.Query([client_schema.LABEL], ".*test.*"))
    self.assertEquals(len(results), 2)

    results = list(index.Query([client_schema.LABEL], "^test1.*"))
    self.assertEquals(len(results), 1)

    results = list(index.Query([client_schema.LABEL], ".*test1$"))
    self.assertEquals(len(results), 1)

    # Check limit works.
    results = list(index.Query([client_schema.LABEL], ".*test.*", limit=1))
    self.assertEquals(len(results), 1)

  def testIndexesDeletion(self):
    """Check indexes can be created and queried."""
    client1 = aff4.FACTORY.Create("C.0000000000000001", "VFSGRRClient",
                                  mode="w", token=self.token)
    client2 = aff4.FACTORY.Create("C.0000000000000002", "VFSGRRClient",
                                  mode="w", token=self.token)
    client_schema = client1.Schema
    client1.Set(client_schema.HOSTNAME("client1"))
    client1.Flush()
    client2.Set(client_schema.HOSTNAME("client2"))
    client2.Flush()

    index = aff4.FACTORY.Create("aff4:/index/myfirstindex", "AFF4Index",
                                mode="w", token=self.token)
    index.Add(client1.urn, client_schema.LABEL, "test1")
    index.Add(client1.urn, client_schema.LABEL, "test2")
    index.Add(client2.urn, client_schema.LABEL, "test2")
    index.Add(client1.urn, client_schema.LABEL, "test2")
    index.Add(client2.urn, client_schema.LABEL, "test3")
    index.Flush(sync=True)
    index.DeleteAttributeIndexesForURN(client_schema.LABEL, "test1",
                                       client1.urn)
    index.Flush(sync=True)

    results = list(index.Query([client_schema.LABEL], "test1"))
    self.assertEquals(len(results), 0)

    index = aff4.FACTORY.Create("aff4:/index/myfirstindex", "AFF4Index",
                                mode="rw", token=self.token)
    index.DeleteAttributeIndexesForURN(client_schema.LABEL, "test2",
                                       client1.urn)
    index.Flush(sync=True)
    results = list(index.Query([client_schema.LABEL], "test2"))
    self.assertEquals(len(results), 1)


class AFF4SparseImageTest(test_lib.GRRBaseTest):

  def AddBlobToBlobStore(self, blob_contents):

    blob_hash = hashlib.sha256(blob_contents).digest()
    # The compressed blob data.
    cdata = zlib.compress(blob_contents)

    urn = rdfvalue.RDFURN("aff4:/blobs").Add(blob_hash.encode("hex"))

    # Write the blob to the data store. We cheat here and just store the
    # compressed data to avoid recompressing it.
    blob_fd = aff4.FACTORY.Create(urn, "AFF4MemoryStream", mode="w",
                                  token=self.token)
    blob_fd.Set(blob_fd.Schema.CONTENT(cdata))
    blob_fd.Set(blob_fd.Schema.SIZE(len(blob_contents)))
    super(aff4.AFF4MemoryStream, blob_fd).Close(sync=True)

    return blob_hash

  def assertChunkEqual(self, fd, chunk, contents):
    fd.Seek(chunk * fd.chunksize)

    self.assertEqual(fd.Read(len(contents)), contents)

  def testAddChunk(self):
    """Makes sure we can add a chunk and modify it."""

    urn = aff4.ROOT_URN.Add("temp_sparse_image.dd")
    fd = aff4.FACTORY.Create(urn, aff4_type="AFF4SparseImage",
                             token=self.token, mode="rw")
    chunk_number = 0
    # 64*1024 characters.
    blob_contents = "test" * 1024 * 16
    blob_hash = self.AddBlobToBlobStore(blob_contents)

    fd.AddBlob(blob_hash=blob_hash, length=len(blob_contents),
               chunk_number=chunk_number)
    fd.index.seek(0)
    fd.index.read(32)
    fd.Flush()

    # Make sure us and our index have been increased in size properly.
    self.assertEqual(fd.size, len(blob_contents))
    self.assertEqual(fd.index.size, len(blob_hash))

    self.assertChunkEqual(fd, chunk_number, blob_contents)

    # Change the contents of the blob.
    blob_contents = blob_contents.replace("test", "estt")
    blob_hash = self.AddBlobToBlobStore(blob_contents)

    # This time we're updating the blob.
    fd.AddBlob(blob_hash, len(blob_contents), chunk_number=chunk_number)
    # The size shouldn't get any bigger, since we got rid of the old blob.
    self.assertEqual(fd.size, len(blob_contents))
    # Similarly for the index.
    self.assertEqual(fd.index.size, len(blob_hash))

    self.assertChunkEqual(fd, chunk_number, blob_contents)

  def testReadAhead(self):
    """Read a chunk, and test that the next few are in cache."""

    urn = aff4.ROOT_URN.Add("temp_sparse_image.dd")
    fd = aff4.FACTORY.Create(urn, aff4_type="AFF4SparseImage",
                             token=self.token, mode="rw")
    start_chunk = 1000
    blob_hashes = []
    blobs = []
    num_chunks = 5
    for chunk in xrange(start_chunk, start_chunk + num_chunks):
      # Make sure the blobs have unique content.
      blob_contents = str(chunk % 10)*64*1024
      blobs.append(blob_contents)
      blob_hash = self.AddBlobToBlobStore(blob_contents)
      fd.AddBlob(blob_hash=blob_hash, length=len(blob_contents),
                 chunk_number=chunk)
      blob_hashes.append(blob_hash)

    self.assertEqual(fd.size, fd.chunksize * num_chunks)
    self.assertEqual(fd.index.size, fd.index.chunksize * num_chunks)

    # Read the first chunk.
    fd.Seek(start_chunk * fd.chunksize)
    fd.Read(fd.chunksize)

    # The cache will have the chunks, but maybe in a different order, so we use
    # assertItemsEqual here, not assertSequenceEqual.
    self.assertItemsEqual(blob_hashes, fd.chunk_cache._hash.keys())

    fd.Flush()
    # They shouldn't be in cache anymore, so the chunk_cache should be empty.
    self.assertFalse(fd.chunk_cache._hash.keys())

    # Make sure the contents of the file are what we put into it.
    fd.Seek(start_chunk * fd.chunksize)
    self.assertEqual(fd.Read(fd.chunksize * num_chunks),
                     "".join(blobs))

  def testReadingAfterLastChunk(self):
    urn = aff4.ROOT_URN.Add("temp_sparse_image.dd")
    fd = aff4.FACTORY.Create(urn, aff4_type="AFF4SparseImage",
                             token=self.token, mode="rw")

    # We shouldn't be able to get any chunks yet.
    self.assertFalse(fd.Read(10000))

    start_chunk = 1000
    num_chunks = 5
    for chunk in xrange(start_chunk, start_chunk + num_chunks):
      # Make sure the blobs have unique content.
      blob_contents = str(chunk % 10)*64*1024
      blob_hash = self.AddBlobToBlobStore(blob_contents)
      fd.AddBlob(blob_hash=blob_hash, length=len(blob_contents),
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


