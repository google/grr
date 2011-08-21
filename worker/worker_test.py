#!/usr/bin/env python

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

"""Tests for the worker."""



from grr.client import conf
from grr.lib import data_store
from grr.lib import flow
from grr.lib import test_lib
from grr.proto import jobs_pb2




# A global collector for test results
RESULTS = []


class SendingTestFlow(flow.GRRFlow):
  """Tests that sent messages are correctly collected."""

  @flow.StateHandler(next_state="Incoming")
  def Start(self):
    for i in range(10):
      self.CallClient("Test",
                      jobs_pb2.PrintStr(data="test%s" % i),
                      data=str(i),
                      next_state="Incoming")

  @flow.StateHandler(jobs_pb2.DataBlob, auth_required=False)
  def Incoming(self, responses):
    # We push the result into a global array so we can examine it
    # better.
    for response in responses:
      RESULTS.append(response.string)


class SendingTestFlow2(SendingTestFlow):
  """Only send a single request."""

  @flow.StateHandler(next_state="Incoming")
  def Start(self):
    i = 1
    self.CallClient("Test",
                    jobs_pb2.PrintStr(data="test%s" % i),
                    data=str(i),
                    next_state="Incoming")


class GrrWorkerTest(test_lib.FlowTestsBaseclass):
  """Tests the GRR Worker."""

  def FakeResponse(self, message):
    """Fake the message being inserted to the response queue."""
    # Retrieve the request state for this request_id
    request_state, _ = data_store.DB.Resolve(
        flow.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow.FlowManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        decoder=jobs_pb2.RequestState)

    request_state.response_count += 1
    if message.type == jobs_pb2.GrrMessage.STATUS:
      request_state.status.ParseFromString(message.args)

    # Store the request and response back
    data_store.DB.Set(
        flow.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow.FlowManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        request_state)

    data_store.DB.Set(
        flow.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow.FlowManager.FLOW_RESPONSE_TEMPLATE % (
            message.request_id, message.response_id),
        message)

  def SendResponse(self, session_id, data):
    """Send a complete response to a message."""
    self.FakeResponse(jobs_pb2.GrrMessage(
        session_id=session_id, args=jobs_pb2.DataBlob(
            string=data).SerializeToString(),
        request_id=1,
        response_id=1))

    status = jobs_pb2.GrrMessage(
        session_id=session_id, args=jobs_pb2.GrrStatus(
            status=jobs_pb2.GrrStatus.OK).SerializeToString(),
        request_id=1,
        response_id=2,
        type=jobs_pb2.GrrMessage.STATUS)

    self.FakeResponse(status)
    tasks = [flow.SCHEDULER.Task(queue="W", value=status)]
    flow.SCHEDULER.Schedule(tasks)

    return tasks

  def testProcessMessages(self):
    """Test processing of several inbound messages."""
    worker = flow.GRRWorker("W")

    # Create a couple of flows
    flow_obj = self.FlowSetup("SendingTestFlow")
    session_id_1 = flow_obj.session_id
    flow.FACTORY.ReturnFlow(flow_obj)

    flow_obj = self.FlowSetup("SendingTestFlow2")
    session_id_2 = flow_obj.session_id
    flow.FACTORY.ReturnFlow(flow_obj)

    # Check that client queue has messages
    tasks_on_client_queue = flow.SCHEDULER.Query(
        self.client_id, 100, decoder=jobs_pb2.GrrMessage)

    # should have 10 requests from SendingTestFlow and 1 from SendingTestFlow2
    self.assertEqual(len(tasks_on_client_queue), 11)

    # Send each of the flows a message
    tasks = (self.SendResponse(session_id_1, "Hello1") +
             self.SendResponse(session_id_2, "Hello2"))

    # Clear the results global
    del RESULTS[:]

    # Process all messages
    worker.ProcessMessages(tasks)

    # Ensure both requests ran
    self.assert_("Hello1" in RESULTS)
    self.assert_("Hello2" in RESULTS)

    # Check that client queue is cleared - should have 2 less messages (since
    # two were completed).
    tasks_on_client_queue = flow.SCHEDULER.Query(
        self.client_id, 100, decoder=jobs_pb2.GrrMessage)

    self.assertEqual(len(tasks_on_client_queue), 9)

    # Ensure that processed requests are removed from state subject
    self.assertEqual((None, 0), data_store.DB.Resolve(
        flow.FlowManager.FLOW_STATE_TEMPLATE % session_id_1,
        flow.FlowManager.FLOW_REQUEST_TEMPLATE % 1))

    flow_pb = flow.FACTORY.FetchFlow(session_id_1)
    self.assert_(flow_pb.state != jobs_pb2.FlowPB.TERMINATED)

    flow_pb = flow.FACTORY.FetchFlow(session_id_2)
    self.assertEqual(flow_pb.state, jobs_pb2.FlowPB.TERMINATED)


def main(_):
  test_lib.main()

if __name__ == "__main__":
  conf.StartMain(main)
