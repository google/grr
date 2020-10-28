#!/usr/bin/env python
"""End to end tests for GRR filesystem-related flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_test.end_to_end_tests import test_base

####################
# Linux and Darwin #
####################


class TestListDirectoryOSLinuxDarwin(test_base.EndToEndTest):
  """Tests if ListDirectory works on Linux and Darwin."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")
    args.pathspec.path = "/bin"
    args.pathspec.pathtype = args.pathspec.OS

    with self.WaitForFileRefresh("fs/os/bin/ls"):
      self.RunFlowAndWait("ListDirectory", args=args)


# TODO(amoser): Find a way to run this on Darwin with Filevault turned on.
class TestListDirectoryTSKLinux(test_base.EndToEndTest):
  """Tests if ListDirectory works on Linux and Darwin using Sleuthkit."""

  platforms = [test_base.EndToEndTest.Platform.LINUX]

  def runTest(self):
    if self.os_release == "CentOS Linux":
      self.skipTest(
          "TSK is not supported on CentOS due to an xfs root filesystem.")

    # We look for the directories inside /usr. It's very difficult to find a
    # file common across all versions of default OS X, Ubuntu, and CentOS that
    # isn't symlinked and doesn't live in a huge directory that takes forever to
    # list with TSK. So we settle for listing /usr instead.
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")
    args.pathspec.path = "/usr"
    args.pathspec.pathtype = args.pathspec.TSK

    f = self.RunFlowAndWait("ListDirectory", args=args)

    results = list(f.ListResults())
    self.assertNotEmpty(results)

    stat_entry = results[0].payload

    # Build a VFS path out of the pathspec.
    path = "fs/tsk/"
    pathspec = stat_entry.pathspec
    while pathspec.path:
      path += pathspec.path
      pathspec = pathspec.nested_path

    # Run ListDirectory again and make sure the path gets updated on VFS.
    with self.WaitForFileRefresh(path):
      self.RunFlowAndWait("ListDirectory", args=args)


class TestRecursiveListDirectoryLinuxDarwin(test_base.EndToEndTest):
  """Test recursive list directory on linux and darwin."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("RecursiveListDirectory")
    args.pathspec.path = "/usr"
    args.pathspec.pathtype = args.pathspec.OS
    args.max_depth = 2

    with self.WaitForFileRefresh("fs/os/usr/bin/less"):
      self.RunFlowAndWait("RecursiveListDirectory", args=args)


# TODO(amoser): Find a way to run this on Darwin with Filevault turned on.
class TestFindTSKLinux(test_base.EndToEndTest):
  """Tests if the find flow works on Linux and Darwin using Sleuthkit."""

  platforms = [test_base.EndToEndTest.Platform.LINUX]

  def runTest(self):
    if self.os_release == "CentOS Linux":
      self.skipTest(
          "TSK is not supported on CentOS due to an xfs root filesystem.")

    args = self.grr_api.types.CreateFlowArgs("FindFiles")
    # Cut down the number of files by specifying a partial regex
    # match, we just want to find /usr/bin/diff, when run on a real
    # system there are thousands which takes forever with TSK.
    # TODO
    args.findspec.max_depth = 1
    args.findspec.path_regex = "di"
    args.findspec.pathspec.path = "/usr/bin"
    args.findspec.pathspec.pathtype = args.findspec.pathspec.TSK

    f = self.RunFlowAndWait("FindFiles", args=args)

    results = list(f.ListResults())
    self.assertNotEmpty(results)

    diff_path = None
    for r in results:
      path = "fs/tsk"
      pathspec = r.payload.pathspec
      while pathspec.path:
        path += pathspec.path
        pathspec = pathspec.nested_path

      if path.endswith("/diff"):
        diff_path = path
        break

    self.assertTrue(diff_path)

    with self.WaitForFileRefresh(diff_path):
      self.RunFlowAndWait("FindFiles", args=args)


class TestFindOSLinuxDarwin(test_base.EndToEndTest):
  """Tests if the find flow works on Linux and Darwin."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("FindFiles")
    args.findspec.path_regex = "^l"
    args.findspec.pathspec.path = "/bin"
    args.findspec.pathspec.pathtype = args.findspec.pathspec.OS

    with self.WaitForFileRefresh("fs/os/bin/ls"):
      self.RunFlowAndWait("FindFiles", args=args)


###########
# Windows #
###########


class TestListDirectoryOSWindows(test_base.EndToEndTest):
  """Tests if ListDirectory works on Windows."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")
    args.pathspec.path = "C:\\Windows"
    args.pathspec.pathtype = args.pathspec.OS

    with self.WaitForFileRefresh("fs/os/C:/Windows/regedit.exe"):
      self.RunFlowAndWait("ListDirectory", args=args)


class TestRecursiveListDirectoryOSWindows(test_base.EndToEndTest):
  """TestRecursiveListDirectoryOSWindows."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("RecursiveListDirectory")
    args.pathspec.path = "C:\\"
    args.pathspec.pathtype = args.pathspec.OS
    args.max_depth = 2

    with self.WaitForFileRefresh("fs/os/C:/Windows/regedit.exe"):
      self.RunFlowAndWait("RecursiveListDirectory", args=args)


class TestListDirectoryTSKWindows(test_base.EndToEndTest):
  """Tests if ListDirectory works on Windows using Sleuthkit."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")
    args.pathspec.path = "C:\\Windows"
    args.pathspec.pathtype = args.pathspec.TSK

    f = self.RunFlowAndWait("ListDirectory", args=args)

    results = list(f.ListResults())
    self.assertNotEmpty(results)

    regedit_path = None
    for r in results:
      path = "fs/tsk"
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


class TestListDirectoryNTFSWindows(test_base.EndToEndTest):
  """Tests if ListDirectory works on Windows using libfsntfs."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")
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


class TestListDirectoryRootTSKWindows(test_base.EndToEndTest):
  """Tests if listing root folder on Windows works with The Sleuth Kit."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")
    args.pathspec.path = "C:\\"
    args.pathspec.pathtype = args.pathspec.TSK

    flow = self.RunFlowAndWait("ListDirectory", args=args)

    def IsWindowsDirPath(pathspec):
      return (pathspec.pathtype == args.pathspec.OS and
              pathspec.mount_point == "C:" and
              pathspec.nested_path.pathtype == args.pathspec.TSK and
              pathspec.nested_path.path.upper().endswith("WINDOWS"))

    pathspecs = [result.payload.pathspec for result in flow.ListResults()]
    self.assertTrue(any(map(IsWindowsDirPath, pathspecs)))


class TestListDirectoryRootNTFSWindows(test_base.EndToEndTest):
  """Tests if listing root folder on Windows works with libfsntfs."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("ListDirectory")
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
