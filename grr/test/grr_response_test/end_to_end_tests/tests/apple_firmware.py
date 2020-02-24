#!/usr/bin/env python
"""End to end tests for memory flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_test.end_to_end_tests import test_base


class TestCollectEfiHashes(test_base.EndToEndTest):
  """E2E test for CollectEfiHashes flow."""

  platforms = [test_base.EndToEndTest.Platform.DARWIN]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs(flow_name="CollectEfiHashes")
    f = self.RunFlowAndWait("CollectEfiHashes", args=args)

    results = [x.payload for x in f.ListResults()]
    self.assertNotEmpty(results, "Expected at least one EfiCollection.")

    for result in results:  # EfiCollection.
      self.assertNotEmpty(result.eficheck_version)
      self.assertNotEmpty(result.boot_rom_version)

      self.assertNotEmpty(result.entries)
      for entry in result.entries:  # EfiEntry.
        self.assertNotEmpty(entry.hash)


class TestDumpEfiImage(test_base.AbstractFileTransferTest):
  """E2E test for DumpEfiImage flow."""

  platforms = [test_base.EndToEndTest.Platform.DARWIN]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs(flow_name="DumpEfiImage")

    f = self.RunFlowAndWait("DumpEfiImage", args=args)

    results = [x.payload for x in f.ListResults()]
    self.assertLen(results, 1)

    response = results[0]  # DumpEfiImageResponse
    self.assertNotEmpty(response.eficheck_version)
    self.assertNotEmpty(response.path.path)
    self.assertNotEmpty(
        self.ReadFromFile("/temp{}".format(response.path.path), -1))
