#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""Tests for the Windows Sleuthkit functions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import collections
import platform
import unittest
from absl import app
from absl.testing import absltest

from grr_response_client import vfs
from grr_response_client.client_actions.file_finder_utils import globbing
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr.test_lib import test_lib


@unittest.skipIf(platform.system() != "Windows", "This test is Windows-only.")
class TSKWindowsGlobbingTest(absltest.TestCase):

  def testGlobComponentGenerateWorksWithTSK(self):
    opts = globbing.PathOpts(pathtype=rdf_paths.PathSpec.PathType.TSK)
    paths = globbing.GlobComponent(u"Windows", opts=opts).Generate("C:\\")
    self.assertEqual(list(paths), [u"C:\\Windows"])

  def testGlobbingExpandPathWorksWithTSK(self):
    opts = globbing.PathOpts(pathtype=rdf_paths.PathSpec.PathType.TSK)
    paths = globbing.ExpandPath("C:/Windows/System32/notepad.exe", opts=opts)
    self.assertEqual(list(paths), [u"C:\\Windows\\System32\\notepad.exe"])

  def testListNamesNoDuplicates(self):
    fd = vfs.VFSOpen(
        rdf_paths.PathSpec(
            path="C:/Windows/System32",
            pathtype=rdf_paths.PathSpec.PathType.TSK))
    names = fd.ListNames()
    counts = collections.Counter(names)
    duplicates = [(name, count) for name, count in counts.items() if count > 1]
    self.assertEmpty(duplicates)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
