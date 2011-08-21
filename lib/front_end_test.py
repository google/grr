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
from grr.lib import data_store
from grr.lib import flow
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
    """Setup all out mocks."""
    test_lib.FlowTestsBaseclass.setUp(self)
    self.server = flow.FrontEndServer(self.key_path + "/server-priv.pem", None)

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

    self.session_id = flow_obj.session_id
    messages = [jobs_pb2.GrrMessage(request_id=1,
                                    response_id=i,
                                    session_id=self.session_id,
                                    args=str(i))
                for i in range(1, 10)]

    self.server.ReceiveMessages(messages, self.client_id, "")

    # Make sure the task is still on the client queue
    tasks_on_client_queue = flow.SCHEDULER.Query(self.client_id, 100)
    self.assertEqual(len(tasks_on_client_queue), 1)

    # Check that messages were stored correctly
    for message in messages:
      stored_message, _ = data_store.DB.Resolve(
          flow.FlowManager.FLOW_STATE_TEMPLATE % self.session_id,
          flow.FlowManager.FLOW_RESPONSE_TEMPLATE %(1, message.response_id),
          decoder=jobs_pb2.GrrMessage)

      self.assertEqual(stored_message, message)

    return messages

  def testReceiveMessagesWithStatus(self):
    """Receiving a sequence of messages with a status."""
    messages = self.testReceiveMessages()

    # Now add the status message
    status = jobs_pb2.GrrStatus(status=jobs_pb2.GrrStatus.OK)
    status_messages = [jobs_pb2.GrrMessage(
        request_id=1, response_id=len(messages)+1,
        session_id=self.session_id, args=status.SerializeToString(),
        type=jobs_pb2.GrrMessage.STATUS)]

    self.server.ReceiveMessages(status_messages, self.client_id, "")

  def testWellKnownFlows(self):
    """Make sure that well known flows get special treatment."""
    self.session_id = test_lib.WellKnownSessionTest.well_known_session_id

    messages = [jobs_pb2.GrrMessage(request_id=0,
                                    response_id=0,
                                    session_id=self.session_id,
                                    args=str(i))
                for i in range(1, 10)]

    self.server.ReceiveMessages(messages, self.client_id, "")

    # These messages should just be sent to the working queue
    queue = self.session_id.split(":")[0]
    tasks_on_working_queue = flow.SCHEDULER.Query(queue, 100)
    self.assertEqual(len(tasks_on_working_queue), len(messages))

    # There should be nothing in the client_queue
    self.assertRaises(KeyError, lambda: data_store.DB.subjects[self.client_id])

  def testDrainUpdateSessionRequestStates(self):
    """Draining the flow requests and preparing messages."""
    # We set this so that task scheduler ids dont trivially correlate
    # with request_ids:
    flow.SCHEDULER.ts_id = 15

    # This flow sends 10 messages on Start()
    flow_obj = self.FlowSetup("SendingTestFlow")
    self.session_id = flow_obj.session_id

    # There should be 10 messages in the client's task queue
    tasks = flow.SCHEDULER.Query(self.client_id, 100,
                                 decoder=jobs_pb2.GrrMessage)
    self.assertEqual(len(tasks), 10)

    # Check that the response state objects have the correct ts_id set
    # in the client_queue:
    for task in tasks:
      request_id = task.value.request_id

      # Retrieve the request state for this request_id
      request_state, _ = data_store.DB.Resolve(
          flow.FlowManager.FLOW_STATE_TEMPLATE % self.session_id,
          flow.FlowManager.FLOW_REQUEST_TEMPLATE % request_id,
          decoder=jobs_pb2.RequestState)

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
      self.assertEqual(response.job[i].request_id, i + 1)
      self.assertEqual(response.job[i].session_id, self.session_id)
      self.assertEqual(response.job[i].name, "Test")


def main(args):
  test_lib.main(args)


if __name__ == "__main__":
  conf.StartMain(main)
