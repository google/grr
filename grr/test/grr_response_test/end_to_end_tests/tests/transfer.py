#!/usr/bin/env python
"""End to end tests for transfer flows."""
from __future__ import absolute_import
from __future__ import division

from grr_response_test.end_to_end_tests import test_base


class TestTransferLinux(test_base.AbstractFileTransferTest):
  """Test GetFile on Linux."""

  platforms = [test_base.EndToEndTest.Platform.LINUX]

  def testGetFileOS(self):
    args = self.grr_api.types.CreateFlowArgs("GetFile")
    args.pathspec.path = "/bin/ls"
    args.pathspec.pathtype = args.pathspec.OS

    path = "fs/os/bin/ls"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait("GetFile", args=args)

    self.CheckELFMagic(path)

  def testGetFileTSK(self):
    args = self.grr_api.types.CreateFlowArgs("GetFile")
    args.pathspec.path = "/usr/bin/diff"
    args.pathspec.pathtype = args.pathspec.TSK

    f = self.RunFlowAndWait("GetFile", args=args)
    results = list(f.ListResults())
    self.assertGreater(len(results), 0)

    stat_entry = results[0].payload
    path = self.TSKPathspecToVFSPath(stat_entry.pathspec)

    # Run GetFile again to make sure the path gets updated.
    with self.WaitForFileRefresh(path):
      self.RunFlowAndWait("GetFile", args=args)

    self.CheckELFMagic(path)


class TestTransferDarwin(test_base.AbstractFileTransferTest):
  """Test GetFile on Darwin."""

  platforms = [test_base.EndToEndTest.Platform.DARWIN]

  def testGetFileOS(self):
    args = self.grr_api.types.CreateFlowArgs("GetFile")
    args.pathspec.path = "/bin/ls"
    args.pathspec.pathtype = args.pathspec.OS

    path = "fs/os/bin/ls"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait("GetFile", args=args)

    self.CheckMacMagic(path)


class TestTransferWindows(test_base.AbstractFileTransferTest):
  """Test GetFile on Windows."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def testGetFileOS(self):
    args = self.grr_api.types.CreateFlowArgs("GetFile")
    args.pathspec.path = "C:\\Windows\\regedit.exe"
    args.pathspec.pathtype = args.pathspec.OS

    path = "fs/os/C:/Windows/regedit.exe"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait("GetFile", args=args)

    self.CheckPEMagic(path)

  def testGetFileTSK(self):
    args = self.grr_api.types.CreateFlowArgs("GetFile")
    args.pathspec.path = "C:\\Windows\\regedit.exe"
    args.pathspec.pathtype = args.pathspec.TSK

    f = self.RunFlowAndWait("GetFile", args=args)
    results = list(f.ListResults())
    self.assertGreater(len(results), 0)

    stat_entry = results[0].payload
    path = self.TSKPathspecToVFSPath(stat_entry.pathspec)

    # Run GetFile again to make sure the path gets updated.
    with self.WaitForFileRefresh(path):
      self.RunFlowAndWait("GetFile", args=args)

    self.CheckPEMagic(path)
