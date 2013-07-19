#!/usr/bin/env python
"""Tests for the flow."""


import time


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
from grr.lib.flows import tests
# pylint: enable=unused-import,g-bad-import-order

from grr.client import actions
from grr.client import vfs
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flags
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import rdfvalue
from grr.lib import scheduler
from grr.lib import test_lib
from grr.lib import type_info


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
    self.state.Register("messages", messages)
    self.CallClient("ReturnBlob",
                    rdfvalue.EchoRequest(data="test"),
                    next_state="Response2")

  @flow.StateHandler()
  def Response2(self, messages):
    # We need to receive one response and it must be the same as that stored in
    # the previous state.
    if (len(list(messages)) != 1 or
        messages.status.status != rdfvalue.GrrStatus.ReturnedStatus.OK or
        list(messages) != list(self.state.messages)):
      raise RuntimeError("Messages not serialized")


class NoRequestChildFlow(flow.GRRFlow):
  """This flow just returns and does not generate any requests."""

  @flow.StateHandler()
  def Start(self, unused_message):
    return


class CallClientChildFlow(flow.GRRFlow):
  """This flow just returns and does not generate any requests."""

  @flow.StateHandler()
  def Start(self, unused_message):
    self.CallClient("GetClientStats", next_state="End")


class NoRequestParentFlow(flow.GRRFlow):

  child_flow = "NoRequestChildFlow"

  @flow.StateHandler(next_state="End")
  def Start(self, unused_message):
    self.CallFlow(self.child_flow)

  @flow.StateHandler()
  def End(self, unused_message):
    pass


class CallClientParentFlow(NoRequestParentFlow):
  child_flow = "CallClientChildFlow"


class FlowCreationTest(test_lib.FlowTestsBaseclass):
  """Test flow creation."""

  def testInvalidClientId(self):
    """Should raise if the client_id is invalid."""
    self.assertRaises(ValueError, flow.GRRFlow.StartFlow,
                      "hello", "FlowOrderTest", token=self.token)

  def testUnknownArg(self):
    """Check that flows reject unknown args."""
    self.assertRaises(type_info.UnknownArg, flow.GRRFlow.StartFlow,
                      self.client_id, "FlowOrderTest", token=self.token,
                      foobar=1)

  def testTypeAttributeIsNotAppendedWhenFlowIsClosed(self):
    session_id = flow.GRRFlow.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)

    flow_obj = aff4.FACTORY.Open(session_id, aff4_type="FlowOrderTest",
                                 age=aff4.ALL_TIMES, mode="rw",
                                 token=self.token)
    flow_obj.Close()

    flow_obj = aff4.FACTORY.Open(session_id, aff4_type="FlowOrderTest",
                                 age=aff4.ALL_TIMES, token=self.token)

    types = list(flow_obj.GetValuesForAttribute(flow_obj.Schema.TYPE))
    self.assertEqual(len(types), 1)

  def testFlowSerialization(self):
    """Check that we can unpickle flows."""
    session_id = flow.GRRFlow.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)

    flow_obj = aff4.FACTORY.Open(session_id, aff4_type="FlowOrderTest",
                                 age=aff4.ALL_TIMES, token=self.token)

    self.assertEqual(flow_obj.__class__, test_lib.FlowOrderTest)

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
    session_id = flow.GRRFlow.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)

    flow.GRRFlow.TerminateFlow(session_id, token=self.token)
    flow_obj = aff4.FACTORY.Open(session_id, aff4_type="FlowOrderTest",
                                 age=aff4.ALL_TIMES, token=self.token)
    self.assertEqual(flow_obj.IsRunning(), False)
    self.assertEqual(flow_obj.state.context.state,
                     rdfvalue.Flow.State.ERROR)

    reason = "no reason"
    session_id = flow.GRRFlow.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)
    flow.GRRFlow.TerminateFlow(session_id, reason=reason, token=self.token)

    flow_obj = aff4.FACTORY.Open(session_id, aff4_type="FlowOrderTest",
                                 age=aff4.ALL_TIMES, token=self.token)
    self.assertEqual(flow_obj.IsRunning(), False)
    self.assertEqual(flow_obj.state.context.state,
                     rdfvalue.Flow.State.ERROR)
    self.assertTrue(reason in flow_obj.state.context.status)

  def testChildTermination(self):
    session_id = flow.GRRFlow.StartFlow(self.client_id, "CallClientParentFlow",
                                        token=self.token)
    flow_obj = aff4.FACTORY.Open(session_id, token=self.token)
    children = list(flow_obj.ListChildren())
    self.assertEqual(len(children), 1)

    reason = "just so"

    flow.GRRFlow.TerminateFlow(session_id, reason=reason, token=self.token)

    flow_obj = aff4.FACTORY.Open(session_id,
                                 aff4_type="CallClientParentFlow",
                                 token=self.token)
    child = aff4.FACTORY.Open(children[0],
                              aff4_type="CallClientChildFlow",
                              token=self.token)
    self.assertEqual(flow_obj.IsRunning(), False)
    self.assertEqual(flow_obj.state.context.state,
                     rdfvalue.Flow.State.ERROR)

    self.assertTrue("user test" in flow_obj.state.context.status)
    self.assertTrue(reason in flow_obj.state.context.status)
    self.assertEqual(child.IsRunning(), False)
    self.assertEqual(child.state.context.state,
                     rdfvalue.Flow.State.ERROR)

    self.assertTrue("user test" in child.state.context.status)
    self.assertTrue("Parent flow terminated." in child.state.context.status)

  def testNotification(self):
    session_id = flow.GRRFlow.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)
    flow_obj = aff4.FACTORY.Open(session_id, aff4_type="FlowOrderTest",
                                 age=aff4.ALL_TIMES, mode="rw",
                                 token=self.token)
    msg = "Flow terminated due to error"
    flow_obj.Notify("FlowStatus", session_id, msg)
    flow_obj.Close()

    user_fd = aff4.FACTORY.Open(rdfvalue.RDFURN("aff4:/users").Add(
        self.token.username), mode="r", token=self.token)
    notifications = user_fd.ShowNotifications(reset=False)
    self.assertEqual(len(notifications), 1)
    for notification in notifications:
      self.assertTrue(notification.message.endswith(": " + msg))
      self.assertEqual(notification.subject, rdfvalue.RDFURN(session_id))

  def testFormatstringNotification(self):
    session_id = flow.GRRFlow.StartFlow(self.client_id, "FlowOrderTest",
                                        token=self.token)
    flow_obj = aff4.FACTORY.Open(session_id, aff4_type="FlowOrderTest",
                                 age=aff4.ALL_TIMES, mode="rw",
                                 token=self.token)
    # msg contains %s.
    msg = "Flow reading %system% terminated due to error"
    flow_obj.Notify("FlowStatus", session_id, msg)
    flow_obj.Status(msg)
    flow_obj.Close()

  def testSendRepliesAttribute(self):
    # Run the flow in the simulated way. Child's send_replies is set to False.
    # Parent flow will raise if number of responses is > 0.
    for _ in test_lib.TestFlowHelper(
        "ParentFlowWithoutResponses", ClientMock(), client_id=self.client_id,
        check_flow_errors=False, token=self.token,):
      pass

    self.assertEqual(ParentFlowWithoutResponses.success, True)

  notifications = {}

  def CollectNotifications(self, queue, session_ids, priorities, **kwargs):
    now = time.time()
    for session_id in session_ids:
      self.notifications.setdefault(session_id, []).append(now)
    self.old_notify(queue, session_ids, priorities, **kwargs)

  def testNoRequestChildFlowRace(self):

    self.old_notify = scheduler.SCHEDULER._MultiNotifyQueue
    scheduler.SCHEDULER._MultiNotifyQueue = self.CollectNotifications
    try:
      session_id = flow.GRRFlow.StartFlow(self.client_id, "NoRequestParentFlow",
                                          token=self.token)
    finally:
      scheduler.SCHEDULER._MultiNotifyQueue = self.old_notify

    self.assertIn(session_id, self.notifications)

    f = aff4.FACTORY.Open(session_id, token=self.token)

    # Check that the first notification came in after the flow was created.
    self.assertLess(int(f.Get(f.Schema.TYPE).age),
                    1e6 * min(self.notifications[session_id]),
                    "There was a notification for a flow before "
                    "the flow was created.")

  def testCallClientChildFlowRace(self):
    session_id = flow.GRRFlow.StartFlow(self.client_id,
                                        "CallClientParentFlow",
                                        token=self.token)

    client_requests = data_store.DB.ResolveRegex(self.client_id, "task:.*",
                                                 token=self.token)
    self.assertEqual(len(client_requests), 1)

    f = aff4.FACTORY.Open(session_id, token=self.token)

    for (_, _, timestamp) in client_requests:
      # Check that the client request was written after the flow was created.
      self.assertLess(int(f.Get(f.Schema.TYPE).age), timestamp,
                      "The client request was issued before "
                      "the flow was created.")


class FlowTest(test_lib.FlowTestsBaseclass):
  """Tests the Flow."""

  def testBrokenFlow(self):
    """Check that flows which call to incorrect states raise."""
    self.assertRaises(flow_runner.FlowRunnerError, flow.GRRFlow.StartFlow,
                      self.client_id, "BrokenFlow", token=self.token)

  def SendMessages(self, response_ids, session_id, authenticated=True):
    """Send messages to the flow."""
    for response_id in response_ids:
      message = rdfvalue.GrrMessage(
          request_id=1,
          response_id=response_id,
          session_id=session_id)

      if authenticated:
        auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED
        message.auth_state = auth_state

      self.SendMessage(message)

  def SendMessage(self, message):
    # Now messages are set in the data store
    response_attribute = flow_runner.FlowManager.FLOW_RESPONSE_TEMPLATE % (
        message.request_id,
        message.response_id)

    data_store.DB.Set(
        flow_runner.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        response_attribute,
        message, token=self.token)

  def SendOKStatus(self, response_id, session_id):
    """Send a message to the flow."""
    message = rdfvalue.GrrMessage(
        request_id=1,
        response_id=response_id,
        session_id=session_id,
        type=rdfvalue.GrrMessage.Type.STATUS,
        auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED)

    status = rdfvalue.GrrStatus(status=rdfvalue.GrrStatus.ReturnedStatus.OK)
    message.payload = status

    self.SendMessage(message)

    # Now also set the state on the RequestState
    request_state, _ = data_store.DB.Resolve(
        flow_runner.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow_runner.FlowManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        decoder=rdfvalue.RequestState, token=self.token)

    request_state.status = status

    data_store.DB.Set(
        flow_runner.FlowManager.FLOW_STATE_TEMPLATE % message.session_id,
        flow_runner.FlowManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        request_state, token=self.token)

    return message

  def testReordering(self):
    """Check that out of order client messages are reordered."""
    flow_obj = self.FlowSetup("FlowOrderTest")

    # Simultate processing messages arriving in random order
    message_ids = [2, 1, 4, 3, 5]
    self.SendMessages(message_ids, flow_obj.session_id)

    # Send the status message
    message = self.SendOKStatus(6, flow_obj.session_id)

    runner = flow_runner.FlowRunner(flow_obj)
    runner.ProcessCompletedRequests([message])

    # Check that the messages were processed in order
    self.assertEqual(flow_obj.messages, [1, 2, 3, 4, 5])

  def testCallClient(self):
    """Flows can send client messages using CallClient()."""
    flow_obj = self.FlowSetup("FlowOrderTest")

    # Check that a message went out to the client
    tasks = scheduler.SCHEDULER.Query(self.client_id, limit=100,
                                      token=self.token)

    self.assertEqual(len(tasks), 1)

    message = tasks[0]

    self.assertEqual(message.session_id, flow_obj.session_id)
    self.assertEqual(message.request_id, 1)
    self.assertEqual(message.name, "Test")

  def testAuthentication1(self):
    """Test that flows refuse to processes unauthenticated messages."""
    flow_obj = self.FlowSetup("FlowOrderTest")

    # Simultate processing messages arriving in random order
    message_ids = [2, 1, 4, 3, 5]
    self.SendMessages(message_ids, flow_obj.session_id,
                      authenticated=False)

    # Send the status message
    message = self.SendOKStatus(6, flow_obj.session_id)

    runner = flow_runner.FlowRunner(flow_obj)
    runner.ProcessCompletedRequests([message])

    # Now messages should actually be processed
    self.assertEqual(flow_obj.messages, [])

  def testAuthentication2(self):
    """Test that flows refuse to processes unauthenticated messages.

    Here we try to simulate an attacker injecting unauthenticated
    messages midstream.

    The current implementation actually fails to process the entire
    flow since the injected messages displace the real ones if they
    arrive earlier. This can be an effective DoS against legitimate
    clients but would require attackers to guess session ids.
    """
    flow_obj = self.FlowSetup("FlowOrderTest")

    # Simultate processing messages arriving in random order
    message_ids = [1, 2]
    self.SendMessages(message_ids, flow_obj.session_id,
                      authenticated=True)

    # Now suppose some of the messages are spoofed
    message_ids = [3, 4, 5]
    self.SendMessages(message_ids, flow_obj.session_id,
                      authenticated=False)

    # And now our real messages arrive
    message_ids = [5, 6]
    self.SendMessages(message_ids, flow_obj.session_id,
                      authenticated=True)

    # Send the status message
    message = self.SendOKStatus(7, flow_obj.session_id)

    runner = flow_runner.FlowRunner(flow_obj)
    runner.ProcessCompletedRequests([message])

    # Some messages should actually be processed
    self.assertEqual(flow_obj.messages, [1, 2, 5, 6])

  def testWellKnownFlows(self):
    """Test the well known flows."""
    test_flow = self.FlowSetup("WellKnownSessionTest")

    # Make sure the session ID is well known
    self.assertEqual(test_flow.session_id,
                     test_lib.WellKnownSessionTest.well_known_session_id)

    # Messages to Well Known flows can be unauthenticated
    messages = [rdfvalue.GrrMessage(args=str(i)) for i in range(10)]

    for message in messages:
      test_flow.ProcessMessage(message)

    # The messages might be processed in arbitrary order
    test_flow.messages.sort()

    # Make sure that messages were processed even without a status
    # message to complete the transaction (Well known flows do not
    # have transactions or states - all messages always get to the
    # ProcessMessage method):
    self.assertEqual(test_flow.messages, range(10))

  def testArgParsing(self):
    """Test that arguments can be extracted and annotated successfully."""

    # Should raise on parsing default.
    self.assertRaises(type_info.TypeValueError, flow.GRRFlow.StartFlow,
                      self.client_id, "BadArgsFlow1", arg1=False,
                      token=self.token)

    # Should not raise now if we provide the correct type.
    flow.GRRFlow.StartFlow(self.client_id, "BadArgsFlow1",
                           arg1=rdfvalue.PathSpec(), token=self.token)


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

      flow.GRRFlow.StartFlow(self.client_id, "DelayedCallStateFlow",
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
    vfs.VFS_HANDLERS[rdfvalue.PathSpec.PathType.OS] = MockVFSHandler
    path = "/"

    # Run the flow in the simulated way
    client_mock = test_lib.ActionMock("IteratedListDirectory")
    for _ in test_lib.TestFlowHelper(
        "IteratedListDirectory", client_mock, client_id=self.client_id,
        pathspec=rdfvalue.PathSpec(path="/",
                                   pathtype=rdfvalue.PathSpec.PathType.OS),
        token=self.token):
      pass

    fd = aff4.FACTORY.Open(self.client_id.Add("fs/os").Add(path),
                           token=self.token)
    directory = [ch for ch in fd.OpenChildren()]
    pb = rdfvalue.PathSpec(path=path,
                           pathtype=rdfvalue.PathSpec.PathType.OS)
    directory2 = list(vfs.VFSOpen(pb).ListFiles())
    directory.sort()
    result = [x.Get(x.Schema.STAT) for x in directory]

    # Make sure that the resulting directory is what it should be
    for x, y in zip(result, directory2):
      self.assertEqual(x.st_mode, y.st_mode)
      self.assertProtoEqual(x, y)

  def testClientEventNotification(self):
    """Make sure that client events handled securely."""
    received_events = []

    class Listener1(flow.EventListener):  # pylint: disable=unused-variable
      well_known_session_id = rdfvalue.SessionID("aff4:/flows/W:test2")
      EVENTS = ["Event2"]

      @flow.EventHandler(auth_required=True)
      def ProcessMessage(self, message=None, event=None):
        # Store the results for later inspection.
        received_events.append((message, event))

    event = rdfvalue.GrrMessage(
        session_id="W:SomeFlow",
        name="test message",
        source="C.1395c448a443c7d9",
        auth_state=rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED,
        payload=rdfvalue.PathSpec(
            path="foobar"))

    flow.PublishEvent("Event2", event, token=self.token)

    worker = test_lib.MockWorker(token=self.token)
    while worker.Next():
      pass
    worker.pool.Join()

    # This should not work - the event listender does not accept client events.
    self.assertEqual(received_events, [])

    class Listener2(flow.EventListener):  # pylint: disable=unused-variable
      well_known_session_id = rdfvalue.SessionID("aff4:/flows/W:test3")
      EVENTS = ["Event2"]

      @flow.EventHandler(auth_required=True, allow_client_access=True)
      def ProcessMessage(self, message=None, event=None):
        # Store the results for later inspection.
        received_events.append((message, event))

    flow.PublishEvent("Event2", event, token=self.token)

    worker = test_lib.MockWorker(token=self.token)
    while worker.Next():
      pass
    worker.pool.Join()

    # This should now work - the event listener does accept client events.
    self.assertEqual(len(received_events), 1)

  def testFlowNotification(self):
    event_queue = "EV"

    received_events = []

    class FlowDoneListener(flow.EventListener):  # pylint: disable=unused-variable
      well_known_session_id = rdfvalue.SessionID(
          "aff4:/flows/%s:FlowDone" % event_queue)
      EVENTS = ["Not used"]

      @flow.EventHandler(auth_required=True)
      def ProcessMessage(self, message=None, event=None):
        _ = event
        # Store the results for later inspection.
        received_events.append(message)

    # Install the mock
    vfs.VFS_HANDLERS[rdfvalue.PathSpec.PathType.OS] = MockVFSHandler
    path = rdfvalue.PathSpec(path="/",
                             pathtype=rdfvalue.PathSpec.PathType.OS)

    # Run the flow in the simulated way
    client_mock = test_lib.ActionMock("IteratedListDirectory")
    for _ in test_lib.TestFlowHelper(
        "IteratedListDirectory", client_mock, client_id=self.client_id,
        notification_event=rdfvalue.SessionID(
            "aff4:/flows/%s:FlowDone" % event_queue),
        pathspec=path, token=self.token):
      pass

    # The event goes to an external queue so we need another worker.
    worker = test_lib.MockWorker(queue=rdfvalue.RDFURN(event_queue),
                                 token=self.token)
    while worker.Next():
      pass
    worker.pool.Join()

    self.assertEqual(len(received_events), 1)
    self.assertEqual(received_events[0].session_id,
                     rdfvalue.SessionID("aff4:/flows/EV:FlowDone"))
    self.assertEqual(received_events[0].source,
                     rdfvalue.RDFURN("IteratedListDirectory"))

    flow_event = rdfvalue.FlowNotification(received_events[0].args)
    self.assertEqual(flow_event.flow_name, "IteratedListDirectory")
    self.assertEqual(flow_event.client_id, "aff4:/C.1000000000000000")
    self.assertEqual(flow_event.status, rdfvalue.FlowNotification.Status.OK)

  def testEventNotification(self):
    """Test that events are sent to listeners."""
    received_events = []

    class Listener1(flow.EventListener):  # pylint: disable=unused-variable
      well_known_session_id = rdfvalue.SessionID("aff4:/flows/W:test1")
      EVENTS = ["Event1"]

      @flow.EventHandler(auth_required=True)
      def ProcessMessage(self, message=None, event=None):
        # Store the results for later inspection.
        received_events.append((message, event))

    event = rdfvalue.GrrMessage(
        session_id="aff4:/W:SomeFlow", name="test message",
        payload=rdfvalue.PathSpec(path="foobar", pathtype=1))

    # Not allowed to publish a message not from a valid source.
    self.assertRaises(RuntimeError, flow.PublishEvent, "Event1", event,
                      token=self.token)

    event.source = "Source"

    # First make the message unauthenticated.
    event.auth_state = rdfvalue.GrrMessage.AuthorizationState.UNAUTHENTICATED

    # Publish the event.
    flow.PublishEvent("Event1", event, token=self.token)

    # Now emulate a worker.
    worker = test_lib.MockWorker(token=self.token)
    while worker.Next():
      pass
    worker.pool.Join()

    # This should not work - the unauthenticated message is dropped.
    self.assertEqual(received_events, [])

    # Now make the message authenticated.
    event.auth_state = rdfvalue.GrrMessage.AuthorizationState.AUTHENTICATED

    # Publish the event.
    flow.PublishEvent("Event1", event, token=self.token)

    # Now emulate a worker.
    while worker.Next():
      pass
    worker.pool.Join()

    # This should now work:
    self.assertEqual(len(received_events), 1)

    # Make sure the source is correctly propagated.
    self.assertEqual(received_events[0][0].source, "aff4:/Source")
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
      self.assertEqual(received_events[i][0].source,
                       "aff4:/Source%d" % i)
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
    args = [(rdfvalue.GrrMessage.Priority.LOW_PRIORITY, "low priority"),
            (rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY, "medium priority"),
            (rdfvalue.GrrMessage.Priority.LOW_PRIORITY, "low priority2"),
            (rdfvalue.GrrMessage.Priority.HIGH_PRIORITY, "high priority"),
            (rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY, "medium priority2")]

    for (priority, msg) in args:
      flow.GRRFlow.StartFlow(
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
    args = [(rdfvalue.GrrMessage.Priority.LOW_PRIORITY, "low priority"),
            (rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY, "medium priority"),
            (rdfvalue.GrrMessage.Priority.LOW_PRIORITY, "low priority2"),
            (rdfvalue.GrrMessage.Priority.HIGH_PRIORITY, "high priority"),
            (rdfvalue.GrrMessage.Priority.MEDIUM_PRIORITY, "medium priority2")]

    server_result = []
    PriorityFlow.storage = server_result

    for (priority, msg) in args:
      flow.GRRFlow.StartFlow(
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


class ResourcedWorker(test_lib.MockWorker):
  USER_CPU = [1, 20, 5, 16]
  SYSTEM_CPU = [4, 20, 2, 8]
  NETWORK_BYTES = [180, 1000, 580, 2000]


class FlowLimitTests(test_lib.FlowTestsBaseclass):

  def RunFlow(self, flow_name, **kwargs):
    result = {}
    client_mock = CPULimitClientMock(result)
    client_mock = test_lib.MockClient(self.client_id, client_mock,
                                      token=self.token)
    worker_mock = ResourcedWorker(check_flow_errors=True,
                                  token=self.token)

    flow.GRRFlow.StartFlow(self.client_id, flow_name,
                           token=self.token, **kwargs)

    while True:
      client_processed = client_mock.Next()
      flows_run = []
      for flow_run in worker_mock.Next():
        flows_run.append(flow_run)

      if client_processed == 0 and not flows_run:
        break

    return result

  def testNetworkLimit(self):
    """Tests that the cpu limit works."""
    result = self.RunFlow("NetworkLimitFlow", network_bytes_limit=10000)
    self.assertEqual(result["networklimit"], [10000, 9820, 8820, 8240])

  def testCPULimit(self):
    """Tests that the cpu limit works."""
    result = self.RunFlow("CPULimitFlow", cpu_limit=300)
    self.assertEqual(result["cpulimit"], [300, 295, 255])


class MockVFSHandler(vfs.VFSHandler):
  """A mock VFS handler with fake files."""
  children = []
  for x in range(10):
    child = rdfvalue.StatEntry(pathspec=rdfvalue.PathSpec(
        path="Foo%s" % x, pathtype=rdfvalue.PathSpec.PathType.OS))
    children.append(child)

  supported_pathtype = rdfvalue.PathSpec.PathType.OS

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

  flow_typeinfo = type_info.TypeDescriptorSet(
      type_info.String(
          name="msg",
          default=""))

  @flow.StateHandler(next_state="Done")
  def Start(self):
    self.CallClient("Store", string=self.state.msg, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    _ = responses
    try:
      self.storage.append(self.state.msg)
    except AttributeError:
      pass


class CPULimitClientMock(object):

  in_rdfvalue = rdfvalue.DataBlob

  def __init__(self, storage):
    # Register us as an action plugin.
    actions.ActionPlugin.classes["Store"] = self
    self.storage = storage

  def HandleMessage(self, message):
    self.storage.setdefault("cpulimit", []).append(message.cpu_limit)
    self.storage.setdefault("networklimit",
                            []).append(message.network_bytes_limit)


class CPULimitFlow(flow.GRRFlow):
  """This flow is used to test the cpu limit."""

  @flow.StateHandler(next_state="State1")
  def Start(self):
    self.CallClient("Store", string="Hey!", next_state="State1")

  @flow.StateHandler(next_state="State2")
  def State1(self):
    self.CallClient("Store", string="Hey!", next_state="State2")

  @flow.StateHandler(next_state="Done")
  def State2(self):
    self.CallClient("Store", string="Hey!", next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    pass


class NetworkLimitFlow(flow.GRRFlow):
  """This flow is used to test the network bytes limit."""

  @flow.StateHandler(next_state="State1")
  def Start(self):
    self.CallClient("Store", next_state="State1")

  @flow.StateHandler(next_state="State2")
  def State1(self):
    # The mock worker doesn't track usage so we add it here.
    self.CallClient("Store", next_state="State2")

  @flow.StateHandler(next_state="State3")
  def State2(self):
    self.CallClient("Store", next_state="State3")

  @flow.StateHandler(next_state="Done")
  def State3(self):
    self.CallClient("Store", next_state="Done")

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
        responses.status.status == rdfvalue.GrrStatus.ReturnedStatus.OK):
      raise RuntimeError("Error not propagated to parent")

    BrokenParentFlow.success = True


class CallStateFlow(flow.GRRFlow):
  """A flow that calls one of its own states."""

  # This is a global flag which will be set when the flow runs.
  success = False

  @flow.StateHandler(next_state="ReceiveHello")
  def Start(self):
    # Call the receive state.
    self.CallState([rdfvalue.RDFString("Hello")],
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
    self.CallState([rdfvalue.RDFString("Hello")],
                   next_state="ReceiveHello")

  @flow.StateHandler(next_state="DelayedHello")
  def ReceiveHello(self, responses):
    if responses.First() != "Hello":
      raise RuntimeError("Did not receive hello.")
    DelayedCallStateFlow.state = 1

    # Call the child flow.
    self.CallState([rdfvalue.RDFString("Hello")],
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
          rdfclass=rdfvalue.PathSpec))


class FlowTestLoader(test_lib.GRRTestLoader):
  base_class = test_lib.FlowTestsBaseclass


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv, testLoader=FlowTestLoader())

if __name__ == "__main__":
  flags.StartMain(main)
