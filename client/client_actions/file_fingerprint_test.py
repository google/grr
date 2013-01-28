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
# pylint: disable=W0611
from grr.client import client_actions
# pylint: enable=W0611
from grr.client import vfs
from grr.lib import rdfvalue
from grr.lib import test_lib


class FilehashTest(test_lib.EmptyActionTest):
  """Test fingerprinting files."""

  def testHashFile(self):
    """Can we hash a file?"""
    path = os.path.join(self.base_path, "numbers.txt")
    p = rdfvalue.RDFPathSpec(path=path,
                             pathtype=rdfvalue.RDFPathSpec.Enum("OS"))
    result = self.RunAction("FingerprintFile",
                            rdfvalue.FingerprintRequest(pathspec=p))
    types = result[0].matching_types
    fingers = {}
    for f in result[0].fingerprint_results:
      fingers[f["name"]] = f
    generic_sha256 = fingers["generic"]["sha256"]
    self.assertEqual(generic_sha256,
                     hashlib.sha256(open(path).read()).digest())

    # Make sure all fingers are listed in types and vice versa.
    t_map = {rdfvalue.FingerprintTuple.Enum("FPT_GENERIC"): "generic",
             rdfvalue.FingerprintTuple.Enum("FPT_PE_COFF"): "pecoff"}
    ti_map = dict((v, k) for k, v in t_map.iteritems())
    for t in types:
      self.assertTrue(t_map[t] in fingers)
    for f in fingers:
      self.assertTrue(ti_map[f] in types)

  def testMissingFile(self):
    """Fail on missing file?"""
    path = os.path.join(self.base_path, "this file does not exist")
    p = rdfvalue.RDFPathSpec(path=path,
                             pathtype=rdfvalue.RDFPathSpec.Enum("OS"))
    self.assertRaises(IOError, self.RunAction, "FingerprintFile",
                      rdfvalue.FingerprintRequest(pathspec=p))


def main(argv):
  # Initialize the VFS system
  vfs.VFSInit()

  test_lib.main(argv)

if __name__ == "__main__":
  conf.StartMain(main)
