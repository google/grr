#!/usr/bin/env python
"""End to end tests for GRR FileFinder flow."""

import functools
import io
import operator

from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_test.end_to_end_tests import test_base


class TestFileFinderOSWindows(test_base.AbstractFileTransferTest):
  """Test for FileFinder flow on Windows machines."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def testCollection(self):
    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]
    args.paths.append("%%environ_systemroot%%\\SYsTEm32\\notepad.*")

    condition = args.conditions.add()
    condition.condition_type = condition.SIZE
    condition.size.max_file_size = 1000000
    args.action.action_type = args.action.DOWNLOAD

    flow = self.RunFlowAndWait("FileFinder", args=args)
    flow_results = list(flow.ListResults())
    self.assertLen(flow_results, 1)

    result_path = flow_results[0].payload.stat_entry.pathspec.path
    # TODO - The path returned by the old agent will have a leading
    # `/` (which makes no sense on Windows) so we strip it. We can remove this
    # workaround once we no longer test with the old agent.
    result_path = result_path.removeprefix("/")
    self.assertEqual(result_path.lower(), "c:/windows/system32/notepad.exe")

    result_content = io.BytesIO()

    result_file = self.client.File(f"fs/os/{result_path}")  # pyrefly: ignore[missing-attribute]
    result_file.GetBlob().WriteToStream(result_content)

    self.assertEqual(result_content.getvalue()[0:2], b"MZ")


class TestFileFinderNTFSWindows(test_base.AbstractFileTransferTest):
  """Test for the file-finder flow with raw filesystem access on Windows."""

  platforms = [test_base.EndToEndTest.Platform.WINDOWS]

  def _pathspecToVFSPath(self, pathspec):
    path = "fs/ntfs/"
    while pathspec.path:
      path += pathspec.path
      pathspec = pathspec.nested_path

    return path

  def testListing(self):
    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]
    args.paths.append("C:\\*")
    args.action.action_type = args.action.STAT
    args.pathtype = jobs_pb2.PathSpec.NTFS

    f = self.RunFlowAndWait("FileFinder", args=args)
    results = list(f.ListResults())
    self.assertNotEmpty(results)

  def testSmallFileCollection(self):
    # TODO - Remove once Keramics is enabled by default.
    runner_args = flows_pb2.FlowRunnerArgs()
    runner_args.rrg_mode = flows_pb2.FlowRunnerArgs.RrgMode.FORCED

    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]

    # TODO - Revert back to Notepad once Keramics is fixed.
    args.paths.append("%%environ_systemroot%%\\system.ini")
    args.action.action_type = args.action.DOWNLOAD
    args.pathtype = jobs_pb2.PathSpec.NTFS

    f = self.RunFlowAndWait("FileFinder", args=args, runner_args=runner_args)
    results = list(f.ListResults())
    self.assertNotEmpty(results)

    ff_result = results[0].payload
    path = self._pathspecToVFSPath(ff_result.stat_entry.pathspec)

    # Run FileFinder again and make sure the path gets updated on VFS.
    with self.WaitForFileRefresh(path):
      f = self.RunFlowAndWait("FileFinder", args=args, runner_args=runner_args)
      results = list(f.ListResults())
      self.assertNotEmpty(results)

    # TODO - Verify PEM once we collect an executable again.
    self.assertEqual(self.ReadFromFile(path, num_bytes=2), b"; ")

  def testLargeFileCollection(self):
    # TODO - Remove once Keramics is enabled by default.
    runner_args = flows_pb2.FlowRunnerArgs()
    runner_args.rrg_mode = flows_pb2.FlowRunnerArgs.RrgMode.FORCED

    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]
    # TODO - Revert back to Notepad once Keramics is fixed.
    args.paths.append("%%environ_systemroot%%\\system.ini")
    # TODO - We use `OS` path here because we use this flow only to
    # get file metadata and in case of `NTFS` path the old agent will mangle the
    # path to a volume path (it will return something like `\?\Volume{...}` that
    # will screw up the logic afterwards (as RRG will not mangle the path when
    # collecting content).
    args.pathtype = jobs_pb2.PathSpec.OS
    args.action.action_type = args.action.STAT

    f = self.RunFlowAndWait("FileFinder", args=args, runner_args=runner_args)
    results = list(f.ListResults())
    self.assertNotEmpty(results)

    ff_result = results[0].payload
    path = self._pathspecToVFSPath(ff_result.stat_entry.pathspec)

    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]
    # TODO - Revert back to Notepad once Keramics is fixed.
    args.paths.append("%%environ_systemroot%%\\system.ini")
    args.pathtype = jobs_pb2.PathSpec.NTFS
    args.action.action_type = args.action.DOWNLOAD
    args.action.download.oversized_file_policy = (
        args.action.download.DOWNLOAD_TRUNCATED)

    with self.WaitForFileRefresh(path):
      self.RunFlowAndWait("FileFinder", args=args, runner_args=runner_args)

    fd = self.client.File(path)  # pyrefly: ignore[missing-attribute]
    last_collected_size = fd.Get().data.last_collected_size

    self.assertGreater(last_collected_size, 0)
    self.assertEqual(
        last_collected_size,
        min(ff_result.stat_entry.st_size, args.action.download.max_size))

    # Make sure first chunk of the file is not empty.
    first_chunk = self.ReadFromFile(path, 1024)
    self.assertNotEqual(first_chunk, b"0" * 1024)

    # Check that fetched file can be read in its entirety.
    total_size = functools.reduce(operator.add,
                                  [len(blob) for blob in fd.GetBlob()], 0)
    self.assertEqual(total_size, last_collected_size)


class TestFileFinderOSDarwin(test_base.AbstractFileTransferTest):
  """Tests the file finder and the client file finder on Darwin e2e."""

  platforms = [test_base.EndToEndTest.Platform.DARWIN]

  flow = "FileFinder"

  def testCollection(self):
    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]
    args.paths.append("/bin/ps")
    args.action.action_type = args.action.DOWNLOAD

    path = "fs/os/bin/ps"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait("FileFinder", args=args)

    self.CheckMacMagic(path)

  def testRandomDevice(self):
    # Reading from /dev/urandom is an interesting test,
    # since the hash can't be precalculated and GRR will
    # be forced to use server-side generated hash. It triggers
    # branches in the code that are not triggered when collecting
    # ordinary files.
    # Reading 400 megabytes to put additional load on the client send-queues
    # and activate the heartbeating logic.
    len_to_read = 1024 * 1024 * 400
    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]

    args.paths.append("/dev/urandom")
    args.action.action_type = args.action.DOWNLOAD
    args.action.download.max_size = len_to_read
    args.process_non_regular_files = True

    with self.WaitForFileCollection("fs/os/dev/urandom"):
      self.RunFlowAndWait("FileFinder", args=args)

    f = self.client.File("fs/os/dev/urandom").Get()  # pyrefly: ignore[missing-attribute]
    self.assertEqual(f.data.last_collected_size, len_to_read)
    self.assertEqual(f.data.hash.num_bytes, len_to_read)


class TestFileFinderOSLinux(test_base.AbstractFileTransferTest):
  """Test for FileFinder on Linux machines."""

  platforms = [test_base.EndToEndTest.Platform.LINUX]

  def testRegularFile(self):
    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]

    args.paths.append("/bin/ps")
    condition = args.conditions.add()
    condition.condition_type = condition.SIZE
    condition.size.max_file_size = 1000000
    args.action.action_type = args.action.DOWNLOAD

    path = "fs/os/bin/ps"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait("FileFinder", args=args)

    self.CheckELFMagic(path)

  def testProcFile(self):
    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]

    args.paths.append("/proc/sys/net/ipv4/ip_forward")
    condition = args.conditions.add()
    condition.condition_type = condition.SIZE
    condition.size.max_file_size = 1000000
    args.action.action_type = args.action.DOWNLOAD

    path = "fs/os/proc/sys/net/ipv4/ip_forward"
    with self.WaitForFileCollection(path):
      self.RunFlowAndWait("FileFinder", args=args)

  def testRandomDevice(self):
    # Reading from /dev/urandom is an interesting test,
    # since the hash can't be precalculated and GRR will
    # be forced to use server-side generated hash. It triggers
    # branches in the code that are not triggered when collecting
    # ordinary files.
    # Reading 400 megabytes to put additional load on the client send-queues
    # and activate the heartbeating logic.
    len_to_read = 1024 * 1024 * 400
    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]

    args.paths.append("/dev/urandom")
    args.action.action_type = args.action.DOWNLOAD
    args.action.download.max_size = len_to_read
    args.process_non_regular_files = True

    with self.WaitForFileCollection("fs/os/dev/urandom"):
      self.RunFlowAndWait("FileFinder", args=args)

    f = self.client.File("fs/os/dev/urandom").Get()  # pyrefly: ignore[missing-attribute]
    self.assertEqual(f.data.last_collected_size, len_to_read)
    self.assertEqual(f.data.hash.num_bytes, len_to_read)


class TestFileFinderOSHomedir(test_base.AbstractFileTransferTest):
  """List files in homedir with FileFinder."""

  platforms = test_base.EndToEndTest.Platform.ALL

  flow = "FileFinder"

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs(self.flow)  # pyrefly: ignore[missing-attribute]

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

  def testLiteralMatching(self):
    keywords = {
        test_base.EndToEndTest.Platform.LINUX: b"ELF",
        test_base.EndToEndTest.Platform.DARWIN: b"Apple",
    }

    keyword = keywords[self.platform]

    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]
    args.paths.append("/bin/ls")
    condition = args.conditions.add()
    condition.condition_type = condition.CONTENTS_LITERAL_MATCH
    condition.contents_literal_match.literal = keyword
    condition_max_size = args.conditions.add()
    condition_max_size.condition_type = condition.SIZE
    condition_max_size.size.max_file_size = 10 * 1024 * 1024  # 10 MiB.
    args.action.action_type = args.action.STAT

    f = self.RunFlowAndWait("FileFinder", args=args)

    results = list(f.ListResults())
    self.assertLen(results, 1)
    result = results[0].payload

    self.assertIn("ls", result.stat_entry.pathspec.path)


class TestFileFinderRegexMatching(test_base.AbstractFileTransferTest):
  """Match files against a regex pattern with FileFinder."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN
  ]

  def testRegexMatching(self):
    regexes = {
        test_base.EndToEndTest.Platform.LINUX: b"E.F",
        test_base.EndToEndTest.Platform.DARWIN: b"Ap..e",
    }

    args = self.grr_api.types.CreateFlowArgs("FileFinder")  # pyrefly: ignore[missing-attribute]
    args.paths.append("/bin/ls")
    condition = args.conditions.add()
    condition.condition_type = condition.CONTENTS_REGEX_MATCH
    condition.contents_regex_match.regex = regexes[self.platform]
    condition_max_size = args.conditions.add()
    condition_max_size.condition_type = condition.SIZE
    condition_max_size.size.max_file_size = 10 * 1024 * 1024  # 10 MiB.
    args.action.action_type = args.action.STAT

    f = self.RunFlowAndWait("FileFinder", args=args)

    results = list(f.ListResults())
    self.assertLen(results, 1)
    result = results[0].payload

    self.assertIn("ls", result.stat_entry.pathspec.path)
