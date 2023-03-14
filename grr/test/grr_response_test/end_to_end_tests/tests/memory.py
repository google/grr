#!/usr/bin/env python
"""End to end tests for memory flows."""

import random
import re
import string

from grr_response_test.end_to_end_tests import test_base


def _GetBinaryName(client):
  """Gets the GRR binary name on the client."""

  client_data = client.Get().data
  return client_data.agent_info.client_binary_name


def _GetProcessNameRegex(client):
  """Returns a regex that matches a process on the client under test."""

  return "^%s$" % _GetBinaryName(client)


class TestYaraScanSignature(test_base.EndToEndTest):
  """YaraScanSignature test."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def testYaraSignature(self):

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
    args.process_regex = _GetProcessNameRegex(self.client)
    args.max_results_per_process = 2
    args.ignore_grr_process = False

    f = self.RunFlowAndWait("YaraProcessScan", args=args)

    all_results = list(f.ListResults())
    self.assertNotEmpty(all_results,
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
          self.assertEqual(string_match.data, b"1")

        rules.add(yara_match.rule_name)

      self.assertEqual(list(rules), ["test_rule"])

      # 20 seconds seems reasonable here, actual values are 0.5s.
      self.assertLess(process_scan_match.scan_time_us, 20 * 1e6)


class TestYaraScanSignatureReference(test_base.EndToEndTest):
  """TestYaraScanSignatureReference test."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.WINDOWS,
  ]

  def testYaraScanSignatureReference(self):
    text = "".join(random.choice(string.ascii_letters) for _ in range(256))

    signature = """\
rule foo {{
  strings:
    $test = "{}"
  condition:
    $test
}}
""".format(text)

    args = self.grr_api.types.CreateFlowArgs(flow_name="YaraProcessScan")
    args.yara_signature_blob_id = self.grr_api.UploadYaraSignature(signature)
    args.process_regex = _GetProcessNameRegex(self.client)
    args.ignore_grr_process = False

    flow = self.RunFlowAndWait("YaraProcessScan", args=args)
    results = list(flow.ListResults())

    self.assertNotEmpty(results)


class TestProcessDump(test_base.AbstractFileTransferTest):
  """Process memory dump test."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs(flow_name="DumpProcessMemory")
    process_name = _GetBinaryName(self.client)
    args.process_regex = _GetProcessNameRegex(self.client)
    args.ignore_grr_process = False
    args.size_limit = 1024 * 1024

    f = self.RunFlowAndWait("DumpProcessMemory", args=args)

    results = [x.payload for x in f.ListResults()]
    self.assertNotEmpty(results, "Expected at least a YaraProcessDumpResponse.")
    process_dump_response = results[0]
    self.assertNotEmpty(process_dump_response.dumped_processes,
                        "Expected at least one dumped process.")
    self.assertEmpty(process_dump_response.errors)

    dump_file_count = 0
    paths_in_dump_response = set()
    for dump_info in process_dump_response.dumped_processes:
      self.assertEqual(dump_info.process.name, process_name)
      for area in dump_info.memory_regions:
        paths_in_dump_response.add(area.file.path)
      self.assertNotEmpty(dump_info.memory_regions)
      dump_file_count += len(dump_info.memory_regions)

    # There should be as many StatEntry responses as the total number of
    # dump-file PathSpecs in the YaraProcessDumpResponse.
    self.assertLen(results, dump_file_count + 1)

    paths_collected = set()
    for dump_file in results[1:]:
      paths_collected.add(dump_file.pathspec.path)

      size = dump_file.st_size
      self.assertGreater(size, 0)

      if size >= 10:
        data = self.ReadFromFile("temp%s" % dump_file.pathspec.path, 10)
        self.assertLen(data, 10)

    self.assertEqual(paths_in_dump_response, paths_collected)
