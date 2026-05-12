#!/usr/bin/env python
"""End to end tests for memory flows."""

import binascii
import os
import pathlib
import re

from grr_response_test.end_to_end_tests import test_base


def _GetBinaryName(client):
  """Gets the GRR binary name on the client."""

  client_data = client.Get().data
  if client_data.rrg_args:
    # Simplest cross-platform way to get the binary name from the RRG args.
    rrg_path = client_data.rrg_args[0].replace("\\", "/")
    return pathlib.Path(rrg_path).name
  return client_data.agent_info.client_binary_name


def _GetProcessNameRegex(client):
  """Returns a regex that matches a process on the client under test."""

  return "^%s$" % _GetBinaryName(client)


class TestYaraScanSignature(test_base.EndToEndTest):
  """YaraScanSignature test."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.WINDOWS,
  ]

  def testYaraSignature(self):
    # `GRR` is name of the destination service the agents use when sending
    # messages through Fleetspeak, so the string should exist somewhere in the
    # memory.
    signature = """
rule test_rule {
  meta:
    desc = "Just for testing."
  strings:
    $grr = "GRR"
  condition:
    $grr
}
"""

    args = self.grr_api.types.CreateFlowArgs(flow_name="YaraProcessScan")
    args.yara_signature = signature
    args.process_regex = _GetProcessNameRegex(self.client)
    args.max_results_per_process = 2
    args.ignore_grr_process = False

    f = self.RunFlowAndWait("YaraProcessScan", args=args)

    all_results = list(f.ListResults())
    self.assertNotEmpty(
        all_results, "We expect results for at least one matching process."
    )

    for flow_result in all_results:
      process_scan_match = flow_result.payload

      self.assertTrue(
          re.match(args.process_regex, process_scan_match.process.name),
          "Process name %s does not match regex %s"
          % (process_scan_match.process.name, args.process_regex),
      )

      rules = set()

      for yara_match in process_scan_match.match:
        # Each hit has some offset + data
        self.assertTrue(yara_match.string_matches)

        for string_match in yara_match.string_matches:
          self.assertEqual(string_match.data, b"GRR")

        rules.add(yara_match.rule_name)

      self.assertEqual(list(rules), ["test_rule"])

      # 20 seconds seems reasonable here, actual values are 0.5s.
      # TODO - Consider re-enabling this check
      # if `scan_time_us` is populated from RRG.
      # self.assertLess(process_scan_match.scan_time_us, 20 * 1e6)


class TestYaraScanSignatureReference(test_base.EndToEndTest):
  """TestYaraScanSignatureReference test."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.WINDOWS,
  ]

  def testYaraScanSignatureReference(self):
    # `GRR` is name of the destination service the agents use when sending
    # messages through Fleetspeak, so the string should exist somewhere in the
    # memory.
    signature = """
rule foo {
  strings:
    $grr = "GRR"
  condition:
    $grr
}
"""

    args = self.grr_api.types.CreateFlowArgs(flow_name="YaraProcessScan")
    args.yara_signature_blob_id = self.grr_api.UploadYaraSignature(signature)
    args.process_regex = _GetProcessNameRegex(self.client)
    args.ignore_grr_process = False

    flow = self.RunFlowAndWait("YaraProcessScan", args=args)
    results = list(flow.ListResults())

    self.assertNotEmpty(results)

  def testYaraScanSignatureReferenceFilestore(self):
    # `GRR` is name of the destination service the agents use when sending
    # messages through Fleetspeak, so the string should exist somewhere in the
    # memory.
    #
    # We also put some large string in the signature (that we do not really need
    # to find) just to force the signature to be uploaded to filestore (small
    # signatures are sent "inline") first.
    #
    # TODO - Using condition with a long string seems to hang the
    # process, so for now we lengthen the signature by adding a long comment.
    signature = f"""
    /* {binascii.hexlify(os.urandom(2 * 1024 * 1024)).decode("ascii")} */
rule foo {{
  strings:
    $grr = "GRR"
  condition:
    $grr
}}
"""

    args = self.grr_api.types.CreateFlowArgs(flow_name="YaraProcessScan")
    args.yara_signature_blob_id = self.grr_api.UploadYaraSignature(signature)
    args.process_regex = _GetProcessNameRegex(self.client)
    args.ignore_grr_process = False

    flow = self.RunFlowAndWait("YaraProcessScan", args=args)
    results = list(flow.ListResults())

    self.assertNotEmpty(results)


class TestProcessDump(test_base.AbstractFileTransferTest):
  """Process memory dump test."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.WINDOWS,
  ]

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
    self.assertNotEmpty(
        process_dump_response.dumped_processes,
        "Expected at least one dumped process.",
    )
    self.assertEmpty(process_dump_response.errors)

    dump_file_count = 0
    pathspecs_in_dump_response = []
    for dump_info in process_dump_response.dumped_processes:
      self.assertEqual(dump_info.process.name, process_name)
      for area in dump_info.memory_regions:
        pathspecs_in_dump_response.append(area.file)
      self.assertNotEmpty(dump_info.memory_regions)
      dump_file_count += len(dump_info.memory_regions)

    for dump_pathspec in pathspecs_in_dump_response:
      data = self.ReadFromFile(self.TempPathspecToVFSPath(dump_pathspec), 10)
      self.assertLen(data, 10)
