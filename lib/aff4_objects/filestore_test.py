#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.filestore."""

import hashlib

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import filestore


class FakeStore(object):

  def __init__(self, path, token):
    self.dest_file = aff4.FACTORY.Create(aff4.ROOT_URN.Add("temp").Add(path),
                                         "AFF4MemoryStream", mode="rw",
                                         token=token)

  def AddFile(self, unused_blob_fd, sync=False):
    _ = sync
    return self.dest_file


class FileStoreTest(test_lib.GRRBaseTest):
  """Tests for cron functionality."""

  def testFileAdd(self):
    fs = aff4.FACTORY.Open(filestore.FileStore.PATH, "FileStore",
                           token=self.token)
    fake_store1 = FakeStore("1", token=self.token)
    fake_store2 = FakeStore("2", token=self.token)
    fs.OpenChildren = lambda: [fake_store1, fake_store2]

    src_fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("temp").Add("src"),
                                 "BlobImage", token=self.token, mode="rw")
    src_fd.SetChunksize(filestore.FileStore.CHUNK_SIZE)

    blob_contents = []
    for value in ["X", "Y", "Z"]:
      blob = value * filestore.FileStore.CHUNK_SIZE
      blob_contents.append(blob)

      blob_hash = hashlib.sha256(blob).digest()
      blob_urn = rdfvalue.RDFURN("aff4:/blobs").Add(blob_hash.encode("hex"))

      fd = aff4.FACTORY.Create(blob_urn, "AFF4MemoryStream", mode="w",
                               token=self.token)
      fd.Write(blob)
      fd.Close(sync=True)

      src_fd.AddBlob(blob_hash, len(blob))

    src_fd.Close(sync=True)

    src_fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("temp").Add("src"),
                                 "BlobImage", token=self.token, mode="rw")

    src_data = "".join(blob_contents)

    fs.AddFile(src_fd)

    # Reset file pointers
    src_fd.Seek(0)
    fake_store1.dest_file.Seek(0)
    fake_store2.dest_file.Seek(0)

    # Check file content got written to both data stores.
    self.assertEqual(src_data, fake_store1.dest_file.Read(-1))
    self.assertEqual(src_data, fake_store2.dest_file.Read(-1))
