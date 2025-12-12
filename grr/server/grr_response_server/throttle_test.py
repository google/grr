#!/usr/bin/env python
from absl import app

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_proto import flows_pb2
from grr_response_server import throttle
from grr_response_server.flows.general import file_finder
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ThrottleTest(test_lib.GRRBaseTest):
  BASE_TIME = 1439501002

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)

  def testCheckFlowRequestLimit(self):
    # Create a flow
    with test_lib.FakeTime(self.BASE_TIME):
      flow_test_lib.StartFlow(
          flow_test_lib.DummyLogFlow,
          client_id=self.client_id,
          creator=self.test_username,
      )

    # One day + 1s later
    with test_lib.FakeTime(self.BASE_TIME + 86400 + 1):
      flow_test_lib.StartFlow(
          flow_cls=flow_test_lib.DummyLogFlow,
          client_id=self.client_id,
          creator=self.test_username,
      )

      # Disable the dup interval checking by setting it to 0.
      throttler = throttle.FlowThrottler(
          daily_req_limit=2,
          dup_interval=rdfvalue.Duration.From(0, rdfvalue.SECONDS),
      )

      # Should succeed, only one flow present in the 1 day window.
      throttler.EnforceLimits(
          self.client_id,
          self.test_username,
          flow_test_lib.DummyLogFlow.__name__,
          None,
      )

      # Start some more flows with a different user
      flow_test_lib.StartFlow(
          flow_cls=flow_test_lib.DummyLogFlow,
          client_id=self.client_id,
          creator="test2",
      )
      flow_test_lib.StartFlow(
          flow_test_lib.DummyLogFlow, client_id=self.client_id, creator="test2"
      )

      # Should still succeed, since we count per-user
      throttler.EnforceLimits(
          self.client_id,
          self.test_username,
          flow_test_lib.DummyLogFlow.__name__,
          None,
      )

      # Add another flow at current time
      flow_test_lib.StartFlow(
          flow_test_lib.DummyLogFlow,
          client_id=self.client_id,
          creator=self.test_username,
      )

      with self.assertRaises(throttle.DailyFlowRequestLimitExceededError):
        throttler.EnforceLimits(
            self.client_id,
            self.test_username,
            flow_test_lib.DummyLogFlow.__name__,
            None,
        )

  def testFlowDuplicateLimit(self):
    # Disable the request limit checking by setting it to 0.
    throttler = throttle.FlowThrottler(
        daily_req_limit=0,
        dup_interval=rdfvalue.Duration.From(1200, rdfvalue.SECONDS),
        flow_args_type=flows_pb2.FileFinderArgs,
    )

    # Running the same flow immediately should fail
    with test_lib.FakeTime(self.BASE_TIME):
      throttler.EnforceLimits(
          self.client_id,
          self.test_username,
          flow_test_lib.DummyLogFlow.__name__,
          None,
      )

      flow_test_lib.StartFlow(
          flow_cls=flow_test_lib.DummyLogFlow,
          client_id=self.client_id,
          creator=self.test_username,
      )

      with self.assertRaises(throttle.DuplicateFlowError):
        throttler.EnforceLimits(
            self.client_id,
            self.test_username,
            flow_test_lib.DummyLogFlow.__name__,
            None,
        )

    # Doing the same outside the window should work
    with test_lib.FakeTime(self.BASE_TIME + 1200 + 1):
      throttler.EnforceLimits(
          self.client_id,
          self.test_username,
          flow_test_lib.DummyLogFlow.__name__,
          None,
      )

      flow_test_lib.StartFlow(
          flow_test_lib.DummyLogFlow,
          client_id=self.client_id,
          creator=self.test_username,
      )

      with self.assertRaises(throttle.DuplicateFlowError):
        throttler.EnforceLimits(
            self.client_id,
            self.test_username,
            flow_test_lib.DummyLogFlow.__name__,
            None,
        )

    # Now try a flow with more complicated args
    args = rdf_file_finder.FileFinderArgs(
        paths=["/tmp/1", "/tmp/2"],
        action=rdf_file_finder.FileFinderAction(action_type="STAT"),
    ).AsPrimitiveProto()
    packed_args = any_pb2.Any()
    packed_args.Pack(args)

    with test_lib.FakeTime(self.BASE_TIME):
      throttler.EnforceLimits(
          self.client_id,
          self.test_username,
          file_finder.FileFinder.__name__,
          packed_args,
      )

      new_args = rdf_file_finder.FileFinderArgs(
          paths=["/tmp/1", "/tmp/2"],
          action=rdf_file_finder.FileFinderAction(action_type="STAT"),
      )

      flow_test_lib.StartFlow(
          flow_cls=file_finder.FileFinder,
          client_id=self.client_id,
          creator=self.test_username,
          flow_args=new_args,
      )

      with self.assertRaises(throttle.DuplicateFlowError):
        throttler.EnforceLimits(
            self.client_id,
            self.test_username,
            file_finder.FileFinder.__name__,
            packed_args,
        )

      # Different args should succeed.
      args = rdf_file_finder.FileFinderArgs(
          paths=["/tmp/1", "/tmp/3"],
          action=rdf_file_finder.FileFinderAction(action_type="STAT"),
      ).AsPrimitiveProto()
      packed_args.Pack(args)

      throttler.EnforceLimits(
          self.client_id,
          self.test_username,
          file_finder.FileFinder.__name__,
          packed_args,
      )


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
