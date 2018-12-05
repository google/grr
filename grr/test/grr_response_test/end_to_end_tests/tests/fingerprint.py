#!/usr/bin/env python
"""End to end tests for GRR fingerprint-related flows."""
from __future__ import absolute_import
from __future__ import division

from grr_response_test.end_to_end_tests import test_base


class TestFingerprintFileOSLinux(test_base.EndToEndTest):
  """Tests if Fingerprinting works on Linux."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("FingerprintFile")
    args.pathspec.path = "/bin/ls"
    args.pathspec.pathtype = args.pathspec.OS

    with self.WaitForFileRefresh("fs/os/bin/ls"):
      f = self.RunFlowAndWait("FingerprintFile", args=args)

    results = list(f.ListResults())
    self.assertGreater(len(results), 0)

    fingerprint_result = results[0].payload
    self.assertLen(fingerprint_result.hash_entry.md5, 16)
    self.assertLen(fingerprint_result.hash_entry.sha1, 20)
    self.assertLen(fingerprint_result.hash_entry.sha256, 32)


class TestFingerprintFileOSWindows(test_base.EndToEndTest):
  """Tests if Fingerprinting works on Windows."""

  platforms = [
      test_base.EndToEndTest.Platform.WINDOWS,
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("FingerprintFile")
    args.pathspec.path = "C:\\Windows\\regedit.exe"
    args.pathspec.pathtype = args.pathspec.OS

    with self.WaitForFileRefresh("fs/os/C:/Windows/regedit.exe"):
      self.RunFlowAndWait("FingerprintFile", args=args)
