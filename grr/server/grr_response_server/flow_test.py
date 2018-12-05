#!/usr/bin/env python
"""Tests for flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import mock

from grr_response_core.lib import flags
from grr_response_core.lib import rdfvalue
from grr_response_core.lib import type_info
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import output_plugin as rdf_output_plugin
from grr.test_lib import acl_test_lib
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import hunt_test_lib
from grr.test_lib import notification_test_lib
from grr.test_lib import test_lib
from grr.test_lib import test_output_plugins


class ClientMock(action_mocks.ActionMock):
  """Mock of client actions."""

  in_rdfvalue = None
  out_rdfvalues = [rdfvalue.RDFString]

  def __init__(self):
    # Register us as an action plugin.
    # TODO(user): this is a hacky shortcut and should be fixed.
    server_stubs.ClientActionStub.classes["ReturnHello"] = self
    self.__name__ = "ReturnHello"

  def ReturnHello(self, _):
    return [rdfvalue.RDFString("Hello World")]


class CallStateFlow(flow_base.FlowBase):
  """A flow that calls one of its own states."""

  # This is a global flag which will be set when the flow runs.
  success = False

  def Start(self):
    # Call the receive state.
    self.CallState(next_state="ReceiveHello")

  def ReceiveHello(self, responses):

    CallStateFlow.success = True


class BasicFlowTest(db_test_lib.RelationalDBEnabledMixin,
                    flow_test_lib.FlowTestsBaseclass):

  def setUp(self):
    super(BasicFlowTest, self).setUp()
    self.client_id = self.SetupTestClientObject(0).client_id


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
    if (len(responses) != 2 or "Child" not in unicode(responses[0]) or
        "Hello" not in unicode(responses[1])):
      raise RuntimeError("Messages not passed to parent")

    ParentFlow.success = True


class ChildFlow(flow_base.FlowBase):
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


class FlowCreationTest(BasicFlowTest):
  """Test flow creation."""

  def testUnknownArg(self):
    """Check that flows reject unknown args."""
    self.assertRaises(
        type_info.UnknownArg,
        flow.StartFlow,
        client_id=self.client_id,
        flow_cls=CallStateFlow,
        foobar=1)

  def testPendingFlowTermination(self):
    client_mock = ClientMock()

    flow_id = flow.StartFlow(flow_cls=ParentFlow, client_id=self.client_id)
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, "RUNNING")

    pending_termination = rdf_flow_objects.PendingFlowTermination(
        reason="testing")
    data_store.REL_DB.UpdateFlow(
        self.client_id, flow_id, pending_termination=pending_termination)

    with flow_test_lib.TestWorker(token=True) as worker:
      with test_lib.SuppressLogs():
        flow_test_lib.RunFlow(
            self.client_id,
            flow_id,
            client_mock=client_mock,
            worker=worker,
            check_flow_errors=False)

      flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
      self.assertEqual(flow_obj.flow_state, "ERROR")
      self.assertEqual(flow_obj.error_message, "testing")

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
        user_cpu_usage=[10], system_cpu_usage=[10], network_usage=[1000])

    flow_test_lib.StartAndRunFlow(
        flow_test_lib.CPULimitFlow,
        client_mock=client_mock,
        client_id=self.client_id,
        cpu_limit=1000,
        network_bytes_limit=10000)

    self.assertEqual(client_mock.storage["cpulimit"], [1000, 980, 960])
    self.assertEqual(client_mock.storage["networklimit"], [10000, 9000, 8000])

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
    self.assertIn("CPU limit exceeded", rdf_flow.backtrace)

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
    self.assertIn("bytes limit exceeded", rdf_flow.backtrace)

  def testUserGetsNotificationWithNumberOfResults(self):
    username = "notification_test_user"
    self.CreateUser(username)

    flow_test_lib.StartAndRunFlow(
        FlowWithMultipleResultTypes, client_id=self.client_id, creator=username)

    notifications = self.GetUserNotifications(username)

    self.assertIn("FlowWithMultipleResultTypes completed with 6 results",
                  notifications[0].message)


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
    super(FlowOutputPluginsTest, self).setUp()
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
      client_mock = hunt_test_lib.SampleHuntMock()

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

    self.assertTrue(
        "Plugin DummyFlowOutputPlugin successfully processed 1 flow replies." in
        log_messages)

  def testFlowLogsFailedOutputPluginProcessing(self):
    log_messages = self._RunFlowAndCollectLogs(output_plugins=[
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name="FailingDummyFlowOutputPlugin")
    ])
    self.assertTrue(
        "Plugin FailingDummyFlowOutputPlugin failed to process 1 replies "
        "due to: Oh no!" in log_messages)

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


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
