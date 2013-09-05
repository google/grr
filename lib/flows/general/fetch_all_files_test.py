#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for the FetchAllFiles flow."""



import hashlib
import os

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import filestore
from grr.lib.flows.general import fetch_all_files


class TestFetchAllFilesFlow(test_lib.FlowTestsBaseclass):
  """Test the FetchAllFiles flow."""

  def testFetchAllFilesFlow(self):
    # Very small chunks to stress test this flow.
    with test_lib.MultiStubber(
        (fetch_all_files.FetchAllFiles, "CHUNK_SIZE", 102400),
        (fetch_all_files.FetchAllFiles, "MAX_CALL_TO_FILE_STORE", 10)):
      with test_lib.Instrument(
          filestore.FileStore, "CheckHashes") as check_hashes_instrument:

        path = os.path.join(self.base_path, "winexec_img.dd")
        self.findspec = rdfvalue.FindSpec(path_regex=r"\.(exe|sys)$")
        self.findspec.pathspec.path = path
        self.findspec.pathspec.pathtype = rdfvalue.PathSpec.PathType.OS
        self.findspec.pathspec.Append(path="/",
                                      pathtype=rdfvalue.PathSpec.PathType.TSK)

        # First create some existing files in the VFS so we can ensure they get
        # updated.
        inspect_path = self.findspec.pathspec.Copy()
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
            "FetchAllFiles", client_mock, token=self.token,
            client_id=self.client_id, findspec=self.findspec):
          pass

        self.CheckFindExeFiles()
        self.CheckPresenceOfSignedData()
        self.CheckIndexLookup()

        # In this test we limit the maximum number of times the filestore check
        # hashes is called to 10. There are 23 hits in the test data, so we
        # expect 3 calls, of 10, 10, and 3:
        self.assertEqual(len(check_hashes_instrument.args), 3)

        self.assertEqual(len(check_hashes_instrument.args[0][1]), 10)
        self.assertEqual(len(check_hashes_instrument.args[1][1]), 10)
        self.assertEqual(len(check_hashes_instrument.args[2][1]), 3)

  def CheckIndexLookup(self):
    # Make sure that indexes exist:
    fd = aff4.FACTORY.Open("aff4:/files/hash/generic/sha256", token=self.token)
    for child in fd.OpenChildren():
      # Now query the index for each of the files:
      for target in child.Query("aff4:/C.+"):
        target_fd = aff4.FACTORY.Open(target, token=self.token)
        target_hash = target_fd.Get(target_fd.Schema.HASH).sha256

        # Check that the hashes match
        self.assertEqual(child.urn.Basename(), str(target_hash))

  def CheckFindExeFiles(self):
    inspect_path = self.findspec.pathspec.Copy()
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
    inspect_path = self.findspec.pathspec

    inspect_path.AppendPath("winpmem-i386.sys")
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(inspect_path,
                                                     self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    hashes = fd.Get(fd.Schema.HASH)
    self.assertEqual(hashes.signed_data[0].revision, 512)
    self.assertTrue(
        "High Assurance EV Root CA" in hashes.signed_data[0].certificate)
