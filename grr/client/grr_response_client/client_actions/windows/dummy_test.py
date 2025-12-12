#!/usr/bin/env python
from absl import app

from grr_response_client.client_actions.windows import dummy
from grr_response_core.lib.rdfvalues import dummy as rdf_dummy
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


class DummyTest(client_test_lib.EmptyActionTest):
  """Test Dummy action."""

  def testDummyReceived(self):
    action_request = rdf_dummy.DummyRequest(action_input="banana")

    # We use `ExecuteAction` instead of `RunAction` to test `status` result too.
    results = self.ExecuteAction(dummy.Dummy, action_request)

    # One result, and one status message.
    self.assertLen(results, 2)

    self.assertIsInstance(results[0], rdf_dummy.DummyResult)
    self.assertIn("banana", results[0].action_output)
    self.assertIn("WIN", results[0].action_output)

    self.assertIsInstance(results[1], rdf_flows.GrrStatus)
    self.assertEqual(rdf_flows.GrrStatus.ReturnedStatus.OK, results[1].status)
    self.assertEmpty(results[1].error_message)

  def testErrorsOnEmptyInput(self):
    action_request = rdf_dummy.DummyRequest()

    # We use `ExecuteAction` instead of `RunAction` to test `status` result too.
    results = self.ExecuteAction(dummy.Dummy, action_request)

    # One status message.
    self.assertLen(results, 1)

    self.assertIsInstance(results[0], rdf_flows.GrrStatus)
    self.assertEqual(
        rdf_flows.GrrStatus.ReturnedStatus.GENERIC_ERROR, results[0].status
    )
    self.assertIn("empty", results[0].error_message)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
