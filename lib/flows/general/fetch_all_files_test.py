#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the FetchAllFiles flow."""



import hashlib
import os

from grr.lib import aff4
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import standard
from grr.proto import jobs_pb2


class TestFetchAllFilesFlow(test_lib.FlowTestsBaseclass):
  """Test the FetchAllFiles flow."""

  def setUp(self):
    super(TestFetchAllFilesFlow, self).setUp()
    path = os.path.join(self.base_path, "winexec_img.dd")
    pathspec = jobs_pb2.Path(pathtype=jobs_pb2.Path.OS,
                             path=path)
    pathspec.nested_path.path = "/"
    pathspec.nested_path.pathtype = jobs_pb2.Path.TSK

    client_mock = test_lib.ActionMock("TransferBuffer", "StatFile", "Find",
                                      "FingerprintFile")
    for _ in test_lib.TestFlowHelper(
        "FetchAllFiles", client_mock, token=self.token,
        client_id=self.client_id,
        pathspec=pathspec):
      pass

    self.pathspec = pathspec

  def tearDown(self):
    pass

  def testFindExeFiles(self):
    inspect_path = self.pathspec
    inspect_path.nested_path.path += "Ext2IFS_1_10b.exe"
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(inspect_path,
                                                     self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(fd.__class__, aff4_grr.VFSFileSymlink)

    stat = fd.Get(fd.Schema.STAT)
    self.assertEqual(stat.data.st_size, 471040)
    fingerprint = fd.Get(fd.Schema.FINGERPRINT)
    generic = fingerprint.Get("generic")["sha256"]
    pecoff = fingerprint.Get("pecoff")["sha1"].encode("hex")
    delegate = fd.Get(fd.Schema.DELEGATE)
    self.assertEqual(delegate.Path(), "/FP/pecoff/sha1/" + pecoff)
    read_through = fd.Read(500000)
    self.assertEqual(stat.data.st_size, len(read_through))
    self.assertEqual(hashlib.sha256(read_through).digest(), generic)

    fd2 = aff4.FACTORY.Open(delegate, token=self.token)
    self.assertEqual(fd2.__class__, standard.HashImage)
    fingerprint2 = fd2.Get(fd2.Schema.FINGERPRINT)
    self.assertProto2Equal(fingerprint.data, fingerprint2.data)

  def testPresenceOfSignedData(self):
    inspect_path = self.pathspec
    inspect_path.nested_path.path += "winpmem-i386.sys"
    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(inspect_path,
                                                     self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    fingerprint = fd.Get(fd.Schema.FINGERPRINT)
    self.assert_(fingerprint.Get("pecoff")["SignedData"])

  #TODO(user): Check the numbers in the flow for files_* ops.
