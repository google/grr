#!/usr/bin/env python
#
# Copyright 2010 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Unittest for grr frontend server."""




from grr.client import conf
from grr.client import conf as flags
from grr.lib import communicator
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_context
from grr.lib import scheduler
from grr.lib import test_lib
from grr.proto import jobs_pb2


class SendingTestFlow(flow.GRRFlow):
  """Tests that sent messages are correctly collected."""

  @flow.StateHandler(next_state="Incoming")
  def Start(self):
    for i in range(10):
      self.CallClient("Test",
                      jobs_pb2.PrintStr(data="test%s" % i),
                      data=str(i),
                      next_state="Incoming")


class GRRFEServerTest(test_lib.FlowTestsBaseclass):
  """Tests the GRRFEServer."""
  string = "Test String"

  def setUp(self):
    """Setup the server."""
    super(GRRFEServerTest, self).setUp()

    # For tests, small pools are ok.
    flags.FLAGS.threadpool_size = 10
    prefix = "pool-%s" % self._testMethodName
    self.server = flow.FrontEndServer(self.key_path + "/server-priv.pem",
                                      None, threadpool_prefix=prefix)

  def CheckMessages(self, left, right):
    """Compares two lists of messages for equality.

    Args:
      left: A list of GrrMessage
      right: A list of (task, GrrMessage)

    Returns:
      True if they are the same.
    """
    if len(right) != len(left):
      return False

    for i in range(len(right)):
      if left[i] != right[i][1]:
        return False

    return True

  def testReceiveMessages(self):
    """Test Receiving messages with no status."""
    flow_obj = self.FlowSetup("FlowOrderTest")

    session_id = flow_obj.session_id
    messages = [jobs_pb2.GrrMessage(request_id=1,
                                    response_id=i,
                                    session_id=session_id,
                                    args=str(i))
                for i in range(1, 10)]

    self.server.ReceiveMessages(messages)

    # Make sure the task is still on the client queue
    tasks_on_client_queue = scheduler.SCHEDULER.Query(self.client_id, 100,
                                                      token=self.token)
    self.assertEqual(len(tasks_on_client_queue), 1)

    # Check that messages were stored correctly
    for message in messages:
      stored_message, _ = data_store.DB.Resolve(
          flow_context.FlowManager.FLOW_STATE_TEMPLATE % session_id,
          flow_context.FlowManager.FLOW_RESPONSE_TEMPLATE % (
              1, message.response_id),
          decoder=jobs_pb2.GrrMessage, token=self.token)

      self.assertEqual(stored_message, message)

    flow.FACTORY.ReturnFlow(flow_obj, token=self.token)
    return messages

  def testReceiveMessagesWithStatus(self):
    """Receiving a sequence of messages with a status."""
    messages = self.testReceiveMessages()

    # Now add the status message
    status = jobs_pb2.GrrStatus(status=jobs_pb2.GrrStatus.OK)
    status_messages = [jobs_pb2.GrrMessage(
        request_id=1, response_id=len(messages)+1,
        session_id=messages[0].session_id, args=status.SerializeToString(),
        type=jobs_pb2.GrrMessage.STATUS)]

    self.server.ReceiveMessages(status_messages)

  def testWellKnownFlows(self):
    """Make sure that well known flows can run on the front end."""
    test_lib.WellKnownSessionTest.messages = []
    session_id = test_lib.WellKnownSessionTest.well_known_session_id

    messages = [jobs_pb2.GrrMessage(request_id=0,
                                    response_id=0,
                                    session_id=session_id,
                                    args=str(i))
                for i in range(1, 10)]

    self.server.ReceiveMessages(messages)

    # Wait for async actions to complete
    self.server.thread_pool.Join()

    test_lib.WellKnownSessionTest.messages.sort()

    # Well known flows are now directly processed on the front end
    self.assertEqual(test_lib.WellKnownSessionTest.messages,
                     list(range(1, 10)))

    # There should be nothing in the client_queue
    self.assertRaises(KeyError, lambda: data_store.DB.subjects[self.client_id])

  def testWellKnownFlowsRemote(self):
    """Make sure that flows that do not exist on the front end get scheduled."""
    test_lib.WellKnownSessionTest.messages = []
    session_id = test_lib.WellKnownSessionTest.well_known_session_id

    messages = [jobs_pb2.GrrMessage(request_id=0,
                                    response_id=0,
                                    session_id=session_id,
                                    args=str(i))
                for i in range(1, 10)]

    # Delete the local well known flow cache is empty.
    self.server.well_known_flows = {}
    self.server.ReceiveMessages(messages)

    # Wait for async actions to complete
    self.server.thread_pool.Join()

    # None get processed now
    self.assertEqual(test_lib.WellKnownSessionTest.messages, [])

    # There should be nothing in the client_queue
    self.assertRaises(KeyError, lambda: data_store.DB.subjects[self.client_id])

    # The well known flows should be waiting in the worker queue instead
    queue = session_id.split(":")[0]
    self.assertEqual(len(scheduler.SCHEDULER.Query(
        queue, 10000, token=self.token)), 9)

  def testDrainUpdateSessionRequestStates(self):
    """Draining the flow requests and preparing messages."""
    # We set this so that task scheduler ids dont trivially correlate
    # with request_ids:
    scheduler.SCHEDULER.ts_id = 15

    # This flow sends 10 messages on Start()
    flow_obj = self.FlowSetup("SendingTestFlow")
    session_id = flow_obj.session_id

    # There should be 10 messages in the client's task queue
    tasks = scheduler.SCHEDULER.Query(self.client_id, 100,
                                      decoder=jobs_pb2.GrrMessage,
                                      token=self.token)
    self.assertEqual(len(tasks), 10)

    # Check that the response state objects have the correct ts_id set
    # in the client_queue:
    for task in tasks:
      request_id = task.value.request_id

      # Retrieve the request state for this request_id
      request_state, _ = data_store.DB.Resolve(
          flow_context.FlowManager.FLOW_STATE_TEMPLATE % session_id,
          flow_context.FlowManager.FLOW_REQUEST_TEMPLATE % request_id,
          decoder=jobs_pb2.RequestState, token=self.token)

      # Check that ts_id for the client message is correctly set in
      # request_state
      self.assertEqual(request_state.ts_id, task.id)

    # Now ask the server to drain the outbound messages into the
    # message list.
    response = jobs_pb2.MessageList()

    self.server.DrainTaskSchedulerQueueForClient(
        self.client_id, 5, response)

    # Check that we received only as many messages as we asked for
    self.assertEqual(len(response.job), 5)

    for i in range(4):
      self.assertEqual(response.job[i].session_id, session_id)
      self.assertEqual(response.job[i].name, "Test")

    flow.FACTORY.ReturnFlow(flow_obj, token=self.token)

  def testHandleMessageBundle(self):
    """Check that HandleMessageBundles() requeues messages if it failed.

    This test makes sure that when messages are pending for a client, and which
    we have no certificate for, the messages are requeued when sending fails.
    """
    # Make a new fake client
    client_id = "C." + "2" * 16

    class MockCommunicator(object):
      """A fake that simulates an unenrolled client."""

      def DecodeMessages(self, *unused_args):
        """For simplicity client sends an empty request."""
        return ([], client_id, 100)

      def EncodeMessages(self, *unused_args, **unused_kw):
        """Raise because the server has no certificates for this client."""
        raise communicator.UnknownClientCert()

    # Install the mock.
    self.server._communicator = MockCommunicator()

    # First request, the server will raise UnknownClientCert.
    request_comms = jobs_pb2.ClientCommunication()
    self.assertRaises(communicator.UnknownClientCert,
                      self.server.HandleMessageBundles, request_comms, 2)

    # We can still schedule a flow for it
    flow.FACTORY.StartFlow(client_id, "SendingFlow", message_count=1,
                           token=self.token)

    tasks = scheduler.SCHEDULER.Query(client_id, limit=100,
                                      token=self.token)

    self.assertRaises(communicator.UnknownClientCert,
                      self.server.HandleMessageBundles, request_comms, 2)

    new_tasks = scheduler.SCHEDULER.Query(client_id, limit=100,
                                          token=self.token)

    # The different in eta times reflect the lease that the server took on the
    # client messages.
    lease_time = (new_tasks[0].eta - tasks[0].eta)/1e6

    # This lease time must be small, as the HandleMessageBundles() call failed,
    # the pending client messages must be put back on the queue.
    self.assert_(lease_time < 1)

    # Since the server tried to send it, the ttl must be decremented
    self.assertEqual(tasks[0].ttl - new_tasks[0].ttl, 1)


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  conf.StartMain(main)
