#!/usr/bin/env python
"""End to end tests for client resource limits."""
from __future__ import absolute_import
from __future__ import division

from grr_response_test.end_to_end_tests import test_base


class TestNetworkFlowLimit(test_base.EndToEndTest):
  """Test limit on bytes transferred for a flow."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN,
  ]

  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("GetFile")
    args.pathspec.path = "/dev/urandom"
    args.pathspec.pathtype = args.pathspec.OS
    args.read_length = 1024 * 1024

    runner_args = self.grr_api.types.CreateFlowRunnerArgs()
    runner_args.network_bytes_limit = 500 * 1024

    try:
      self.RunFlowAndWait("GetFile", args=args, runner_args=runner_args)
      self.fail("RunFlowAndWait was supposed to throw an error.")
    except test_base.RunFlowAndWaitError as e:
      self.assertAlmostEqual(
          e.flow.data.context.network_bytes_sent, 500 * 1024, delta=30000)
      self.assertTrue(e.flow.data.context.backtrace)
      self.assertIn("Network bytes limit exceeded.",
                    e.flow.data.context.backtrace)
