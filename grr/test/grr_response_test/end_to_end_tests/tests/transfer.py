#!/usr/bin/env python
"""End to end tests for transfer flows."""

import io

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

    flow = self.RunFlowAndWait("MultiGetFile", args=args)
    flow_results = list(flow.ListResults())
    self.assertLen(flow_results, 1)

    result_path = flow_results[0].payload.pathspec.path
    # TODO - The path returned by the old agent will have a leading
    # `/` (which makes no sense on Windows) so we strip it. We can remove this
    # workaround once we no longer test with the old agent.
    result_path = result_path.removeprefix("/")
    self.assertEqual(result_path.lower(), "c:/windows/regedit.exe")

    result_content = io.BytesIO()

    result_file = self.client.File(f"fs/os/{result_path}")
    result_file.GetBlob().WriteToStream(result_content)

    self.assertEqual(result_content.getvalue()[0:2], b"MZ")

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
