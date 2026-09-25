#!/usr/bin/env python
"""End to end tests for GRR filesystem-related flows."""

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
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")  # pyrefly: ignore[missing-attribute]
    args.pathspec.path = "C:\\Windows"
    args.pathspec.pathtype = args.pathspec.NTFS

    f = self.RunFlowAndWait("ListDirectory", args=args)

    results = list(f.ListResults())
    self.assertNotEmpty(results)

    regedit_path = None
    for r in results:
      path = "fs/ntfs"
      pathspec = r.payload.pathspec
      while pathspec.path:
        path += pathspec.path
        pathspec = pathspec.nested_path

      if path.endswith("/regedit.exe"):
        regedit_path = path
        break

    self.assertTrue(regedit_path)

    with self.WaitForFileRefresh(regedit_path):
      self.RunFlowAndWait("ListDirectory", args=args)


class TestListDirectoryRootNTFSWindows(test_base.EndToEndTest):
  """Tests if listing root folder on Windows works with libfsntfs."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")  # pyrefly: ignore[missing-attribute]
    args.pathspec.path = "C:\\"
    args.pathspec.pathtype = args.pathspec.NTFS

    flow = self.RunFlowAndWait("ListDirectory", args=args)

    def IsWindowsDirPath(pathspec):
      return (pathspec.pathtype == args.pathspec.OS and
              pathspec.mount_point == "C:" and
              pathspec.nested_path.pathtype == args.pathspec.NTFS and
              pathspec.nested_path.path.upper().endswith("WINDOWS"))

    pathspecs = [result.payload.pathspec for result in flow.ListResults()]
    self.assertTrue(any(map(IsWindowsDirPath, pathspecs)))
