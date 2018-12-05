#!/usr/bin/env python
"""Tests for grr.lib.throttle."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_server import access_control
from grr_response_server import throttle
from grr_response_server.flows.general import file_finder
from grr_response_server.gui import api_regression_test_lib
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


@db_test_lib.DualDBTest
class ThrottleTest(test_lib.GRRBaseTest):
  BASE_TIME = 1439501002

  def setUp(self):
    super(ThrottleTest, self).setUp()
    self.client_id = self.SetupClient(0).Basename()

  def testCheckFlowRequestLimit(self):
    # Create a flow
    with test_lib.FakeTime(self.BASE_TIME):
      api_regression_test_lib.StartFlow(
          client_id=self.client_id,
          flow_cls=flow_test_lib.DummyLogFlow,
          token=self.token)

    # One day + 1s later
    with test_lib.FakeTime(self.BASE_TIME + 86400 + 1):
      api_regression_test_lib.StartFlow(
          client_id=self.client_id,
          flow_cls=flow_test_lib.DummyLogFlow,
          token=self.token)

      # Disable the dup interval checking by setting it to 0.
      throttler = throttle.FlowThrottler(
          daily_req_limit=2, dup_interval=rdfvalue.Duration("0s"))

      # Should succeeed, only one flow present in the 1 day window.
      throttler.EnforceLimits(
          self.client_id,
          self.token.username,
          flow_test_lib.DummyLogFlow.__name__,
          None,
          token=self.token)

      # Start some more flows with a different user
      token2 = access_control.ACLToken(username="test2", reason="Running tests")
      api_regression_test_lib.StartFlow(
          client_id=self.client_id,
          flow_cls=flow_test_lib.DummyLogFlow,
          token=token2)
      api_regression_test_lib.StartFlow(
          client_id=self.client_id,
          flow_cls=flow_test_lib.DummyLogFlow,
          token=token2)

      # Should still succeed, since we count per-user
      throttler.EnforceLimits(
          self.client_id,
          self.token.username,
          flow_test_lib.DummyLogFlow.__name__,
          None,
          token=self.token)

      # Add another flow at current time
      api_regression_test_lib.StartFlow(
          client_id=self.client_id,
          flow_cls=flow_test_lib.DummyLogFlow,
          token=self.token)

      with self.assertRaises(throttle.DailyFlowRequestLimitExceededError):
        throttler.EnforceLimits(
            self.client_id,
            self.token.username,
            flow_test_lib.DummyLogFlow.__name__,
            None,
            token=self.token)

  def testFlowDuplicateLimit(self):
    # Disable the request limit checking by setting it to 0.
    throttler = throttle.FlowThrottler(
        daily_req_limit=0, dup_interval=rdfvalue.Duration("1200s"))

    # Running the same flow immediately should fail
    with test_lib.FakeTime(self.BASE_TIME):
      throttler.EnforceLimits(
          self.client_id,
          self.token.username,
          flow_test_lib.DummyLogFlow.__name__,
          None,
          token=self.token)

      api_regression_test_lib.StartFlow(
          client_id=self.client_id,
          flow_cls=flow_test_lib.DummyLogFlow,
          token=self.token)

      with self.assertRaises(throttle.DuplicateFlowError):
        throttler.EnforceLimits(
            self.client_id,
            self.token.username,
            flow_test_lib.DummyLogFlow.__name__,
            None,
            token=self.token)

    # Doing the same outside the window should work
    with test_lib.FakeTime(self.BASE_TIME + 1200 + 1):
      throttler.EnforceLimits(
          self.client_id,
          self.token.username,
          flow_test_lib.DummyLogFlow.__name__,
          None,
          token=self.token)

      api_regression_test_lib.StartFlow(
          client_id=self.client_id,
          flow_cls=flow_test_lib.DummyLogFlow,
          token=self.token)

      with self.assertRaises(throttle.DuplicateFlowError):
        throttler.EnforceLimits(
            self.client_id,
            self.token.username,
            flow_test_lib.DummyLogFlow.__name__,
            None,
            token=self.token)

    # Now try a flow with more complicated args
    args = rdf_file_finder.FileFinderArgs(
        paths=["/tmp/1", "/tmp/2"],
        action=rdf_file_finder.FileFinderAction(action_type="STAT"))

    with test_lib.FakeTime(self.BASE_TIME):
      throttler.EnforceLimits(
          self.client_id,
          self.token.username,
          file_finder.FileFinder.__name__,
          args,
          token=self.token)

      new_args = rdf_file_finder.FileFinderArgs(
          paths=["/tmp/1", "/tmp/2"],
          action=rdf_file_finder.FileFinderAction(action_type="STAT"))

      api_regression_test_lib.StartFlow(
          client_id=self.client_id,
          flow_cls=file_finder.FileFinder,
          token=self.token,
          flow_args=new_args)

      with self.assertRaises(throttle.DuplicateFlowError):
        throttler.EnforceLimits(
            self.client_id,
            self.token.username,
            file_finder.FileFinder.__name__,
            args,
            token=self.token)

      # Different args should succeed.
      args = rdf_file_finder.FileFinderArgs(
          paths=["/tmp/1", "/tmp/3"],
          action=rdf_file_finder.FileFinderAction(action_type="STAT"))

      throttler.EnforceLimits(
          self.client_id,
          self.token.username,
          file_finder.FileFinder.__name__,
          args,
          token=self.token)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
