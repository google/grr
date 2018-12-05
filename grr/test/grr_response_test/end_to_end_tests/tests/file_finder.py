#!/usr/bin/env python
"""End to end tests for GRR FileFinder flow."""
from __future__ import absolute_import
from __future__ import division

from grr_response_proto import jobs_pb2
from grr_response_test.end_to_end_tests import test_base


class TestFileFinderOSWindows(test_base.AbstractFileTransferTest):
  """Test for FileFinder flow on Windows machines."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def _testCollection(self, flow, path_to_collect):
    args = self.grr_api.types.CreateFlowArgs(flow)
    args.paths.append(path_to_collect)

    condition = args.conditions.add()
    condition.condition_type = condition.SIZE
    condition.size.max_file_size = 1000000
    args.action.action_type = args.action.DOWNLOAD

    # Note that this path is case corrected.
    path = "fs/os/C:/Windows/System32/notepad.exe"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait(flow, args=args)

    self.CheckPEMagic(path)

  def testRegularCollection(self):
    flow = "FileFinder"
    path = "%%environ_systemroot%%\\SYsTEm32\\notepad.*"
    self._testCollection(flow, path)

  def testCFFRegularCollection(self):
    flow = "ClientFileFinder"
    # ClientFileFinder does not have a knowledgebase available.
    path = "c:\\Windows\\SYSTEM32\\notepad.*"
    self._testCollection(flow, path)


class TestFileFinderTSKWindows(test_base.AbstractFileTransferTest):
  """Test for FileFinder flow on Windows machines."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def testTSKCollection(self):
    args = self.grr_api.types.CreateFlowArgs("FileFinder")

    args.paths.append("%%environ_systemroot%%\\System32\\notepad.*")
    args.action.action_type = args.action.DOWNLOAD
    args.pathtype = jobs_pb2.PathSpec.TSK

    f = self.RunFlowAndWait("FileFinder", args=args)
    results = list(f.ListResults())
    self.assertGreater(len(results), 0)

    ff_result = results[0].payload
    path = self.TSKPathspecToVFSPath(ff_result.stat_entry.pathspec)

    # Run FileFinder again and make sure the path gets updated on VFS.
    with self.WaitForFileRefresh(path):
      self.RunFlowAndWait("FileFinder", args=args)

    self.CheckPEMagic(path)


class TestFileFinderOSDarwin(test_base.AbstractFileTransferTest):
  """Tests the file finder and the client file finder on Darwin e2e."""

  platforms = [test_base.EndToEndTest.Platform.DARWIN]

  flow = "FileFinder"

  def _testCollection(self, flow):
    args = self.grr_api.types.CreateFlowArgs(flow)
    args.paths.append("/bin/ps")
    args.action.action_type = args.action.DOWNLOAD

    path = "fs/os/bin/ps"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait(flow, args=args)

    self.CheckMacMagic(path)

  def testFileFinder(self):
    self._testCollection("FileFinder")

  def testCFF(self):
    self._testCollection("ClientFileFinder")


class TestFileFinderOSLinux(test_base.AbstractFileTransferTest):
  """Test for FileFinder on Linux machines."""

  platforms = [test_base.EndToEndTest.Platform.LINUX]

  def _testRegularFile(self, flow):
    args = self.grr_api.types.CreateFlowArgs(flow)

    args.paths.append("/bin/ps")
    condition = args.conditions.add()
    condition.condition_type = condition.SIZE
    condition.size.max_file_size = 1000000
    args.action.action_type = args.action.DOWNLOAD

    path = "fs/os/bin/ps"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait(flow, args=args)

    self.CheckELFMagic(path)

  def testRegularFile(self):
    self._testRegularFile("FileFinder")

  def testCFFRegularFile(self):
    self._testRegularFile("ClientFileFinder")

  def _testProcFile(self, flow):
    args = self.grr_api.types.CreateFlowArgs(flow)

    args.paths.append("/proc/sys/net/ipv4/ip_forward")
    condition = args.conditions.add()
    condition.condition_type = condition.SIZE
    condition.size.max_file_size = 1000000
    args.action.action_type = args.action.DOWNLOAD

    path = "fs/os/proc/sys/net/ipv4/ip_forward"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait(flow, args=args)

  def testProcFile(self):
    self._testProcFile("FileFinder")

  def testCFFProcFile(self):
    self._testProcFile("ClientFileFinder")


class TestFileFinderOSHomedir(test_base.AbstractFileTransferTest):
  """List files in homedir with FileFinder."""

  platforms = test_base.EndToEndTest.Platform.ALL

  flow = "FileFinder"

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs(self.flow)

    args.paths.append("%%users.homedir%%/*")
    args.action.action_type = args.action.STAT

    f = self.RunFlowAndWait(self.flow, args=args)

    results = list(f.ListResults())
    self.assertGreater(len(results), 0)


class TestFileFinderLiteralMatching(test_base.AbstractFileTransferTest):
  """Match files against a literal pattern with FileFinder."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN
  ]

  def _testLiteralMatching(self, flow):
    keywords = {
        test_base.EndToEndTest.Platform.LINUX: "ELF",
        test_base.EndToEndTest.Platform.DARWIN: "Apple",
    }

    keyword = keywords[self.platform]

    args = self.grr_api.types.CreateFlowArgs(flow)
    args.paths.append("/bin/ls")
    condition = args.conditions.add()
    condition.condition_type = condition.CONTENTS_LITERAL_MATCH
    condition.contents_literal_match.literal = keyword
    args.action.action_type = args.action.STAT

    f = self.RunFlowAndWait(flow, args=args)

    results = list(f.ListResults())
    self.assertLen(results, 1)
    result = results[0].payload

    self.assertIn("ls", result.stat_entry.pathspec.path)

    self.assertGreater(len(result.matches), 0)
    for match in result.matches:
      self.assertIn(keyword, match.data)

  def testLiteralMatching(self):
    self._testLiteralMatching("FileFinder")

  def testCFFLiteralMatching(self):
    self._testLiteralMatching("ClientFileFinder")


class TestFileFinderRegexMatching(test_base.AbstractFileTransferTest):
  """Match files against a regex pattern with FileFinder."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN
  ]

  flow = "FileFinder"

  def _testRegexMatching(self, flow):
    regexes = {
        test_base.EndToEndTest.Platform.LINUX: "E.F",
        test_base.EndToEndTest.Platform.DARWIN: "Ap..e",
    }
    keywords = {
        test_base.EndToEndTest.Platform.LINUX: "elf",
        test_base.EndToEndTest.Platform.DARWIN: "apple",
    }

    args = self.grr_api.types.CreateFlowArgs(flow)
    args.paths.append("/bin/ls")
    condition = args.conditions.add()
    condition.condition_type = condition.CONTENTS_REGEX_MATCH
    condition.contents_regex_match.regex = regexes[self.platform]
    args.action.action_type = args.action.STAT

    f = self.RunFlowAndWait(flow, args=args)

    results = list(f.ListResults())
    self.assertLen(results, 1)
    result = results[0].payload

    self.assertIn("ls", result.stat_entry.pathspec.path)

    self.assertGreater(len(result.matches), 0)
    for match in result.matches:
      self.assertIn(keywords[self.platform], match.data.lower())

  def testRegexMatching(self):
    self._testRegexMatching("FileFinder")

  def testCFFRegexMatching(self):
    self._testRegexMatching("ClientFileFinder")
