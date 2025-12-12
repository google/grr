#!/usr/bin/env python
"""End to end tests for transfer flows."""

from grr_response_test.end_to_end_tests import test_base


class TestTransferLinux(test_base.AbstractFileTransferTest):
  """Test MultiGetFile on Linux."""

  platforms = [test_base.EndToEndTest.Platform.LINUX]

  def testMultiGetFileOS(self):
    args = self.grr_api.types.CreateFlowArgs("MultiGetFile")
    pathspec = args.pathspecs.add()
    pathspec.path = "/bin/ls"
    pathspec.pathtype = pathspec.OS

    path = "fs/os/bin/ls"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait("MultiGetFile", args=args)

    self.CheckELFMagic(path)

  def testMultiGetFileTSK(self):
    if self.os_release == "CentOS Linux":
      self.skipTest(
          "TSK is not supported on CentOS due to an xfs root filesystem.")

    args = self.grr_api.types.CreateFlowArgs("MultiGetFile")
    pathspec = args.pathspecs.add()
    pathspec.path = "/usr/bin/diff"
    pathspec.pathtype = pathspec.TSK

    f = self.RunFlowAndWait("MultiGetFile", args=args)
    results = list(f.ListResults())
    self.assertNotEmpty(results)

    stat_entry = results[0].payload
    path = self.TSKPathspecToVFSPath(stat_entry.pathspec)

    # Run MultiGetFile again to make sure the path gets updated.
    with self.WaitForFileRefresh(path):
      self.RunFlowAndWait("MultiGetFile", args=args)

    self.CheckELFMagic(path)


class TestTransferDarwin(test_base.AbstractFileTransferTest):
  """Test MultiGetFile on Darwin."""

  platforms = [test_base.EndToEndTest.Platform.DARWIN]

  def testMultiGetFileOS(self):
    args = self.grr_api.types.CreateFlowArgs("MultiGetFile")
    pathspec = args.pathspecs.add()
    pathspec.path = "/bin/ls"
    pathspec.pathtype = pathspec.OS

    path = "fs/os/bin/ls"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait("MultiGetFile", args=args)

    self.CheckMacMagic(path)


class TestTransferWindows(test_base.AbstractFileTransferTest):
  """Test MultiGetFile on Windows."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def testMultiGetFileOS(self):
    args = self.grr_api.types.CreateFlowArgs("MultiGetFile")
    pathspec = args.pathspecs.add()
    pathspec.path = "C:\\Windows\\regedit.exe"
    pathspec.pathtype = pathspec.OS

    path = "fs/os/C:/Windows/regedit.exe"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait("MultiGetFile", args=args)

    self.CheckPEMagic(path)

  def testMultiGetFileTSK(self):
    args = self.grr_api.types.CreateFlowArgs("MultiGetFile")
    pathspec = args.pathspecs.add()
    pathspec.path = "C:\\Windows\\regedit.exe"
    pathspec.pathtype = pathspec.TSK

    f = self.RunFlowAndWait("MultiGetFile", args=args)
    results = list(f.ListResults())
    self.assertNotEmpty(results)

    stat_entry = results[0].payload
    path = self.TSKPathspecToVFSPath(stat_entry.pathspec)

    # Run MultiGetFile again to make sure the path gets updated.
    with self.WaitForFileRefresh(path):
      self.RunFlowAndWait("MultiGetFile", args=args)

    self.CheckPEMagic(path)

  def testMultiGetFileNTFS(self):
    args = self.grr_api.types.CreateFlowArgs("MultiGetFile")
    pathspec = args.pathspecs.add()
    pathspec.path = "C:\\Windows\\regedit.exe"
    pathspec.pathtype = pathspec.NTFS

    f = self.RunFlowAndWait("MultiGetFile", args=args)
    results = list(f.ListResults())
    self.assertNotEmpty(results)

    stat_entry = results[0].payload
    path = self.NTFSPathspecToVFSPath(stat_entry.pathspec)

    # Run MultiGetFile again to make sure the path gets updated.
    with self.WaitForFileRefresh(path):
      self.RunFlowAndWait("MultiGetFile", args=args)

    self.CheckPEMagic(path)
