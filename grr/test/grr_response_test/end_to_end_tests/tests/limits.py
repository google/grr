#!/usr/bin/env python
"""End to end tests for client resource limits."""

from grr_response_test.end_to_end_tests import test_base


class TestNetworkFlowLimit(test_base.EndToEndTest):
  """Test limit on bytes transferred for a flow."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN,
  ]

  # TODO(user): this test depends on the internals of the MultiGetFile
  # implementation (its chunk size setting). It should be rewritten
  # to be MultiGetFile implementation-agnostic.
  #
  # NOTE: given the MultiGetFile's implementation, this test effectively checks
  # that if multiple CallClient calls are done from a particular flow state
  # handler, and then the results of these calls are delivered in the same batch
  # and get processed, then if processing one of the results leads to the flow's
  # failure, the processing is stopped and other responses are ignored.
  #
  # Please see the FlowBase.ProcessAllReadyRequests in the flow_base.py for
  # more details.
  def runTest(self):
    args = self.grr_api.types.CreateFlowArgs("MultiGetFile")
    pathspec = args.pathspecs.add()
    pathspec.path = "/dev/urandom"
    pathspec.pathtype = pathspec.OS
    args.file_size = 1024 * 1024

    runner_args = self.grr_api.types.CreateFlowRunnerArgs()
    runner_args.network_bytes_limit = 500 * 1024

    try:
      self.RunFlowAndWait("MultiGetFile", args=args, runner_args=runner_args)
      self.fail("RunFlowAndWait was supposed to throw an error.")
    except test_base.RunFlowAndWaitError as e:
      self.assertAlmostEqual(
          e.flow.data.context.network_bytes_sent, 500 * 1024, delta=30000)
      self.assertIn("Network bytes limit exceeded", e.flow.data.context.status)
