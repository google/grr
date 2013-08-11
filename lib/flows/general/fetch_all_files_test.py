#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for the FetchAllFiles flow."""



import hashlib
import os

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.flows.general import fetch_all_files


class TestFetchAllFilesFlow(test_lib.FlowTestsBaseclass):
  """Test the FetchAllFiles flow."""

  def testFetchAllFilesFlow(self):
    # Very small chunks to stress test this flow.
    with test_lib.Stubber(fetch_all_files.FetchAllFiles, "CHUNK_SIZE", 102400):
      path = os.path.join(self.base_path, "winexec_img.dd")
      self.findspec = rdfvalue.RDFFindSpec(path_regex=r"\.(exe|sys)$")
      self.findspec.pathspec.path = path
      self.findspec.pathspec.pathtype = rdfvalue.PathSpec.PathType.OS
      self.findspec.pathspec.Append(path="/",
                                    pathtype=rdfvalue.PathSpec.PathType.TSK)

      client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                        "HashFile", "HashBuffer")
      for _ in test_lib.TestFlowHelper(
          "FetchAllFiles", client_mock, token=self.token,
          client_id=self.client_id, findspec=self.findspec):
        pass

      self.CheckFindExeFiles()
      self.CheckPresenceOfSignedData()
      self.CheckIndexLookup()

  def CheckIndexLookup(self):
    # Make sure that indexes exist:
    fd = aff4.FACTORY.Open("aff4:/FP/generic/sha256", token=self.token)
    for child in fd.OpenChildren():
      # Now query the index for each of the files:
      for target in child.Query("aff4:/C.+"):
        target_fd = aff4.FACTORY.Open(target, token=self.token)
        target_hash = target_fd.Get(target_fd.Schema.HASH)

        # Check that the hashes match
        self.assertEqual(child.urn.Basename(), str(target_hash))

  def CheckFindExeFiles(self):
    inspect_path = self.findspec.pathspec.Copy()
    inspect_path.AppendPath("Ext2IFS_1_10b.exe")

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        inspect_path, self.client_id)

    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(fd.__class__, aff4.VFSBlobImage)

    stat = fd.Get(fd.Schema.STAT)
    self.assertEqual(stat.st_size, 471040)

    sha_hash = fd.Get(fd.Schema.HASH)

    read_through = fd.Read(500000)
    self.assertEqual(stat.st_size, len(read_through))
    self.assertEqual(hashlib.sha256(read_through).digest(), sha_hash)

    # Make sure the canonical file exists.
    canonical_urn = aff4.ROOT_URN.Add("FP/generic/sha256").Add(str(sha_hash))

    fd2 = aff4.FACTORY.Open(canonical_urn, token=self.token)
    self.assertEqual(fd2.__class__, fetch_all_files.FileStoreImage)
    self.assertEqual(hashlib.sha256(fd2.Read(500000)).digest(), sha_hash)

  def CheckPresenceOfSignedData(self):
    inspect_path = self.findspec.pathspec

    inspect_path.AppendPath("winpmem-i386.sys")
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(inspect_path,
                                                     self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    signed_data = fd.Get(fd.Schema.SIGNED_DATA)
    self.assertEqual(signed_data.revision, 512)
    self.assertTrue(
        "High Assurance EV Root CA" in signed_data.certificate)
