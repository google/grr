#!/usr/bin/env python
"""Tests for dummy flow."""

from absl import app

from grr_response_client import actions
from grr_response_core.lib.rdfvalues import dummy as rdf_dummy
from grr_response_server.flows.general import dummy
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib

# pylint:mode=test


# Mocks the Dummy Client Action.
class DummyActionReturnsOnce(actions.ActionPlugin):
  """Sends a single Reply (like real action would)."""

  in_rdfvalue = rdf_dummy.DummyRequest
  out_rdfvalues = [rdf_dummy.DummyResult]

  def Run(self, args: rdf_dummy.DummyRequest) -> None:
    self.SendReply(rdf_dummy.DummyResult(action_output="single"))


# Mocks the Dummy Client Action, sending two replies.
class DummyActionReturnsTwice(actions.ActionPlugin):
  """Sends more than one Reply."""

  in_rdfvalue = rdf_dummy.DummyRequest
  out_rdfvalues = [rdf_dummy.DummyResult]

  def Run(self, args: rdf_dummy.DummyRequest) -> None:
    self.SendReply(rdf_dummy.DummyResult(action_output="first"))
    self.SendReply(rdf_dummy.DummyResult(action_output="second"))


class DummyTest(flow_test_lib.FlowTestsBaseclass):
  """Test the Dummy Flow."""

  def setUp(self):
    super().setUp()
    # We need a Client where we can execute the Flow/call the Action.
    self.client_id = self.SetupClient(0)

  def testHasInput(self):
    """Test that the Dummy flow works."""

    flow_id = flow_test_lib.TestFlowHelper(
        dummy.Dummy.__name__,
        # Uses mocked implementation.
        action_mocks.ActionMock.With({"Dummy": DummyActionReturnsOnce}),
        creator=self.test_username,
        client_id=self.client_id,
        # Flow arguments
        flow_input="batata",
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertLen(results, 1)
    self.assertEqual(
        "responses.action_output: 'single'",
        results[0].flow_output,
    )

  def testFailsIfEmptyFlowInput(self):
    """Test that the Dummy flow fails when there's no input."""

    with self.assertRaisesRegex(
        RuntimeError, r"args.flow_input is empty, cannot proceed!"
    ):
      flow_test_lib.TestFlowHelper(
          dummy.Dummy.__name__,
          # Should fail before calling the client
          None,
          creator=self.test_username,
          client_id=self.client_id,
          # Flow arguments are empty
      )

  def testFailsIfMultipleActionOutputs(self):
    """Test that the Dummy flow fails when there's no input."""

    with self.assertRaisesRegex(
        RuntimeError, r".*Oops, something weird happened.*"
    ):
      flow_test_lib.TestFlowHelper(
          dummy.Dummy.__name__,
          # Uses mocked implementation.
          action_mocks.ActionMock.With({"Dummy": DummyActionReturnsTwice}),
          creator=self.test_username,
          client_id=self.client_id,
          # Flow arguments
          flow_input="banana",
      )


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
