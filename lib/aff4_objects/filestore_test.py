#!/usr/bin/env python
"""Tests for grr.lib.aff4_objects.filestore."""

import os
import StringIO
import time

from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import utils
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
  """Tests for file store functionality."""

  def testFileAdd(self):
    fs = aff4.FACTORY.Open(filestore.FileStore.PATH, "FileStore",
                           token=self.token)
    fake_store1 = FakeStore("aff4:/files/temp1", self.token)
    fake_store2 = FakeStore("aff4:/files/temp2", self.token)

    with utils.Stubber(fs, "OpenChildren",
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

    with utils.Stubber(fs, "OpenChildren",
                       lambda: [priority3, priority1, priority2]):

      child_list = list(fs.GetChildrenByPriority())
      self.assertEqual(child_list[0].PRIORITY, 2)
      self.assertEqual(child_list[1].PRIORITY, 3)

      child_list = list(fs.GetChildrenByPriority(allow_external=False))
      self.assertEqual(child_list[0].PRIORITY, 2)


class HashFileStoreTest(test_lib.GRRBaseTest):
  """Tests for hash file store functionality."""

  def setUp(self):
    super(HashFileStoreTest, self).setUp()

    client_ids = self.SetupClients(1)
    self.client_id = client_ids[0]

  @staticmethod
  def AddFileToFileStore(pathspec=None, client_id=None, token=None):
    """Adds file with given pathspec to the hash file store."""
    if pathspec is None:
      raise ValueError("pathspec can't be None")

    if client_id is None:
      raise ValueError("client_id can't be None")

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, client_id)

    client_mock = action_mocks.ActionMock("TransferBuffer", "StatFile",
                                          "HashBuffer")
    for _ in test_lib.TestFlowHelper(
        "GetFile", client_mock, token=token, client_id=client_id,
        pathspec=pathspec):
      pass

    auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED
    flow.Events.PublishEvent(
        "FileStore.AddFileToStore",
        rdfvalue.GrrMessage(payload=urn, auth_state=auth_state),
        token=token)
    worker = test_lib.MockWorker(token=token)
    worker.Simulate()

  def AddFile(self, path):
    """Add file with a subpath (relative to winexec_img.dd) to the store."""
    pathspec = rdfvalue.PathSpec(
        pathtype=rdfvalue.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(path=path, pathtype=rdfvalue.PathSpec.PathType.TSK)

    return self.AddFileToFileStore(pathspec, client_id=self.client_id,
                                   token=self.token)

  def testListHashes(self):
    self.AddFile("/Ext2IFS_1_10b.exe")
    hashes = list(aff4.HashFileStore.ListHashes(token=self.token))
    self.assertEqual(len(hashes), 5)

    self.assertTrue(rdfvalue.FileStoreHash(
        fingerprint_type="pecoff", hash_type="md5",
        hash_value="a3a3259f7b145a21c7b512d876a5da06") in hashes)
    self.assertTrue(rdfvalue.FileStoreHash(
        fingerprint_type="pecoff", hash_type="sha1",
        hash_value="019bddad9cac09f37f3941a7f285c79d3c7e7801") in hashes)
    self.assertTrue(rdfvalue.FileStoreHash(
        fingerprint_type="generic", hash_type="md5",
        hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a") in hashes)
    self.assertTrue(rdfvalue.FileStoreHash(
        fingerprint_type="generic", hash_type="sha1",
        hash_value="7dd6bee591dfcb6d75eb705405302c3eab65e21a") in hashes)
    self.assertTrue(rdfvalue.FileStoreHash(
        fingerprint_type="generic", hash_type="sha256",
        hash_value="0e8dc93e150021bb4752029ebbff51394aa36f06"
        "9cf19901578e4f06017acdb5") in hashes)

  def testListHashesWithAge(self):
    with utils.Stubber(time, "time", lambda: 42):
      self.AddFile("/Ext2IFS_1_10b.exe")

    hashes = list(aff4.HashFileStore.ListHashes(token=self.token, age=41e6))
    self.assertEqual(len(hashes), 0)

    hashes = list(aff4.HashFileStore.ListHashes(token=self.token, age=43e6))
    self.assertEqual(len(hashes), 5)

    hashes = list(aff4.HashFileStore.ListHashes(token=self.token))
    self.assertEqual(len(hashes), 5)

  def testHashAgeUpdatedWhenNewHitAddedWithinAFF4IndexCacheAge(self):
    # Check that there are no hashes.
    hashes = list(aff4.HashFileStore.ListHashes(token=self.token,
                                                age=(41e6, 1e10)))
    self.assertEqual(len(hashes), 0)

    with utils.Stubber(time, "time", lambda: 42):
      self.AddFileToFileStore(
          rdfvalue.PathSpec(pathtype=rdfvalue.PathSpec.PathType.OS,
                            path=os.path.join(self.base_path, "empty_file")),
          client_id=self.client_id, token=self.token)

    hashes = list(aff4.HashFileStore.ListHashes(token=self.token,
                                                age=(41e6, 1e10)))
    self.assertTrue(hashes)
    hits = list(aff4.HashFileStore.GetClientsForHash(hashes[0],
                                                     token=self.token))
    self.assertEqual(len(hits), 1)

    latest_time = 42 + config_lib.CONFIG["AFF4.intermediate_cache_age"] - 1
    with utils.Stubber(time, "time", lambda: latest_time):
      self.AddFileToFileStore(
          rdfvalue.PathSpec(
              pathtype=rdfvalue.PathSpec.PathType.OS,
              path=os.path.join(self.base_path, "a", "b", "c", "helloc.txt")),
          client_id=self.client_id, token=self.token)

    # Check that now we have two hits for the previosly added hash.
    hits = list(aff4.HashFileStore.GetClientsForHash(hashes[0],
                                                     token=self.token))
    self.assertEqual(len(hits), 2)

    # Check that new hit doesn't affect hash age.
    hashes = list(aff4.HashFileStore.ListHashes(token=self.token,
                                                age=(43e6, 1e10)))
    self.assertFalse(hashes)

  def testHashAgeUpdatedWhenNewHitAddedAfterAFF4IndexCacheAge(self):
    # Check that there are no hashes.
    hashes = list(aff4.HashFileStore.ListHashes(token=self.token,
                                                age=(41e6, 1e10)))
    self.assertEqual(len(hashes), 0)

    with utils.Stubber(time, "time", lambda: 42):
      self.AddFileToFileStore(
          rdfvalue.PathSpec(pathtype=rdfvalue.PathSpec.PathType.OS,
                            path=os.path.join(self.base_path, "empty_file")),
          client_id=self.client_id, token=self.token)

    hashes = list(aff4.HashFileStore.ListHashes(token=self.token,
                                                age=(41e6, 1e10)))
    self.assertTrue(hashes)
    hits = list(aff4.HashFileStore.GetClientsForHash(hashes[0],
                                                     token=self.token))
    self.assertEqual(len(hits), 1)

    latest_time = 42 + config_lib.CONFIG["AFF4.intermediate_cache_age"] + 1
    with utils.Stubber(time, "time", lambda: latest_time):
      self.AddFileToFileStore(
          rdfvalue.PathSpec(
              pathtype=rdfvalue.PathSpec.PathType.OS,
              path=os.path.join(self.base_path, "a", "b", "c", "helloc.txt")),
          client_id=self.client_id, token=self.token)

    # Check that now we have two hits for the previosly added hash.
    hits = list(aff4.HashFileStore.GetClientsForHash(hashes[0],
                                                     token=self.token))
    self.assertEqual(len(hits), 2)

    # Check that new hit affects hash age.
    hashes = list(aff4.HashFileStore.ListHashes(token=self.token,
                                                age=(43e6, 1e10)))
    self.assertTrue(hashes)

  def testGetClientsForHash(self):
    self.AddFile("/Ext2IFS_1_10b.exe")
    self.AddFile("/idea.dll")

    hits = list(aff4.HashFileStore.GetClientsForHash(rdfvalue.FileStoreHash(
        fingerprint_type="generic", hash_type="md5",
        hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a"), token=self.token))
    self.assertListEqual(hits, [self.client_id.Add(
        "fs/tsk").Add(self.base_path).Add("winexec_img.dd/Ext2IFS_1_10b.exe")])

  def testGetClientsForHashWithAge(self):
    with utils.Stubber(time, "time", lambda: 42):
      self.AddFile("/Ext2IFS_1_10b.exe")
      self.AddFile("/idea.dll")

    hits = list(aff4.HashFileStore.GetClientsForHash(
        rdfvalue.FileStoreHash(
            fingerprint_type="generic", hash_type="md5",
            hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a"),
        age=41e6,
        token=self.token))
    self.assertEqual(len(hits), 0)

    hits = list(aff4.HashFileStore.GetClientsForHash(
        rdfvalue.FileStoreHash(
            fingerprint_type="generic", hash_type="md5",
            hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a"),
        age=43e6,
        token=self.token))
    self.assertEqual(len(hits), 1)

    hits = list(aff4.HashFileStore.GetClientsForHash(
        rdfvalue.FileStoreHash(
            fingerprint_type="generic", hash_type="md5",
            hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a"),
        token=self.token))
    self.assertEqual(len(hits), 1)

  def testGetClientsForHashes(self):
    self.AddFile("/Ext2IFS_1_10b.exe")
    self.AddFile("/idea.dll")

    hash1 = rdfvalue.FileStoreHash(
        fingerprint_type="generic", hash_type="md5",
        hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a")
    hash2 = rdfvalue.FileStoreHash(
        fingerprint_type="generic", hash_type="sha1",
        hash_value="e1f7e62b3909263f3a2518bbae6a9ee36d5b502b")

    hits = dict(aff4.HashFileStore.GetClientsForHashes([hash1, hash2],
                                                       token=self.token))
    self.assertEqual(len(hits), 2)
    self.assertListEqual(hits[hash1], [self.client_id.Add(
        "fs/tsk").Add(self.base_path).Add("winexec_img.dd/Ext2IFS_1_10b.exe")])
    self.assertListEqual(hits[hash2], [self.client_id.Add(
        "fs/tsk").Add(self.base_path).Add("winexec_img.dd/idea.dll")])

  def testGetClientsForHashesWithAge(self):
    with utils.Stubber(time, "time", lambda: 42):
      self.AddFile("/Ext2IFS_1_10b.exe")
      self.AddFile("/idea.dll")

    hash1 = rdfvalue.FileStoreHash(
        fingerprint_type="generic", hash_type="md5",
        hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a")
    hash2 = rdfvalue.FileStoreHash(
        fingerprint_type="generic", hash_type="sha1",
        hash_value="e1f7e62b3909263f3a2518bbae6a9ee36d5b502b")

    hits = dict(aff4.HashFileStore.GetClientsForHashes([hash1, hash2],
                                                       age=41e6,
                                                       token=self.token))
    self.assertEqual(len(hits), 0)

    hits = dict(aff4.HashFileStore.GetClientsForHashes([hash1, hash2],
                                                       age=43e6,
                                                       token=self.token))
    self.assertEqual(len(hits), 2)

    hits = dict(aff4.HashFileStore.GetClientsForHashes([hash1, hash2],
                                                       token=self.token))
    self.assertEqual(len(hits), 2)
