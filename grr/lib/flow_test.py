#!/usr/bin/env python
"""Tests for the flow."""


import time


from grr.client import actions
from grr.client import vfs
from grr.lib import access_control
from grr.lib import action_mocks
from grr.lib import aff4
from grr.lib import data_store
from grr.lib import flags
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import output_plugin
from grr.lib import queue_manager
from grr.lib import rdfvalue
from grr.lib import test_lib
from grr.lib import type_info
from grr.lib import utils
# For GetClientStats. pylint: disable=unused-import
from grr.lib.flows.general import administrative
# pylint: enable=unused-import
from grr.lib.flows.general import transfer
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import flows as rdf_flows
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import protodict as rdf_protodict
from grr.lib.rdfvalues import structs as rdf_structs
from grr.proto import tests_pb2

# pylint: mode=test


class FlowResponseSerialization(flow.GRRFlow):
  """Demonstrate saving responses in the flow."""

  @flow.StateHandler(next_state="Response1")
  def Start(self, unused_message=None):
    self.CallClient("ReturnBlob",
                    rdf_client.EchoRequest(data="test"),
                    next_state="Response1")

  @flow.StateHandler(next_state="Response2")
  def Response1(self, messages):
    """Record the message id for testing."""
    self.state.Register("messages", messages)
    self.CallClient("ReturnBlob",
                    rdf_client.EchoRequest(data="test"),
                    next_state="Response2")

  @flow.StateHandler()
  def Response2(self, messages):
    # We need to receive one response and it must be the same as that stored in
    # the previous state.
    if (len(list(messages)) != 1 or
        messages.status.status != rdf_flows.GrrStatus.ReturnedStatus.OK or
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
    self.CallFlow(self.child_flow, next_state="End")

  @flow.StateHandler()
  def End(self, unused_message):
    pass


class CallClientParentFlow(NoRequestParentFlow):
  child_flow = "CallClientChildFlow"


class BasicFlowTest(test_lib.FlowTestsBaseclass):
  pass


class FlowCreationTest(BasicFlowTest):
  """Test flow creation."""

  def testInvalidClientId(self):
    """Should raise if the client_id is invalid."""
    self.assertRaises(ValueError,
                      flow.GRRFlow.StartFlow,
                      client_id="hello",
                      flow_name="FlowOrderTest",
                      token=self.token)

  def testUnknownArg(self):
    """Check that flows reject unknown args."""
    self.assertRaises(type_info.UnknownArg,
                      flow.GRRFlow.StartFlow,
                      client_id=self.client_id,
                      flow_name="FlowOrderTest",
                      token=self.token,
                      foobar=1)

  def testTypeAttributeIsNotAppendedWhenFlowIsClosed(self):
    session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        flow_name="FlowOrderTest",
                                        token=self.token)

    flow_obj = aff4.FACTORY.Open(session_id,
                                 aff4_type=test_lib.FlowOrderTest,
                                 age=aff4.ALL_TIMES,
                                 mode="rw",
                                 token=self.token)
    flow_obj.Close()

    flow_obj = aff4.FACTORY.Open(session_id,
                                 aff4_type=test_lib.FlowOrderTest,
                                 age=aff4.ALL_TIMES,
                                 token=self.token)

    types = list(flow_obj.GetValuesForAttribute(flow_obj.Schema.TYPE))
    self.assertEqual(len(types), 1)

  def testFlowSerialization(self):
    """Check that we can unpickle flows."""
    session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        flow_name="FlowOrderTest",
                                        token=self.token)

    flow_obj = aff4.FACTORY.Open(session_id,
                                 aff4_type=test_lib.FlowOrderTest,
                                 age=aff4.ALL_TIMES,
                                 token=self.token)

    self.assertEqual(flow_obj.__class__, test_lib.FlowOrderTest)

  def testFlowSerialization2(self):
    """Check that we can unpickle flows."""

    class TestClientMock(object):

      in_rdfvalue = rdf_client.EchoRequest
      out_rdfvalues = [rdf_protodict.DataBlob]

      def __init__(self):
        # Register us as an action plugin.
        actions.ActionPlugin.classes["ReturnBlob"] = self

      def ReturnBlob(self, unused_args):
        return [rdf_protodict.DataBlob(integer=100)]

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("FlowResponseSerialization",
                                     TestClientMock(),
                                     token=self.token,
                                     client_id=self.client_id):
      pass

  def testTerminate(self):
    session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        flow_name="FlowOrderTest",
                                        token=self.token)

    flow.GRRFlow.TerminateFlow(session_id, token=self.token)
    flow_obj = aff4.FACTORY.Open(session_id,
                                 aff4_type=test_lib.FlowOrderTest,
                                 age=aff4.ALL_TIMES,
                                 token=self.token)
    runner = flow_obj.GetRunner()
    self.assertEqual(runner.IsRunning(), False)
    self.assertEqual(runner.context.state, rdf_flows.Flow.State.ERROR)

    reason = "no reason"
    session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        flow_name="FlowOrderTest",
                                        token=self.token)
    flow.GRRFlow.TerminateFlow(session_id, reason=reason, token=self.token)

    flow_obj = aff4.FACTORY.Open(session_id,
                                 aff4_type=test_lib.FlowOrderTest,
                                 age=aff4.ALL_TIMES,
                                 token=self.token)
    runner = flow_obj.GetRunner()
    self.assertEqual(runner.IsRunning(), False)
    self.assertEqual(runner.context.state, rdf_flows.Flow.State.ERROR)
    self.assertTrue(reason in runner.context.status)

  def testChildTermination(self):
    session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        flow_name="CallClientParentFlow",
                                        token=self.token)

    # The child URN should be contained within the parent session_id URN.
    flow_obj = aff4.FACTORY.Open(session_id, token=self.token)

    children = list(flow_obj.ListChildren())
    self.assertEqual(len(children), 1)

    reason = "just so"

    flow.GRRFlow.TerminateFlow(session_id, reason=reason, token=self.token)

    flow_obj = aff4.FACTORY.Open(session_id,
                                 aff4_type=CallClientParentFlow,
                                 token=self.token)

    runner = flow_obj.GetRunner()
    self.assertEqual(runner.IsRunning(), False)
    self.assertEqual(runner.context.state, rdf_flows.Flow.State.ERROR)

    self.assertTrue("user test" in runner.context.status)
    self.assertTrue(reason in runner.context.status)

    child = aff4.FACTORY.Open(children[0],
                              aff4_type=CallClientChildFlow,
                              token=self.token)
    runner = child.GetRunner()
    self.assertEqual(runner.IsRunning(), False)
    self.assertEqual(runner.context.state, rdf_flows.Flow.State.ERROR)

    self.assertTrue("user test" in runner.context.status)
    self.assertTrue("Parent flow terminated." in runner.context.status)

  def testNotification(self):
    session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        flow_name="FlowOrderTest",
                                        token=self.token)
    with aff4.FACTORY.Open(session_id,
                           aff4_type=test_lib.FlowOrderTest,
                           age=aff4.ALL_TIMES,
                           mode="rw",
                           token=self.token) as flow_obj:
      msg = "Flow terminated due to error"
      flow_obj.GetRunner().Notify("FlowStatus", session_id, msg)

    user_fd = aff4.FACTORY.Open(
        rdfvalue.RDFURN("aff4:/users").Add(self.token.username),
        mode="r",
        token=self.token)
    notifications = user_fd.ShowNotifications(reset=False)
    self.assertEqual(len(notifications), 1)
    for notification in notifications:
      self.assertTrue(notification.message.endswith(": " + msg))
      self.assertEqual(notification.subject, rdfvalue.RDFURN(session_id))

  def testFormatstringNotification(self):
    session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        flow_name="FlowOrderTest",
                                        token=self.token)
    with aff4.FACTORY.Open(session_id,
                           aff4_type=test_lib.FlowOrderTest,
                           age=aff4.ALL_TIMES,
                           mode="rw",
                           token=self.token) as flow_obj:
      runner = flow_obj.GetRunner()
      # msg contains %s.
      msg = "Flow reading %system% terminated due to error"
      runner.Notify("FlowStatus", session_id, msg)
      runner.Status(msg)

  def testSendRepliesAttribute(self):
    # Run the flow in the simulated way. Child's send_replies is set to False.
    # Parent flow will raise if number of responses is > 0.
    for _ in test_lib.TestFlowHelper("ParentFlowWithoutResponses",
                                     ClientMock(),
                                     client_id=self.client_id,
                                     check_flow_errors=False,
                                     token=self.token,):
      pass

    self.assertEqual(ParentFlowWithoutResponses.success, True)

  notifications = {}

  def CollectNotifications(self, queue, notifications, **kwargs):
    now = time.time()
    for notification in notifications:
      self.notifications.setdefault(notification.session_id, []).append(now)
    self.old_notify(queue, notifications, **kwargs)

  def testNoRequestChildFlowRace(self):

    manager = queue_manager.QueueManager(token=self.token)
    self.old_notify = manager._MultiNotifyQueue
    with utils.Stubber(queue_manager.QueueManager, "_MultiNotifyQueue",
                       self.CollectNotifications):
      session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                          flow_name="NoRequestParentFlow",
                                          token=self.token)

    self.assertIn(session_id, self.notifications)

    f = aff4.FACTORY.Open(session_id, token=self.token)

    # Check that the first notification came in after the flow was created.
    self.assertLess(
        int(f.Get(f.Schema.TYPE).age),
        1e6 * min(self.notifications[session_id]),
        "There was a notification for a flow before "
        "the flow was created.")

  def testCallClientChildFlowRace(self):
    session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        flow_name="CallClientParentFlow",
                                        token=self.token)

    client_requests = data_store.DB.ResolvePrefix(self.client_id.Queue(),
                                                  "task:",
                                                  token=self.token)

    self.assertEqual(len(client_requests), 1)

    f = aff4.FACTORY.Open(session_id, token=self.token)

    for (_, _, timestamp) in client_requests:
      # Check that the client request was written after the flow was created.
      self.assertLess(
          int(f.Get(f.Schema.TYPE).age), timestamp,
          "The client request was issued before "
          "the flow was created.")

  def testFlowLogging(self):
    """Check that flows log correctly."""
    flow_urn = None
    for session_id in test_lib.TestFlowHelper("DummyLogFlow",
                                              action_mocks.ActionMock(),
                                              token=self.token,
                                              client_id=self.client_id):
      flow_urn = session_id

    with aff4.FACTORY.Open(
        flow_urn.Add("Logs"),
        age=aff4.ALL_TIMES,
        token=self.token) as log_collection:
      count = 0
      # Can't use len with PackedVersionCollection
      for log in log_collection:
        self.assertEqual(log.client_id, self.client_id)
        self.assertTrue(log.log_message in [
            "First", "Second", "Third", "Fourth", "Uno", "Dos", "Tres", "Cuatro"
        ])
        self.assertTrue(log.flow_name in ["DummyLogFlow", "DummyLogFlowChild"])
        self.assertTrue(str(flow_urn) in str(log.urn))
        count += 1
      self.assertEqual(count, 8)


class FlowTest(BasicFlowTest):
  """Tests the Flow."""

  def testBrokenFlow(self):
    """Check that flows which call to incorrect states raise."""
    client_mock = action_mocks.ActionMock("ReadBuffer")
    with self.assertRaises(RuntimeError):
      for _ in test_lib.TestFlowHelper("BrokenFlow",
                                       client_mock,
                                       client_id=self.client_id,
                                       check_flow_errors=True,
                                       token=self.token):
        pass

  def SendMessages(self,
                   response_ids,
                   session_id,
                   authenticated=True,
                   args_rdf_name="DataBlob"):
    """Send messages to the flow."""
    for response_id in response_ids:
      message = rdf_flows.GrrMessage(request_id=1,
                                     response_id=response_id,
                                     session_id=session_id,
                                     args_rdf_name=args_rdf_name)

      if authenticated:
        auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED
        message.auth_state = auth_state

      self.SendMessage(message)

  def SendMessage(self, message):
    # Now messages are set in the data store
    with queue_manager.QueueManager(token=self.token) as manager:
      manager.QueueResponse(message.session_id, message)

  def SendOKStatus(self, response_id, session_id):
    """Send a message to the flow."""
    message = rdf_flows.GrrMessage(
        request_id=1,
        response_id=response_id,
        session_id=session_id,
        type=rdf_flows.GrrMessage.Type.STATUS,
        auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)

    status = rdf_flows.GrrStatus(status=rdf_flows.GrrStatus.ReturnedStatus.OK)
    message.payload = status

    self.SendMessage(message)

    # Now also set the state on the RequestState
    request_state, _ = data_store.DB.Resolve(
        message.session_id.Add("state"),
        queue_manager.QueueManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        token=self.token)

    request_state = rdf_flows.RequestState(request_state)
    request_state.status = status

    data_store.DB.Set(
        message.session_id.Add("state"),
        queue_manager.QueueManager.FLOW_REQUEST_TEMPLATE % message.request_id,
        request_state,
        token=self.token)

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
    notification = rdf_flows.Notification(
        timestamp=rdfvalue.RDFDatetime().Now())
    runner.ProcessCompletedRequests(notification, [message])

    # Check that the messages were processed in order
    self.assertEqual(flow_obj.messages, [1, 2, 3, 4, 5])

  def testCallClient(self):
    """Flows can send client messages using CallClient()."""
    flow_obj = self.FlowSetup("FlowOrderTest")

    # Check that a message went out to the client
    manager = queue_manager.QueueManager(token=self.token)
    tasks = manager.Query(self.client_id, limit=100)

    self.assertEqual(len(tasks), 1)

    message = tasks[0]

    self.assertEqual(message.session_id, flow_obj.session_id)
    self.assertEqual(message.request_id, 1)
    self.assertEqual(message.name, "Test")

  def testCallClientWellKnown(self):
    """Well known flows can also call the client."""
    cls = flow.GRRFlow.classes["GetClientStatsAuto"]
    flow_obj = cls(cls.well_known_session_id, mode="rw", token=self.token)

    flow_obj.CallClient(self.client_id, "GetClientStats")

    # Check that a message went out to the client
    manager = queue_manager.QueueManager(token=self.token)
    tasks = manager.Query(self.client_id, limit=100)

    self.assertEqual(len(tasks), 1)

    message = tasks[0]

    # If we don't specify where to send the replies, they go to the devnull flow
    devnull = flow.GRRFlow.classes["IgnoreResponses"]
    self.assertEqual(message.session_id, devnull.well_known_session_id)
    self.assertEqual(message.request_id, 0)
    self.assertEqual(message.name, "GetClientStats")

    messages = []

    def StoreMessage(_, msg):
      messages.append(msg)

    with utils.Stubber(devnull, "ProcessMessage", StoreMessage):
      client_mock = action_mocks.ActionMock("GetClientStats")
      for _ in test_lib.TestFlowHelper("ClientActionRunner",
                                       client_mock,
                                       client_id=self.client_id,
                                       action="GetClientStats",
                                       token=self.token):
        pass

    # Make sure the messages arrived.
    self.assertEqual(len(messages), 1)

  def testAuthentication1(self):
    """Test that flows refuse to processes unauthenticated messages."""
    flow_obj = self.FlowSetup("FlowOrderTest")

    # Simultate processing messages arriving in random order
    message_ids = [2, 1, 4, 3, 5]
    self.SendMessages(message_ids, flow_obj.session_id, authenticated=False)

    # Send the status message
    message = self.SendOKStatus(6, flow_obj.session_id)

    runner = flow_runner.FlowRunner(flow_obj)
    notification = rdf_flows.Notification(
        timestamp=rdfvalue.RDFDatetime().Now())
    runner.ProcessCompletedRequests(notification, [message])

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
    self.SendMessages(message_ids, flow_obj.session_id, authenticated=True)

    # Now suppose some of the messages are spoofed
    message_ids = [3, 4, 5]
    self.SendMessages(message_ids, flow_obj.session_id, authenticated=False)

    # And now our real messages arrive
    message_ids = [5, 6]
    self.SendMessages(message_ids, flow_obj.session_id, authenticated=True)

    # Send the status message
    message = self.SendOKStatus(7, flow_obj.session_id)

    runner = flow_runner.FlowRunner(flow_obj)
    notification = rdf_flows.Notification(
        timestamp=rdfvalue.RDFDatetime().Now())
    runner.ProcessCompletedRequests(notification, [message])

    # Some messages should actually be processed
    self.assertEqual(flow_obj.messages, [1, 2, 5, 6])

  def testWellKnownFlows(self):
    """Test the well known flows."""
    test_flow = self.FlowSetup("WellKnownSessionTest")

    # Make sure the session ID is well known
    self.assertEqual(test_flow.session_id,
                     test_lib.WellKnownSessionTest.well_known_session_id)

    # Messages to Well Known flows can be unauthenticated
    messages = [
        rdf_flows.GrrMessage(payload=rdfvalue.RDFInteger(i)) for i in range(10)
    ]

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
    self.assertRaises(type_info.TypeValueError,
                      flow.GRRFlow.StartFlow,
                      client_id=self.client_id,
                      flow_name="BadArgsFlow1",
                      arg1=False,
                      token=self.token)

    # Should not raise now if we provide the correct type.
    flow.GRRFlow.StartFlow(client_id=self.client_id,
                           flow_name="BadArgsFlow1",
                           arg1=rdf_paths.PathSpec(),
                           token=self.token)


class FlowTerminationTest(BasicFlowTest):
  """Flow termination-related tests."""

  def testFlowMarkedForTerminationTerminatesInStateHandler(self):
    flow_obj = self.FlowSetup("FlowOrderTest")
    flow.GRRFlow.MarkForTermination(flow_obj.urn,
                                    reason="because i can",
                                    token=self.token)

    def ProcessFlow():
      for _ in test_lib.TestFlowHelper(flow_obj.urn,
                                       client_id=self.client_id,
                                       token=self.token):
        pass

    self.assertRaisesRegexp(RuntimeError, "because i can", ProcessFlow)


class DummyFlowOutputPlugin(output_plugin.OutputPluginWithOutputStreams):
  """Dummy plugin that opens a dummy stream."""
  num_calls = 0
  num_responses = 0

  def ProcessResponses(self, responses):
    stream = self._CreateOutputStream("dummy")
    stream.Write("dummy")
    stream.Flush()

    DummyFlowOutputPlugin.num_calls += 1
    DummyFlowOutputPlugin.num_responses += len(list(responses))


class FailingDummyFlowOutputPlugin(output_plugin.OutputPlugin):

  def ProcessResponses(self, unused_responses):
    raise RuntimeError("Oh no!")


class LongRunningDummyFlowOutputPlugin(output_plugin.OutputPlugin):
  num_calls = 0

  def ProcessResponses(self, unused_responses):
    LongRunningDummyFlowOutputPlugin.num_calls += 1
    time.time = lambda: 100


class FlowOutputPluginsTest(BasicFlowTest):

  def setUp(self):
    super(FlowOutputPluginsTest, self).setUp()
    DummyFlowOutputPlugin.num_calls = 0
    DummyFlowOutputPlugin.num_responses = 0

  def RunFlow(self,
              flow_name=None,
              plugins=None,
              flow_args=None,
              client_mock=None):
    runner_args = flow_runner.FlowRunnerArgs(flow_name=flow_name or "GetFile",
                                             output_plugins=plugins)

    if flow_args is None:
      flow_args = transfer.GetFileArgs(pathspec=rdf_paths.PathSpec(
          path="/tmp/evil.txt",
          pathtype=rdf_paths.PathSpec.PathType.OS))

    if client_mock is None:
      client_mock = test_lib.SampleHuntMock()

    flow_urn = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                      args=flow_args,
                                      runner_args=runner_args,
                                      token=self.token)

    for _ in test_lib.TestFlowHelper(flow_urn,
                                     client_mock=client_mock,
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    return flow_urn

  def testFlowWithoutOutputPluginsCompletes(self):
    self.RunFlow()

  def testFlowWithOutputPluginButWithoutResultsCompletes(self):
    self.RunFlow(flow_name="NoRequestParentFlow",
                 plugins=output_plugin.OutputPluginDescriptor(
                     plugin_name="DummyFlowOutputPlugin"))
    self.assertEqual(DummyFlowOutputPlugin.num_calls, 0)

  def testFlowWithOutputPluginProcessesResultsSuccessfully(self):
    self.RunFlow(plugins=output_plugin.OutputPluginDescriptor(
        plugin_name="DummyFlowOutputPlugin"))
    self.assertEqual(DummyFlowOutputPlugin.num_calls, 1)
    self.assertEqual(DummyFlowOutputPlugin.num_responses, 1)

  def testFlowLogsSuccessfulOutputPluginProcessing(self):
    flow_urn = self.RunFlow(plugins=output_plugin.OutputPluginDescriptor(
        plugin_name="DummyFlowOutputPlugin"))
    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    log_messages = [item.log_message for item in flow_obj.GetLog()]
    self.assertTrue(
        "Plugin DummyFlowOutputPlugin sucessfully processed 1 flow replies." in
        log_messages)

  def testFlowLogsFailedOutputPluginProcessing(self):
    flow_urn = self.RunFlow(plugins=output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyFlowOutputPlugin"))
    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    log_messages = [item.log_message for item in flow_obj.GetLog()]
    self.assertTrue(
        "Plugin FailingDummyFlowOutputPlugin failed to process 1 replies "
        "due to: Oh no!" in log_messages)

  def testFlowDoesNotFailWhenOutputPluginFails(self):
    flow_urn = self.RunFlow(plugins=output_plugin.OutputPluginDescriptor(
        plugin_name="FailingDummyFlowOutputPlugin"))
    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    self.assertEqual(flow_obj.state.context.state, "TERMINATED")

  def testFailingPluginDoesNotImpactOtherPlugins(self):
    self.RunFlow(plugins=[
        output_plugin.OutputPluginDescriptor(
            plugin_name="FailingDummyFlowOutputPlugin"),
        output_plugin.OutputPluginDescriptor(
            plugin_name="DummyFlowOutputPlugin")
    ])

    self.assertEqual(DummyFlowOutputPlugin.num_calls, 1)
    self.assertEqual(DummyFlowOutputPlugin.num_responses, 1)


class NoClientListener(flow.EventListener):  # pylint: disable=unused-variable
  well_known_session_id = rdfvalue.SessionID(flow_name="test2")
  EVENTS = ["TestEvent"]

  received_events = []

  @flow.EventHandler(auth_required=True)
  def ProcessMessage(self, message=None, event=None):
    # Store the results for later inspection.
    self.__class__.received_events.append((message, event))


class ClientListener(flow.EventListener):
  well_known_session_id = rdfvalue.SessionID(flow_name="test3")
  EVENTS = ["TestEvent"]

  received_events = []

  @flow.EventHandler(auth_required=True, allow_client_access=True)
  def ProcessMessage(self, message=None, event=None):
    # Store the results for later inspection.
    self.__class__.received_events.append((message, event))


class FlowDoneListener(flow.EventListener):
  well_known_session_id = rdfvalue.SessionID(queue=rdfvalue.RDFURN("EV"),
                                             flow_name="FlowDone")
  EVENTS = ["Not used"]
  received_events = []

  @flow.EventHandler(auth_required=True)
  def ProcessMessage(self, message=None, event=None):
    _ = event
    # Store the results for later inspection.
    FlowDoneListener.received_events.append(message)


class GeneralFlowsTest(BasicFlowTest):
  """Tests some flows."""

  def testCallState(self):
    """Test the ability to chain flows."""
    CallStateFlow.success = False

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("CallStateFlow",
                                     ClientMock(),
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
    with test_lib.FakeTime(10000):
      client_mock = ClientMock()
      client_mock = test_lib.MockClient(self.client_id,
                                        client_mock,
                                        token=self.token)
      worker_mock = test_lib.MockWorker(check_flow_errors=True,
                                        token=self.token)

      flow.GRRFlow.StartFlow(client_id=self.client_id,
                             flow_name="DelayedCallStateFlow",
                             token=self.token)

      self.Work(client_mock, worker_mock)

      # We should have done the first CallState so far.
      self.assertEqual(DelayedCallStateFlow.flow_ran, 1)

    with test_lib.FakeTime(10050):
      # 50 seconds more is not enough.
      self.Work(client_mock, worker_mock)
      self.assertEqual(DelayedCallStateFlow.flow_ran, 1)

    with test_lib.FakeTime(10100):
      # But 100 is.
      self.Work(client_mock, worker_mock)
      self.assertEqual(DelayedCallStateFlow.flow_ran, 2)

  def testChainedFlow(self):
    """Test the ability to chain flows."""
    ParentFlow.success = False

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("ParentFlow",
                                     ClientMock(),
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    self.assertEqual(ParentFlow.success, True)

  def testCreatorPropagation(self):

    # Instantiate the flow using one username.
    session_id = flow.GRRFlow.StartFlow(client_id=self.client_id,
                                        flow_name="ParentFlow",
                                        sync=False,
                                        token=access_control.ACLToken(
                                            username="original_user",
                                            reason="testing"))

    # Run the flow using another user ("test").
    for _ in test_lib.TestFlowHelper(session_id,
                                     ClientMock(),
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    self.assertEqual(ParentFlow.success, True)
    subflows = list(aff4.FACTORY.Open(session_id,
                                      token=self.token).ListChildren())
    self.assertEqual(len(subflows), 1)
    child_flow = aff4.FACTORY.Open(subflows[0], token=self.token)
    self.assertEqual(child_flow.GetRunner().context.creator, "original_user")

  def testBrokenChainedFlow(self):
    """Test that exceptions are properly handled in chain flows."""
    BrokenParentFlow.success = False

    # Run the flow in the simulated way
    for _ in test_lib.TestFlowHelper("BrokenParentFlow",
                                     ClientMock(),
                                     client_id=self.client_id,
                                     check_flow_errors=False,
                                     token=self.token):
      pass

    self.assertEqual(BrokenParentFlow.success, True)

  def testIteratedDirectoryListing(self):
    """Test that the client iterator works."""
    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS, MockVFSHandler):
      path = "/"
      # Run the flow in the simulated way
      client_mock = action_mocks.ActionMock("IteratedListDirectory")
      for _ in test_lib.TestFlowHelper(
          "IteratedListDirectory",
          client_mock,
          client_id=self.client_id,
          pathspec=rdf_paths.PathSpec(path="/",
                                      pathtype=rdf_paths.PathSpec.PathType.OS),
          token=self.token):
        pass

      fd = aff4.FACTORY.Open(
          self.client_id.Add("fs/os").Add(path),
          token=self.token)
      directory = [ch for ch in fd.OpenChildren()]
      pb = rdf_paths.PathSpec(path=path,
                              pathtype=rdf_paths.PathSpec.PathType.OS)
      directory2 = list(vfs.VFSOpen(pb).ListFiles())
      directory.sort()
      result = [x.Get(x.Schema.STAT) for x in directory]

      # Make sure that the resulting directory is what it should be
      for x, y in zip(result, directory2):
        x.aff4path = None

        self.assertEqual(x.st_mode, y.st_mode)
        self.assertRDFValuesEqual(x, y)

  def testClientEventNotification(self):
    """Make sure that client events handled securely."""
    ClientListener.received_events = []
    NoClientListener.received_events = []

    event = rdf_flows.GrrMessage(
        source="C.1395c448a443c7d9",
        auth_state=rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED)

    event.payload = rdf_paths.PathSpec(path="foobar")

    flow.Events.PublishEvent("TestEvent", event, token=self.token)
    test_lib.MockWorker(token=self.token).Simulate()

    # The same event should be sent to both listeners, but only the listener
    # which accepts client messages should register it.
    self.assertRDFValuesEqual(ClientListener.received_events[0][0].payload,
                              event.payload)
    self.assertEqual(NoClientListener.received_events, [])

  def testFlowNotification(self):
    FlowDoneListener.received_events = []

    with test_lib.VFSOverrider(rdf_paths.PathSpec.PathType.OS, MockVFSHandler):
      path = rdf_paths.PathSpec(path="/",
                                pathtype=rdf_paths.PathSpec.PathType.OS)

      # Run the flow in the simulated way
      client_mock = action_mocks.ActionMock("IteratedListDirectory")
      for _ in test_lib.TestFlowHelper("IteratedListDirectory",
                                       client_mock,
                                       client_id=self.client_id,
                                       notification_urn=rdfvalue.SessionID(
                                           queue=rdfvalue.RDFURN("EV"),
                                           flow_name="FlowDone"),
                                       pathspec=path,
                                       token=self.token):
        pass

      # The event goes to an external queue so we need another worker.
      worker = test_lib.MockWorker(queues=[rdfvalue.RDFURN("EV")],
                                   token=self.token)
      worker.Simulate()

      self.assertEqual(len(FlowDoneListener.received_events), 1)

      flow_event = FlowDoneListener.received_events[0].payload
      self.assertEqual(flow_event.flow_name, "IteratedListDirectory")
      self.assertEqual(flow_event.client_id, "aff4:/C.1000000000000000")
      self.assertEqual(flow_event.status, rdf_flows.FlowNotification.Status.OK)

  def testEventNotification(self):
    """Test that events are sent to listeners."""
    NoClientListener.received_events = []
    worker = test_lib.MockWorker(token=self.token)

    event = rdf_flows.GrrMessage(
        session_id=rdfvalue.SessionID(flow_name="SomeFlow"),
        name="test message",
        payload=rdf_paths.PathSpec(path="foobar", pathtype="TSK"),
        source="aff4:/C.0000000000000001",
        auth_state="AUTHENTICATED")

    # Not allowed to publish a message from a client..
    flow.Events.PublishEvent("TestEvent", event, token=self.token)
    worker.Simulate()

    self.assertEqual(NoClientListener.received_events, [])

    event.source = "Source"

    # First make the message unauthenticated.
    event.auth_state = rdf_flows.GrrMessage.AuthorizationState.UNAUTHENTICATED

    # Publish the event.
    flow.Events.PublishEvent("TestEvent", event, token=self.token)
    worker.Simulate()

    # This should not work - the unauthenticated message is dropped.
    self.assertEqual(NoClientListener.received_events, [])

    # Now make the message authenticated.
    event.auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED

    # Publish the event.
    flow.Events.PublishEvent("TestEvent", event, token=self.token)
    worker.Simulate()

    # This should now work:
    self.assertEqual(len(NoClientListener.received_events), 1)

    # Make sure the source is correctly propagated.
    self.assertEqual(NoClientListener.received_events[0][0].source,
                     "aff4:/Source")
    self.assertEqual(NoClientListener.received_events[0][1].path, "foobar")

    NoClientListener.received_events = []
    # Now schedule ten events at the same time.
    for i in xrange(10):
      event.source = "Source%d" % i
      flow.Events.PublishEvent("TestEvent", event, token=self.token)

    worker.Simulate()

    self.assertEqual(len(NoClientListener.received_events), 10)

    # Events do not have to be delivered in order so we sort them here for
    # comparison.
    NoClientListener.received_events.sort(key=lambda x: x[0].source)
    for i in range(10):
      self.assertEqual(NoClientListener.received_events[i][0].source,
                       "aff4:/Source%d" % i)
      self.assertEqual(NoClientListener.received_events[i][1].path, "foobar")

  def testClientPrioritization(self):
    """Test that flow priorities work on the client side."""

    result = []
    client_mock = PriorityClientMock(result)
    client_mock = test_lib.MockClient(self.client_id,
                                      client_mock,
                                      token=self.token)
    worker_mock = test_lib.MockWorker(check_flow_errors=True, token=self.token)

    # Start some flows with different priorities.
    args = [(rdf_flows.GrrMessage.Priority.LOW_PRIORITY, "low priority"),
            (rdf_flows.GrrMessage.Priority.MEDIUM_PRIORITY, "medium priority"),
            (rdf_flows.GrrMessage.Priority.LOW_PRIORITY, "low priority2"),
            (rdf_flows.GrrMessage.Priority.HIGH_PRIORITY, "high priority"),
            (rdf_flows.GrrMessage.Priority.MEDIUM_PRIORITY, "medium priority2")]

    for (priority, msg) in args:
      flow.GRRFlow.StartFlow(client_id=self.client_id,
                             flow_name="PriorityFlow",
                             msg=msg,
                             priority=priority,
                             token=self.token)

    while True:
      client_processed = client_mock.Next()
      flows_run = []
      for flow_run in worker_mock.Next():
        flows_run.append(flow_run)

      if client_processed == 0 and not flows_run:
        break

    # The flows should be run in order of priority.
    self.assertEqual(result[0:1], [u"high priority"])
    self.assertEqual(
        sorted(result[1:3]), [u"medium priority", u"medium priority2"])
    self.assertEqual(sorted(result[3:5]), [u"low priority", u"low priority2"])

  def testWorkerPrioritization(self):
    """Test that flow priorities work on the worker side."""

    result = []
    client_mock = PriorityClientMock(result)
    client_mock = test_lib.MockClient(self.client_id,
                                      client_mock,
                                      token=self.token)
    worker_mock = test_lib.MockWorker(check_flow_errors=True, token=self.token)

    # Start some flows with different priorities.
    args = [(rdf_flows.GrrMessage.Priority.LOW_PRIORITY, "low priority"),
            (rdf_flows.GrrMessage.Priority.MEDIUM_PRIORITY, "medium priority"),
            (rdf_flows.GrrMessage.Priority.LOW_PRIORITY, "low priority2"),
            (rdf_flows.GrrMessage.Priority.HIGH_PRIORITY, "high priority"),
            (rdf_flows.GrrMessage.Priority.MEDIUM_PRIORITY, "medium priority2")]

    server_result = []
    PriorityFlow.storage = server_result

    for (priority, msg) in args:
      flow.GRRFlow.StartFlow(client_id=self.client_id,
                             flow_name="PriorityFlow",
                             msg=msg,
                             priority=priority,
                             token=self.token)

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
    self.assertEqual(server_result[0:1], [u"high priority"])
    self.assertEqual(
        sorted(server_result[1:3]), [u"medium priority", u"medium priority2"])
    self.assertEqual(
        sorted(server_result[3:5]), [u"low priority", u"low priority2"])


class ResourcedWorker(test_lib.MockWorker):
  USER_CPU = [1, 20, 5, 16]
  SYSTEM_CPU = [4, 20, 2, 8]
  NETWORK_BYTES = [180, 1000, 580, 2000]


class FlowLimitTests(BasicFlowTest):

  def RunFlow(self, flow_name, **kwargs):
    result = {}
    client_mock = CPULimitClientMock(result)
    client_mock = test_lib.MockClient(self.client_id,
                                      client_mock,
                                      token=self.token)
    worker_mock = ResourcedWorker(check_flow_errors=True, token=self.token)

    flow.GRRFlow.StartFlow(client_id=self.client_id,
                           flow_name=flow_name,
                           token=self.token,
                           **kwargs)

    while True:
      client_processed = client_mock.Next()
      flows_run = []
      for flow_run in worker_mock.Next():
        flows_run.append(flow_run)

      if client_processed == 0 and not flows_run:
        break

    return result

  def testNetworkLimit(self):
    """Tests that the network limit works."""
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
    child = rdf_client.StatEntry(pathspec=rdf_paths.PathSpec(
        path="Foo%s" % x,
        pathtype=rdf_paths.PathSpec.PathType.OS))
    children.append(child)

  supported_pathtype = rdf_paths.PathSpec.PathType.OS

  def __init__(self,
               base_fd,
               pathspec=None,
               progress_callback=None,
               full_pathspec=None):
    super(MockVFSHandler, self).__init__(base_fd,
                                         pathspec=pathspec,
                                         progress_callback=progress_callback,
                                         full_pathspec=full_pathspec)

    self.pathspec.Append(pathspec)

  def ListFiles(self):
    return self.children

  def IsDirectory(self):
    return self.pathspec.path == "/"


class PriorityClientMock(object):

  in_rdfvalue = rdf_protodict.DataBlob

  def __init__(self, storage):
    # Register us as an action plugin.
    actions.ActionPlugin.classes["Store"] = self
    self.storage = storage

  def Store(self, data):
    self.storage.append(self.in_rdfvalue(data).string)
    return [rdf_protodict.DataBlob(string="Hello World")]


class PriorityFlowArgs(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.PriorityFlowArgs


class PriorityFlow(flow.GRRFlow):
  """This flow is used to test priorities."""
  args_type = PriorityFlowArgs
  storage = []

  @flow.StateHandler(next_state="Done")
  def Start(self):
    self.CallClient("Store", string=self.args.msg, next_state="Done")

  @flow.StateHandler()
  def Done(self, responses):
    _ = responses
    self.storage.append(self.args.msg)


class CPULimitClientMock(object):

  in_rdfvalue = rdf_protodict.DataBlob

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
  out_rdfvalues = [rdfvalue.RDFString]

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
    self.CallFlow("ChildFlow", next_state="ParentReceiveHello")

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
    self.CallFlow("BrokenChildFlow", next_state="ReceiveHello")

  @flow.StateHandler()
  def ReceiveHello(self, responses):
    if (responses or
        responses.status.status == rdf_flows.GrrStatus.ReturnedStatus.OK):
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
                   next_state="ReceiveHello",
                   request_data={"test_req_data": 2})

  @flow.StateHandler()
  def ReceiveHello(self, responses):
    if responses.First() != "Hello":
      raise RuntimeError("Did not receive hello.")

    if responses.request_data["test_req_data"] != 2:
      raise RuntimeError("request_data did not propagate.")

    CallStateFlow.success = True


class DelayedCallStateFlow(flow.GRRFlow):
  """A flow that calls one of its own states with a delay."""

  # This is a global flag which will be set when the flow runs.
  flow_ran = 0

  @flow.StateHandler(next_state="ReceiveHello")
  def Start(self):
    # Call the child flow.
    self.CallState([rdfvalue.RDFString("Hello")], next_state="ReceiveHello")

  @flow.StateHandler(next_state="DelayedHello")
  def ReceiveHello(self, responses):
    if responses.First() != "Hello":
      raise RuntimeError("Did not receive hello.")
    DelayedCallStateFlow.flow_ran = 1

    # Call the child flow.
    self.CallState([rdfvalue.RDFString("Hello")],
                   next_state="DelayedHello",
                   start_time=rdfvalue.RDFDatetime().Now() + 100)

  @flow.StateHandler()
  def DelayedHello(self, responses):
    if responses.First() != "Hello":
      raise RuntimeError("Did not receive hello.")
    DelayedCallStateFlow.flow_ran = 2


class BadArgsFlow1Args(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.BadArgsFlow1Args


class BadArgsFlow1(flow.GRRFlow):
  """A flow that has args that mismatch type info."""

  args_type = BadArgsFlow1Args


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
