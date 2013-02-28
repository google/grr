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


import time

from grr.client import conf
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_context
from grr.lib import rdfvalue
from grr.lib import scheduler
from grr.lib import server_plugins  # pylint: disable=W0611
from grr.lib import test_lib


# A global collector for test results
RESULTS = []


class WorkerSendingTestFlow(flow.GRRFlow):
  """Tests that sent messages are correctly collected."""

  @flow.StateHandler(next_state="Incoming")
  def Start(self):
    for i in range(10):
      self.CallClient("Test",
                      rdfvalue.DataBlob(string="test%s" % i),
                      data=str(i),
                      next_state="Incoming")

  @flow.StateHandler(auth_required=False)
  def Incoming(self, responses):
    # Add a delay here to catch thread races.
    time.sleep(0.2)
    # We push the result into a global array so we can examine it
    # better.
    for response in responses:
      RESULTS.append(response.string)


class WorkerSendingTestFlow2(WorkerSendingTestFlow):
  """Only send a single request."""

  @flow.StateHandler(next_state="Incoming")
  def Start(self):
    i = 1
    self.CallClient("Test",
                    rdfvalue.DataBlob(string="test%s" % i),
                    data=str(i),
                    next_state="Incoming")


class GrrWorkerTest(test_lib.FlowTestsBaseclass):
  """Tests the GRR Worker."""

  def FakeResponse(self, message):
    """Fake the message being inserted to the response queue."""
    # Retrieve the request state for this request_id
    request_state, _ = data_store.DB.Resolve(
        flow_context.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow_context.FlowManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        decoder=rdfvalue.RequestState, token=self.token)

    request_state.response_count += 1
    if message.type == rdfvalue.GRRMessage.Enum("STATUS"):
      request_state.status.ParseFromString(message.args)

    # Store the request and response back
    data_store.DB.Set(
        flow_context.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow_context.FlowManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        request_state, token=self.token)

    data_store.DB.Set(
        flow_context.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow_context.FlowManager.FLOW_RESPONSE_TEMPLATE % (
            message.request_id, message.response_id),
        message, token=self.token)

  def SendResponse(self, session_id, data):
    """Send a complete response to a message."""
    self.FakeResponse(rdfvalue.GRRMessage(
        session_id=session_id,
        payload=rdfvalue.DataBlob(string=data),
        request_id=1, response_id=1))

    status = rdfvalue.GRRMessage(
        session_id=session_id,
        payload=rdfvalue.GrrStatus(status=rdfvalue.GrrStatus.Enum("OK")),
        request_id=1, response_id=2,
        type=rdfvalue.GRRMessage.Enum("STATUS"))

    self.FakeResponse(status)

    # Signal on the worker queue that this flow is ready.
    data_store.DB.Set("W", "task:%s" % session_id, "X", token=self.token)

  def testProcessMessages(self):
    """Test processing of several inbound messages."""
    worker = flow.GRRWorker("W", token=self.token)

    # Create a couple of flows
    flow_obj = self.FlowSetup("WorkerSendingTestFlow")
    session_id_1 = flow_obj.session_id
    flow.FACTORY.ReturnFlow(flow_obj, token=self.token)

    flow_obj = self.FlowSetup("WorkerSendingTestFlow2")
    session_id_2 = flow_obj.session_id
    flow.FACTORY.ReturnFlow(flow_obj, token=self.token)

    # Check that client queue has messages
    tasks_on_client_queue = scheduler.SCHEDULER.Query(
        self.client_id, 100, token=self.token)

    # should have 10 requests from WorkerSendingTestFlow and 1 from
    # SendingTestFlow2
    self.assertEqual(len(tasks_on_client_queue), 11)

    # Send each of the flows a repeated message
    self.SendResponse(session_id_1, "Hello1")
    self.SendResponse(session_id_2, "Hello2")
    self.SendResponse(session_id_1, "Hello1")
    self.SendResponse(session_id_2, "Hello2")

    # Clear the results global
    del RESULTS[:]

    # Process all messages
    worker.RunOnce()

    worker.thread_pool.Join()

    # Ensure both requests ran exactly once
    RESULTS.sort()
    self.assertEqual(2, len(RESULTS))
    self.assertEqual("Hello1", RESULTS[0])
    self.assertEqual("Hello2", RESULTS[1])

    # Check that client queue is cleared - should have 2 less messages (since
    # two were completed).
    tasks_on_client_queue = scheduler.SCHEDULER.Query(
        self.client_id, 100, token=self.token)

    self.assertEqual(len(tasks_on_client_queue), 9)

    # Ensure that processed requests are removed from state subject
    self.assertEqual((None, 0), data_store.DB.Resolve(
        flow_context.FlowManager.FLOW_STATE_TEMPLATE % session_id_1,
        flow_context.FlowManager.FLOW_REQUEST_TEMPLATE % 1,
        token=self.token))

    rdf_flow = flow.FACTORY.FetchFlow(session_id_1, token=self.token)
    self.assert_(rdf_flow.state != rdfvalue.Flow.Enum("TERMINATED"))
    flow.FACTORY.ReturnFlow(rdf_flow, token=self.token)

    rdf_flow = flow.FACTORY.FetchFlow(session_id_2, token=self.token)
    self.assertEqual(rdf_flow.state, rdfvalue.Flow.Enum("TERMINATED"))
    flow.FACTORY.ReturnFlow(rdf_flow, token=self.token)


def main(_):
  test_lib.main()

if __name__ == "__main__":
  conf.StartMain(main)
