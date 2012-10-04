#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2010 Google Inc.
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


"""Test client vfs."""


import hashlib
import os


from grr.client import conf
# Populate the action registry
from grr.client import client_actions
from grr.client import conf
from grr.client import vfs
from grr.lib import test_lib
from grr.lib import utils
from grr.proto import jobs_pb2




class FilehashTest(test_lib.EmptyActionTest):
  """Test fingerprinting files."""

  def testHashFile(self):
    """Can we hash a file?"""
    path = os.path.join(self.base_path, "numbers.txt")
    p = jobs_pb2.Path(path=path, pathtype=jobs_pb2.Path.OS)
    result = self.RunAction("FingerprintFile",
                            jobs_pb2.FingerprintRequest(pathspec=p))
    types, fingers = parse_result(result[0])
    generic_sha256 = fingers["generic"]["sha256"]
    self.assertEqual(generic_sha256,
                     hashlib.sha256(open(path).read()).digest())

    # Make sure all fingers are listed in types and vice versa.
    t_map = {jobs_pb2.FPT_GENERIC: "generic", jobs_pb2.FPT_PE_COFF: "pecoff"}
    ti_map = dict((v, k) for k, v in t_map.iteritems())
    for t in types:
      self.assertTrue(t_map[t] in fingers)
    for f in fingers:
      self.assertTrue(ti_map[f] in types)

  def testMissingFile(self):
    """Fail on missing file?"""
    path = os.path.join(self.base_path, "this file does not exist")
    p = jobs_pb2.Path(path=path, pathtype=jobs_pb2.Path.OS)
    self.assertRaises(IOError, self.RunAction, "FingerprintFile",
                      jobs_pb2.FingerprintRequest(pathspec=p))


def parse_result(proto):
  types = proto.matching_types
  fingers = dict()
  for f in proto.fingerprint_results:
    d = utils.ProtoDict(f).ToDict()
    fingers[d["name"]] = d
  return types, fingers


def main(argv):
  # Initialize the VFS system
  vfs.VFSInit()

  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
