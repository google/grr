#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.standard."""

import StringIO


from grr.lib import aff4
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
