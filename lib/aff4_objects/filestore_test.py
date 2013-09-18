#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.filestore."""

import StringIO

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import filestore


class FakeStore(object):
  PRIORITY = 99
  PATH = rdfvalue.RDFURN("aff4:/files/temp")

  def __init__(self, path, token):
    self.dest_file = aff4.FACTORY.Create(path, "AFF4MemoryStream",
                                         mode="rw", token=token)

  def AddFile(self, unused_blob_fd, sync=False):
    _ = sync
    return self.dest_file

  def Get(self, _):
    return True

  class Schema(object):
    ACTIVE = "unused"


class FileStoreTest(test_lib.GRRBaseTest):
  """Tests for cron functionality."""

  def testFileAdd(self):
    fs = aff4.FACTORY.Open(filestore.FileStore.PATH, "FileStore",
                           token=self.token)
    fake_store1 = FakeStore("aff4:/files/temp1", self.token)
    fake_store2 = FakeStore("aff4:/files/temp2", self.token)

    with test_lib.Stubber(fs, "OpenChildren",
                          lambda: [fake_store1, fake_store2]):

      src_fd = aff4.FACTORY.Create(aff4.ROOT_URN.Add("temp").Add("src"),
                                   "VFSBlobImage", token=self.token, mode="rw")
      src_fd.SetChunksize(filestore.FileStore.CHUNK_SIZE)

      src_data = "ABC" * filestore.FileStore.CHUNK_SIZE
      src_data_fd = StringIO.StringIO(src_data)
      src_fd.AppendContent(src_data_fd)

      fs.AddFile(src_fd)

      # Reset file pointers
      src_fd.Seek(0)
      fake_store1.dest_file.Seek(0)
      fake_store2.dest_file.Seek(0)

      # Check file content got written to both data stores.
      self.assertEqual(src_data, fake_store1.dest_file.Read(-1))
      self.assertEqual(src_data, fake_store2.dest_file.Read(-1))

  def testGetByPriority(self):
    priority1 = aff4.FACTORY.Create("aff4:/files/1", "FileStore", mode="rw",
                                    token=self.token)
    priority1.PRIORITY = 1
    priority1.Set(priority1.Schema.ACTIVE(False))

    priority2 = aff4.FACTORY.Create("aff4:/files/2", "FileStore", mode="rw",
                                    token=self.token)
    priority2.PRIORITY = 2

    priority3 = aff4.FACTORY.Create("aff4:/files/3", "FileStore", mode="rw",
                                    token=self.token)
    priority3.PRIORITY = 3

    fs = aff4.FACTORY.Open(filestore.FileStore.PATH, "FileStore",
                           token=self.token)

    with test_lib.Stubber(fs, "OpenChildren",
                          lambda: [priority3, priority1, priority2]):

      child_list = list(fs.GetChildrenByPriority())
      self.assertEqual(child_list[0].PRIORITY, 2)
      self.assertEqual(child_list[1].PRIORITY, 3)

      child_list = list(fs.GetChildrenByPriority(allow_external=False))
      self.assertEqual(child_list[0].PRIORITY, 2)

