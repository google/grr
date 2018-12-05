#!/usr/bin/env python
"""End to end tests for GRR administrative flows."""
from __future__ import absolute_import
from __future__ import division

from grr_response_test.end_to_end_tests import test_base


class TestGetClientStats(test_base.EndToEndTest):
  """GetClientStats test."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def runTest(self):
    f = self.RunFlowAndWait("GetClientStats")

    results = list(f.ListResults())
    self.assertTrue(results)

    cstats = results[0].payload
    self.assertGreater(len(cstats.cpu_samples), 0)
    if self.platform != test_base.EndToEndTest.Platform.DARWIN:
      # No io counters on mac.
      self.assertGreater(len(cstats.io_samples), 0)

    self.assertGreater(cstats.RSS_size, 0)
    self.assertGreater(cstats.VMS_size, 0)
    self.assertGreater(cstats.boot_time, 0)
    self.assertGreater(cstats.bytes_received, 0)
    self.assertGreater(cstats.bytes_sent, 0)
    self.assertGreater(cstats.memory_percent, 0)


class TestLaunchBinaries(test_base.EndToEndTest):

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.WINDOWS
  ]

  def runTest(self):
    binary_names = {
        test_base.EndToEndTest.Platform.WINDOWS:
            "aff4:/config/executables/windows/test/hello.exe",
        test_base.EndToEndTest.Platform.LINUX:
            "aff4:/config/executables/linux/test/hello"
    }

    args = self.grr_api.types.CreateFlowArgs(flow_name="LaunchBinary")
    args.binary = binary_names[self.platform]
    f = self.RunFlowAndWait("LaunchBinary", args=args)

    logs = "\n".join(l.log_message for l in f.ListLogs())
    self.assertIn("Hello world", logs)
