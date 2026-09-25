#!/usr/bin/env python
"""End to end tests for transfer flows."""

import io

from grr_response_proto import flows_pb2
from grr_response_test.end_to_end_tests import test_base


class TestTransferLinux(test_base.AbstractFileTransferTest):
  """Test MultiGetFile on Linux."""

  platforms = [test_base.EndToEndTest.Platform.LINUX]

  def testMultiGetFileOS(self):
    args = self.grr_api.types.CreateFlowArgs("MultiGetFile")  # pyrefly: ignore[missing-attribute]
    pathspec = args.pathspecs.add()
    pathspec.path = "/bin/ls"
    pathspec.pathtype = pathspec.OS

    path = "fs/os/bin/ls"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait("MultiGetFile", args=args)

    self.CheckELFMagic(path)


class TestTransferDarwin(test_base.AbstractFileTransferTest):
  """Test MultiGetFile on Darwin."""

  platforms = [test_base.EndToEndTest.Platform.DARWIN]

  def testMultiGetFileOS(self):
    args = self.grr_api.types.CreateFlowArgs("MultiGetFile")  # pyrefly: ignore[missing-attribute]
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
    args = self.grr_api.types.CreateFlowArgs("MultiGetFile")  # pyrefly: ignore[missing-attribute]
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

    result_file = self.client.File(f"fs/os/{result_path}")  # pyrefly: ignore[missing-attribute]
    result_file.GetBlob().WriteToStream(result_content)

    self.assertEqual(result_content.getvalue()[0:2], b"MZ")

  def testMultiGetFileNTFS(self):
    # TODO - Remove once Keramics is enabled by default.
    runner_args = flows_pb2.FlowRunnerArgs()
    runner_args.rrg_mode = flows_pb2.FlowRunnerArgs.RrgMode.FORCED

    args = self.grr_api.types.CreateFlowArgs("MultiGetFile")  # pyrefly: ignore[missing-attribute]
    pathspec = args.pathspecs.add()
    # TODO - Revert back to `regedit.exe` once Keramics is fixed.
    pathspec.path = "C:\\Windows\\system.ini"
    pathspec.pathtype = pathspec.NTFS

    f = self.RunFlowAndWait("MultiGetFile", args=args, runner_args=runner_args)
    results = list(f.ListResults())
    self.assertNotEmpty(results)

    stat_entry = results[0].payload
    path = self.NTFSPathspecToVFSPath(stat_entry.pathspec)

    # Run MultiGetFile again to make sure the path gets updated.
    with self.WaitForFileRefresh(path):
      self.RunFlowAndWait("MultiGetFile", args=args, runner_args=runner_args)

    # TODO - Verify PEM once we collect an executable again.
    self.assertEqual(self.ReadFromFile(path, num_bytes=2), b"; ")
