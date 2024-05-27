#!/usr/bin/env python
from unittest import mock

from absl.testing import absltest

from grr_response_client import actions
from grr_response_client import client_actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import mig_client_action
from grr_response_proto import jobs_pb2
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


class ExecuteCommandActionMockTest(absltest.TestCase):

  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    testing_startup.TestInit()

  def testCmdIncorrect(self):
    action_mock = action_mocks.ExecuteCommandActionMock(cmd="/usr/bin/foo")

    args = jobs_pb2.ExecuteRequest()
    args.cmd = "/usr/bin/bar"
    args = mig_client_action.ToRDFExecuteRequest(args)

    with self.assertRaises(RuntimeError) as context:
      list(action_mock.ExecuteCommand(args))

    self.assertEqual(str(context.exception), "Unexpected command: /usr/bin/bar")

  def testArgsIncorrect(self):
    action_mock = action_mocks.ExecuteCommandActionMock(
        cmd="/usr/bin/foo",
        args=["bar", "baz"],
    )

    args = jobs_pb2.ExecuteRequest()
    args.cmd = "/usr/bin/foo"
    args.args.append("quux")
    args = mig_client_action.ToRDFExecuteRequest(args)

    with self.assertRaises(RuntimeError) as context:
      list(action_mock.ExecuteCommand(args))

    self.assertEqual(str(context.exception), "Unexpected arguments: ['quux']")

  def testExitStatus(self):
    action_mock = action_mocks.ExecuteCommandActionMock(
        cmd="/usr/bin/foo",
        exit_status=42,
    )

    args = jobs_pb2.ExecuteRequest()
    args.cmd = "/usr/bin/foo"
    args = mig_client_action.ToRDFExecuteRequest(args)

    results = list(action_mock.ExecuteCommand(args))

    self.assertLen(results, 1)
    self.assertEqual(results[0].exit_status, 42)

  def testStdout(self):
    action_mock = action_mocks.ExecuteCommandActionMock(
        cmd="/usr/bin/foo",
        stdout=b"foo_stdout",
    )

    args = jobs_pb2.ExecuteRequest()
    args.cmd = "/usr/bin/foo"
    args = mig_client_action.ToRDFExecuteRequest(args)

    results = list(action_mock.ExecuteCommand(args))

    self.assertLen(results, 1)
    self.assertEqual(results[0].stdout, b"foo_stdout")

  def testStderr(self):
    action_mock = action_mocks.ExecuteCommandActionMock(
        cmd="/usr/bin/foo",
        stderr=b"foo_stderr",
    )

    args = jobs_pb2.ExecuteRequest()
    args.cmd = "/usr/bin/foo"
    args = mig_client_action.ToRDFExecuteRequest(args)

    results = list(action_mock.ExecuteCommand(args))

    self.assertLen(results, 1)
    self.assertEqual(results[0].stderr, b"foo_stderr")


if __name__ == "__main__":
  absltest.main()
