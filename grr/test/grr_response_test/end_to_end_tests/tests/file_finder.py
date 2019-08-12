#!/usr/bin/env python
"""End to end tests for GRR FileFinder flow."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import functools
import operator

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

  def _testTSKListing(self, flow_name):
    args = self.grr_api.types.CreateFlowArgs(flow_name)
    args.paths.append("C:\\*")
    args.action.action_type = args.action.STAT
    args.pathtype = jobs_pb2.PathSpec.TSK

    f = self.RunFlowAndWait(flow_name, args=args)
    results = list(f.ListResults())
    self.assertNotEmpty(results)

  def testTSKListing(self):
    self._testTSKListing("FileFinder")

  def testTSKListingClientFileFinder(self):
    self._testTSKListing("ClientFileFinder")

  def _testTSKSmallFileCollection(self, flow_name):
    args = self.grr_api.types.CreateFlowArgs(flow_name)

    args.paths.append("%%environ_systemroot%%\\System32\\notepad.*")
    args.action.action_type = args.action.DOWNLOAD
    args.pathtype = jobs_pb2.PathSpec.TSK

    f = self.RunFlowAndWait(flow_name, args=args)
    results = list(f.ListResults())
    self.assertNotEmpty(results)

    ff_result = results[0].payload
    path = self.TSKPathspecToVFSPath(ff_result.stat_entry.pathspec)

    # Run FileFinder again and make sure the path gets updated on VFS.
    with self.WaitForFileRefresh(path):
      self.RunFlowAndWait(flow_name, args=args)

    self.CheckPEMagic(path)

  def testTSKSmallFileCollection(self):
    self._testTSKSmallFileCollection("FileFinder")

  def testTSKSmallFileCollectionClientFileFinder(self):
    self._testTSKSmallFileCollection("ClientFileFinder")

  def _testTSKLargeFileCollection(self, flow_name):
    args = self.grr_api.types.CreateFlowArgs(flow_name)
    args.paths.append("%%environ_systemdrive%%\\$MFT")
    args.pathtype = jobs_pb2.PathSpec.TSK
    args.action.action_type = args.action.STAT

    f = self.RunFlowAndWait(flow_name, args=args)
    results = list(f.ListResults())
    self.assertNotEmpty(results)

    ff_result = results[0].payload
    path = self.TSKPathspecToVFSPath(ff_result.stat_entry.pathspec)

    args = self.grr_api.types.CreateFlowArgs(flow_name)
    args.paths.append("%%environ_systemdrive%%\\$MFT")
    args.pathtype = jobs_pb2.PathSpec.TSK
    args.action.action_type = args.action.DOWNLOAD
    args.action.download.oversized_file_policy = (
        args.action.download.DOWNLOAD_TRUNCATED)

    with self.WaitForFileRefresh(path):
      self.RunFlowAndWait(flow_name, args=args)

    fd = self.client.File(path)
    last_collected_size = fd.Get().data.last_collected_size

    # Check that the last_collected_size is non-zero and that the
    # difference between reported and collected size is less than 10%
    # (this is due to the fact that $MFT may be changing while being read).
    # Note that we have to take into account the fact that $MFT may be
    # larger than the FileFinderDownloadActionOptions.max_size setting.
    self.assertGreater(last_collected_size, 0)
    self.assertLess(
        abs(last_collected_size -
            min(ff_result.stat_entry.st_size, args.action.download.max_size)),
        int(last_collected_size * 0.1))

    # Make sure first chunk of the file is not empty.
    first_chunk = self.ReadFromFile(path, 1024)
    self.assertNotEqual(first_chunk, b"0" * 1024)

    # Check that fetched MFT can be read in its entirety.
    total_size = functools.reduce(operator.add,
                                  [len(blob) for blob in fd.GetBlob()], 0)
    self.assertEqual(total_size, last_collected_size)

  def testTSKLargeFileCollection(self):
    self._testTSKLargeFileCollection("FileFinder")

  def testTSKLargeFileCollectionClientFileFinder(self):
    self._testTSKLargeFileCollection("ClientFileFinder")


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

  def _testRandomDevice(self, flow):
    # Reading from /dev/urandom is an interesting test,
    # since the hash can't be precalculated and GRR will
    # be forced to use server-side generated hash. It triggers
    # branches in the code that are not triggered when collecting
    # ordinary files.
    len_to_read = 1024
    args = self.grr_api.types.CreateFlowArgs(flow)

    args.paths.append("/dev/urandom")
    args.action.action_type = args.action.DOWNLOAD
    args.action.download.max_size = len_to_read
    args.process_non_regular_files = True

    with self.WaitForFileCollection("fs/os/dev/urandom"):
      self.RunFlowAndWait(flow, args=args)

    f = self.client.File("fs/os/dev/urandom").Get()
    self.assertEqual(f.data.last_collected_size, len_to_read)
    self.assertEqual(f.data.hash.num_bytes, len_to_read)

  def testRandomDevice(self):
    self._testRandomDevice("FileFinder")

  def testCFFRandomDevice(self):
    self._testRandomDevice("ClientFileFinder")


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
    self.assertNotEmpty(results)


class TestFileFinderLiteralMatching(test_base.AbstractFileTransferTest):
  """Match files against a literal pattern with FileFinder."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN
  ]

  def _testLiteralMatching(self, flow):
    keywords = {
        test_base.EndToEndTest.Platform.LINUX: b"ELF",
        test_base.EndToEndTest.Platform.DARWIN: b"Apple",
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
        test_base.EndToEndTest.Platform.LINUX: b"E.F",
        test_base.EndToEndTest.Platform.DARWIN: b"Ap..e",
    }
    keywords = {
        test_base.EndToEndTest.Platform.LINUX: b"elf",
        test_base.EndToEndTest.Platform.DARWIN: b"apple",
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
