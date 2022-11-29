#!/usr/bin/env python
"""Tests for the client."""

from unittest import mock

from absl import app

# Need to import client to add the flags.
from grr_response_client import actions
from grr_response_client import client_actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr.test_lib import test_lib
from grr.test_lib import worker_mocks


class MockAction(actions.ActionPlugin):
  in_rdfvalue = rdf_client.LogMessage
  out_rdfvalues = [rdf_client.LogMessage]

  def Run(self, message):
    self.SendReply(
        rdf_client_action.EchoRequest(
            data="Received Message: %s. Data %s" % (message.data, "x" * 100)))


class RaiseAction(actions.ActionPlugin):
  """A mock action which raises an error."""
  in_rdfvalue = rdf_client.LogMessage
  out_rdfvalues = [rdf_client.LogMessage]

  def Run(self, unused_args):
    raise RuntimeError("I dont like.")


class TestedContext(worker_mocks.ClientWorker):
  """We test a simpler Context without crypto here."""

  def LoadCertificates(self):
    self.certs_loaded = True


class BasicContextTests(test_lib.GRRBaseTest):
  """Test the GRR contexts."""
  to_test_context = TestedContext

  def setUp(self):
    super().setUp()
    self.context = self.to_test_context()
    self.context.LoadCertificates()
    self.session_id = rdfvalue.RDFURN("W:1234")

  def testHandleMessage(self):
    """Test handling of a normal request with a response."""
    args = rdf_client.LogMessage(data="hello")
    # Push a request on it
    message = rdf_flows.GrrMessage(
        name="MockAction",
        session_id=self.session_id,
        auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED,
        payload=args,
        request_id=1,
        generate_task_id=True)

    with mock.patch.object(client_actions, "REGISTRY",
                           {"MockAction": MockAction}):
      self.context.HandleMessage(message)

    # Check the response - one data and one status

    message_list = self.context.Drain().job

    self.assertEqual(message_list[0].session_id, self.session_id)
    self.assertEqual(message_list[0].response_id, 1)
    self.assertIn("hello", message_list[0].payload.data)
    self.assertEqual(message_list[1].response_id, 2)
    self.assertEqual(message_list[1].type, rdf_flows.GrrMessage.Type.STATUS)

  def testHandleError(self):
    """Test handling of a request which raises."""
    # Push a request on it
    message = rdf_flows.GrrMessage(
        name="RaiseAction",
        session_id=self.session_id,
        auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED,
        request_id=1,
        generate_task_id=True)

    with mock.patch.object(client_actions, "REGISTRY",
                           {"RaiseAction": RaiseAction}):
      self.context.HandleMessage(message)

    # Check the response - one data and one status
    message_list = self.context.Drain().job
    self.assertEqual(message_list[0].session_id, self.session_id)
    self.assertEqual(message_list[0].response_id, 1)
    status = rdf_flows.GrrStatus(message_list[0].payload)
    self.assertIn("RuntimeError", status.error_message)
    self.assertNotEqual(status.status, rdf_flows.GrrStatus.ReturnedStatus.OK)

  def testUnauthenticated(self):
    """What happens if an unauthenticated message is sent to the client?

    RuntimeError needs to be issued, and the client needs to send a
    GrrStatus message with the traceback in it.
    """
    # Push a request on it
    message = rdf_flows.GrrMessage(
        name="MockAction",
        session_id=self.session_id,
        auth_state=rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED,
        request_id=1,
        generate_task_id=True)

    with mock.patch.object(client_actions, "REGISTRY",
                           {"MockAction": MockAction}):
      self.context.HandleMessage(message)

    # We expect to receive an GrrStatus to indicate an exception was
    # raised:
    # Check the response - one data and one status
    message_list = self.context.Drain().job
    self.assertLen(message_list, 1)
    self.assertEqual(message_list[0].session_id, self.session_id)
    self.assertEqual(message_list[0].response_id, 1)
    status = rdf_flows.GrrStatus(message_list[0].payload)
    self.assertIn("not Authenticated", status.error_message)
    self.assertIn("RuntimeError", status.error_message)
    self.assertNotEqual(status.status, rdf_flows.GrrStatus.ReturnedStatus.OK)

  def testFastPoll(self):
    """Test fast poll settings propagated to status results."""
    for i in range(10):
      message = rdf_flows.GrrMessage(
          name="MockAction",
          session_id=self.session_id.Basename() + str(i),
          auth_state=rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED,
          request_id=1,
          require_fastpoll=i % 2,
          generate_task_id=True)

      with mock.patch.object(client_actions, "REGISTRY",
                             {"MockAction": MockAction}):
        self.context.HandleMessage(message)

    message_list = self.context.Drain(max_size=1000000).job
    self.assertLen(message_list, 10)
    self.assertCountEqual([m.require_fastpoll for m in message_list],
                          [0, 1, 0, 1, 0, 1, 0, 1, 0, 1])


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
