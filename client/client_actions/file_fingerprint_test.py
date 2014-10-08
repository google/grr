#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-

# Copyright 2010 Google Inc. All Rights Reserved.

"""Test client vfs."""


import hashlib
import os


# Populate the action registry
# pylint: disable=unused-import
from grr.client import client_actions
# pylint: enable=unused-import
from grr.client import vfs
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


class FilehashTest(test_lib.EmptyActionTest):
  """Test fingerprinting files."""

  def testHashFile(self):
    """Can we hash a file?"""
    path = os.path.join(self.base_path, "numbers.txt")
    p = rdfvalue.PathSpec(path=path,
                          pathtype=rdfvalue.PathSpec.PathType.OS)
    result = self.RunAction("FingerprintFile",
                            rdfvalue.FingerprintRequest(pathspec=p))
    types = result[0].matching_types
    fingers = {}
    for f in result[0].results:
      fingers[f["name"]] = f
    generic_sha256 = fingers["generic"]["sha256"]
    self.assertEqual(generic_sha256,
                     hashlib.sha256(open(path).read()).digest())

    # Make sure all fingers are listed in types and vice versa.
    t_map = {rdfvalue.FingerprintTuple.Type.FPT_GENERIC: "generic",
             rdfvalue.FingerprintTuple.Type.FPT_PE_COFF: "pecoff"}
    ti_map = dict((v, k) for k, v in t_map.iteritems())
    for t in types:
      self.assertTrue(t_map[t] in fingers)
    for f in fingers:
      self.assertTrue(ti_map[f] in types)

    self.assertEqual(result[0].pathspec.path, path)

  def testMissingFile(self):
    """Fail on missing file?"""
    path = os.path.join(self.base_path, "this file does not exist")
    p = rdfvalue.PathSpec(path=path,
                          pathtype=rdfvalue.PathSpec.PathType.OS)
    self.assertRaises(IOError, self.RunAction, "FingerprintFile",
                      rdfvalue.FingerprintRequest(pathspec=p))


def main(argv):
  # Initialize the VFS system
  vfs.VFSInit()

  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
