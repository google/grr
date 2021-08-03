#!/usr/bin/env python
import contextlib
import os
import platform
import unittest
from absl.testing import absltest
from grr_response_client import client_utils
from grr_response_client import streaming
from grr_response_client.unprivileged import communication
from grr_response_client.unprivileged import test_lib
from grr_response_client.unprivileged.memory import client
from grr_response_client.unprivileged.memory import server
from grr_response_client.unprivileged.proto import memory_pb2

_SEARCH_STRING = b"I am a test string, just for testing!!!!"

_SIGNATURE = """
    rule test_rule {
      meta:
        desc = "Just for testing."
      strings:
        $s1 = "I am a test string, just for testing!!!!"
      condition:
        $s1
    }
    """


@unittest.skipIf(platform.system() == "Darwin",
                 "Sandboxed memory scanning is not yet supported on OSX.")
class MemoryTest(absltest.TestCase):

  def setUp(self):
    super().setUp()
    stack = contextlib.ExitStack()
    self.addCleanup(stack.close)

    self._process = stack.enter_context(
        client_utils.OpenProcessForMemoryAccess(os.getpid()))
    self._process.Open()

    self._process_file_descriptor = (
        communication.FileDescriptor.FromSerialized(
            self._process.serialized_file_descriptor, communication.Mode.READ))

    self._server = stack.enter_context(
        server.CreateMemoryServer([self._process_file_descriptor]))
    self._client = client.Client(self._server.Connect())

  def testProcessScan(self):

    self._client.UploadSignature(_SIGNATURE)

    all_scan_matches = []

    for region in self._process.Regions():
      streamer = streaming.Streamer(
          chunk_size=1024 * 1024, overlap_size=32 * 1024)
      for chunk in streamer.StreamRanges(region.start, region.size):
        response = self._client.ProcessScan(
            self._process_file_descriptor.Serialize(),
            [memory_pb2.Chunk(offset=chunk.offset, size=chunk.amount)], 60)
        self.assertEqual(response.status,
                         memory_pb2.ProcessScanResponse.Status.NO_ERROR)
        all_scan_matches.extend(response.scan_result.scan_match)

    self.assertTrue(all_scan_matches)

    found_in_actual_memory_count = 0

    for scan_match in all_scan_matches:
      self.assertEqual(scan_match.rule_name, "test_rule")
      for string_match in scan_match.string_matches:
        self.assertEqual(string_match.string_id, "$s1")
        self.assertEqual(string_match.data, _SEARCH_STRING)
        # Check that the reported result resides in memory of the
        # scanned process.
        actual_memory = self._process.ReadBytes(string_match.offset,
                                                len(string_match.data))
        # Since copies of the string might be in dynamic memory, we won't be
        # able to read back every match. We'll check that at least one of the
        # reads succeeds later.
        if actual_memory == _SEARCH_STRING:
          found_in_actual_memory_count += 1

    self.assertTrue(found_in_actual_memory_count)


def setUpModule() -> None:
  test_lib.SetUpDummyConfig()


if __name__ == "__main__":
  absltest.main()
