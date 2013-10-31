#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc. All Rights Reserved.
"""Tests for the Fingerprint flow."""



import os

from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr


class TestFingerprintFlow(test_lib.FlowTestsBaseclass):
  """Test the FetchAllFiles flow."""

  def testFingerprintPresence(self):
    path = os.path.join(self.base_path, "winexec_img.dd")
    pathspec = rdfvalue.PathSpec(
        pathtype=rdfvalue.PathSpec.PathType.OS, path=path)

    pathspec.Append(path="/winpmem-amd64.sys",
                    pathtype=rdfvalue.PathSpec.PathType.TSK)

    client_mock = test_lib.ActionMock("FingerprintFile")
    for _ in test_lib.TestFlowHelper(
        "FingerprintFile", client_mock, token=self.token,
        client_id=self.client_id, pathspec=pathspec):
      pass

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(fd.__class__, aff4_grr.VFSFile)
    fingerprint = fd.Get(fd.Schema.FINGERPRINT)
    pecoff = fingerprint.GetFingerprint("pecoff")["sha1"].encode("hex")
    self.assertEqual(pecoff, "1f32fa4eedfba023653c094143d90999f6b9bc4f")

    hash_obj = fd.Get(fd.Schema.HASH)
    self.assertEqual(hash_obj.pecoff_sha1,
                     "1f32fa4eedfba023653c094143d90999f6b9bc4f")

    self.assertEqual(hash_obj.signed_data[0].revision, 512)
