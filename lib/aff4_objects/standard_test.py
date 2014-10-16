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
    index.Add(client1.urn, client_schema.LABELS, "test1")
    index.Add(client1.urn, client_schema.LABELS, "test2")
    index.Add(client2.urn, client_schema.LABELS, "extra-test1-extra")
    index.Add(client2.urn, client_schema.LABELS, "test2")
    index.Flush(sync=True)
    index.Close(sync=True)

    # Reopen for querying.
    index = aff4.FACTORY.Open("aff4:/index/myfirstindex", aff4_type="AFF4Index",
                              token=self.token)
    results = list(index.Query([client_schema.LABELS], "test1"))
    self.assertEqual(len(results), 1)

    results = list(index.Query([client_schema.LABELS], ".*test.*"))
    self.assertEqual(len(results), 2)

    results = list(index.Query([client_schema.LABELS], "^test1.*"))
    self.assertEqual(len(results), 1)

    results = list(index.Query([client_schema.LABELS], ".*test1$"))
    self.assertEqual(len(results), 1)

    # Check limit works.
    results = list(index.Query([client_schema.LABELS], ".*test.*", limit=1))
    self.assertEqual(len(results), 1)

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
    index.Add(client1.urn, client_schema.LABELS, "test1")
    index.Add(client1.urn, client_schema.LABELS, "test2")
    index.Add(client2.urn, client_schema.LABELS, "test2")
    index.Add(client1.urn, client_schema.LABELS, "test2")
    index.Add(client2.urn, client_schema.LABELS, "test3")
    index.Flush(sync=True)
    index.DeleteAttributeIndexesForURN(client_schema.LABELS, "test1",
                                       client1.urn)
    index.Flush(sync=True)

    results = list(index.Query([client_schema.LABELS], "test1"))
    self.assertEqual(len(results), 0)

    index = aff4.FACTORY.Create("aff4:/index/myfirstindex", "AFF4Index",
                                mode="rw", token=self.token)
    index.DeleteAttributeIndexesForURN(client_schema.LABELS, "test2",
                                       client1.urn)
    index.Flush(sync=True)
    results = list(index.Query([client_schema.LABELS], "test2"))
    self.assertEqual(len(results), 1)


class AFF4IndexSetTest(test_lib.GRRBaseTest):

  def CreateIndex(self, token=None):
    return aff4.FACTORY.Create("aff4:/index/foo", "AFF4IndexSet",
                               mode="w", token=token)

  def ReadIndex(self, token=None):
    return aff4.FACTORY.Open("aff4:/index/foo", aff4_type="AFF4IndexSet",
                             token=token)

  def testValueAddedToTheIndexIsThenListed(self):
    with self.CreateIndex(token=self.token) as index:
      index.Add("wow")

    index = self.ReadIndex(token=self.token)
    self.assertListEqual(["wow"], list(index.ListValues()))

    with self.CreateIndex(token=self.token) as index:
      index.Add("wow2")

    index = self.ReadIndex(token=self.token)
    self.assertListEqual(["wow", "wow2"], sorted(index.ListValues()))

  def testValuesAddedToTheIndexAreListedBeforeFlushing(self):
    with self.CreateIndex(token=self.token) as index:
      index.Add("wow")
      index.Add("wow2")

      self.assertListEqual(["wow", "wow2"], sorted(index.ListValues()))

  def testValueRemovedFromTheIndexIsNotListed(self):
    with self.CreateIndex(token=self.token) as index:
      index.Add("wow")
      index.Add("wow2")
      index.Add("wow3")

    index = self.ReadIndex(token=self.token)
    self.assertListEqual(["wow", "wow2", "wow3"], sorted(index.ListValues()))

    with self.CreateIndex(token=self.token) as index:
      index.Remove("wow2")

    index = self.ReadIndex(token=self.token)
    self.assertListEqual(["wow", "wow3"], sorted(index.ListValues()))

  def testValueRemovedFromTheIndexIsNotListedBeforeFlushing(self):
    with self.CreateIndex(token=self.token) as index:
      index.Add("wow")
      index.Add("wow2")
      index.Add("wow3")

    index = self.ReadIndex(token=self.token)
    index.Remove("wow2")
    self.assertListEqual(["wow", "wow3"], sorted(index.ListValues()))

  def testValuesAddedAndThenFremovedAreNotListedBeforeFlushing(self):
    with self.CreateIndex(token=self.token) as index:
      index.Add("wow")
      index.Add("wow2")
      index.Add("wow3")
      index.Remove("wow2")

      self.assertListEqual(["wow", "wow3"], sorted(index.ListValues()))


class AFF4LabelsIndexTest(test_lib.GRRBaseTest):

  def CreateIndex(self, token=None):
    return aff4.FACTORY.Create("aff4:/index/labels", "AFF4LabelsIndex",
                               mode="w", token=token)

  def ReadIndex(self, token=None):
    return aff4.FACTORY.Open("aff4:/index/labels", aff4_type="AFF4LabelsIndex",
                             token=token)

  def testIndexSeparatorNotAllowedInLabelName(self):
    self.assertRaises(ValueError, rdfvalue.AFF4ObjectLabel,
                      name=aff4.AFF4LabelsIndex.SEPARATOR)

  def testAddedLabelIsCorrectlyListed(self):
    urn = rdfvalue.RDFURN("aff4:/foo/bar")

    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(urn, "foo", owner="testuser")

    index = self.ReadIndex(token=self.token)
    self.assertListEqual(index.ListUsedLabels(),
                         [rdfvalue.AFF4ObjectLabel(name="foo",
                                                   owner="testuser")])

  def testMultipleLabelsWithDifferentOwnersAreCorrectlyListed(self):
    urn = rdfvalue.RDFURN("aff4:/foo/bar")

    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(urn, "foo", owner="testuser1")
      index.AddLabel(urn, "foo", owner="testuser2")

    index = self.ReadIndex(token=self.token)
    self.assertListEqual(index.ListUsedLabels(),
                         [rdfvalue.AFF4ObjectLabel(name="foo",
                                                   owner="testuser1"),
                          rdfvalue.AFF4ObjectLabel(name="foo",
                                                   owner="testuser2")])

  def testUrnWithAddedLabelCanBeFound(self):
    urn = rdfvalue.RDFURN("aff4:/foo/bar")

    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(urn, "foo", owner="testuser")

    index = self.ReadIndex(token=self.token)
    found_urns = index.FindUrnsByLabel("foo")
    self.assertListEqual(found_urns, [urn])

  def testUrnWithAddedLabelCanBeFoundWithOwnerSpecified(self):
    urn = rdfvalue.RDFURN("aff4:/foo/bar")

    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(urn, "foo", owner="testuser")

    index = self.ReadIndex(token=self.token)

    found_urns = index.FindUrnsByLabel("foo", owner="testuser")
    self.assertListEqual(found_urns, [urn])

  def testUrnsWithAddedLabelNotFoundWithAnotherOwner(self):
    urn = rdfvalue.RDFURN("aff4:/foo/bar")

    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(urn, "foo", owner="testuser")

    index = self.ReadIndex(token=self.token)

    found_urns = index.FindUrnsByLabel("foo", owner="another")
    self.assertFalse(found_urns)

  def testUrnWithAddedLabelCanBeFoundViaLabelRegex(self):
    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar1"),
                     "foo", owner="testuser1")
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar2"),
                     "bar", owner="testuser2")
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar3"),
                     "foo", owner="testuser3")

    index = self.ReadIndex(token=self.token)
    found_urns = index.FindUrnsByLabelNameRegex("f.*o")
    self.assertEqual(len(found_urns), 2)
    self.assertListEqual(
        found_urns[rdfvalue.AFF4ObjectLabel(name="foo", owner="testuser1")],
        [rdfvalue.RDFURN("aff4:/foo/bar1")])
    self.assertListEqual(
        found_urns[rdfvalue.AFF4ObjectLabel(name="foo", owner="testuser3")],
        [rdfvalue.RDFURN("aff4:/foo/bar3")])

  def testUrnWithAddedLabelCanBeFoundViaLabelRegexAndOwner(self):
    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar1"),
                     "foo", owner="testuser1")
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar2"),
                     "bar", owner="testuser2")
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar3"),
                     "foo", owner="testuser3")

    index = self.ReadIndex(token=self.token)
    found_urns = index.FindUrnsByLabelNameRegex("f.*o", owner="testuser3")
    self.assertEqual(len(found_urns), 1)
    self.assertListEqual(
        found_urns[rdfvalue.AFF4ObjectLabel(name="foo", owner="testuser3")],
        [rdfvalue.RDFURN("aff4:/foo/bar3")])

  def testUrnWithAddedLabelNotFoundWithWrongOwner(self):
    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar1"),
                     "foo", owner="testuser1")
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar2"),
                     "bar", owner="testuser2")
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar3"),
                     "foo", owner="testuser3")

    index = self.ReadIndex(token=self.token)
    found_urns = index.FindUrnsByLabelNameRegex("f.*o", owner="another")
    self.assertEqual(len(found_urns), 0)

  def testTimestampInformationIsNotStoredInIndex(self):
    urn = rdfvalue.RDFURN("aff4:/foo/bar")

    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(urn, "foo", owner="user")

    index = self.ReadIndex(token=self.token)
    used_labels = index.ListUsedLabels()
    self.assertEqual(len(used_labels), 1)
    self.assertFalse(used_labels[0].HasField("timestamp"))

  def testOwnerInformationIsStoredInIndex(self):
    urn = rdfvalue.RDFURN("aff4:/foo/bar")

    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(urn, "foo", owner="testuser")

    index = self.ReadIndex(token=self.token)
    used_labels = index.ListUsedLabels()
    self.assertEqual(len(used_labels), 1)
    self.assertEqual("testuser", used_labels[0].owner)

  def testDeletedLabelIsRemovedFromUrnsAndLabelsMapping(self):
    urn = rdfvalue.RDFURN("aff4:/foo/bar")

    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(urn, "foo", owner="testuser")

    index = self.ReadIndex(token=self.token)
    found_urns = index.FindUrnsByLabel("foo")
    self.assertListEqual(found_urns, [urn])

    with self.CreateIndex(token=self.token) as index:
      index.RemoveLabel(urn, "foo", owner="testuser")

    index = self.ReadIndex(token=self.token)
    found_urns = index.FindUrnsByLabel("foo")
    self.assertFalse(found_urns)

  def testDeletedLabelIsNotRemovedFromUsedLabelsList(self):
    label = rdfvalue.AFF4ObjectLabel(name="foo", owner="testuser")
    urn = rdfvalue.RDFURN("aff4:/foo/bar")

    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(urn, "foo", owner="testuser")

    index = self.ReadIndex(token=self.token)
    self.assertListEqual(index.ListUsedLabels(), [label])

    with self.CreateIndex(token=self.token) as index:
      index.RemoveLabel(urn, "foo", owner="testuser")

    index = self.ReadIndex(token=self.token)
    self.assertListEqual(index.ListUsedLabels(), [label])

  def testLabelsWhoseNamesAreSubstringsAreDistinguished1(self):
    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar1"),
                     "foo", owner="testuser1")
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar2"),
                     "foobar", owner="testuser2")

    index = self.ReadIndex(token=self.token)
    found_urns = index.FindUrnsByLabel("foo")
    self.assertEqual(len(found_urns), 1)
    self.assertListEqual(
        found_urns,
        [rdfvalue.RDFURN("aff4:/foo/bar1")])

  def testLabelsWhoseNamesAreSubstringsAreDistinguished2(self):
    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar1"),
                     "foo", owner="testuser1")
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar2"),
                     "barfoobar", owner="testuser2")

    index = self.ReadIndex(token=self.token)
    found_urns = index.FindUrnsByLabel("foo")
    self.assertEqual(len(found_urns), 1)
    self.assertListEqual(
        found_urns,
        [rdfvalue.RDFURN("aff4:/foo/bar1")])

  def testLabelsWhoseNamesAreSubstringsAreDistinguished3(self):
    with self.CreateIndex(token=self.token) as index:
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar1"),
                     "foo", owner="testuser1")
      index.AddLabel(rdfvalue.RDFURN("aff4:/foo/bar2"),
                     "barfoo", owner="testuser2")

    index = self.ReadIndex(token=self.token)
    found_urns = index.FindUrnsByLabel("foo")
    self.assertEqual(len(found_urns), 1)
    self.assertListEqual(
        found_urns,
        [rdfvalue.RDFURN("aff4:/foo/bar1")])


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


class VFSDirectoryTest(test_lib.GRRBaseTest):

  def testRealPathspec(self):

    client_id = rdfvalue.ClientURN("C.%016X" % 1234)
    for path in ["a/b", "a/b/c/d"]:
      d = aff4.FACTORY.Create(client_id.Add("fs/os").Add(path),
                              aff4_type="VFSDirectory",
                              token=self.token)
      pathspec = rdfvalue.PathSpec(path=path,
                                   pathtype=rdfvalue.PathSpec.PathType.OS)
      d.Set(d.Schema.PATHSPEC, pathspec)
      d.Close()

    d = aff4.FACTORY.Create(client_id.Add("fs/os").Add("a/b/c"),
                            aff4_type="VFSDirectory", mode="rw",
                            token=self.token)
    self.assertEqual(d.real_pathspec.CollapsePath(), "a/b/c")
