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
    pathspec = rdfvalue.RDFPathSpec(
        pathtype=rdfvalue.RDFPathSpec.Enum("OS"), path=path)

    pathspec.Append(path="/Ext2IFS_1_10b.exe",
                    pathtype=rdfvalue.RDFPathSpec.Enum("TSK"))

    client_mock = test_lib.ActionMock("FingerprintFile")
    for _ in test_lib.TestFlowHelper(
        "FingerprintFile", client_mock, token=self.token,
        client_id=self.client_id, pathspec=pathspec):
      pass

    urn = aff4.AFF4Object.VFSGRRClient.PathspecToURN(pathspec, self.client_id)
    fd = aff4.FACTORY.Open(urn, token=self.token)
    self.assertEqual(fd.__class__, aff4_grr.VFSFile)
    fingerprint = fd.Get(fd.Schema.FINGERPRINT)
    pecoff = fingerprint.Get("pecoff")["sha1"].encode("hex")
    self.assertEqual(pecoff, "019bddad9cac09f37f3941a7f285c79d3c7e7801")
