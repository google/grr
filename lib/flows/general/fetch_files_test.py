#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for the FetchFiles flow."""



import hashlib
import os
import StringIO

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import filestore
from grr.lib.flows.general import transfer


class TestFetchFilesFlow(test_lib.FlowTestsBaseclass):
  """Test the FetchFiles flow."""

  def setUp(self):
    super(TestFetchFilesFlow, self).setUp()
    # binary hash of pciide.sys
    self.existing_hash = ("\xf2\xa7\xccd[\x96\x94l\xc6[\xf6\x0e\x14"
                          "\xe7\r\xc0\x9c\x84\x8d'\xc7\x94<\xe5\xde\xa0\xc0"
                          "\x1ak\x864\x80")
    self.existing_hash_urn = "aff4:/files/hash/generic/sha256/%s" % (
        self.existing_hash.encode("hex"))

    self.chunk_size = 102400

    self.blob_fd = aff4.FACTORY.Create(self.existing_hash_urn, "FileStoreImage",
                                       token=self.token,
                                       mode="rw")
    self.blob_fd.SetChunksize(self.chunk_size)
    self.blob_fd.AppendContent(StringIO.StringIO("MZ" * self.chunk_size))
    self.blob_fd.Set(self.blob_fd.Schema.HASH(sha256=self.existing_hash))
    self.blob_fd.Flush()

  def testFetchFilesFlow(self):

    # Very small chunks to stress test this flow.
    with test_lib.MultiStubber(
        (transfer.MultiGetFile, "CHUNK_SIZE", self.chunk_size),
        (transfer.MultiGetFile, "MIN_CALL_TO_FILE_STORE", 10)):
      with test_lib.Instrument(
          filestore.FileStore, "CheckHashes") as check_hashes_instrument:

        path = os.path.join(self.base_path, "winexec_img.dd")
        self.findspec = rdfvalue.FindSpec(path_regex=r"\.(exe|sys)$")
        self.findspec.pathspec.path = path
        self.findspec.pathspec.pathtype = rdfvalue.PathSpec.PathType.OS
        self.findspec.pathspec.Append(path="/",
                                      pathtype=rdfvalue.PathSpec.PathType.TSK)

        self.base_pathspec = self.findspec.pathspec.Copy()

        # First create some existing files in the VFS so we can ensure they get
        # updated.
        inspect_path = self.base_pathspec.Copy()
        inspect_path.AppendPath("Ext2IFS_1_10b.exe")

        urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            inspect_path, self.client_id)

        fd = aff4.FACTORY.Create(urn, "AFF4MemoryStream", token=self.token)
        fd.Write("hello")
        fd.Close()

        # Now run the fetch all files.
        client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                          "HashFile", "HashBuffer")

        for _ in test_lib.TestFlowHelper(
            "FetchFiles", client_mock, token=self.token,
            client_id=self.client_id, findspec=self.findspec):
          pass

        self.CheckFindExeFiles()
        self.CheckPresenceOfSignedData()
        self.CheckIndexLookup()
        pathlist = ["/a/b/c/g/f/pciide.sys", "pciide.sys",
                    "/a/b/c/g/h/pciide.sys", "/a/b/c/g/pciide.sys"]
        self.CheckExistingFile(pathlist)

        # In this test we limit the maximum number of times the filestore check
        # hashes is called to 10. There are 23 hits in the test data, so we
        # expect 3 calls, of 10, 10, and 3:
        self.assertEqual(len(check_hashes_instrument.args), 3)

        self.assertEqual(len(check_hashes_instrument.args[0][1]), 10)
        self.assertEqual(len(check_hashes_instrument.args[1][1]), 10)
        self.assertEqual(len(check_hashes_instrument.args[2][1]), 3)

        fd = aff4.FACTORY.Open(self.client_id.Add("analysis/FetchFiles"),
                               token=self.token)
        collection = list(fd.OpenChildren())[0]
        self.assertEqual(len(collection), 23)

  def testFetchFilesGlobFlow(self):
    # Very small chunks to stress test this flow.
    with test_lib.MultiStubber(
        (transfer.MultiGetFile, "CHUNK_SIZE", self.chunk_size),
        (transfer.MultiGetFile, "MIN_CALL_TO_FILE_STORE", 3)):
      with test_lib.Instrument(
          filestore.FileStore, "CheckHashes") as check_hashes_instrument:

        self.base_pathspec = rdfvalue.PathSpec(
            path=os.path.join(self.base_path, "winexec_img.dd"),
            pathtype=rdfvalue.PathSpec.PathType.OS)
        self.base_pathspec.Append(path="/",
                                  pathtype=rdfvalue.PathSpec.PathType.TSK)

        inspect_path = self.base_pathspec.Copy()
        inspect_path.AppendPath("Ext2IFS_1_10b.exe")

        urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
            inspect_path, self.client_id)

        fd = aff4.FACTORY.Create(urn, "AFF4MemoryStream", token=self.token)
        fd.Write("hello")
        fd.Close()

        # Now run the fetch all files.
        client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                          "HashFile", "HashBuffer")

        for _ in test_lib.TestFlowHelper(
            "FetchFiles", client_mock, token=self.token,
            paths=["*.exe", "*.sys"],
            root_path=self.base_pathspec,
            pathtype=rdfvalue.PathSpec.PathType.OS,
            client_id=self.client_id):
          pass

        self.CheckFindExeFiles()
        self.CheckPresenceOfSignedData()
        self.CheckIndexLookup()
        pathlist = ["pciide.sys"]
        self.CheckExistingFile(pathlist)

        # In this test we limit the maximum number of times the filestore check
        # hashes is called to 3. There are 7 hits in the test data, so we
        # expect 3 calls, of 3, 3, and 1:
        self.assertEqual(len(check_hashes_instrument.args), 3)

        self.assertEqual(len(check_hashes_instrument.args[0][1]), 3)
        self.assertEqual(len(check_hashes_instrument.args[1][1]), 3)
        self.assertEqual(len(check_hashes_instrument.args[2][1]), 1)

  def CheckIndexLookup(self):
    # Make sure that indexes exist:
    fd = aff4.FACTORY.Open("aff4:/files/hash/generic/sha256", token=self.token)
    for child in fd.OpenChildren():
      # Now query the index for each of the files:
      index = list(child.Query("aff4:/C.+"))
      self.assertTrue(index)
      for target in index:
        target_fd = aff4.FACTORY.Open(target, token=self.token)
        target_hash = target_fd.Get(target_fd.Schema.HASH).sha256

        # Check that the hashes match
        self.assertEqual(child.urn.Basename(), str(target_hash))

  def _MakeURN(self, path):
    inspect_path = self.base_pathspec.Copy()
    inspect_path.AppendPath(path)
    return aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        inspect_path, self.client_id)

  def _CheckHashAndFiletype(self, urn):
    fd = aff4.FACTORY.Open(urn, "FileStoreImage", token=self.token)
    self.assertEqual(fd.Get(fd.Schema.HASH).sha256, self.existing_hash)

  def CheckExistingFile(self, pathlist):
    urns = []
    for path in pathlist:
      urn = self._MakeURN(path)
      urns.append(urn)
      self._CheckHashAndFiletype(urn)

    fd = aff4.FACTORY.Open(self.existing_hash_urn, "FileStoreImage",
                           token=self.token)
    index_list = list(fd.Query("aff4:/C.+"))
    self.assertEqual(len(index_list), len(pathlist))
    self.assertItemsEqual(index_list, urns)

  def CheckFindExeFiles(self):
    inspect_path = self.base_pathspec.Copy()
    inspect_path.AppendPath("Ext2IFS_1_10b.exe")

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        inspect_path, self.client_id)

    # This file started off being an AFF4MemoryStream but now it is a BlobImage.
    fd = aff4.FACTORY.Open(urn, age=aff4.ALL_TIMES, token=self.token)
    self.assertEqual(fd.__class__, aff4.VFSBlobImage)

    # Oldest attribute is AFF4MemoryStream.
    self.assertEqual(list(fd.GetValuesForAttribute(
        fd.Schema.TYPE))[-1], "AFF4MemoryStream")

    # Newest attribute is BlobImage.
    self.assertEqual(list(fd.GetValuesForAttribute(
        fd.Schema.TYPE))[0], "VFSBlobImage")

    stat = fd.Get(fd.Schema.STAT)
    self.assertEqual(stat.st_size, 471040)

    hashes = fd.Get(fd.Schema.HASH)

    read_through = fd.Read(500000)
    self.assertEqual(stat.st_size, len(read_through))
    self.assertEqual(hashlib.sha256(read_through).digest(), hashes.sha256)

    # Make sure the canonical file exists.
    canonical_urn = aff4.ROOT_URN.Add(
        "files/hash/generic/sha256").Add(str(hashes.sha256))

    fd2 = aff4.FACTORY.Open(canonical_urn, token=self.token)
    self.assertEqual(fd2.__class__, filestore.FileStoreImage)
    canonical_data = fd2.Read(500000)
    self.assertEqual(read_through, canonical_data)
    self.assertEqual(hashlib.sha256(canonical_data).digest(), hashes.sha256)
    self.assertEqual(hashlib.sha1(canonical_data).digest(), hashes.sha1)
    self.assertEqual(hashlib.md5(canonical_data).digest(), hashes.md5)
    self.assertEqual("019bddad9cac09f37f3941a7f285c79d3c7e7801",
                     hashes.pecoff_sha1)
    self.assertEqual("a3a3259f7b145a21c7b512d876a5da06",
                     hashes.pecoff_md5)

  def CheckPresenceOfSignedData(self):
    inspect_path = self.base_pathspec.Copy()

    inspect_path.AppendPath("winpmem-i386.sys")
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(inspect_path,
                                                     self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)

    hashes = fd.Get(fd.Schema.HASH)
    self.assertEqual(hashes.signed_data[0].revision, 512)
    self.assertTrue(
        "High Assurance EV Root CA" in hashes.signed_data[0].certificate)
