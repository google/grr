#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for the FetchAllFiles flow."""



import hashlib
import os

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import standard


class TestFetchAllFilesFlow(test_lib.FlowTestsBaseclass):
  """Test the FetchAllFiles flow."""

  def setUp(self):
    super(TestFetchAllFilesFlow, self).setUp()
    path = os.path.join(self.base_path, "winexec_img.dd")
    self.findspec = rdfvalue.RDFFindSpec()
    self.findspec.pathspec.path = path
    self.findspec.pathspec.pathtype = rdfvalue.PathSpec.PathType.OS
    self.findspec.pathspec.Append(path="/",
                                  pathtype=rdfvalue.PathSpec.PathType.TSK)

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                      "FingerprintFile")
    for _ in test_lib.TestFlowHelper(
        "FetchAllFiles", client_mock, token=self.token,
        client_id=self.client_id, findspec=self.findspec):
      pass

  def tearDown(self):
    pass

  def testFindExeFiles(self):
    inspect_path = self.findspec.pathspec.Copy()
    inspect_path.AppendPath("Ext2IFS_1_10b.exe")

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(
        inspect_path, self.client_id)

    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(fd.__class__, aff4_grr.VFSFileSymlink)

    stat = fd.Get(fd.Schema.STAT)
    self.assertEqual(stat.st_size, 471040)
    fingerprint = fd.Get(fd.Schema.FINGERPRINT)
    generic = fingerprint.GetFingerprint("generic")["sha256"]
    pecoff = fingerprint.GetFingerprint("pecoff")["sha1"].encode("hex")
    delegate = fd.Get(fd.Schema.DELEGATE)
    self.assertEqual(delegate.Path(), "/FP/pecoff/sha1/" + pecoff)
    read_through = fd.Read(500000)
    self.assertEqual(stat.st_size, len(read_through))
    self.assertEqual(hashlib.sha256(read_through).digest(), generic)

    fd2 = aff4.FACTORY.Open(delegate, token=self.token)
    self.assertEqual(fd2.__class__, standard.HashImage)
    fingerprint2 = fd2.Get(fd2.Schema.FINGERPRINT)

    self.assertEqual(fingerprint.results, fingerprint2.results)

  def testPresenceOfSignedData(self):
    inspect_path = self.findspec.pathspec

    inspect_path.AppendPath("winpmem-i386.sys")
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(inspect_path,
                                                     self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    fingerprint = fd.Get(fd.Schema.FINGERPRINT)
    self.assertTrue(fingerprint.GetFingerprint("pecoff")["SignedData"])

  # TODO(user): Check the numbers in the flow for files_* ops.
