#!/usr/bin/env python
"""Tests for flows."""

import random
from unittest import mock

from absl import app
from absl.testing import absltest

from grr_response_client import actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import action_registry
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server import worker_lib
from grr_response_server.databases import db
from grr_response_server.flows import file
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import flow_runner as rdf_flow_runner
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import test_lib
from grr.test_lib import test_output_plugins


class ReturnHello(actions.ActionPlugin):
  """A test client action."""

  out_rdfvalues = [rdfvalue.RDFString]

  def Run(self, _):
    self.SendReply(rdfvalue.RDFString("Hello World"))


action_registry.RegisterAdditionalTestClientAction(ReturnHello)


class ClientMock(action_mocks.ActionMock):
  """Mock of client actions."""

  def __init__(self):
    super().__init__(ReturnHello)


class CallStateFlow(flow_base.FlowBase):
  """A flow that calls one of its own states."""

  # This is a global flag which will be set when the flow runs.
  success = False

  def Start(self):
    # Call the receive state.
    self.CallState(next_state="ReceiveHello")

  def ReceiveHello(self, responses):

    CallStateFlow.success = True


class BasicFlowTest(flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super().setUp()
    self.client_id = self.SetupClient(0)


class FlowWithMultipleResultTypes(flow_base.FlowBase):
  """Flow returning multiple results."""

  def Start(self):
    self.CallState(next_state="SendReplies")

  def SendReplies(self, responses):
    self.SendReply(rdfvalue.RDFInteger(42))
    self.SendReply(rdfvalue.RDFString("foo bar"))
    self.SendReply(rdfvalue.RDFString("foo1 bar1"))
    self.SendReply(rdfvalue.RDFURN("aff4:/foo/bar"))
    self.SendReply(rdfvalue.RDFURN("aff4:/foo1/bar1"))
    self.SendReply(rdfvalue.RDFURN("aff4:/foo2/bar2"))


class ParentFlow(flow_base.FlowBase):
  """This flow will launch a child flow."""

  # This is a global flag which will be set when the flow runs.
  success = False

  def Start(self):
    # Call the child flow.
    self.CallFlow("ChildFlow", next_state="ParentReceiveHello")

  def ParentReceiveHello(self, responses):
    responses = list(responses)
    if (len(responses) != 2 or "Child" not in str(responses[0]) or
        "Hello" not in str(responses[1])):
      raise RuntimeError("Messages not passed to parent")

    ParentFlow.success = True


class ChildFlow(flow_base.FlowBase):
  """This flow will be called by our parent."""

  def Start(self):
    self.CallClient(ReturnHello, next_state="ReceiveHello")

  def ReceiveHello(self, responses):
    # Relay the client's message to our parent
    for response in responses:
      self.SendReply(rdfvalue.RDFString("Child received"))
      self.SendReply(response)


class BrokenParentFlow(flow_base.FlowBase):
  """This flow will launch a broken child flow."""

  # This is a global flag which will be set when the flow runs.
  success = False

  def Start(self):
    # Call the child flow.
    self.CallFlow("BrokenChildFlow", next_state="ReceiveHello")

  def ReceiveHello(self, responses):
    if responses or responses.status.status == "OK":
      raise RuntimeError("Error not propagated to parent")

    BrokenParentFlow.success = True


class BrokenChildFlow(ChildFlow):
  """A broken flow which raises."""

  def ReceiveHello(self, responses):
    raise IOError("Boo")


class CallClientParentFlow(flow_base.FlowBase):

  def Start(self):
    self.CallFlow("CallClientChildFlow", next_state="End")

  def End(self, responses):
    del responses  # Unused.


class CallClientChildFlow(flow_base.FlowBase):

  def Start(self):
    self.CallClient(server_stubs.GetClientStats, next_state="End")


class ParentFlowWithoutForwardingOutputPlugins(flow_base.FlowBase):
  """This flow creates a Child without forwarding OutputPlugins."""

  def Start(self):
    # Call the child flow WITHOUT output plugins.
    self.CallFlow("ChildFlow", next_state="IgnoreChildReplies")

  def IgnoreChildReplies(self, responses):
    del responses  # Unused
    self.SendReply(rdfvalue.RDFString("Parent received"))


class ParentFlowWithForwardedOutputPlugins(flow_base.FlowBase):
  """This flow creates a Child without forwarding OutputPlugins."""

  def Start(self):
    # Calls the child flow WITH output plugins.
    self.CallFlow(
        "ChildFlow",
        output_plugins=self.rdf_flow.output_plugins,
        next_state="IgnoreChildReplies")

  def IgnoreChildReplies(self, responses):
    del responses  # Unused
    self.SendReply(rdfvalue.RDFString("Parent received"))


class FlowWithBrokenStart(flow_base.FlowBase):

  def Start(self):
    raise ValueError("boo")


class FlowCreationTest(BasicFlowTest):
  """Test flow creation."""

  def testUnknownArg(self):
    """Check that flows reject unknown args."""
    with self.assertRaises(type_info.UnknownArg):
      flow.StartFlow(client_id=self.client_id, flow_cls=CallStateFlow, foobar=1)

  def testDuplicateIDsAreNotAllowed(self):
    flow_id = flow.StartFlow(
        flow_cls=CallClientParentFlow, client_id=self.client_id)
    with self.assertRaises(flow.CanNotStartFlowWithExistingIdError):
      flow.StartFlow(
          flow_cls=CallClientParentFlow,
          parent=flow.FlowParent.FromHuntID(flow_id),
          client_id=self.client_id)

  def testChildTermination(self):
    flow_id = flow.StartFlow(
        flow_cls=CallClientParentFlow, client_id=self.client_id)
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    client_flow_obj = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id)[0]

    self.assertEqual(flow_obj.flow_state, "RUNNING")
    self.assertEqual(client_flow_obj.flow_state, "RUNNING")

    # Terminate the parent flow.
    flow_base.TerminateFlow(self.client_id, flow_id, reason="Testing")

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    client_flow_obj = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id)[0]

    self.assertEqual(flow_obj.flow_state, "ERROR")
    self.assertEqual(client_flow_obj.flow_state, "ERROR")

  def testExceptionInStart(self):
    flow_id = flow.StartFlow(
        flow_cls=FlowWithBrokenStart, client_id=self.client_id)
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)

    self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.ERROR)
    self.assertEqual(flow_obj.error_message, "boo")
    self.assertIsNotNone(flow_obj.backtrace)


class GeneralFlowsTest(notification_test_lib.NotificationTestMixin,
                       acl_test_lib.AclTestMixin, BasicFlowTest):
  """Tests some flows."""

  def testCallState(self):
    """Test the ability to chain flows."""
    CallStateFlow.success = False

    # Run the flow in the simulated way
    flow_test_lib.StartAndRunFlow(CallStateFlow, client_id=self.client_id)

    self.assertEqual(CallStateFlow.success, True)

  def testChainedFlow(self):
    """Test the ability to chain flows."""
    ParentFlow.success = False

    # Run the flow in the simulated way
    flow_test_lib.StartAndRunFlow(
        ParentFlow, client_mock=ClientMock(), client_id=self.client_id)

    self.assertEqual(ParentFlow.success, True)

  def testBrokenChainedFlow(self):
    BrokenParentFlow.success = False

    # Run the flow in the simulated way
    with test_lib.SuppressLogs():
      flow_test_lib.StartAndRunFlow(
          BrokenParentFlow,
          client_mock=ClientMock(),
          client_id=self.client_id,
          check_flow_errors=False)

    self.assertEqual(BrokenParentFlow.success, True)

  def testCreatorPropagation(self):
    username = u"original user"
    data_store.REL_DB.WriteGRRUser(username)

    client_mock = ClientMock()

    flow_id = flow_test_lib.StartAndRunFlow(
        flow_cls=ParentFlow,
        client_id=self.client_id,
        creator=username,
        client_mock=client_mock)

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.creator, username)

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id)
    self.assertLen(child_flows, 1)
    child_flow = child_flows[0]

    self.assertEqual(child_flow.creator, username)

  def testLimitPropagation(self):
    """This tests that client actions are limited properly."""
    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[10],
        system_cpu_usage=[10],
        network_usage=[1000],
        runtime_us=[rdfvalue.Duration.From(1, rdfvalue.SECONDS)])

    flow_test_lib.StartAndRunFlow(
        flow_test_lib.CPULimitFlow,
        client_mock=client_mock,
        client_id=self.client_id,
        cpu_limit=1000,
        network_bytes_limit=10000,
        runtime_limit=rdfvalue.Duration.From(5, rdfvalue.SECONDS))

    self.assertEqual(client_mock.storage["cpulimit"], [1000, 980, 960])
    self.assertEqual(client_mock.storage["networklimit"], [10000, 9000, 8000])
    self.assertEqual(client_mock.storage["networklimit"], [10000, 9000, 8000])
    self.assertEqual(client_mock.storage["runtimelimit"], [
        rdfvalue.Duration.From(5, rdfvalue.SECONDS),
        rdfvalue.Duration.From(4, rdfvalue.SECONDS),
        rdfvalue.Duration.From(3, rdfvalue.SECONDS),
    ])

  def testCPULimitExceeded(self):
    """This tests that the cpu limit for flows is working."""
    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[10], system_cpu_usage=[10], network_usage=[1000])

    with test_lib.SuppressLogs():
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_test_lib.CPULimitFlow,
          client_mock=client_mock,
          client_id=self.client_id,
          cpu_limit=30,
          network_bytes_limit=10000,
          check_flow_errors=False)

    rdf_flow = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(rdf_flow.flow_state, "ERROR")
    self.assertIn("CPU limit exceeded", rdf_flow.error_message)

  def testNetworkLimitExceeded(self):
    """This tests that the network limit for flows is working."""
    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[10], system_cpu_usage=[10], network_usage=[1000])

    with test_lib.SuppressLogs():
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_test_lib.CPULimitFlow,
          client_mock=client_mock,
          client_id=self.client_id,
          cpu_limit=1000,
          network_bytes_limit=1500,
          check_flow_errors=False)

    rdf_flow = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(rdf_flow.flow_state, "ERROR")
    self.assertIn("bytes limit exceeded", rdf_flow.error_message)

  def testRuntimeLimitExceeded(self):
    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[1],
        system_cpu_usage=[1],
        network_usage=[1],
        runtime_us=[rdfvalue.Duration.From(4, rdfvalue.SECONDS)])

    with test_lib.SuppressLogs():
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_test_lib.CPULimitFlow,
          client_mock=client_mock,
          client_id=self.client_id,
          runtime_limit=rdfvalue.Duration.From(9, rdfvalue.SECONDS),
          check_flow_errors=False)

    rdf_flow = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(rdf_flow.flow_state, "ERROR")
    self.assertIn("Runtime limit exceeded", rdf_flow.error_message)

  def testUserGetsNotificationWithNumberOfResults(self):
    username = "notification_test_user"
    self.CreateUser(username)

    flow_test_lib.StartAndRunFlow(
        FlowWithMultipleResultTypes, client_id=self.client_id, creator=username)

    notifications = self.GetUserNotifications(username)

    self.assertIn("FlowWithMultipleResultTypes completed with 6 results",
                  notifications[0].message)

  def testNestedFlowsHaveTheirResultsSaved(self):
    # Run the flow in the simulated way
    parent_flow_id = flow_test_lib.StartAndRunFlow(
        ParentFlow, client_mock=ClientMock(), client_id=self.client_id)

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, parent_flow_id)
    self.assertLen(child_flows, 1)

    child_flow_results = flow_test_lib.GetFlowResults(self.client_id,
                                                      child_flows[0].flow_id)
    self.assertNotEmpty(child_flow_results)


class NoRequestChildFlow(flow_base.FlowBase):
  """This flow just returns and does not generate any requests."""

  def Start(self):
    return


class NoRequestParentFlow(flow_base.FlowBase):

  child_flow = "NoRequestChildFlow"

  def Start(self):
    self.CallFlow(self.child_flow, next_state="End")

  def End(self, responses):
    del responses  # Unused.


class FlowOutputPluginsTest(BasicFlowTest):

  def setUp(self):
    super().setUp()
    test_output_plugins.DummyFlowOutputPlugin.num_calls = 0
    test_output_plugins.DummyFlowOutputPlugin.num_responses = 0

  def RunFlow(self,
              flow_cls=None,
              output_plugins=None,
              flow_args=None,
              client_mock=None):

    if flow_args is None:
      flow_args = transfer.GetFileArgs(
          pathspec=rdf_paths.PathSpec(
              path="/tmp/evil.txt", pathtype=rdf_paths.PathSpec.PathType.OS))

    if client_mock is None:
      client_mock = hunt_test_lib.SampleHuntMock(failrate=2)

    flow_urn = flow_test_lib.StartAndRunFlow(
        flow_cls or transfer.GetFile,
        client_mock=client_mock,
        client_id=self.client_id,
        flow_args=flow_args,
        output_plugins=output_plugins)

    return flow_urn

  def testFlowWithoutOutputPluginsCompletes(self):
    self.RunFlow()

  def testFlowWithOutputPluginButWithoutResultsCompletes(self):
    self.RunFlow(
        flow_cls=NoRequestParentFlow,
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin")
        ])
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 0)

  def testFlowWithOutputPluginProcessesResultsSuccessfully(self):
    self.RunFlow(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyFlowOutputPlugin")
    ])
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)

  def _RunFlowAndCollectLogs(self, output_plugins):
    log_lines = []
    with mock.patch.object(flow_base.FlowBase, "Log") as log_f:
      self.RunFlow(output_plugins=output_plugins)

      for args in log_f.call_args_list:
        log_lines.append(args[0][0] % args[0][1:])
    return log_lines

  def testFlowLogsSuccessfulOutputPluginProcessing(self):
    log_messages = self._RunFlowAndCollectLogs(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyFlowOutputPlugin")
    ])

    self.assertIn(
        "Plugin DummyFlowOutputPlugin successfully processed 1 flow replies.",
        log_messages)

  def testFlowLogsFailedOutputPluginProcessing(self):
    log_messages = self._RunFlowAndCollectLogs(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="FailingDummyFlowOutputPlugin")
    ])
    self.assertIn(
        "Plugin FailingDummyFlowOutputPlugin failed to process 1 replies "
        "due to: Oh no!", log_messages)

  def testFlowDoesNotFailWhenOutputPluginFails(self):
    flow_id = self.RunFlow(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="FailingDummyFlowOutputPlugin")
    ])
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, "FINISHED")

  def testFailingPluginDoesNotImpactOtherPlugins(self):
    self.RunFlow(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="FailingDummyFlowOutputPlugin"),
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="DummyFlowOutputPlugin")
    ])

    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)

  def testOutputPluginsOnlyRunInParentFlow_DoesNotForward(self):
    self.RunFlow(
        flow_cls=ParentFlowWithoutForwardingOutputPlugins,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin")
        ])

    # Parent calls once, and child doesn't call.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    # Parent has one response, child has two.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)

  def testOutputPluginsOnlyRunInParentFlow_Forwards(self):
    self.RunFlow(
        flow_cls=ParentFlowWithForwardedOutputPlugins,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin")
        ])

    # Parent calls once, and child doesn't call.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    # Parent has one response, child has two.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)


class ScheduleFlowTest(flow_test_lib.FlowTestsBaseclass):

  def SetupUser(self, username="u0"):
    data_store.REL_DB.WriteGRRUser(username)
    return username

  def ScheduleFlow(self, **kwargs):
    merged_kwargs = {
        "flow_name":
            file.CollectSingleFile.__name__,
        "flow_args":
            rdf_file_finder.CollectSingleFileArgs(
                path="/foo{}".format(random.randint(0, 1000))),
        "runner_args":
            rdf_flow_runner.FlowRunnerArgs(cpu_limit=random.randint(0, 60)),
        **kwargs
    }

    return flow.ScheduleFlow(**merged_kwargs)

  def testScheduleFlowCreatesMultipleScheduledFlows(self):
    client_id0 = self.SetupClient(0)
    client_id1 = self.SetupClient(1)
    username0 = self.SetupUser("u0")
    username1 = self.SetupUser("u1")

    sf0 = self.ScheduleFlow(client_id=client_id0, creator=username0)
    sf1 = self.ScheduleFlow(client_id=client_id0, creator=username0)
    sf2 = self.ScheduleFlow(client_id=client_id1, creator=username0)
    sf3 = self.ScheduleFlow(client_id=client_id0, creator=username1)

    self.assertEqual([sf0, sf1], flow.ListScheduledFlows(client_id0, username0))
    self.assertEqual([sf2], flow.ListScheduledFlows(client_id1, username0))
    self.assertEqual([sf3], flow.ListScheduledFlows(client_id0, username1))

  def testStartScheduledFlowsCreatesFlow(self):
    client_id = self.SetupClient(0)
    username = self.SetupUser("u0")

    self.ScheduleFlow(
        client_id=client_id,
        creator=username,
        flow_name=file.CollectSingleFile.__name__,
        flow_args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
        runner_args=rdf_flow_runner.FlowRunnerArgs(cpu_limit=60))

    flow.StartScheduledFlows(client_id, username)

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id)
    self.assertLen(flows, 1)

    self.assertEqual(flows[0].client_id, client_id)
    self.assertEqual(flows[0].creator, username)
    self.assertEqual(flows[0].flow_class_name, file.CollectSingleFile.__name__)
    self.assertEqual(flows[0].args.path, "/foo")
    self.assertEqual(flows[0].flow_state,
                     rdf_flow_objects.Flow.FlowState.RUNNING)
    self.assertEqual(flows[0].cpu_limit, 60)

  def testStartScheduledFlowsDeletesScheduledFlows(self):
    client_id = self.SetupClient(0)
    username = self.SetupUser("u0")

    self.ScheduleFlow(client_id=client_id, creator=username)
    self.ScheduleFlow(client_id=client_id, creator=username)

    flow.StartScheduledFlows(client_id, username)
    self.assertEmpty(flow.ListScheduledFlows(client_id, username))

  def testStartScheduledFlowsSucceedsWithoutScheduledFlows(self):
    client_id = self.SetupClient(0)
    username = self.SetupUser("u0")

    flow.StartScheduledFlows(client_id, username)

  def testStartScheduledFlowsFailsForUnknownClient(self):
    self.SetupClient(0)
    username = self.SetupUser("u0")

    with self.assertRaises(db.UnknownClientError):
      flow.StartScheduledFlows("C.1234123412341234", username)

  def testStartScheduledFlowsFailsForUnknownUser(self):
    client_id = self.SetupClient(0)
    self.SetupUser("u0")

    with self.assertRaises(db.UnknownGRRUserError):
      flow.StartScheduledFlows(client_id, "nonexistent")

  def testStartScheduledFlowsStartsMultipleFlows(self):
    client_id = self.SetupClient(0)
    username = self.SetupUser("u0")

    self.ScheduleFlow(client_id=client_id, creator=username)
    self.ScheduleFlow(client_id=client_id, creator=username)

    flow.StartScheduledFlows(client_id, username)

  def testStartScheduledFlowsHandlesErrorInFlowConstructor(self):
    client_id = self.SetupClient(0)
    username = self.SetupUser("u0")

    self.ScheduleFlow(
        client_id=client_id,
        creator=username,
        flow_name=file.CollectSingleFile.__name__,
        flow_args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
        runner_args=rdf_flow_runner.FlowRunnerArgs(cpu_limit=60))

    with mock.patch.object(
        file.CollectSingleFile, "__init__",
        side_effect=ValueError("foobazzle")):
      flow.StartScheduledFlows(client_id, username)

    self.assertEmpty(data_store.REL_DB.ReadAllFlowObjects(client_id))

    scheduled_flows = flow.ListScheduledFlows(client_id, username)
    self.assertLen(scheduled_flows, 1)
    self.assertIn("foobazzle", scheduled_flows[0].error)

  def testStartScheduledFlowsHandlesErrorInFlowArgsValidation(self):
    client_id = self.SetupClient(0)
    username = self.SetupUser("u0")

    self.ScheduleFlow(
        client_id=client_id,
        creator=username,
        flow_name=file.CollectSingleFile.__name__,
        flow_args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
        runner_args=rdf_flow_runner.FlowRunnerArgs(cpu_limit=60))

    with mock.patch.object(
        rdf_file_finder.CollectSingleFileArgs,
        "Validate",
        side_effect=ValueError("foobazzle")):
      flow.StartScheduledFlows(client_id, username)

    self.assertEmpty(data_store.REL_DB.ReadAllFlowObjects(client_id))

    scheduled_flows = flow.ListScheduledFlows(client_id, username)
    self.assertLen(scheduled_flows, 1)
    self.assertIn("foobazzle", scheduled_flows[0].error)

  def testStartScheduledFlowsContinuesNextOnFailure(self):
    client_id = self.SetupClient(0)
    username = self.SetupUser("u0")

    self.ScheduleFlow(
        client_id=client_id,
        creator=username,
        flow_name=file.CollectSingleFile.__name__,
        flow_args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
        runner_args=rdf_flow_runner.FlowRunnerArgs(cpu_limit=60))

    self.ScheduleFlow(
        client_id=client_id,
        creator=username,
        flow_name=file.CollectSingleFile.__name__,
        flow_args=rdf_file_finder.CollectSingleFileArgs(path="/foo"),
        runner_args=rdf_flow_runner.FlowRunnerArgs(cpu_limit=60))

    with mock.patch.object(
        rdf_file_finder.CollectSingleFileArgs,
        "Validate",
        side_effect=[ValueError("foobazzle"), mock.DEFAULT]):
      flow.StartScheduledFlows(client_id, username)

    self.assertLen(data_store.REL_DB.ReadAllFlowObjects(client_id), 1)
    self.assertLen(flow.ListScheduledFlows(client_id, username), 1)

  def testUnscheduleFlowCorrectlyRemovesScheduledFlow(self):
    client_id = self.SetupClient(0)
    username = self.SetupUser("u0")

    sf1 = self.ScheduleFlow(client_id=client_id, creator=username)
    sf2 = self.ScheduleFlow(client_id=client_id, creator=username)

    flow.UnscheduleFlow(client_id, username, sf1.scheduled_flow_id)

    self.assertEqual([sf2], flow.ListScheduledFlows(client_id, username))

    flow.StartScheduledFlows(client_id, username)

    self.assertLen(data_store.REL_DB.ReadAllFlowObjects(client_id), 1)

  def testStartedFlowUsesScheduledFlowId(self):
    client_id = self.SetupClient(0)
    username = self.SetupUser("u0")

    sf = self.ScheduleFlow(client_id=client_id, creator=username)

    flow.StartScheduledFlows(client_id, username)
    flows = data_store.REL_DB.ReadAllFlowObjects(client_id)

    self.assertGreater(len(sf.scheduled_flow_id), 0)
    self.assertEqual(flows[0].flow_id, sf.scheduled_flow_id)


class RandomFlowIdTest(absltest.TestCase):

  def testFlowIdGeneration(self):
    self.assertLen(flow.RandomFlowId(), 16)

    with mock.patch.object(
        flow.random, "Id64", return_value=0xF0F1F2F3F4F5F6F7):
      self.assertEqual(flow.RandomFlowId(), "F0F1F2F3F4F5F6F7")

    with mock.patch.object(flow.random, "Id64", return_value=0):
      self.assertEqual(flow.RandomFlowId(), "0000000000000000")

    with mock.patch.object(flow.random, "Id64", return_value=1):
      self.assertEqual(flow.RandomFlowId(), "0000000000000001")

    with mock.patch.object(
        flow.random, "Id64", return_value=0x0000000100000000):
      self.assertEqual(flow.RandomFlowId(), "0000000100000000")


class NotSendingStatusClientMock(action_mocks.ActionMock):
  """A mock for testing resource limits."""

  NUM_INCREMENTAL_RESPONSES = 10

  def __init__(self, shuffle=False):
    super().__init__()
    self._shuffle = shuffle

  def HandleMessage(self, message):
    responses = [
        rdfvalue.RDFString(f"Hello World {i}")
        for i in range(self.NUM_INCREMENTAL_RESPONSES)
    ]

    messages = []
    for i, r in enumerate(responses):
      messages.append(
          rdf_flows.GrrMessage(
              session_id=message.session_id,
              request_id=message.request_id,
              task_id=message.Get("task_id"),
              name=message.name,
              response_id=i + 1,
              payload=r,
              type=rdf_flows.GrrMessage.Type.MESSAGE))

    if self._shuffle:
      random.shuffle(messages)

    return messages


class StatusOnlyClientMock(action_mocks.ActionMock):

  def HandleMessage(self, message):
    return [self.GenerateStatusMessage(message, response_id=42)]


class FlowWithIncrementalCallback(flow_base.FlowBase):
  """This flow will be called by our parent."""

  def Start(self):
    self.CallClient(
        ReturnHello,
        callback_state=self.ReceiveHelloCallback.__name__,
        next_state=self.ReceiveHello.__name__)

  def ReceiveHelloCallback(self, responses):
    # Relay each message when it comes.
    for r in responses:
      self.SendReply(r)

  def ReceiveHello(self, responses):
    # Relay all incoming messages once more (but prefix the strings).
    for response in responses:
      self.SendReply(rdfvalue.RDFString("Final: " + str(response)))


class IncrementalResponseHandlingTest(BasicFlowTest):

  @mock.patch.object(FlowWithIncrementalCallback, "ReceiveHelloCallback")
  def testIncrementalCallbackReturnsResultsBeforeStatus(self, m):
    # Mocks don't have names by default.
    m.__name__ = "ReceiveHelloCallback"

    flow_id = flow_test_lib.StartAndRunFlow(
        FlowWithIncrementalCallback,
        client_mock=NotSendingStatusClientMock(),
        client_id=self.client_id,
        # Set check_flow_errors to False, otherwise test runner will complain
        # that the flow has finished in the RUNNING state.
        check_flow_errors=False)
    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.RUNNING)

    self.assertEqual(m.call_count,
                     NotSendingStatusClientMock.NUM_INCREMENTAL_RESPONSES)
    for i in range(NotSendingStatusClientMock.NUM_INCREMENTAL_RESPONSES):
      # Get the positional arguments of each call.
      args = m.mock_calls[i][1]
      # Compare the first positional argument ('responses') to the responses
      # list that we expect to have been passed to the callback.
      self.assertEqual(list(args[0]), [rdfvalue.RDFString(f"Hello World {i}")])

  @mock.patch.object(FlowWithIncrementalCallback, "ReceiveHelloCallback")
  def testIncrementalCallbackIsNotCalledWhenStatusMessageArrivesEarly(self, m):
    # Mocks don't have names by default.
    m.__name__ = "ReceiveHelloCallback"

    flow_id = flow_test_lib.StartAndRunFlow(
        FlowWithIncrementalCallback,
        client_mock=StatusOnlyClientMock(),
        client_id=self.client_id,
        # Set check_flow_errors to False, otherwise test runner will complain
        # that the flow has finished in the RUNNING state.
        check_flow_errors=False)

    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.RUNNING)

    self.assertEqual(m.call_count, 0)

  def testSendReplyWorksCorrectlyInIncrementalCallback(self):
    flow_id = flow_test_lib.StartAndRunFlow(
        FlowWithIncrementalCallback,
        client_mock=NotSendingStatusClientMock(),
        client_id=self.client_id,
        # Set check_flow_errors to False, otherwise test runner will complain
        # that the flow has finished in the RUNNING state.
        check_flow_errors=False)
    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.RUNNING)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertListEqual(results, [
        rdfvalue.RDFString(f"Hello World {i}")
        for i in range(NotSendingStatusClientMock.NUM_INCREMENTAL_RESPONSES)
    ])

  def testIncrementalCallbackIsCalledWithResponsesInRightOrder(self):
    flow_id = flow_test_lib.StartAndRunFlow(
        FlowWithIncrementalCallback,
        client_mock=NotSendingStatusClientMock(shuffle=True),
        client_id=self.client_id,
        # Set check_flow_errors to False, otherwise test runner will complain
        # that the flow has finished in the RUNNING state.
        check_flow_errors=False)

    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.RUNNING)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertListEqual(results, [
        rdfvalue.RDFString(f"Hello World {i}")
        for i in range(NotSendingStatusClientMock.NUM_INCREMENTAL_RESPONSES)
    ])

  def testIncrementalCallbackIsCalledWhenAllResponsesArriveAtOnce(self):
    flow_id = flow_test_lib.StartAndRunFlow(
        FlowWithIncrementalCallback,
        client_mock=ClientMock(),
        client_id=self.client_id)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertListEqual(results, [
        rdfvalue.RDFString("Hello World"),
        rdfvalue.RDFString("Final: Hello World")
    ])


class WorkerTest(BasicFlowTest):

  def testRaisesIfFlowProcessingRequestDoesNotTriggerAnyProcessing(self):
    with flow_test_lib.TestWorker() as worker:
      flow_id = flow.StartFlow(
          flow_cls=CallClientParentFlow, client_id=self.client_id)
      fpr = rdf_flows.FlowProcessingRequest(
          client_id=self.client_id, flow_id=flow_id)
      with self.assertRaises(worker_lib.FlowHasNothingToProcessError):
        worker.ProcessFlow(fpr)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
