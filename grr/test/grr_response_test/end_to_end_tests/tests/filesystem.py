#!/usr/bin/env python
"""End to end tests for GRR filesystem-related flows."""

import pathlib

from grr_response_proto import flows_pb2
from grr_response_test.end_to_end_tests import test_base

####################
# Linux and Darwin #
####################


class TestListDirectoryOSLinux(test_base.EndToEndTest):
  """Tests if ListDirectory works on Linux."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")  # pyrefly: ignore[missing-attribute]
    args.pathspec.path = "/usr/bin"
    args.pathspec.pathtype = args.pathspec.OS

    with self.WaitForFileRefresh("fs/os/usr/bin/ls"):
      self.RunFlowAndWait("ListDirectory", args=args)


class TestListDirectoryOSDarwin(test_base.EndToEndTest):
  """Tests if ListDirectory works on Darwin."""

  platforms = [
      test_base.EndToEndTest.Platform.DARWIN,
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")  # pyrefly: ignore[missing-attribute]
    args.pathspec.path = "/bin"
    args.pathspec.pathtype = args.pathspec.OS

    with self.WaitForFileRefresh("fs/os/bin/ls"):
      self.RunFlowAndWait("ListDirectory", args=args)


class TestRecursiveListDirectoryLinuxDarwin(test_base.EndToEndTest):
  """Test recursive list directory on linux and darwin."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("RecursiveListDirectory")  # pyrefly: ignore[missing-attribute]
    args.pathspec.path = "/usr"
    args.pathspec.pathtype = args.pathspec.OS
    args.max_depth = 2

    with self.WaitForFileRefresh("fs/os/usr/bin/uname"):
      self.RunFlowAndWait("RecursiveListDirectory", args=args)


###########
# Windows #
###########


class TestListDirectoryOSWindows(test_base.EndToEndTest):
  """Tests if ListDirectory works on Windows."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")  # pyrefly: ignore[missing-attribute]
    args.pathspec.path = "C:\\Windows"
    args.pathspec.pathtype = args.pathspec.OS

    with self.WaitForFileRefresh("fs/os/C:/Windows/regedit.exe"):
      self.RunFlowAndWait("ListDirectory", args=args)


class TestRecursiveListDirectoryOSWindows(test_base.EndToEndTest):
  """TestRecursiveListDirectoryOSWindows."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("RecursiveListDirectory")  # pyrefly: ignore[missing-attribute]
    args.pathspec.path = "C:\\"
    args.pathspec.pathtype = args.pathspec.OS
    args.max_depth = 2

    with self.WaitForFileRefresh("fs/os/C:/Windows/regedit.exe"):
      self.RunFlowAndWait("RecursiveListDirectory", args=args)


class TestListDirectoryNTFSWindows(test_base.EndToEndTest):
  """Tests if ListDirectory works on Windows using libfsntfs."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    # TODO - Remove once Keramics is enabled by default.
    runner_args = flows_pb2.FlowRunnerArgs()
    runner_args.rrg_mode = flows_pb2.FlowRunnerArgs.RrgMode.FORCED

    args = self.grr_api.types.CreateFlowArgs("ListDirectory")  # pyrefly: ignore[missing-attribute]
    args.pathspec.path = "C:\\Windows"
    args.pathspec.pathtype = args.pathspec.NTFS

    f = self.RunFlowAndWait("ListDirectory", args=args, runner_args=runner_args)

    results = list(f.ListResults())
    self.assertNotEmpty(results)

    # TODO - Simplify to testing with a literal once the old agent
    # is no longer there.
    regedit_path = None
    for r in results:
      path = "fs/ntfs"
      pathspec = r.payload.pathspec
      while pathspec.path:
        # One agent has a leading forward slash, the other does not so we need
        # to normalize here.
        path += f"/{pathspec.path.removeprefix('/')}"
        pathspec = pathspec.nested_path

      if path.endswith("/regedit.exe"):
        regedit_path = path
        break

    self.assertTrue(regedit_path)

    with self.WaitForFileRefresh(regedit_path):
      self.RunFlowAndWait("ListDirectory", args=args, runner_args=runner_args)


class TestListDirectoryRootNTFSWindows(test_base.EndToEndTest):
  """Tests if listing root folder on Windows works with libfsntfs."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    # TODO - Remove once Keramics is enabled by default.
    runner_args = flows_pb2.FlowRunnerArgs()
    runner_args.rrg_mode = flows_pb2.FlowRunnerArgs.RrgMode.FORCED

    args = self.grr_api.types.CreateFlowArgs("ListDirectory")  # pyrefly: ignore[missing-attribute]
    args.pathspec.path = "C:\\"
    args.pathspec.pathtype = args.pathspec.NTFS

    flow = self.RunFlowAndWait(
        "ListDirectory",
        args=args,
        runner_args=runner_args,
    )

    # TODO - Simplify to testing with a literal once the old agent
    # is no longer there.
    # TODO - Revert back to testing for the "Windows" folder once
    # Keramics is fixed.
    def IsMFTPath(pathspec):
      # One agent works with nested paths and mount points, the other does not.
      if pathspec.mount_point:
        path = pathlib.PureWindowsPath(f"{pathspec.mount_point}\\")
        path = path / pathspec.nested_path.path.removeprefix("/")
      else:
        path = pathlib.PureWindowsPath(pathspec.path)

      return path == pathlib.PureWindowsPath("C:/$MFT")

    pathspecs = [result.payload.pathspec for result in flow.ListResults()]
    self.assertTrue(any(map(IsMFTPath, pathspecs)))
