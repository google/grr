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

"""Tests for the flow."""


import pickle
import time


from grr.client import conf
from grr.client import actions
from grr.client import vfs
from grr.lib import aff4
# pylint: disable=W0611
from grr.lib import aff4_objects
# pylint: enable=W0611
from grr.lib import data_store
from grr.lib import flow
from grr.lib import flow_context
from grr.lib import rdfvalue
# pylint: disable=W0611
from grr.lib import registry
# pylint: enable=W0611
from grr.lib import scheduler
from grr.lib import test_lib
from grr.lib import type_info
# These import populate the AFF4 registry
# pylint: disable=W0611
from grr.lib.flows import general
from grr.lib.flows import tests
# pylint: enable=W0611
from grr.proto import jobs_pb2


class FlowResponseSerialization(flow.GRRFlow):
  """Demonstrate saving responses in the flow."""

  @flow.StateHandler(next_state="Response1")
  def Start(self, unused_message=None):
    self.CallClient("ReturnBlob",
                    rdfvalue.EchoRequest(data="test"),
                    next_state="Response1")

  @flow.StateHandler(next_state="Response2")
  def Response1(self, messages):
    """Record the message id for testing."""
    self.messages = messages
    self.CallClient("ReturnBlob",
                    rdfvalue.EchoRequest(data="test"),
                    next_state="Response2")

  @flow.StateHandler()
  def Response2(self, messages):
    # We need to receive one response and it must be the same as that stored in
    # the previous state.
    if (len(list(messages)) != 1 or
        messages.status.status != rdfvalue.GrrStatus.Enum("OK") or
        list(messages) != list(self.messages)):
      raise RuntimeError("Messages not serialized")


class FlowFactoryTest(test_lib.FlowTestsBaseclass):
  """Test the flow factory."""

  def testInvalidClientId(self):
    """Should raise if the client_id is invalid."""
    self.assertRaises(IOError, flow.FACTORY.StartFlow,
                      "hello", "FlowOrderTest", token=self.token)

  def testUnknownArg(self):
    """Check that flows reject unknown args."""
    self.assertRaises(type_info.UnknownArg, flow.FACTORY.StartFlow,
                      self.client_id, "FlowOrderTest", token=self.token,
                      foobar=1)

  def testFetchReturn(self):
    """Check that we can Fetch and Return a flow."""
    session_id = flow.FACTORY.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)

    flow_pb = flow.FACTORY.FetchFlow(session_id, sync=False, token=self.token)

    # We should not be able to fetch the flow again since its leased
    # now:
    self.assertRaises(flow.LockError, flow.FACTORY.FetchFlow,
                      session_id, sync=False, token=self.token)

    # Ok now its returned
    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)
    flow_pb = flow.FACTORY.FetchFlow(session_id, token=self.token)

    self.assert_(flow_pb)
    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

  def testFlowSerialization(self):
    """Check that we can unpickle flows."""
    session_id = flow.FACTORY.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)

    flow_pb = flow.FACTORY.FetchFlow(session_id, token=self.token)

    flow_obj = flow.FACTORY.LoadFlow(flow_pb)

    self.assertEqual(flow_obj.context.flow_pb.__class__, jobs_pb2.FlowPB)
    self.assertEqual(flow_obj.__class__, test_lib.FlowOrderTest)

    serialized = flow_obj.Dump()
    flow_obj.FlushMessages()

    # Now try to unpickle it
    result = pickle.loads(serialized.pickle)

    self.assertEqual(result.context.flow_pb, None)
    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

  def testFlowSerialization2(self):
    """Check that we can unpickle flows."""

    class TestClientMock(object):

      in_rdfvalue = rdfvalue.EchoRequest
      out_rdfvalue = rdfvalue.DataBlob

      def __init__(self):
        # Register us as an action plugin.
        actions.ActionPlugin.classes["ReturnBlob"] = self

      def ReturnBlob(self, unused_args):
        return [rdfvalue.DataBlob(integer=100)]

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("FlowResponseSerialization",
                                     TestClientMock(), token=self.token,
                                     client_id=self.client_id):
      pass

  def testTerminate(self):
    session_id = flow.FACTORY.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)
    flow.FACTORY.TerminateFlow(session_id, token=self.token)
    flow_pb = flow.FACTORY.FetchFlow(session_id, token=self.token)
    flow_obj = flow.FACTORY.LoadFlow(flow_pb)
    self.assertEqual(flow_obj.context.IsRunning(), False)
    self.assertEqual(flow_obj.context.flow_pb.state,
                     flow_obj.context.flow_pb.ERROR)
    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

    session_id = flow.FACTORY.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)
    flow.FACTORY.TerminateFlow(session_id, reason="no reason",
                               token=self.token)
    flow_pb = flow.FACTORY.FetchFlow(session_id, token=self.token)
    flow_obj = flow.FACTORY.LoadFlow(flow_pb)

    self.assertEqual(flow_obj.context.IsRunning(), False)
    self.assertEqual(flow_obj.context.flow_pb.state,
                     flow_obj.context.flow_pb.ERROR)
    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

  def testNotification(self):
    session_id = flow.FACTORY.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)
    flow_pb = flow.FACTORY.FetchFlow(session_id, token=self.token)
    flow_obj = flow.FACTORY.LoadFlow(flow_pb)
    msg = "Flow terminated due to error"
    flow_obj.Notify("FlowStatus", session_id, msg)
    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

    user_fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add("users").Add(
        self.token.username), mode="r", token=self.token)
    notifications = user_fd.ShowNotifications(reset=False)
    self.assertEqual(len(notifications), 1)
    for notification in notifications:
      self.assertEqual(notification.message, ": " + msg)
      self.assertEqual(notification.subject, rdfvalue.RDFURN(session_id))

  def testFormatstringNotification(self):
    session_id = flow.FACTORY.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)
    flow_pb = flow.FACTORY.FetchFlow(session_id, token=self.token)
    flow_obj = flow.FACTORY.LoadFlow(flow_pb)

    # msg contains %s.
    msg = "Flow reading %system% terminated due to error"
    flow_obj.Notify("FlowStatus", session_id, msg)
    flow_obj.Status(msg)

    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

  def testSendRepliesAttribute(self):
    # Run the flow in the simulated way. Child's send_replies is set to False.
    # Parent flow will raise if number of responses is > 0.
    for _ in test_lib.TestFlowHelper(
        "ParentFlowWithoutResponses", ClientMock(), client_id=self.client_id,
        check_flow_errors=False, token=self.token,):
      pass

    self.assertEqual(ParentFlowWithoutResponses.success, True)


class FlowTest(test_lib.FlowTestsBaseclass):
  """Tests the Flow."""

  def testBrokenFlow(self):
    """Check that flows which call to incorrect states raise."""
    self.assertRaises(flow_context.FlowContextError, flow.FACTORY.StartFlow,
                      self.client_id, "BrokenFlow", token=self.token)

  def SendMessages(self, response_ids, session_id, authenticated=True):
    """Send messages to the flow."""
    for response_id in response_ids:
      message = rdfvalue.GRRMessage(
          request_id=1,
          response_id=response_id,
          session_id=session_id)

      if authenticated:
        message.auth_state = rdfvalue.GRRMessage.Enum("AUTHENTICATED")

      self.SendMessage(message)

  def SendMessage(self, message):
    # Now messages are set in the data store
    response_attribute = flow_context.FlowManager.FLOW_RESPONSE_TEMPLATE % (
        message.request_id,
        message.response_id)

    data_store.DB.Set(
        flow_context.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        response_attribute,
        message, token=self.token)

  def SendOKStatus(self, response_id, session_id):
    """Send a message to the flow."""
    message = rdfvalue.GRRMessage(
        request_id=1,
        response_id=response_id,
        session_id=session_id,
        type=rdfvalue.GRRMessage.Enum("STATUS"),
        auth_state=rdfvalue.GRRMessage.Enum("AUTHENTICATED"))

    status = rdfvalue.GrrStatus(status=rdfvalue.GrrStatus.Enum("OK"))
    message.payload = status

    self.SendMessage(message)

    # Now also set the state on the RequestState
    request_state, _ = data_store.DB.Resolve(
        flow_context.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow_context.FlowManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        decoder=jobs_pb2.RequestState, token=self.token)

    request_state.status.CopyFrom(status.ToProto())

    data_store.DB.Set(
        flow_context.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow_context.FlowManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        request_state, token=self.token)

    return message

  def testReordering(self):
    """Check that out of order client messages are reordered."""
    flow_pb = self.FlowSetup("FlowOrderTest")

    # Retrieve the flow object
    flow_obj = flow.FACTORY.LoadFlow(flow_pb)

    # Simultate processing messages arriving in random order
    message_ids = [2, 1, 4, 3, 5]
    self.SendMessages(message_ids, flow_pb.session_id)

    # Send the status message
    message = self.SendOKStatus(6, flow_pb.session_id)

    flow_obj.ProcessCompletedRequests([message])

    # Check that the messages were processed in order
    self.assertEqual(flow_obj.messages, [1, 2, 3, 4, 5])

    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

  def testCallClient(self):
    """Flows can send client messages using CallClient()."""
    flow_pb = self.FlowSetup("FlowOrderTest")

    # Check that a message went out to the client
    tasks = scheduler.SCHEDULER.Query(self.client_id, limit=100,
                                      decoder=jobs_pb2.GrrMessage,
                                      token=self.token)

    self.assertEqual(len(tasks), 1)

    message = tasks[0].value

    self.assertEqual(message.session_id, flow_pb.session_id)
    self.assertEqual(message.request_id, 1)
    self.assertEqual(message.name, "Test")
    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

  def testAuthentication1(self):
    """Test that flows refuse to processes unauthenticated messages."""
    flow_pb = self.FlowSetup("FlowOrderTest")

    # Retrieve the flow object
    flow_obj = flow.FACTORY.LoadFlow(flow_pb)

    # Simultate processing messages arriving in random order
    message_ids = [2, 1, 4, 3, 5]
    self.SendMessages(message_ids, flow_pb.session_id,
                      authenticated=False)

    # Send the status message
    message = self.SendOKStatus(6, flow_pb.session_id)

    flow_obj.ProcessCompletedRequests([message])

    # Now messages should actually be processed
    self.assertEqual(flow_obj.messages, [])
    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

  def testAuthentication2(self):
    """Test that flows refuse to processes unauthenticated messages.

    Here we try to simulate an attacker injecting unauthenticated
    messages midstream.

    The current implementation actually fails to process the entire
    flow since the injected messages displace the real ones if they
    arrive earlier. This can be an effective DoS against legitimate
    clients but would require attackers to guess session ids.
    """
    flow_pb = self.FlowSetup("FlowOrderTest")

    # Retrieve the flow object
    flow_obj = flow.FACTORY.LoadFlow(flow_pb)

    # Simultate processing messages arriving in random order
    message_ids = [1, 2]
    self.SendMessages(message_ids, flow_pb.session_id,
                      authenticated=True)

    # Now suppose some of the messages are spoofed
    message_ids = [3, 4, 5]
    self.SendMessages(message_ids, flow_pb.session_id,
                      authenticated=False)

    # And now our real messages arrive
    message_ids = [5, 6]
    self.SendMessages(message_ids, flow_pb.session_id,
                      authenticated=True)

    # Send the status message
    message = self.SendOKStatus(7, flow_pb.session_id)

    flow_obj.ProcessCompletedRequests([message])

    # Some messages should actually be processed
    self.assertEqual(flow_obj.messages, [1, 2, 5, 6])
    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

  def testWellKnownFlows(self):
    """Test the well known flows."""
    flow_pb = self.FlowSetup("WellKnownSessionTest")

    # Retrieve the flow object
    test_flow = flow.FACTORY.LoadFlow(flow_pb)

    # Make sure the session ID is well known
    self.assertEqual(test_flow.session_id,
                     test_lib.WellKnownSessionTest.well_known_session_id)

    # Messages to Well Known flows can be unauthenticated
    messages = [rdfvalue.GRRMessage(args=str(i)) for i in range(10)]

    for message in messages:
      test_flow.ProcessMessage(message)

    # The messages might be processed in arbitrary order
    test_flow.messages.sort()

    # Make sure that messages were processed even without a status
    # message to complete the transaction (Well known flows do not
    # have transactions or states - all messages always get to the
    # ProcessMessage method):
    self.assertEqual(test_flow.messages, range(10))
    flow.FACTORY.ReturnFlow(flow_pb, token=self.token)

  def testArgParsing(self):
    """Test that arguments can be extracted and annotated successfully."""

    # Should raise on parsing default.
    self.assertRaises(type_info.TypeValueError, flow.FACTORY.StartFlow,
                      self.client_id, "BadArgsFlow1", arg1=False,
                      token=self.token)

    # Should not raise now if we provide the correct type.
    flow.FACTORY.StartFlow(self.client_id, "BadArgsFlow1",
                           arg1=rdfvalue.RDFPathSpec(), token=self.token)


class GeneralFlowsTest(test_lib.FlowTestsBaseclass):
  """Tests some flows."""

  def testCallState(self):
    """Test the ability to chain flows."""
    CallStateFlow.success = False

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("CallStateFlow", ClientMock(),
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    self.assertEqual(CallStateFlow.success, True)

  def Work(self, client_mock, worker_mock):
    while True:
      client_processed = client_mock.Next()
      flows_run = []
      for flow_run in worker_mock.Next():
        flows_run.append(flow_run)

      if client_processed == 0 and not flows_run:
        break

  def testDelayedCallState(self):
    """Tests the ability to delay a CallState invocation."""

    old_time = time.time
    try:
      time.time = lambda: 10000

      client_mock = ClientMock()
      client_mock = test_lib.MockClient(self.client_id, client_mock,
                                        token=self.token)
      worker_mock = test_lib.MockWorker(check_flow_errors=True,
                                        token=self.token)

      flow.FACTORY.StartFlow(self.client_id, "DelayedCallStateFlow",
                             token=self.token)

      self.Work(client_mock, worker_mock)

      # We should have done the first CallState so far.
      self.assertEqual(DelayedCallStateFlow.state, 1)

      time.time = lambda: 10050

      # 50 seconds more is not enough.
      self.Work(client_mock, worker_mock)
      self.assertEqual(DelayedCallStateFlow.state, 1)

      # But 100 is.
      time.time = lambda: 10100
      self.Work(client_mock, worker_mock)
      self.assertEqual(DelayedCallStateFlow.state, 2)

    finally:
      time.time = old_time

  def testChainedFlow(self):
    """Test the ability to chain flows."""
    ParentFlow.success = False

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("ParentFlow", ClientMock(),
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    self.assertEqual(ParentFlow.success, True)

  def testBrokenChainedFlow(self):
    """Test that exceptions are properly handled in chain flows."""
    BrokenParentFlow.success = False

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper(
        "BrokenParentFlow", ClientMock(), client_id=self.client_id,
        check_flow_errors=False, token=self.token):
      pass

    self.assertEqual(BrokenParentFlow.success, True)

  def testIteratedDirectoryListing(self):
    """Test that the client iterator works."""
    # Install the mock
    vfs.VFS_HANDLERS[rdfvalue.RDFPathSpec.Enum("OS")] = MockVFSHandler
    path = "/"

    # Run the flow in the simulated way
    client_mock = test_lib.ActionMock("IteratedListDirectory")
    for _ in test_lib.TestFlowHelper(
        "IteratedListDirectory", client_mock, client_id=self.client_id,
        pathspec=rdfvalue.RDFPathSpec(path="/",
                                      pathtype=rdfvalue.RDFPathSpec.Enum("OS")),
        token=self.token):
      pass

    fd = aff4.FACTORY.Open(aff4.ROOT_URN.Add(self.client_id).Add(
        "fs/os").Add(path), token=self.token)
    directory = [ch for ch in fd.OpenChildren()]
    pb = rdfvalue.RDFPathSpec(path=path,
                              pathtype=rdfvalue.RDFPathSpec.Enum("OS"))
    directory2 = [x.ToProto() for x in vfs.VFSOpen(pb).ListFiles()]
    directory.sort()
    result = [x.Get(x.Schema.STAT).ToProto() for x in directory]

    # Make sure that the resulting directory is what it should be
    for x, y in zip(result, directory2):
      self.assertProto2Equal(x, y)

  def testClientEventNotification(self):
    """Make sure that client events handled securely."""
    received_events = []

    class Listener1(flow.EventListener):  # pylint:disable=W0612
      well_known_session_id = "aff4:/flows/W:test2"
      EVENTS = ["Event2"]

      @flow.EventHandler(auth_required=True)
      def ProcessMessage(self, message=None, event=None):
        # Store the results for later inspection.
        received_events.append((message, event))

    event = rdfvalue.GRRMessage(
        session_id="W:SomeFlow",
        name="test message",
        source="C.1395c448a443c7d9",
        auth_state=rdfvalue.GRRMessage.Enum("AUTHENTICATED"),
        payload=rdfvalue.RDFPathSpec(
            path="foobar"))

    flow.PublishEvent("Event2", event, token=self.token)

    worker = test_lib.MockWorker(queue_name="W", token=self.token)
    while worker.Next():
      pass
    worker.pool.Join()

    # This should not work - the event listender does not accept client events.
    self.assertEqual(received_events, [])

    class Listener2(flow.EventListener):  # pylint:disable=W0612
      well_known_session_id = "aff4:/flows/W:test3"
      EVENTS = ["Event2"]

      @flow.EventHandler(auth_required=True, allow_client_access=True)
      def ProcessMessage(self, message=None, event=None):
        # Store the results for later inspection.
        received_events.append((message, event))

    flow.PublishEvent("Event2", event, token=self.token)

    worker = test_lib.MockWorker(queue_name="W", token=self.token)
    while worker.Next():
      pass
    worker.pool.Join()

    # This should now work - the event listener does accept client events.
    self.assertEqual(len(received_events), 1)

  def testFlowNotification(self):
    event_queue = "EV"

    received_events = []

    class FlowDoneListener(flow.EventListener):  # pylint:disable=W0612
      well_known_session_id = "aff4:/flows/%s:FlowDone" % event_queue
      EVENTS = ["Not used"]

      @flow.EventHandler(auth_required=True)
      def ProcessMessage(self, message=None, event=None):
        _ = event
        # Store the results for later inspection.
        received_events.append(message)

    # Install the mock
    vfs.VFS_HANDLERS[rdfvalue.RDFPathSpec.Enum("OS")] = MockVFSHandler
    path = rdfvalue.RDFPathSpec(path="/",
                                pathtype=rdfvalue.RDFPathSpec.Enum("OS"))

    # Run the flow in the simulated way
    client_mock = test_lib.ActionMock("IteratedListDirectory")
    for _ in test_lib.TestFlowHelper(
        "IteratedListDirectory", client_mock, client_id=self.client_id,
        notification_event="aff4:/flows/%s:FlowDone" % event_queue,
        pathspec=path, token=self.token):
      pass

    # The event goes to an external queue so we need another worker.
    worker = test_lib.MockWorker(queue_name=event_queue, token=self.token)
    while worker.Next():
      pass
    worker.pool.Join()

    self.assertEqual(len(received_events), 1)
    self.assertEqual(received_events[0].session_id, "aff4:/flows/EV:FlowDone")
    self.assertEqual(received_events[0].source, "IteratedListDirectory")

    flow_event = rdfvalue.FlowNotification(received_events[0].args)
    self.assertEqual(flow_event.flow_name, "IteratedListDirectory")
    self.assertEqual(flow_event.client_id, "C.1000000000000000")
    self.assertEqual(flow_event.status, rdfvalue.FlowNotification.Enum("OK"))

  def testEventNotification(self):
    """Test that events are sent to listeners."""
    received_events = []

    class Listener1(flow.EventListener):  # pylint:disable=W0612
      well_known_session_id = "aff4:/flows/W:test1"
      EVENTS = ["Event1"]

      @flow.EventHandler(auth_required=True)
      def ProcessMessage(self, message=None, event=None):
        # Store the results for later inspection.
        received_events.append((message, event))

    event = rdfvalue.GRRMessage(
        session_id="W:SomeFlow", name="test message",
        payload=rdfvalue.RDFPathSpec(path="foobar", pathtype=1))

    # Not allowed to publish a message not from a valid source.
    self.assertRaises(RuntimeError, flow.PublishEvent, "Event1", event,
                      token=self.token)

    event.source = "Source"

    # First make the message unauthenticated.
    event.auth_state = rdfvalue.GRRMessage.Enum("UNAUTHENTICATED")

    # Publish the event.
    flow.PublishEvent("Event1", event, token=self.token)

    # Now emulate a worker.
    worker = test_lib.MockWorker(queue_name="W", token=self.token)
    while worker.Next():
      pass
    worker.pool.Join()

    # This should not work - the unauthenticated message is dropped.
    self.assertEqual(received_events, [])

    # First make the message unauthenticated.
    event.auth_state = rdfvalue.GRRMessage.Enum("AUTHENTICATED")

    # Publish the event.
    flow.PublishEvent("Event1", event, token=self.token)

    # Now emulate a worker.
    while worker.Next():
      pass
    worker.pool.Join()

    # This should now work:
    self.assertEqual(len(received_events), 1)

    # Make sure the source is correctly propagated.
    self.assertEqual(received_events[0][0].source, "Source")
    self.assertEqual(received_events[0][1].path, "foobar")

    received_events = []
    # Now schedule ten events at the same time.
    for i in xrange(10):
      event.source = "Source%d" % i
      flow.PublishEvent("Event1", event, token=self.token)

    # Now emulate a worker.
    while worker.Next():
      pass
    worker.pool.Join()

    self.assertEqual(len(received_events), 10)
    for i in range(10):
      self.assertEqual(received_events[i][0].source, "Source%d" % i)
      self.assertEqual(received_events[i][1].path, "foobar")

  def testClientPrioritization(self):
    """Test that flow priorities work on the client side."""

    result = []
    client_mock = PriorityClientMock(result)
    client_mock = test_lib.MockClient(self.client_id, client_mock,
                                      token=self.token)
    worker_mock = test_lib.MockWorker(check_flow_errors=True,
                                      token=self.token)

    # Start some flows with different priorities.
    args = [(rdfvalue.GRRMessage.Enum("LOW_PRIORITY"), "low priority"),
            (rdfvalue.GRRMessage.Enum("MEDIUM_PRIORITY"), "medium priority"),
            (rdfvalue.GRRMessage.Enum("LOW_PRIORITY"), "low priority2"),
            (rdfvalue.GRRMessage.Enum("HIGH_PRIORITY"), "high priority"),
            (rdfvalue.GRRMessage.Enum("MEDIUM_PRIORITY"), "medium priority2")]

    for (priority, msg) in args:
      flow.FACTORY.StartFlow(
          self.client_id, "PriorityFlow", msg=msg,
          priority=priority, token=self.token)

    while True:
      client_processed = client_mock.Next()
      flows_run = []
      for flow_run in worker_mock.Next():
        flows_run.append(flow_run)

      if client_processed == 0 and not flows_run:
        break

    # The flows should be run in order of priority.
    self.assertEqual(result[0:1],
                     [u"high priority"])
    self.assertEqual(sorted(result[1:3]),
                     [u"medium priority", u"medium priority2"])
    self.assertEqual(sorted(result[3:5]),
                     [u"low priority", u"low priority2"])

  def testWorkerPrioritization(self):
    """Test that flow priorities work on the worker side."""

    result = []
    client_mock = PriorityClientMock(result)
    client_mock = test_lib.MockClient(self.client_id, client_mock,
                                      token=self.token)
    worker_mock = test_lib.MockWorker(check_flow_errors=True,
                                      token=self.token)

    # Start some flows with different priorities.
    args = [(rdfvalue.GRRMessage.Enum("LOW_PRIORITY"), "low priority"),
            (rdfvalue.GRRMessage.Enum("MEDIUM_PRIORITY"), "medium priority"),
            (rdfvalue.GRRMessage.Enum("LOW_PRIORITY"), "low priority2"),
            (rdfvalue.GRRMessage.Enum("HIGH_PRIORITY"), "high priority"),
            (rdfvalue.GRRMessage.Enum("MEDIUM_PRIORITY"), "medium priority2")]

    server_result = []
    PriorityFlow.storage = server_result

    for (priority, msg) in args:
      flow.FACTORY.StartFlow(
          self.client_id, "PriorityFlow", msg=msg,
          priority=priority, token=self.token)

    while True:
      # Run all the clients first so workers have messages to choose from.
      client_processed = 1
      while client_processed:
        client_processed = client_mock.Next()
      # Now process the results, this should happen in the correct order.
      flows_run = []
      for flow_run in worker_mock.Next():
        flows_run.append(flow_run)

      if not flows_run:
        break

    # The flows should be run in order of priority.
    self.assertEqual(server_result[0:1],
                     [u"high priority"])
    self.assertEqual(sorted(server_result[1:3]),
                     [u"medium priority", u"medium priority2"])
    self.assertEqual(sorted(server_result[3:5]),
                     [u"low priority", u"low priority2"])

  def testCPULimit(self):
    """Tests that the cpu limit works."""

    result = []
    client_mock = CPULimitClientMock(result)
    client_mock = test_lib.MockClient(self.client_id, client_mock,
                                      token=self.token)
    worker_mock = test_lib.MockWorker(check_flow_errors=True,
                                      token=self.token)

    flow.FACTORY.StartFlow(
        self.client_id, "CPULimitFlow",
        cpu_limit=100, token=self.token)

    while True:
      client_processed = client_mock.Next()
      flows_run = []
      for flow_run in worker_mock.Next():
        flows_run.append(flow_run)

      if client_processed == 0 and not flows_run:
        break

    self.assertEqual(result, [100, 98, 78])


class MockVFSHandler(vfs.VFSHandler):
  """A mock VFS handler with fake files."""
  children = []
  for x in range(10):
    child = rdfvalue.StatEntry(pathspec=rdfvalue.RDFPathSpec(
        path="Foo%s" % x, pathtype=rdfvalue.RDFPathSpec.Enum("OS")))
    children.append(child)

  supported_pathtype = rdfvalue.RDFPathSpec.Enum("OS")

  def __init__(self, base_fd, pathspec=None):
    super(MockVFSHandler, self).__init__(base_fd, pathspec=pathspec)

    self.pathspec.Append(pathspec)

  def ListFiles(self):
    return self.children

  def IsDirectory(self):
    return self.pathspec.path == "/"


class PriorityClientMock(object):

  in_rdfvalue = rdfvalue.DataBlob

  def __init__(self, storage):
    # Register us as an action plugin.
    actions.ActionPlugin.classes["Store"] = self
    self.storage = storage

  def Store(self, data):
    self.storage.append(self.in_rdfvalue(data).string)
    return [rdfvalue.DataBlob(string="Hello World")]


class PriorityFlow(flow.GRRFlow):
  """This flow is used to test priorities."""

  def __init__(self, msg="", **kw):
    super(PriorityFlow, self).__init__(**kw)
    self.msg = msg

  @flow.StateHandler(next_state="Done")
  def Start(self):
    self.CallClient("Store", string=self.msg, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    _ = responses
    try:
      self.storage.append(self.msg)
    except AttributeError:
      pass


class CPULimitClientMock(object):

  in_rdfvalue = rdfvalue.DataBlob

  def __init__(self, storage):
    # Register us as an action plugin.
    actions.ActionPlugin.classes["Store"] = self
    self.storage = storage

  def HandleMessage(self, message):
    self.storage.append(message.cpu_limit)


class CPULimitFlow(flow.GRRFlow):
  """This flow is used to test the cpu limit."""

  @flow.StateHandler(next_state="State1")
  def Start(self):
    self.CallClient("Store", string="Hey!", next_state="State1")

  @flow.StateHandler(next_state="State2")
  def State1(self):
    # The mock worker doesn't track usage so we add it here.
    self.flow_pb.cpu_used.user_cpu_time += 1
    self.flow_pb.cpu_used.system_cpu_time += 1
    self.flow_pb.remaining_cpu_quota -= 2
    self.CallClient("Store", string="Hey!", next_state="State2")

  @flow.StateHandler(next_state="Done")
  def State2(self):
    self.flow_pb.cpu_used.user_cpu_time += 10
    self.flow_pb.cpu_used.system_cpu_time += 10
    self.flow_pb.remaining_cpu_quota -= 20
    self.CallClient("Store", string="Hey!", next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    pass


class ClientMock(object):
  """Mock of client actions."""

  in_rdfvalue = None
  out_rdfvalue = rdfvalue.RDFString

  def __init__(self):
    # Register us as an action plugin.
    actions.ActionPlugin.classes["ReturnHello"] = self

  def ReturnHello(self, _):
    return [rdfvalue.RDFString("Hello World")]


class ChildFlow(flow.GRRFlow):
  """This flow will be called by our parent."""

  @flow.StateHandler(next_state="ReceiveHello")
  def Start(self):
    self.CallClient("ReturnHello", next_state="ReceiveHello")

  @flow.StateHandler()
  def ReceiveHello(self, responses):
    # Relay the client's message to our parent
    for response in responses:
      self.SendReply(rdfvalue.RDFString("Child received"))
      self.SendReply(response)


class BrokenChildFlow(ChildFlow):
  """A broken flow which raises."""

  @flow.StateHandler()
  def ReceiveHello(self, responses):
    raise IOError("Boo")


class ParentFlow(flow.GRRFlow):
  """This flow will launch a child flow."""

  # This is a global flag which will be set when the flow runs.
  success = False

  @flow.StateHandler(next_state="ParentReceiveHello")
  def Start(self):
    # Call the child flow.
    self.CallFlow("ChildFlow",
                  next_state="ParentReceiveHello")

  @flow.StateHandler()
  def ParentReceiveHello(self, responses):
    responses = list(responses)
    if (len(responses) != 2 or "Child" not in unicode(responses[0]) or
        "Hello" not in unicode(responses[1])):
      raise RuntimeError("Messages not passed to parent")

    ParentFlow.success = True


class ParentFlowWithoutResponses(flow.GRRFlow):
  """This flow will launch a child flow."""

  success = False

  @flow.StateHandler(next_state="ParentReceiveHello")
  def Start(self):
    # Call the child flow.
    self.CallFlow("ChildFlow",
                  send_replies=False,
                  next_state="ParentReceiveHello")

  @flow.StateHandler()
  def ParentReceiveHello(self, responses):
    if responses:
      raise RuntimeError("Messages are not expected to be passed to parent")

    ParentFlowWithoutResponses.success = True


class BrokenParentFlow(flow.GRRFlow):
  """This flow will launch a broken child flow."""

  # This is a global flag which will be set when the flow runs.
  success = False

  @flow.StateHandler(next_state="ReceiveHello")
  def Start(self):
    # Call the child flow.
    self.CallFlow("BrokenChildFlow",
                  next_state="ReceiveHello")

  @flow.StateHandler()
  def ReceiveHello(self, responses):
    if (responses or
        responses.status.status == rdfvalue.GrrStatus.Enum("OK")):
      raise RuntimeError("Error not propagated to parent")

    BrokenParentFlow.success = True


class CallStateFlow(flow.GRRFlow):
  """A flow that calls one of its own states."""

  # This is a global flag which will be set when the flow runs.
  success = False

  @flow.StateHandler(next_state="ReceiveHello")
  def Start(self):
    # Call the child flow.
    self.context.CallState([rdfvalue.RDFString("Hello")],
                           next_state="ReceiveHello")

  @flow.StateHandler()
  def ReceiveHello(self, responses):
    if responses.First() != "Hello":
      raise RuntimeError("Did not receive hello.")

    CallStateFlow.success = True


class DelayedCallStateFlow(flow.GRRFlow):
  """A flow that calls one of its own states with a delay."""

  # This is a global flag which will be set when the flow runs.
  state = 0

  @flow.StateHandler(next_state="ReceiveHello")
  def Start(self):
    # Call the child flow.
    self.context.CallState([rdfvalue.RDFString("Hello")],
                           next_state="ReceiveHello")

  @flow.StateHandler(next_state="DelayedHello")
  def ReceiveHello(self, responses):
    if responses.First() != "Hello":
      raise RuntimeError("Did not receive hello.")
    DelayedCallStateFlow.state = 1

    # Call the child flow.
    self.context.CallState([rdfvalue.RDFString("Hello")],
                           next_state="DelayedHello", delay=100)

  @flow.StateHandler()
  def DelayedHello(self, responses):
    if responses.First() != "Hello":
      raise RuntimeError("Did not receive hello.")
    DelayedCallStateFlow.state = 2


class BadArgsFlow1(flow.GRRFlow):
  """A flow that has args that mismatch type info."""

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.RDFValueType(
          name="arg1",
          rdfclass=rdfvalue.RDFPathSpec))


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.FlowTestsBaseclass


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  conf.StartMain(main)
