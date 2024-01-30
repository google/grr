#!/usr/bin/env python
"""End to end tests for GRR administrative flows."""

from grr_response_test.end_to_end_tests import test_base


class TestLaunchBinaries(test_base.EndToEndTest):

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.WINDOWS
  ]

  def runTest(self):
    binary_names = {
        test_base.EndToEndTest.Platform.WINDOWS:
            "aff4:/config/executables/windows/test/win_hello.exe",
        test_base.EndToEndTest.Platform.LINUX:
            "aff4:/config/executables/linux/test/linux_hello"
    }

    args = self.grr_api.types.CreateFlowArgs(flow_name="LaunchBinary")
    args.binary = binary_names[self.platform]
    f = self.RunFlowAndWait("LaunchBinary", args=args)

    logs = "\n".join(l.log_message for l in f.ListLogs())
    self.assertIn("Hello world", logs)
