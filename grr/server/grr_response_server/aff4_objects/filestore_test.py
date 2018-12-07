#!/usr/bin/env python
"""Tests for the filestore."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import hashlib
import io
import os
import time

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import aff4
from grr_response_server import data_store_utils
from grr_response_server.aff4_objects import aff4_grr
from grr_response_server.aff4_objects import filestore
from grr_response_server.aff4_objects import filestore_test_lib
from grr_response_server.flows.general import file_finder
from grr.test_lib import action_mocks
from grr.test_lib import aff4_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib
from grr.test_lib import worker_test_lib


class FakeStore(object):
  PRIORITY = 99
  PATH = rdfvalue.RDFURN("aff4:/files/temp")

  def __init__(self, path, token):
    self.dest_file = aff4.FACTORY.Create(
        path, aff4.AFF4MemoryStream, mode="rw", token=token)

  def AddFile(self, unused_blob_fd, sync=False):
    _ = sync
    return self.dest_file

  def Get(self, _):
    return True

  class Schema(object):
    ACTIVE = "unused"


@db_test_lib.DualDBTest
class FileStoreTest(aff4_test_lib.AFF4ObjectTest):
  """Tests for file store functionality."""

  def testFileAdd(self):
    fs = aff4.FACTORY.Open(
        filestore.FileStore.PATH, filestore.FileStore, token=self.token)
    fake_store1 = FakeStore("aff4:/files/temp1", self.token)
    fake_store2 = FakeStore("aff4:/files/temp2", self.token)

    with utils.Stubber(fs, "OpenChildren", lambda: [fake_store1, fake_store2]):

      src_fd = aff4.FACTORY.Create(
          aff4.ROOT_URN.Add("temp").Add("src"),
          aff4_grr.VFSBlobImage,
          token=self.token,
          mode="rw")
      src_fd.SetChunksize(filestore.FileStore.CHUNK_SIZE)

      src_data = b"ABC" * filestore.FileStore.CHUNK_SIZE
      src_data_fd = io.BytesIO(src_data)
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
    priority1 = aff4.FACTORY.Create(
        "aff4:/files/1", filestore.FileStore, mode="rw", token=self.token)
    priority1.PRIORITY = 1
    priority1.Set(priority1.Schema.ACTIVE(False))

    priority2 = aff4.FACTORY.Create(
        "aff4:/files/2", filestore.FileStore, mode="rw", token=self.token)
    priority2.PRIORITY = 2

    priority3 = aff4.FACTORY.Create(
        "aff4:/files/3", filestore.FileStore, mode="rw", token=self.token)
    priority3.PRIORITY = 3

    fs = aff4.FACTORY.Open(
        filestore.FileStore.PATH, filestore.FileStore, token=self.token)

    with utils.Stubber(
        fs, "OpenChildren", lambda: [priority3, priority1, priority2]):

      child_list = list(fs.GetChildrenByPriority())
      self.assertEqual(child_list[0].PRIORITY, 2)
      self.assertEqual(child_list[1].PRIORITY, 3)

      child_list = list(fs.GetChildrenByPriority(allow_external=False))
      self.assertEqual(child_list[0].PRIORITY, 2)


class HashFileStoreTest(aff4_test_lib.AFF4ObjectTest):
  """Tests for hash file store functionality."""

  def setUp(self):
    super(HashFileStoreTest, self).setUp()
    self.client_id = self.SetupClient(0)

  def AddFile(self, path):
    """Add file with a subpath (relative to winexec_img.dd) to the store."""
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path=os.path.join(self.base_path, "winexec_img.dd"))
    pathspec.Append(path=path, pathtype=rdf_paths.PathSpec.PathType.TSK)

    return filestore_test_lib.AddFileToFileStore(
        pathspec, client_id=self.client_id, token=self.token)

  def testListHashes(self):
    self.AddFile("/Ext2IFS_1_10b.exe")
    hashes = list(filestore.HashFileStore.ListHashes())
    self.assertLen(hashes, 5)

    self.assertTrue(
        filestore.FileStoreHash(
            fingerprint_type="pecoff",
            hash_type="md5",
            hash_value="a3a3259f7b145a21c7b512d876a5da06") in hashes)
    self.assertTrue(
        filestore.FileStoreHash(
            fingerprint_type="pecoff",
            hash_type="sha1",
            hash_value="019bddad9cac09f37f3941a7f285c79d3c7e7801") in hashes)
    self.assertTrue(
        filestore.FileStoreHash(
            fingerprint_type="generic",
            hash_type="md5",
            hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a") in hashes)
    self.assertTrue(
        filestore.FileStoreHash(
            fingerprint_type="generic",
            hash_type="sha1",
            hash_value="7dd6bee591dfcb6d75eb705405302c3eab65e21a") in hashes)
    self.assertTrue(
        filestore.FileStoreHash(
            fingerprint_type="generic",
            hash_type="sha256",
            hash_value="0e8dc93e150021bb4752029ebbff51394aa36f06"
            "9cf19901578e4f06017acdb5") in hashes)

  def testListHashesWithAge(self):
    with utils.Stubber(time, "time", lambda: 42):
      self.AddFile("/Ext2IFS_1_10b.exe")

    hashes = list(filestore.HashFileStore.ListHashes(age=41e6))
    self.assertEmpty(hashes)

    hashes = list(filestore.HashFileStore.ListHashes(age=43e6))
    self.assertLen(hashes, 5)

    hashes = list(filestore.HashFileStore.ListHashes())
    self.assertLen(hashes, 5)

  def testHashAgeUpdatedWhenNewHitAddedWithinAFF4IndexCacheAge(self):
    # Check that there are no hashes.
    hashes = list(filestore.HashFileStore.ListHashes(age=(41e6, 1e10)))
    self.assertEmpty(hashes)

    with utils.Stubber(time, "time", lambda: 42):
      filestore_test_lib.AddFileToFileStore(
          rdf_paths.PathSpec(
              pathtype=rdf_paths.PathSpec.PathType.OS,
              path=os.path.join(self.base_path, "one_a")),
          client_id=self.client_id,
          token=self.token)

    hashes = list(filestore.HashFileStore.ListHashes(age=(41e6, 1e10)))
    self.assertTrue(hashes)
    hits = list(
        filestore.HashFileStore.GetClientsForHash(hashes[0], token=self.token))
    self.assertLen(hits, 1)

    latest_time = 42 + aff4.FACTORY.intermediate_cache_age - 1
    with utils.Stubber(time, "time", lambda: latest_time):
      filestore_test_lib.AddFileToFileStore(
          rdf_paths.PathSpec(
              pathtype=rdf_paths.PathSpec.PathType.OS,
              path=os.path.join(self.base_path, "a", "b", "c", "helloc.txt")),
          client_id=self.client_id,
          token=self.token)

    # Check that now we have two hits for the previosly added hash.
    hits = list(
        filestore.HashFileStore.GetClientsForHash(hashes[0], token=self.token))
    self.assertLen(hits, 2)

    # Check that new hit doesn't affect hash age.
    hashes = list(filestore.HashFileStore.ListHashes(age=(43e6, 1e10)))
    self.assertFalse(hashes)

  def testHashAgeUpdatedWhenNewHitAddedAfterAFF4IndexCacheAge(self):
    # Check that there are no hashes.
    hashes = list(filestore.HashFileStore.ListHashes(age=(41e6, 1e10)))
    self.assertEmpty(hashes)

    with utils.Stubber(time, "time", lambda: 42):
      filestore_test_lib.AddFileToFileStore(
          rdf_paths.PathSpec(
              pathtype=rdf_paths.PathSpec.PathType.OS,
              path=os.path.join(self.base_path, "one_a")),
          client_id=self.client_id,
          token=self.token)

    hashes = list(filestore.HashFileStore.ListHashes(age=(41e6, 1e10)))
    self.assertTrue(hashes)
    hits = list(
        filestore.HashFileStore.GetClientsForHash(hashes[0], token=self.token))
    self.assertLen(hits, 1)

    latest_time = 42 + aff4.FACTORY.intermediate_cache_age + 1
    with utils.Stubber(time, "time", lambda: latest_time):
      filestore_test_lib.AddFileToFileStore(
          rdf_paths.PathSpec(
              pathtype=rdf_paths.PathSpec.PathType.OS,
              path=os.path.join(self.base_path, "a", "b", "c", "helloc.txt")),
          client_id=self.client_id,
          token=self.token)

    # Check that now we have two hits for the previosly added hash.
    hits = list(
        filestore.HashFileStore.GetClientsForHash(hashes[0], token=self.token))

    self.assertLen(hits, 2)

    # Check that new hit affects hash age.
    hashes = list(filestore.HashFileStore.ListHashes(age=(43e6, 1e10)))
    self.assertTrue(hashes)

  def testGetClientsForHash(self):
    self.AddFile("/Ext2IFS_1_10b.exe")
    self.AddFile("/idea.dll")

    hits = list(
        filestore.HashFileStore.GetClientsForHash(
            filestore.FileStoreHash(
                fingerprint_type="generic",
                hash_type="md5",
                hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a"),
            token=self.token))
    self.assertListEqual(hits, [
        self.client_id.Add("fs/tsk").Add(
            self.base_path).Add("winexec_img.dd/Ext2IFS_1_10b.exe")
    ])

  def testGetClientsForHashWithAge(self):
    with utils.Stubber(time, "time", lambda: 42):
      self.AddFile("/Ext2IFS_1_10b.exe")
      self.AddFile("/idea.dll")

    hits = list(
        filestore.HashFileStore.GetClientsForHash(
            filestore.FileStoreHash(
                fingerprint_type="generic",
                hash_type="md5",
                hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a"),
            age=41e6,
            token=self.token))
    self.assertEmpty(hits)

    hits = list(
        filestore.HashFileStore.GetClientsForHash(
            filestore.FileStoreHash(
                fingerprint_type="generic",
                hash_type="md5",
                hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a"),
            age=43e6,
            token=self.token))
    self.assertLen(hits, 1)

    hits = list(
        filestore.HashFileStore.GetClientsForHash(
            filestore.FileStoreHash(
                fingerprint_type="generic",
                hash_type="md5",
                hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a"),
            token=self.token))
    self.assertLen(hits, 1)

  def testGetClientsForHashes(self):
    self.AddFile("/Ext2IFS_1_10b.exe")
    self.AddFile("/idea.dll")

    hash1 = filestore.FileStoreHash(
        fingerprint_type="generic",
        hash_type="md5",
        hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a")
    hash2 = filestore.FileStoreHash(
        fingerprint_type="generic",
        hash_type="sha1",
        hash_value="e1f7e62b3909263f3a2518bbae6a9ee36d5b502b")

    hits = dict(
        filestore.HashFileStore.GetClientsForHashes([hash1, hash2],
                                                    token=self.token))
    self.assertLen(hits, 2)
    self.assertListEqual(hits[hash1], [
        self.client_id.Add("fs/tsk").Add(
            self.base_path).Add("winexec_img.dd/Ext2IFS_1_10b.exe")
    ])
    self.assertListEqual(hits[hash2], [
        self.client_id.Add("fs/tsk").Add(
            self.base_path).Add("winexec_img.dd/idea.dll")
    ])

  def testGetClientsForHashesWithAge(self):
    with utils.Stubber(time, "time", lambda: 42):
      self.AddFile("/Ext2IFS_1_10b.exe")
      self.AddFile("/idea.dll")

    hash1 = filestore.FileStoreHash(
        fingerprint_type="generic",
        hash_type="md5",
        hash_value="bb0a15eefe63fd41f8dc9dee01c5cf9a")
    hash2 = filestore.FileStoreHash(
        fingerprint_type="generic",
        hash_type="sha1",
        hash_value="e1f7e62b3909263f3a2518bbae6a9ee36d5b502b")

    hits = dict(
        filestore.HashFileStore.GetClientsForHashes([hash1, hash2],
                                                    age=41e6,
                                                    token=self.token))
    self.assertEmpty(hits)

    hits = dict(
        filestore.HashFileStore.GetClientsForHashes([hash1, hash2],
                                                    age=43e6,
                                                    token=self.token))
    self.assertLen(hits, 2)

    hits = dict(
        filestore.HashFileStore.GetClientsForHashes([hash1, hash2],
                                                    token=self.token))
    self.assertLen(hits, 2)

  def testAttributesOfFileFoundInHashFileStoreAreSetCorrectly(self):
    client_ids = self.SetupClients(2)

    filename = os.path.join(self.base_path, "tcpip.sig")
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=filename)
    urn1 = pathspec.AFF4Path(client_ids[0])
    urn2 = pathspec.AFF4Path(client_ids[1])

    for client_id in client_ids:
      client_mock = action_mocks.FileFinderClientMock()
      flow_test_lib.TestFlowHelper(
          file_finder.FileFinder.__name__,
          client_mock,
          token=self.token,
          client_id=client_id,
          paths=[filename],
          action=rdf_file_finder.FileFinderAction.Download())
      # Running worker to make sure LegacyFileStore.AddFileToStore event is
      # processed by the worker.
      worker = worker_test_lib.MockWorker(token=self.token)
      worker.Simulate()

    fd1 = aff4.FACTORY.Open(urn1, token=self.token)
    self.assertIsInstance(fd1, aff4_grr.VFSBlobImage)

    fd2 = aff4.FACTORY.Open(urn2, token=self.token)
    self.assertIsInstance(fd2, aff4_grr.VFSBlobImage)

    self.assertTrue(fd1.Get(fd1.Schema.STAT))
    self.assertTrue(fd2.Get(fd2.Schema.STAT))
    self.assertEqual(fd1.Get(fd1.Schema.SIZE), fd2.Get(fd2.Schema.SIZE))
    self.assertEqual(
        fd1.Get(fd1.Schema.CONTENT_LAST), fd2.Get(fd2.Schema.CONTENT_LAST))

  def testEmptyFileHasNoBackreferences(self):

    # First make sure we store backrefs for a non empty file.
    filename = os.path.join(self.base_path, "tcpip.sig")
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=filename)
    filestore_test_lib.AddFileToFileStore(
        pathspec, client_id=self.client_id, token=self.token)
    self.assertLen(self._GetBackRefs(filename), 3)

    # Now use the empty file.
    filename = os.path.join(self.base_path, "empty_file")
    pathspec = rdf_paths.PathSpec(
        pathtype=rdf_paths.PathSpec.PathType.OS, path=filename)
    filestore_test_lib.AddFileToFileStore(
        pathspec, client_id=self.client_id, token=self.token)
    self.assertEmpty(self._GetBackRefs(filename))

  def _GetBackRefs(self, filename):
    res = []
    data = open(filename, "rb").read()
    for name, algo, f in [
        ("sha256", hashlib.sha256, "GetReferencesSHA256"),
        ("sha1", hashlib.sha1, "GetReferencesSHA1"),
        ("md5", hashlib.md5, "GetReferencesMD5"),
    ]:
      h = algo()
      h.update(data)

      urn = rdfvalue.RDFURN("aff4:/files/hash/generic/").Add(name)
      urn = urn.Add(h.hexdigest())

      fs = filestore.HashFileStore
      for ref in getattr(fs, f)(h.hexdigest(), token=self.token):
        res.append(ref)

    return res

  def _SetupNSRLFiles(self):
    urn1 = self.AddFile("/Ext2IFS_1_10b.exe")
    urn2 = self.AddFile("/idea.dll")

    self.hashes1 = data_store_utils.GetUrnHashEntry(urn1)
    self.hashes2 = data_store_utils.GetUrnHashEntry(urn2)

    # Pretend this file is part of the NSRL.
    nsrl_fs = aff4.FACTORY.Open("aff4:/files/nsrl", token=self.token)
    nsrl_fs.AddHash("e1f7e62b3909263f3a2518bbae6a9ee36d5b502b",
                    "bb0a15eefe63fd41f8dc9dee01c5cf9a", None, "idea.dll", 100,
                    None, None, "M")

    self.sha1_hash = filestore.FileStoreHash(
        fingerprint_type="generic",
        hash_type="sha1",
        hash_value="e1f7e62b3909263f3a2518bbae6a9ee36d5b502b")
    return nsrl_fs

  def CheckHashesNSRL(self):
    nsrl_fs = self._SetupNSRLFiles()
    hits = list(nsrl_fs.CheckHashes([self.hashes1, self.hashes2]))

    self.assertLen(hits, 1)
    hit = hits[0]
    self.assertEqual(hit[1], self.hashes2)

  def testNSRLInfo(self):
    nsrl_fs = self._SetupNSRLFiles()
    sha1s = [
        "e1f7e62b3909263f3a2518bbae6a9ee36d5b502b",
        "0000000000000000000000000000000000000000"
    ]
    infos = nsrl_fs.NSRLInfoForSHA1s(sha1s)
    self.assertIn(sha1s[0], infos)
    self.assertNotIn(sha1s[1], infos)

    fd = infos[sha1s[0]]
    info = fd.Get(fd.Schema.NSRL)
    self.assertEqual(info.md5, "bb0a15eefe63fd41f8dc9dee01c5cf9a")
    self.assertEqual(info.file_size, 100)

  def testGetClientsForHashesNSRL(self):
    """Tests GetClientsForHashes for the NSRL filestore.

    This is just forwarding to the hash file store but we test it
    anyways.
    """
    nsrl_fs = self._SetupNSRLFiles()
    hits = dict(nsrl_fs.GetClientsForHashes([self.sha1_hash], token=self.token))
    self.assertLen(hits, 1)
    self.assertListEqual(hits[self.sha1_hash], [
        self.client_id.Add("fs/tsk").Add(
            self.base_path).Add("winexec_img.dd/idea.dll")
    ])


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
