#!/usr/bin/env python
from unittest import mock

from absl.testing import absltest

from grr_response_client import actions
from grr_response_client import client_actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr.test_lib import action_mocks
from grr.test_lib import testing_startup


class ActionMockTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  class EchoAction(actions.ActionPlugin):

    in_rdfvalue = rdfvalue.RDFString
    out_rdfvalues = [rdfvalue.RDFString]

    def Run(self, args: rdfvalue.RDFString) -> None:
      self.SendReply(args)

  def testWith(self):
    action_mock = action_mocks.ActionMock.With({
        "Echo": self.EchoAction,
    })

    message = rdf_flows.GrrMessage()
    message.name = "Echo"
    message.payload = rdfvalue.RDFString("foobar")

    responses = action_mock.HandleMessage(message)
    self.assertLen(responses, 2)
    self.assertEqual(responses[0].payload, rdfvalue.RDFString("foobar"))

  @mock.patch.object(client_actions, "REGISTRY", {})
  def testWithRegistry(self):
    client_actions.Register("Echo", self.EchoAction)
    action_mock = action_mocks.ActionMock.WithRegistry()

    message = rdf_flows.GrrMessage()
    message.name = "Echo"
    message.payload = rdfvalue.RDFString("foobar")

    responses = action_mock.HandleMessage(message)
    self.assertLen(responses, 2)
    self.assertEqual(responses[0].payload, rdfvalue.RDFString("foobar"))


if __name__ == "__main__":
  absltest.main()
