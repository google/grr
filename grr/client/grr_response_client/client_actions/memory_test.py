#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from absl import app

from grr_response_client.client_actions import memory
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


class YaraProcessScanTest(client_test_lib.EmptyActionTest):

  def setUp(self):
    super(YaraProcessScanTest, self).setUp()

    config_overrider = test_lib.ConfigOverrider({
        "Client.tempdir_roots": [self.temp_dir],
        "Client.grr_tempdir": "GRRTest",
    })
    config_overrider.Start()
    self.addCleanup(config_overrider.Stop)

  def testSignatureShards_Multiple(self):
    requests = [
        rdf_memory.YaraProcessScanRequest(
            signature_shard=rdf_memory.YaraSignatureShard(
                index=0, payload=b"123"),
            num_signature_shards=3),
        rdf_memory.YaraProcessScanRequest(
            signature_shard=rdf_memory.YaraSignatureShard(
                index=1, payload=b"456"),
            num_signature_shards=3),
        rdf_memory.YaraProcessScanRequest(
            signature_shard=rdf_memory.YaraSignatureShard(
                index=2, payload=b"789"),
            num_signature_shards=3),
    ]
    flow_id = "01234567"
    signature_dir = os.path.join(self.temp_dir, "GRRTest", "Sig_%s" % flow_id)
    session_id = "C.0123456789abcdef/%s" % flow_id

    results = self.ExecuteAction(
        memory.YaraProcessScan, arg=requests[2], session_id=session_id)
    self.assertLen(results, 1)
    self.assertIsInstance(results[0], rdf_flows.GrrStatus)
    self.assertTrue(os.path.isdir(signature_dir))
    self.assertCountEqual(os.listdir(signature_dir), ["shard_02_of_03"])
    with open(os.path.join(signature_dir, "shard_02_of_03"), "rb") as f:
      self.assertEqual(f.read(), b"789")

    results = self.ExecuteAction(
        memory.YaraProcessScan, arg=requests[0], session_id=session_id)
    self.assertLen(results, 1)
    self.assertIsInstance(results[0], rdf_flows.GrrStatus)
    self.assertCountEqual(
        os.listdir(signature_dir), ["shard_00_of_03", "shard_02_of_03"])
    with open(os.path.join(signature_dir, "shard_00_of_03"), "rb") as f:
      self.assertEqual(f.read(), b"123")

    results = self.ExecuteAction(
        memory.YaraProcessScan, arg=requests[1], session_id=session_id)
    # We expect at least one YaraProcessScanResponse and a final GrrStatus.
    self.assertGreater(len(results), 1)
    self.assertIsInstance(results[0], rdf_memory.YaraProcessScanResponse)
    self.assertIsInstance(results[-1], rdf_flows.GrrStatus)
    # The Yara signature provided is invalid, so we expect errors.
    self.assertNotEmpty(results[0].errors)
    # Make sure the temporary directory gets deleted when all shards have
    # been received.
    self.assertFalse(os.path.exists(signature_dir))

  def testSignatureShards_Single(self):
    flow_id = "01234567"
    signature_dir = os.path.join(self.temp_dir, "GRRTest", "Sig_%s" % flow_id)
    session_id = "C.0123456789abcdef/%s" % flow_id
    scan_request = rdf_memory.YaraProcessScanRequest(
        signature_shard=rdf_memory.YaraSignatureShard(index=0, payload=b"123"),
        num_signature_shards=1)

    results = self.ExecuteAction(
        memory.YaraProcessScan, arg=scan_request, session_id=session_id)
    # We expect at least one YaraProcessScanResponse and a final GrrStatus.
    self.assertGreater(len(results), 1)
    self.assertIsInstance(results[0], rdf_memory.YaraProcessScanResponse)
    self.assertIsInstance(results[-1], rdf_flows.GrrStatus)
    # The temporary directory should not get created if there is only one
    # shard.
    self.assertFalse(os.path.exists(signature_dir))


if __name__ == "__main__":
  app.run(test_lib.main)
