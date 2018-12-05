#!/usr/bin/env python
"""End to end tests for Yara based flows."""
from __future__ import absolute_import
from __future__ import division

import re

from grr_response_core import config
from grr_response_test.end_to_end_tests import test_base


def GetProcessName(platform):
  """Gets the process name for the different platforms.

  By default, this function will return:
    Windows: GRRservice.exe
    Linux: grrd
    Darwin: grr

  Args:
    platform: The platform the client under test is running on.

  Returns:
     The process name the test should use.

  Raises:
    ValueError: An unknown platform was passed.
  """
  if platform == test_base.EndToEndTest.Platform.WINDOWS:
    return config.CONFIG.Get("Client.binary_name", context=["Platform:Windows"])
  elif platform == test_base.EndToEndTest.Platform.LINUX:
    return config.CONFIG.Get("Client.binary_name", context=["Platform:Linux"])
  elif platform == test_base.EndToEndTest.Platform.DARWIN:
    return config.CONFIG.Get("Client.binary_name", context=["Platform:Darwin"])
  else:
    raise ValueError("Platform %s unknown" % platform)


def GetProcessNameRegex(platform):
  """Returns a regex that matches a process on the client under test."""

  return "^%s$" % GetProcessName(platform)


class TestYaraScan(test_base.EndToEndTest):
  """YaraScan test."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def runTest(self):

    signature = """
rule test_rule {
  meta:
    desc = "Just for testing."
  strings:
    $s1 = { 31 }
  condition:
    $s1
}
"""

    args = self.grr_api.types.CreateFlowArgs(flow_name="YaraProcessScan")
    args.yara_signature = signature
    args.process_regex = GetProcessNameRegex(self.platform)
    args.max_results_per_process = 2
    args.ignore_grr_process = False

    f = self.RunFlowAndWait("YaraProcessScan", args=args)

    all_results = list(f.ListResults())
    self.assertTrue(all_results,
                    "We expect results for at least one matching process.")

    for flow_result in all_results:
      process_scan_match = flow_result.payload

      self.assertLen(process_scan_match.match, 2)

      self.assertTrue(
          re.match(args.process_regex, process_scan_match.process.name),
          "Process name %s does not match regex %s" %
          (process_scan_match.process.name, args.process_regex))

      rules = set()

      for yara_match in process_scan_match.match:
        # Each hit has some offset + data
        self.assertTrue(yara_match.string_matches)

        for string_match in yara_match.string_matches:
          self.assertEqual(string_match.data, "1")

        rules.add(yara_match.rule_name)

      self.assertEqual(list(rules), ["test_rule"])

      # Ten seconds seems reasonable here, actual values are 0.5s.
      self.assertLess(process_scan_match.scan_time_us, 10 * 1e6)


class TestYaraProcessDump(test_base.AbstractFileTransferTest):
  """Yara process memory dump test."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs(flow_name="YaraDumpProcessMemory")
    process_name = GetProcessName(self.platform)
    args.process_regex = GetProcessNameRegex(self.platform)
    args.ignore_grr_process = False
    args.size_limit = 100 * 1024 * 1024

    f = self.RunFlowAndWait("YaraDumpProcessMemory", args=args)

    results = [x.payload for x in f.ListResults()]
    self.assertTrue(results, "Expected at least a YaraProcessDumpResponse.")
    process_dump_response = results[0]
    self.assertTrue(process_dump_response.dumped_processes,
                    "Expected at least one dumped process.")
    self.assertFalse(process_dump_response.errors)

    dump_file_count = 0
    paths_in_dump_response = set()
    for dump_info in process_dump_response.dumped_processes:
      self.assertEqual(dump_info.process.name, process_name)
      paths_in_dump_response.update(
          {f.path[f.path.find(process_name):] for f in dump_info.dump_files})
      self.assertTrue(dump_info.dump_files)
      dump_file_count += len(dump_info.dump_files)

    # There should be as many StatEntry responses as the total number of
    # dump-file PathSpecs in the YaraProcessDumpResponse.
    self.assertLen(results, dump_file_count + 1)

    paths_collected = set()
    for dump_file in results[1:]:
      paths_collected.add(
          dump_file.pathspec.path[dump_file.pathspec.path.find(process_name):])

      size = dump_file.st_size
      self.assertTrue(size)

      if size >= 10:
        data = self.ReadFromFile("temp%s" % dump_file.pathspec.path, 10)
        self.assertLen(data, 10)

    self.assertEqual(paths_in_dump_response, paths_collected)
