#!/usr/bin/env python
"""End to end tests for GRR administrative flows."""

import signal

from grr_response_proto import flows_pb2
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

    args = self.grr_api.types.CreateFlowArgs(flow_name="LaunchBinary")  # pyrefly: ignore[missing-attribute]
    args.binary = binary_names[self.platform]
    f = self.RunFlowAndWait("LaunchBinary", args=args)

    logs = "\n".join(l.log_message for l in f.ListLogs())
    self.assertIn("Hello world", logs)


class TestLaunchExecutable(test_base.EndToEndTest):
  """End-to-end test for the `LaunchExecutable` flow."""

  platforms = [
      test_base.EndToEndTest.Platform.DARWIN,
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.WINDOWS,
  ]

  def runTest(self):
    args = flows_pb2.LaunchExecutableArgs()
    args.signed_command_id = "e2e_hello"
    args.timeout.seconds = 10

    flow = self.RunFlowAndWait("LaunchExecutable", args=args)

    results = list(flow.ListResults())
    self.assertLen(results, 1)
    self.assertEqual(results[0].payload.exit_code, 0)
    self.assertEqual(results[0].payload.stdout, b"Hello world")


class TestLaunchExecutableExitCode(test_base.EndToEndTest):
  """End-to-end test for the `LaunchExecutable` flow."""

  platforms = [
      test_base.EndToEndTest.Platform.DARWIN,
      test_base.EndToEndTest.Platform.LINUX,
  ]

  def runTest(self):
    args = flows_pb2.LaunchExecutableArgs()
    args.signed_command_id = "e2e_exit42"
    args.timeout.seconds = 10

    flow = self.RunFlowAndWait("LaunchExecutable", args=args)

    results = list(flow.ListResults())
    self.assertLen(results, 1)
    self.assertEqual(results[0].payload.exit_code, 42)


class TestLaunchExecutableTimeout(test_base.EndToEndTest):
  """End-to-end test for the `LaunchExecutable` flow."""

  platforms = [
      test_base.EndToEndTest.Platform.DARWIN,
      test_base.EndToEndTest.Platform.LINUX,
  ]

  def runTest(self):
    args = flows_pb2.LaunchExecutableArgs()
    args.signed_command_id = "e2e_sleep"
    args.timeout.seconds = 0
    args.timeout.nanos = 1

    flow = self.RunFlowAndWait("LaunchExecutable", args=args)

    results = list(flow.ListResults())
    self.assertLen(results, 1)
    self.assertTrue(results[0].payload.timeout_reached)
    self.assertEqual(results[0].payload.exit_signal, signal.SIGKILL)
