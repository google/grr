#!/usr/bin/env python
"""End to end tests for client resource limits."""

from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_test.end_to_end_tests import test_base


class TestNetworkFlowLimit(test_base.EndToEndTest):
  """Test limit on bytes transferred for a flow."""

  platforms = [
      test_base.EndToEndTest.Platform.LINUX,
      test_base.EndToEndTest.Platform.DARWIN,
  ]

  def runTest(self):
    args = flows_pb2.FileFinderArgs()
    args.paths.append("/dev/urandom")
    args.pathtype = jobs_pb2.PathSpec.PathType.OS
    args.process_non_regular_files = True
    args.action.action_type = flows_pb2.FileFinderAction.DOWNLOAD
    args.action.download.max_size = 1024 * 1024

    runner_args = flows_pb2.FlowRunnerArgs()
    runner_args.network_bytes_limit = 500 * 1024

    with self.assertRaises(test_base.RunFlowAndWaitError) as context:
      self.RunFlowAndWait("FileFinder", args=args, runner_args=runner_args)

    flow = context.exception.flow
    self.assertIn("Network bytes limit exceeded", flow.data.context.status)
