#!/usr/bin/env python
"""Tests for aff4 flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import time


from builtins import range  # pylint: disable=redefined-builtin

from grr_response_client.client_actions import standard
from grr_response_core import config
from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import tests_pb2
from grr_response_server import access_control
from grr_response_server import aff4
from grr_response_server import aff4_flows
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import queue_manager
from grr_response_server import server_stubs
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import test_lib
from grr.test_lib import test_output_plugins
from grr.test_lib import worker_test_lib

# pylint: mode=test


class FlowResponseSerialization(flow.GRRFlow):
  """Demonstrate saving responses in the flow."""

  def Start(self):
    self.CallClient(
        server_stubs.ClientActionStub.classes["ReturnBlob"],
        rdf_client_action.EchoRequest(data="test"),
        next_state="Response1")

  def Response1(self, messages):
    """Record the message id for testing."""
    self.state.messages = list(messages)
    self.CallClient(
        server_stubs.ClientActionStub.classes["ReturnBlob"],
        rdf_client_action.EchoRequest(data="test"),
        next_state="Response2")

  def Response2(self, messages):
    # We need to receive one response and it must be the same as that stored in
    # the previous state.
    if (len(list(messages)) != 1 or
        messages.status.status != rdf_flows.GrrStatus.ReturnedStatus.OK or
        list(messages) != list(self.state.messages)):
      raise RuntimeError("Messages not serialized")


class NoRequestChildFlow(flow.GRRFlow):
  """This flow just returns and does not generate any requests."""

  def Start(self):
    return


class CallClientChildFlow(flow.GRRFlow):
  """This flow just returns and does not generate any requests."""

  def Start(self):
    self.CallClient(server_stubs.GetClientStats, next_state="End")


class NoRequestParentFlow(flow.GRRFlow):

  child_flow = "NoRequestChildFlow"

  def Start(self):
    self.CallFlow(self.child_flow, next_state="End")

  def End(self, responses):
    del responses


class CallClientParentFlow(NoRequestParentFlow):
  child_flow = "CallClientChildFlow"


class BasicFlowTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(BasicFlowTest, self).setUp()
    self.client_id = self.SetupClient(0)


class FlowWithMultipleResultTypes(flow.GRRFlow):
  """This flow will be called by our parent."""

  def Start(self):
    self.CallState(next_state="End")

  def End(self, responses):
    self.SendReply(rdfvalue.RDFInteger(42))
    self.SendReply(rdfvalue.RDFString("foo bar"))
    self.SendReply(rdfvalue.RDFString("foo1 bar1"))
    self.SendReply(rdfvalue.RDFURN("aff4:/foo/bar"))
    self.SendReply(rdfvalue.RDFURN("aff4:/foo1/bar1"))
    self.SendReply(rdfvalue.RDFURN("aff4:/foo2/bar2"))


class MultiEndedFlow(flow.GRRFlow):
  """This flow will end - call the End state - multiple times."""

  def Start(self):
    self.state.counter = 0
    self.CallState(next_state="End")

  def End(self, responses):
    super(MultiEndedFlow, self).End(responses)

    self.state.counter += 1
    if self.state.counter < 3:
      self.CallState(next_state="End")


class FlowCreationTest(BasicFlowTest):
  """Test flow creation."""

  def testInvalidClientId(self):
    """Should raise if the client_id is invalid."""
    with self.assertRaises(ValueError):
      flow.StartAFF4Flow(
          client_id="hello",
          flow_name=aff4_flows.FlowOrderTest.__name__,
          token=self.token)

  def testUnknownArg(self):
    """Check that flows reject unknown args."""
    self.assertRaises(
        type_info.UnknownArg,
        flow.StartAFF4Flow,
        client_id=self.client_id,
        flow_name=aff4_flows.FlowOrderTest.__name__,
        token=self.token,
        foobar=1)

  def testTypeAttributeIsNotAppendedWhenFlowIsClosed(self):
    session_id = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name=aff4_flows.FlowOrderTest.__name__,
        token=self.token)

    flow_obj = aff4.FACTORY.Open(
        session_id,
        aff4_type=aff4_flows.FlowOrderTest,
        age=aff4.ALL_TIMES,
        mode="rw",
        token=self.token)
    flow_obj.Close()

    flow_obj = aff4.FACTORY.Open(
        session_id,
        aff4_type=aff4_flows.FlowOrderTest,
        age=aff4.ALL_TIMES,
        token=self.token)

    types = list(flow_obj.GetValuesForAttribute(flow_obj.Schema.TYPE))
    self.assertLen(types, 1)

  def testFlowSerialization(self):
    """Check that we can serialize flows."""
    session_id = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name=aff4_flows.FlowOrderTest.__name__,
        token=self.token)

    flow_obj = aff4.FACTORY.Open(
        session_id,
        aff4_type=aff4_flows.FlowOrderTest,
        age=aff4.ALL_TIMES,
        token=self.token)

    self.assertEqual(flow_obj.__class__, aff4_flows.FlowOrderTest)

  def testFlowSerialization2(self):
    """Check that we can serialize flows."""

    class TestClientMock(action_mocks.ActionMock):

      in_rdfvalue = rdf_client_action.EchoRequest
      out_rdfvalues = [rdf_protodict.DataBlob]

      def __init__(self):
        super(TestClientMock, self).__init__()
        # Register us as an action plugin.
        # TODO(user): this is a hacky shortcut and should be fixed.
        server_stubs.ClientActionStub.classes["ReturnBlob"] = self
        self.__name__ = "ReturnBlob"

      def ReturnBlob(self, unused_args):
        return [rdf_protodict.DataBlob(integer=100)]

    # Run the flow in the simulated way
    flow_test_lib.TestFlowHelper(
        "FlowResponseSerialization",
        TestClientMock(),
        token=self.token,
        client_id=self.client_id)

  def testTerminate(self):
    session_id = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name=aff4_flows.FlowOrderTest.__name__,
        token=self.token)

    flow.GRRFlow.TerminateAFF4Flow(session_id, token=self.token)
    flow_obj = aff4.FACTORY.Open(
        session_id,
        aff4_type=aff4_flows.FlowOrderTest,
        age=aff4.ALL_TIMES,
        token=self.token)
    runner = flow_obj.GetRunner()
    self.assertEqual(runner.IsRunning(), False)
    self.assertEqual(runner.context.state,
                     rdf_flow_runner.FlowContext.State.ERROR)

    reason = "no reason"
    session_id = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name=aff4_flows.FlowOrderTest.__name__,
        token=self.token)
    flow.GRRFlow.TerminateAFF4Flow(session_id, reason=reason, token=self.token)

    flow_obj = aff4.FACTORY.Open(
        session_id,
        aff4_type=aff4_flows.FlowOrderTest,
        age=aff4.ALL_TIMES,
        token=self.token)
    runner = flow_obj.GetRunner()
    self.assertEqual(runner.IsRunning(), False)
    self.assertEqual(runner.context.state,
                     rdf_flow_runner.FlowContext.State.ERROR)
    self.assertIn(reason, runner.context.status)

  def testChildTermination(self):
    session_id = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name="CallClientParentFlow",
        token=self.token)

    # The child URN should be contained within the parent session_id URN.
    flow_obj = aff4.FACTORY.Open(session_id, token=self.token)

    children = list(
        obj for obj in flow_obj.OpenChildren() if isinstance(obj, flow.GRRFlow))
    self.assertLen(children, 1)

    reason = "just so"

    flow.GRRFlow.TerminateAFF4Flow(session_id, reason=reason, token=self.token)

    flow_obj = aff4.FACTORY.Open(
        session_id, aff4_type=CallClientParentFlow, token=self.token)

    runner = flow_obj.GetRunner()
    self.assertEqual(runner.IsRunning(), False)
    self.assertEqual(runner.context.state,
                     rdf_flow_runner.FlowContext.State.ERROR)

    self.assertTrue("user test" in runner.context.status)
    self.assertTrue(reason in runner.context.status)

    child = aff4.FACTORY.Open(
        children[0].urn, aff4_type=CallClientChildFlow, token=self.token)
    runner = child.GetRunner()
    self.assertEqual(runner.IsRunning(), False)
    self.assertEqual(runner.context.state,
                     rdf_flow_runner.FlowContext.State.ERROR)

    self.assertTrue("user test" in runner.context.status)
    self.assertTrue("Parent flow terminated." in runner.context.status)

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
      session_id = flow.StartAFF4Flow(
          client_id=self.client_id,
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
    close_call_times = []

    def Close(self):
      if isinstance(self, CallClientParentFlow):
        close_call_times.append(time.time())
      return aff4.AFF4Object.Close.old_target(self)

    qst_call_times = []

    def QueueScheduleTasks(self, *args):
      qst_call_times.append(time.time())
      return data_store.DB.mutation_pool_cls.QueueScheduleTasks.old_target(
          self, *args)

    with utils.MultiStubber(
        (aff4.AFF4Object, "Close", Close),
        # This is a pool method and will only get written once the
        # pool is flushed. The flush will happen after the queuing and
        # doesn't change the test.
        (data_store.DB.mutation_pool_cls, "QueueScheduleTasks",
         QueueScheduleTasks)):
      flow.StartAFF4Flow(
          client_id=self.client_id,
          flow_name="CallClientParentFlow",
          token=self.token)

    self.assertLen(close_call_times, 1)
    self.assertLen(qst_call_times, 1)

    # Check that the client request was written after the flow was created.
    self.assertLess(
        close_call_times[0], qst_call_times[0],
        "The client request was issued before "
        "the flow was created.")

  def testFlowLogging(self):
    """Check that flows log correctly."""
    flow_urn = flow_test_lib.TestFlowHelper(
        aff4_flows.DummyLogFlow.__name__,
        action_mocks.ActionMock(),
        token=self.token,
        client_id=self.client_id)

    log_collection = flow.GRRFlow.LogCollectionForFID(flow_urn)
    self.assertLen(log_collection, 8)
    for log in log_collection:
      self.assertEqual(log.client_id, self.client_id)
      self.assertTrue(log.log_message in [
          "First", "Second", "Third", "Fourth", "Uno", "Dos", "Tres", "Cuatro"
      ])
      self.assertTrue(log.flow_name in [
          aff4_flows.DummyLogFlow.__name__,
          aff4_flows.DummyLogFlowChild.__name__
      ])
      self.assertTrue(str(flow_urn) in str(log.urn))

  def testFlowStoresResultsPerType(self):
    flow_urn = flow_test_lib.TestFlowHelper(
        FlowWithMultipleResultTypes.__name__,
        action_mocks.ActionMock(),
        token=self.token,
        client_id=self.client_id)

    c = flow.GRRFlow.TypedResultCollectionForFID(flow_urn)
    self.assertEqual(
        set(c.ListStoredTypes()),
        set([
            rdfvalue.RDFInteger.__name__, rdfvalue.RDFString.__name__,
            rdfvalue.RDFURN.__name__
        ]))
    self.assertEqual(c.LengthByType(rdfvalue.RDFInteger.__name__), 1)
    self.assertEqual(c.LengthByType(rdfvalue.RDFString.__name__), 2)
    self.assertEqual(c.LengthByType(rdfvalue.RDFURN.__name__), 3)

    self.assertListEqual(
        [v.payload for _, v in c.ScanByType(rdfvalue.RDFInteger.__name__)],
        [rdfvalue.RDFInteger(42)])
    self.assertListEqual(
        [v.payload for _, v in c.ScanByType(rdfvalue.RDFString.__name__)],
        [rdfvalue.RDFString("foo bar"),
         rdfvalue.RDFString("foo1 bar1")])
    self.assertListEqual(
        [v.payload for _, v in c.ScanByType(rdfvalue.RDFURN.__name__)], [
            rdfvalue.RDFURN("foo/bar"),
            rdfvalue.RDFURN("foo1/bar1"),
            rdfvalue.RDFURN("foo2/bar2")
        ])


class FlowTest(notification_test_lib.NotificationTestMixin,
               acl_test_lib.AclTestMixin, BasicFlowTest):
  """Tests the Flow."""

  def testBrokenFlow(self):
    """Check that flows which call to incorrect states raise."""
    client_mock = action_mocks.ActionMock(standard.ReadBuffer)
    with self.assertRaises(RuntimeError):
      with test_lib.SuppressLogs():
        flow_test_lib.TestFlowHelper(
            aff4_flows.BrokenFlow.__name__,
            client_mock,
            client_id=self.client_id,
            check_flow_errors=True,
            token=self.token)

  def SendMessages(self, response_ids, session_id, authenticated=True):
    """Send messages to the flow."""
    for response_id in response_ids:
      message = rdf_flows.GrrMessage(
          request_id=1, response_id=response_id, session_id=session_id)

      blob = rdf_protodict.DataBlob()
      blob.SetValue(response_id)
      message.payload = blob

      if authenticated:
        auth_state = rdf_flows.GrrMessage.AuthorizationState.AUTHENTICATED
        message.auth_state = auth_state

      self.SendMessage(message)

  def SendMessage(self, message):
    # Now messages are set in the data store
    with queue_manager.QueueManager(token=self.token) as manager:
      manager.QueueResponse(message)

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

  def testReordering(self):
    """Check that out of order client messages are reordered."""
    flow_obj = self.FlowSetup(aff4_flows.FlowOrderTest.__name__)

    # Simulate processing messages arriving in random order
    message_ids = [2, 1, 4, 3, 5]
    self.SendMessages(message_ids, flow_obj.session_id)

    # Send the status message
    self.SendOKStatus(6, flow_obj.session_id)

    runner = flow_obj.GetRunner()
    notification = rdf_flows.GrrNotification(
        timestamp=rdfvalue.RDFDatetime.Now())
    runner.ProcessCompletedRequests(notification)

    # Check that the messages were processed in order
    self.assertEqual(flow_obj.messages, [1, 2, 3, 4, 5])

  def testCallClient(self):
    """Flows can send client messages using CallClient()."""
    flow_obj = self.FlowSetup(aff4_flows.FlowOrderTest.__name__)

    # Check that a message went out to the client
    manager = queue_manager.QueueManager(token=self.token)
    tasks = manager.Query(self.client_id, limit=100)

    self.assertLen(tasks, 1)

    message = tasks[0]

    self.assertEqual(message.session_id, flow_obj.session_id)
    self.assertEqual(message.request_id, 1)
    self.assertEqual(message.name, "Test")

  def testAuthentication1(self):
    """Test that flows refuse to processes unauthenticated messages."""
    flow_obj = self.FlowSetup(aff4_flows.FlowOrderTest.__name__)

    # Simulate processing messages arriving in random order
    message_ids = [2, 1, 4, 3, 5]
    self.SendMessages(message_ids, flow_obj.session_id, authenticated=False)

    # Send the status message
    self.SendOKStatus(6, flow_obj.session_id)

    runner = flow_obj.GetRunner()
    notification = rdf_flows.GrrNotification(
        timestamp=rdfvalue.RDFDatetime.Now())
    runner.ProcessCompletedRequests(notification)

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
    flow_obj = self.FlowSetup(aff4_flows.FlowOrderTest.__name__)

    # Simulate processing messages arriving in random order
    message_ids = [1, 2]
    self.SendMessages(message_ids, flow_obj.session_id, authenticated=True)

    # Now suppose some of the messages are spoofed
    message_ids = [3, 4, 5]
    self.SendMessages(message_ids, flow_obj.session_id, authenticated=False)

    # And now our real messages arrive
    message_ids = [5, 6]
    self.SendMessages(message_ids, flow_obj.session_id, authenticated=True)

    # Send the status message
    self.SendOKStatus(7, flow_obj.session_id)

    runner = flow_obj.GetRunner()
    notification = rdf_flows.GrrNotification(
        timestamp=rdfvalue.RDFDatetime.Now())
    runner.ProcessCompletedRequests(notification)

    # Some messages should actually be processed
    self.assertEqual(flow_obj.messages, [1, 2, 5, 6])

  def testWellKnownFlows(self):
    """Test the well known flows."""
    test_flow = self.FlowSetup(flow_test_lib.WellKnownSessionTest.__name__)

    # Make sure the session ID is well known
    self.assertEqual(test_flow.session_id,
                     flow_test_lib.WellKnownSessionTest.well_known_session_id)

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
    self.assertEqual(test_flow.messages, list(range(10)))

  def testArgParsing(self):
    """Test that arguments can be extracted and annotated successfully."""

    # Should raise on parsing default.
    with self.assertRaises(ValueError):
      flow.StartAFF4Flow(
          client_id=self.client_id,
          flow_name="BadArgsFlow1",
          arg1=False,
          token=self.token)

    # Should not raise now if we provide the correct type.
    flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name="BadArgsFlow1",
        arg1=rdf_paths.PathSpec(),
        token=self.token)

  def testUserGetsNotificationWithNumberOfResults(self):
    self.token.username = "notification_test_user"
    self.CreateUser(self.token.username)

    flow_test_lib.TestFlowHelper(
        FlowWithMultipleResultTypes.__name__,
        action_mocks.ActionMock(),
        token=self.token,
        client_id=self.client_id)

    notifications = self.GetUserNotifications(self.token.username)
    self.assertIn("completed with 6 results", notifications[0].message)


class FlowTerminationTest(BasicFlowTest):
  """Flow termination-related tests."""

  def testFlowMarkedForTerminationTerminatesInStateHandler(self):
    flow_obj = self.FlowSetup(aff4_flows.FlowOrderTest.__name__)
    with data_store.DB.GetMutationPool() as pool:
      flow.GRRFlow.MarkForTermination(
          flow_obj.urn, reason="because i can", mutation_pool=pool)

    with self.assertRaisesRegexp(RuntimeError, "because i can"):
      flow_test_lib.TestFlowHelper(
          flow_obj.urn,
          client_mock=ClientMock(),
          client_id=self.client_id,
          token=self.token)


class FlowOutputPluginsTest(BasicFlowTest):

  def setUp(self):
    super(FlowOutputPluginsTest, self).setUp()
    test_output_plugins.DummyFlowOutputPlugin.num_calls = 0
    test_output_plugins.DummyFlowOutputPlugin.num_responses = 0

  def RunFlow(self,
              flow_name=None,
              plugins=None,
              flow_args=None,
              client_mock=None):
    runner_args = rdf_flow_runner.FlowRunnerArgs(
        flow_name=flow_name or transfer.GetFile.__name__,
        output_plugins=plugins)

    if flow_args is None:
      flow_args = transfer.GetFileArgs(
          pathspec=rdf_paths.PathSpec(
              path="/tmp/evil.txt", pathtype=rdf_paths.PathSpec.PathType.OS))

    if client_mock is None:
      client_mock = hunt_test_lib.SampleHuntMock()

    return flow_test_lib.TestFlowHelper(
        flow_name,
        args=flow_args,
        runner_args=runner_args,
        client_mock=client_mock,
        client_id=self.client_id,
        token=self.token)

  def testFlowWithoutOutputPluginsCompletes(self):
    self.RunFlow()

  def testFlowWithOutputPluginButWithoutResultsCompletes(self):
    self.RunFlow(
        flow_name="NoRequestParentFlow",
        plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin")
        ])
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 0)

  def testFlowWithOutputPluginProcessesResultsSuccessfully(self):
    self.RunFlow(plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyFlowOutputPlugin")
    ])
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)

  def testFlowLogsSuccessfulOutputPluginProcessing(self):
    flow_urn = self.RunFlow(plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyFlowOutputPlugin")
    ])
    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    log_messages = [item.log_message for item in flow_obj.GetLog()]
    self.assertTrue(
        "Plugin DummyFlowOutputPlugin successfully processed 1 flow replies." in
        log_messages)

  def testFlowLogsFailedOutputPluginProcessing(self):
    flow_urn = self.RunFlow(plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="FailingDummyFlowOutputPlugin")
    ])
    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    log_messages = [item.log_message for item in flow_obj.GetLog()]
    self.assertTrue(
        "Plugin FailingDummyFlowOutputPlugin failed to process 1 replies "
        "due to: Oh no!" in log_messages)

  def testFlowDoesNotFailWhenOutputPluginFails(self):
    flow_urn = self.RunFlow(plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="FailingDummyFlowOutputPlugin")
    ])
    flow_obj = aff4.FACTORY.Open(flow_urn, token=self.token)
    self.assertEqual(flow_obj.context.state, "TERMINATED")

  def testFailingPluginDoesNotImpactOtherPlugins(self):
    self.RunFlow(plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="FailingDummyFlowOutputPlugin"),
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyFlowOutputPlugin")
    ])

    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)


class GeneralFlowsTest(BasicFlowTest):
  """Tests some flows."""

  def testCallState(self):
    """Test the ability to chain flows."""
    CallStateFlow.success = False

    # Run the flow in the simulated way
    flow_test_lib.TestFlowHelper(
        "CallStateFlow",
        ClientMock(),
        client_id=self.client_id,
        token=self.token)

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
      client_mock = flow_test_lib.MockClient(
          self.client_id, client_mock, token=self.token)
      worker_mock = worker_test_lib.MockWorker(
          check_flow_errors=True, token=self.token)

      flow.StartAFF4Flow(
          client_id=self.client_id,
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
    flow_test_lib.TestFlowHelper(
        "ParentFlow", ClientMock(), client_id=self.client_id, token=self.token)

    self.assertEqual(ParentFlow.success, True)

  def testCreatorPropagation(self):

    # Instantiate the flow using one username.
    session_id = flow.StartAFF4Flow(
        client_id=self.client_id,
        flow_name="ParentFlow",
        sync=False,
        token=access_control.ACLToken(
            username="original_user", reason="testing"))

    # Run the flow using another user ("test").
    flow_test_lib.TestFlowHelper(
        session_id, ClientMock(), client_id=self.client_id, token=self.token)

    self.assertEqual(ParentFlow.success, True)
    subflows = list(
        obj for obj in aff4.FACTORY.Open(session_id,
                                         token=self.token).OpenChildren()
        if isinstance(obj, flow.GRRFlow))
    self.assertLen(subflows, 1)
    self.assertEqual(subflows[0].GetRunner().context.creator, "original_user")

  def testBrokenChainedFlow(self):
    """Test that exceptions are properly handled in chain flows."""
    BrokenParentFlow.success = False

    # Run the flow in the simulated way
    with test_lib.SuppressLogs():
      flow_test_lib.TestFlowHelper(
          "BrokenParentFlow",
          ClientMock(),
          client_id=self.client_id,
          check_flow_errors=False,
          token=self.token)

    self.assertEqual(BrokenParentFlow.success, True)


class ResourcedWorker(worker_test_lib.MockWorker):
  USER_CPU = [1, 20, 5, 16]
  SYSTEM_CPU = [4, 20, 2, 8]
  NETWORK_BYTES = [180, 1000, 580, 2000]


class FlowLimitTests(BasicFlowTest):

  def RunFlow(self, flow_name, **kwargs):
    result = {}
    client_mock = action_mocks.CPULimitClientMock(result)
    client_mock = flow_test_lib.MockClient(
        self.client_id, client_mock, token=self.token)
    worker_mock = ResourcedWorker(check_flow_errors=True, token=self.token)

    flow.StartAFF4Flow(
        client_id=self.client_id,
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
    result = self.RunFlow(aff4_flows.CPULimitFlow.__name__, cpu_limit=300)
    self.assertEqual(result["cpulimit"], [300, 295, 255])


class NetworkLimitFlow(flow.GRRFlow):
  """This flow is used to test the network bytes limit."""

  def Start(self):
    self.CallClient(
        server_stubs.ClientActionStub.classes["Store"], next_state="State1")

  def State1(self, responses):
    del responses
    self.CallClient(
        server_stubs.ClientActionStub.classes["Store"], next_state="State2")

  def State2(self, responses):
    del responses
    self.CallClient(
        server_stubs.ClientActionStub.classes["Store"], next_state="State3")

  def State3(self, responses):
    del responses
    self.CallClient(
        server_stubs.ClientActionStub.classes["Store"], next_state="Done")

  def Done(self, responses):
    del responses


class ClientMock(action_mocks.ActionMock):
  """Mock of client actions."""

  in_rdfvalue = None
  out_rdfvalues = [rdfvalue.RDFString]

  def __init__(self):
    super(ClientMock, self).__init__()
    # Register us as an action plugin.
    # TODO(user): this is a hacky shortcut and should be fixed.
    server_stubs.ClientActionStub.classes["ReturnHello"] = self
    self.__name__ = "ReturnHello"

  def ReturnHello(self, _):
    return [rdfvalue.RDFString("Hello World")]


class ChildFlow(flow.GRRFlow):
  """This flow will be called by our parent."""

  def Start(self):
    self.CallClient(
        server_stubs.ClientActionStub.classes["ReturnHello"],
        next_state="ReceiveHello")

  def ReceiveHello(self, responses):
    # Relay the client's message to our parent
    for response in responses:
      self.SendReply(rdfvalue.RDFString("Child received"))
      self.SendReply(response)


class BrokenChildFlow(ChildFlow):
  """A broken flow which raises."""

  def ReceiveHello(self, responses):
    raise IOError("Boo")


class ParentFlow(flow.GRRFlow):
  """This flow will launch a child flow."""

  # This is a global flag which will be set when the flow runs.
  success = False

  def Start(self):
    # Call the child flow.
    self.CallFlow("ChildFlow", next_state="ParentReceiveHello")

  def ParentReceiveHello(self, responses):
    responses = list(responses)
    if (len(responses) != 2 or "Child" not in unicode(responses[0]) or
        "Hello" not in unicode(responses[1])):
      raise RuntimeError("Messages not passed to parent")

    ParentFlow.success = True


class BrokenParentFlow(flow.GRRFlow):
  """This flow will launch a broken child flow."""

  # This is a global flag which will be set when the flow runs.
  success = False

  def Start(self):
    # Call the child flow.
    self.CallFlow("BrokenChildFlow", next_state="ReceiveHello")

  def ReceiveHello(self, responses):
    if (responses or
        responses.status.status == rdf_flows.GrrStatus.ReturnedStatus.OK):
      raise RuntimeError("Error not propagated to parent")

    BrokenParentFlow.success = True


class CallStateFlow(flow.GRRFlow):
  """A flow that calls one of its own states."""

  # This is a global flag which will be set when the flow runs.
  success = False

  def Start(self):
    # Call the receive state.
    self.CallState(next_state="ReceiveHello")

  def ReceiveHello(self, responses):

    CallStateFlow.success = True


class DelayedCallStateFlow(flow.GRRFlow):
  """A flow that calls one of its own states with a delay."""

  # This is a global flag which will be set when the flow runs.
  flow_ran = 0

  def Start(self):
    # Call the child flow.
    self.CallState(next_state="ReceiveHello")

  def ReceiveHello(self, responses):
    DelayedCallStateFlow.flow_ran = 1

    # Call the child flow.
    self.CallState(
        next_state="DelayedHello", start_time=rdfvalue.RDFDatetime.Now() + 100)

  def DelayedHello(self, responses):
    DelayedCallStateFlow.flow_ran = 2


class BadArgsFlow1Args(rdf_structs.RDFProtoStruct):
  protobuf = tests_pb2.BadArgsFlow1Args
  rdf_deps = [rdf_paths.PathSpec]


class BadArgsFlow1(flow.GRRFlow):
  """A flow that has args that mismatch type info."""

  args_type = BadArgsFlow1Args


@db_test_lib.DualDBTest
class FlowPropertiesTest(flow_test_lib.FlowTestsBaseclass):

  # These tests are creating test-local flows. But since test functions can be
  # (and are because this is a dual-database test case), they may spawn multiple
  # flows with the same name. Thanks to the metaclass registry flows use this
  # results in a runtime error. Because these tests do not care for other flows
  # being registered, we clear the registry and restore it after each test case.

  def setUp(self):
    super(FlowPropertiesTest, self).setUp()
    self._flow_classes = flow.GRRFlow.classes
    self._flow_base_classes = flow_base.FlowBase.classes
    flow.GRRFlow.classes = {}
    flow_base.FlowBase.classes = {}

  def tearDown(self):
    super(FlowPropertiesTest, self).tearDown()
    flow.GRRFlow.classes = self._flow_classes
    flow_base.FlowBase.classes = self._flow_base_classes

  def testClientId(self):
    test = self
    client_id = test.SetupClient(0)

    @flow_base.DualDBFlow  # pylint: disable=unused-variable
    class IdCheckerFlowMixin(object):

      def Start(self):
        test.assertEqual(self.client_id, client_id)

    flow_test_lib.TestFlowHelper(
        IdCheckerFlow.__name__, client_id=client_id, token=self.token)  # pylint: disable=undefined-variable

  def testClientVersion(self):
    test = self
    client_id = test.SetupClient(0)

    @flow_base.DualDBFlow  # pylint: disable=unused-variable
    class VersionCheckerFlowMixin(object):

      def Start(self):
        version = config.CONFIG["Source.version_numeric"]
        test.assertEqual(self.client_version, version)
        test.assertEqual(self.client_version, version)  # Force cache usage.

    flow_test_lib.TestFlowHelper(
        VersionCheckerFlow.__name__, client_id=client_id, token=self.token)  # pylint: disable=undefined-variable

  def testClientOs(self):
    test = self
    client_id = test.SetupClient(0, system="Windows")

    @flow_base.DualDBFlow  # pylint: disable=unused-variable
    class OsCheckerFlowMixin(object):

      def Start(self):
        test.assertEqual(self.client_os, "Windows")
        test.assertEqual(self.client_os, "Windows")  # Force cache usage.

    flow_test_lib.TestFlowHelper(
        OsCheckerFlow.__name__, client_id=client_id, token=self.token)  # pylint: disable=undefined-variable


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
