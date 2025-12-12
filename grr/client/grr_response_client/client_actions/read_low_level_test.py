#!/usr/bin/env python
import hashlib

from absl import app

from grr_response_client.client_actions import read_low_level
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import read_low_level as rdf_read_low_level
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


class ReadLowLevelTest(client_test_lib.EmptyActionTest):
  """Test ReadLowLevel action."""

  def testReadsOneAlignedChunk(self):
    temp_file = self.create_tempfile()
    temp_file.write_bytes(b"123456")

    request1 = rdf_read_low_level.ReadLowLevelRequest(
        path=temp_file.full_path, length=1
    )  # offset should default to 0

    # We call ExecuteAction rather than RunAction because we need the
    # the ClientAction `message` set in order to call `ChargeBytesToSession`.
    results = self.ExecuteAction(read_low_level.ReadLowLevel, request1)

    # One buffer reference, and one status message.
    self.assertLen(results, 2)

    self.assertIsInstance(results[0], rdf_read_low_level.ReadLowLevelResult)
    self.assertEqual(1, results[0].blob.length)
    self.assertEqual(0, results[0].blob.offset)
    self.assertEqual(hashlib.sha256(b"1").digest(), results[0].blob.data)
    self.assertEqual(hashlib.sha256(b"1").digest(), results[0].accumulated_hash)

    self.assertIsInstance(results[1], rdf_flows.GrrStatus)
    self.assertEqual(rdf_flows.GrrStatus.ReturnedStatus.OK, results[1].status)
    self.assertEmpty(results[1].error_message)

  def testReadsOneMisalignedChunk(self):
    temp_file = self.create_tempfile()
    temp_file.write_bytes(b"123456")

    request23 = rdf_read_low_level.ReadLowLevelRequest(
        path=temp_file.full_path, length=2, offset=1
    )

    # We call ExecuteAction rather than RunAction because we need the
    # the ClientAction `message` set in order to call `ChargeBytesToSession`.
    results = self.ExecuteAction(read_low_level.ReadLowLevel, request23)

    # One buffer reference, and one status message.
    self.assertLen(results, 2)

    self.assertIsInstance(results[0], rdf_read_low_level.ReadLowLevelResult)
    self.assertEqual(2, results[0].blob.length)
    self.assertEqual(0, results[0].blob.offset)
    self.assertEqual(hashlib.sha256(b"23").digest(), results[0].blob.data)
    self.assertEqual(
        hashlib.sha256(b"23").digest(), results[0].accumulated_hash
    )

    self.assertIsInstance(results[1], rdf_flows.GrrStatus)
    self.assertEqual(rdf_flows.GrrStatus.ReturnedStatus.OK, results[1].status)
    self.assertEmpty(results[1].error_message)

  def testReadsMultipleMisalignedChunks(self):
    temp_file = self.create_tempfile()
    temp_file.write_bytes(b"123456")

    # Worth noting that blob_size=1 here will mean unaligned reads for blobs
    # 2 and 3.
    # TODO: Update test when blob size is also "aligned"
    request23_2blobs = rdf_read_low_level.ReadLowLevelRequest(
        path=temp_file.full_path, length=2, offset=1, blob_size=1
    )

    # We call ExecuteAction rather than RunAction because we need the
    # the ClientAction `message` set in order to call `ChargeBytesToSession`.
    results = self.ExecuteAction(read_low_level.ReadLowLevel, request23_2blobs)

    # Two buffer references (each one with one byte), and one status message.
    self.assertLen(results, 3)

    self.assertIsInstance(results[0], rdf_read_low_level.ReadLowLevelResult)
    self.assertEqual(1, results[0].blob.length)
    self.assertEqual(0, results[0].blob.offset)  # 'corrected' offset
    self.assertEqual(hashlib.sha256(b"2").digest(), results[0].blob.data)
    self.assertEqual(hashlib.sha256(b"2").digest(), results[0].accumulated_hash)

    self.assertIsInstance(results[1], rdf_read_low_level.ReadLowLevelResult)
    self.assertEqual(1, results[1].blob.length)
    self.assertEqual(1, results[1].blob.offset)  # 'corrected' offset
    self.assertEqual(hashlib.sha256(b"3").digest(), results[1].blob.data)
    self.assertEqual(
        hashlib.sha256(b"23").digest(), results[1].accumulated_hash
    )

    self.assertIsInstance(results[2], rdf_flows.GrrStatus)
    self.assertEqual(rdf_flows.GrrStatus.ReturnedStatus.OK, results[2].status)
    self.assertEmpty(results[2].error_message)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
