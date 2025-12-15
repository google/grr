#!/usr/bin/env python
import random
from typing import Optional, Sequence
from unittest import mock

from absl import app
from absl.testing import absltest

from google.protobuf import any_pb2
from google.protobuf import message as message_pb2
from grr_response_client import actions
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import file_finder as rdf_file_finder
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server import action_registry
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import output_plugin
from grr_response_server import server_stubs
from grr_response_server import worker_lib
from grr_response_server.databases import db
from grr_response_server.flows import file
from grr_response_server.flows.general import dummy
from grr_response_server.flows.general import file_finder
from grr_response_server.output_plugins import test_plugins
from grr_response_server.rdfvalues import flow_objects as rdf_flow_objects
from grr_response_server.rdfvalues import mig_flow_objects
from grr_response_server.rdfvalues import mig_output_plugin
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


class CallStateFlowWithResponses(flow_base.FlowBase):
  """Test flow that calls its own state and passes responses."""

  # This is a global flag which will be set when the flow runs.
  success = False

  def Start(self) -> None:
    responses = [
        rdf_paths.PathSpec(
            path=f"/tmp/{i}.txt", pathtype=rdf_paths.PathSpec.PathType.OS
        )
        for i in range(10)
    ]
    self.CallState(
        next_state=self.ReceiveHello.__name__,
        responses=responses,
        # Calling the state a little in the future to avoid inline processing
        # done by the flow test library. Inline processing will break the
        # CallState logic: responses are written after requests, but the
        # inline processing is triggered already when requests are written.
        # Inline processing doesn't happen if flow requests are scheduled in
        # the future.
        start_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1s"),
    )

  def ReceiveHello(self, responses: flow_responses.Responses) -> None:
    if len(responses) != 10:
      raise RuntimeError(f"Expected 10 responses, got: {len(responses)}")

    for i, r in enumerate(sorted(responses, key=lambda x: x.path)):
      expected = rdf_paths.PathSpec(
          path=f"/tmp/{i}.txt", pathtype=rdf_paths.PathSpec.PathType.OS
      )
      if r != expected:
        raise RuntimeError(f"Unexpected response: {r}, expected: {expected}")

    CallStateFlowWithResponses.success = True


class CallStateProtoFlow(flow_base.FlowBase):
  """A flow that calls one of its own states."""

  # This is a global flag which will be set when the flow runs.
  success = False

  def Start(self):
    self.CallStateProto(next_state="ReceiveHello")

  def ReceiveHello(self, responses):
    del responses
    CallStateProtoFlow.success = True


class CallStateProtoFlowWithResponsesMixed(flow_base.FlowBase):
  """Test flow that calls its own state and passes responses."""

  # This is a global flag which will be set when the flow runs.
  success = False

  def Start(self) -> None:
    responses = [
        jobs_pb2.PathSpec(
            path=f"/tmp/{i}.txt", pathtype=jobs_pb2.PathSpec.PathType.OS
        )
        for i in range(10)
    ]
    self.CallStateProto(
        next_state=self.ReceiveHelloRDF.__name__,
        responses=responses,
        # Calling the state a little in the future to avoid inline processing
        # done by the flow test library. Inline processing will break the
        # CallStateProto logic: responses are written after requests, but the
        # inline processing is triggered already when requests are written.
        # Inline processing doesn't happen if flow requests are scheduled in
        # the future.
        start_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1s"),
    )

  def ReceiveHelloRDF(self, responses: flow_responses.Responses) -> None:
    if len(responses) != 10:
      raise RuntimeError(f"Expected 10 responses, got: {len(responses)}")

    for i, r in enumerate(sorted(responses, key=lambda x: x.path)):
      expected = jobs_pb2.PathSpec(
          path=f"/tmp/{i}.txt", pathtype=jobs_pb2.PathSpec.PathType.OS
      )
      # This method is not marked with @flow_base.UseProto2AnyResponses, so it
      # should not receive RDFValues.
      expected = mig_paths.ToRDFPathSpec(expected)
      if r != expected:
        raise RuntimeError(f"Unexpected response: {r}, expected: {expected}")

    CallStateProtoFlowWithResponsesMixed.success = True


class CallStateProtoFlowWithResponsesOnlyProtos(flow_base.FlowBase):
  """Test flow that calls its own state and passes responses."""

  # This is a global flag which will be set when the flow runs.
  success = False

  def Start(self) -> None:
    responses = [
        jobs_pb2.PathSpec(
            path=f"/tmp/{i}.txt", pathtype=jobs_pb2.PathSpec.PathType.OS
        )
        for i in range(10)
    ]
    self.CallStateProto(
        next_state=self.ReceiveHelloProto.__name__,
        responses=responses,
        # Calling the state a little in the future to avoid inline processing
        # done by the flow test library. Inline processing will break the
        # CallStateProto logic: responses are written after requests, but the
        # inline processing is triggered already when requests are written.
        # Inline processing doesn't happen if flow requests are scheduled in
        # the future.
        start_time=rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1s"),
    )

  @flow_base.UseProto2AnyResponses
  def ReceiveHelloProto(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    if len(responses) != 10:
      raise RuntimeError(f"Expected 10 responses, got: {len(responses)}")

    unpacked_responses = []
    for r in responses:
      unpacked = jobs_pb2.PathSpec()
      r.Unpack(unpacked)
      unpacked_responses.append(unpacked)

    for i, r in enumerate(sorted(unpacked_responses, key=lambda x: x.path)):
      expected = jobs_pb2.PathSpec(
          path=f"/tmp/{i}.txt", pathtype=jobs_pb2.PathSpec.PathType.OS
      )
      if r != expected:
        raise RuntimeError(
            f"Unexpected response: {unpacked}, expected: {expected}"
        )

    CallStateProtoFlowWithResponsesOnlyProtos.success = True


class FlowWithSingleProtoResult(flow_base.FlowBase):
  proto_result_types = (jobs_pb2.LogMessage,)

  def Start(self):
    self.SendReplyProto(jobs_pb2.LogMessage(data="Reply"))


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
    if (
        len(responses) != 2
        or "Child" not in str(responses[0])
        or "Hello" not in str(responses[1])
    ):
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
    self.CallFlow(
        "CallClientChildFlow",
        next_state=self._ProcessChildFlow.__name__,
    )

  def _ProcessChildFlow(self, responses) -> None:
    del responses  # Unused.


class CallClientChildFlow(flow_base.FlowBase):

  def Start(self):
    self.CallClient(
        server_stubs.GetPlatformInfo,
        next_state=self._ProcessGetPlatformInfo.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessGetPlatformInfo(self, responses) -> None:
    del responses  # Unused.


class CallClientProtoParentFlow(flow_base.FlowBase):

  def Start(self):
    self.CallFlowProto(
        "CallClientProtoChildFlow",
        next_state=self._ProcessChildFlow.__name__,
    )

  def _ProcessChildFlow(self, responses) -> None:
    del responses  # Unused.


class CallClientProtoChildFlow(flow_base.FlowBase):

  def Start(self):
    self.CallClientProto(
        server_stubs.GetPlatformInfo,
        next_state=self._ProcessGetPlatformInfo.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessGetPlatformInfo(self, responses) -> None:
    del responses  # Unused.


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
        next_state="IgnoreChildReplies",
    )

  def IgnoreChildReplies(self, responses):
    del responses  # Unused
    self.SendReply(rdfvalue.RDFString("Parent received"))


class FlowWithBrokenStart(flow_base.FlowBase):

  def Start(self):
    raise ValueError("boo")


class OPPWithArgs(output_plugin.OutputPluginProto):
  """A dummy output plugin that accepts arguments."""

  name = "OPPWithArgs"
  description = "Dummy output plugin with arguments."
  args_type = jobs_pb2.LogMessage

  args_during_init: list[jobs_pb2.LogMessage] = []

  def __init__(
      self,
      source_urn: Optional[rdfvalue.RDFURN] = None,
      args: Optional[jobs_pb2.LogMessage] = None,
  ):
    super().__init__(source_urn=source_urn, args=args)
    OPPWithArgs.args_during_init.append(args)

  def ProcessResults(self, replies: Sequence[flows_pb2.FlowResult]) -> None:
    pass


class OPPProcessResultsIncrements(output_plugin.OutputPluginProto):
  num_calls = 0
  num_responses = 0
  got_results = []

  def ProcessResults(self, results: Sequence[flows_pb2.FlowResult]):
    OPPProcessResultsIncrements.got_results.extend(results)
    OPPProcessResultsIncrements.num_calls += 1
    OPPProcessResultsIncrements.num_responses += len(list(results))
    self.Log(f"OPPProcessResultsIncrements: Processed {len(results)} replies.")


class OPPInitFails(output_plugin.OutputPluginProto):

  def __init__(
      self, source_urn: rdfvalue.RDFURN, args: Optional[message_pb2.Message]
  ):
    super().__init__(source_urn, args)
    raise RuntimeError("Oh no!")


class OPPProcessResultsFails(output_plugin.OutputPluginProto):

  def ProcessResults(self, results: Sequence[flows_pb2.FlowResult]):
    raise RuntimeError("Oh no!")


class RDFOPIncrementsOnProcessing(output_plugin.OutputPlugin):
  num_calls = 0
  num_responses = 0

  def ProcessResponses(self, state, responses):
    RDFOPIncrementsOnProcessing.num_calls += 1
    RDFOPIncrementsOnProcessing.num_responses += len(list(responses))


class RDFOPIncrementsState(output_plugin.OutputPlugin):
  """Stateful dummy hunt output plugin."""

  data = []
  num_calls = 0
  num_responses = 0

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.delta = 0

  def InitializeState(self, state):
    super().InitializeState(state)
    state.count = 0

  def ProcessResponses(self, state, responses):
    RDFOPIncrementsState.data.append(state.count + self.delta)
    RDFOPIncrementsState.num_calls += 1
    RDFOPIncrementsState.num_responses += len(list(responses))
    self.delta += 1

  def UpdateState(self, state):
    state.count += self.delta


class GetOutputPluginStatesTest(absltest.TestCase):

  def testGetOutputPluginStates(self):
    fake_plugin_1 = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=RDFOPIncrementsOnProcessing.__name__
    )
    fake_plugin_2 = rdf_output_plugin.OutputPluginDescriptor(
        plugin_name=RDFOPIncrementsState.__name__
    )

    states = flow.GetOutputPluginStates(
        [(5, fake_plugin_2), (0, fake_plugin_1)], source="tests"
    )

    self.assertLen(states, 2)

    self.assertEqual(states[0].plugin_id, "5")
    self.assertEqual(
        states[0].plugin_descriptor.plugin_name, fake_plugin_2.plugin_name
    )
    self.assertEqual(states[0].plugin_state, {"args": None, "count": 0})

    self.assertEqual(states[1].plugin_id, "0")
    self.assertEqual(
        states[1].plugin_descriptor.plugin_name, fake_plugin_1.plugin_name
    )
    self.assertEqual(states[1].plugin_state, {"args": None})


class FlowCreationTest(BasicFlowTest):
  """Test flow creation."""

  def testNotMatchingArgTypeRaises(self):
    """Check that flows reject not matching args type."""
    with self.assertRaises(TypeError):
      flow.StartFlow(
          client_id=self.client_id,
          flow_cls=CallStateFlow,
          flow_args=dummy.DummyArgs(),
          start_at=None,
      )

  def testDuplicateIDsAreNotAllowed(self):
    flow_id = flow.StartFlow(
        flow_cls=CallClientParentFlow,
        client_id=self.client_id,
        start_at=None,
    )
    with self.assertRaises(flow.CanNotStartFlowWithExistingIdError):
      flow.StartFlow(
          flow_cls=CallClientParentFlow,
          parent=flow.FlowParent.FromHuntID(flow_id),
          client_id=self.client_id,
          start_at=None,
      )

  def testDisableRRGSupport(self):
    flow_id = flow.StartFlow(
        flow_cls=ChildFlow,
        client_id=self.client_id,
        start_at=None,
        disable_rrg_support=True,
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertTrue(flow_obj.disable_rrg_support)

  def testDisableRRGSupport_Child(self):
    flow_id = flow.StartFlow(
        flow_cls=ParentFlow,
        client_id=self.client_id,
        start_at=None,
        disable_rrg_support=True,
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(
        client_id=self.client_id,
        flow_id=flow_id,
    )
    self.assertTrue(flow_obj.disable_rrg_support)

    child_flow_obj = data_store.REL_DB.ReadChildFlowObjects(
        client_id=self.client_id,
        flow_id=flow_id,
    )[0]
    self.assertTrue(child_flow_obj.disable_rrg_support)

  def testChildTermination(self):
    flow_id = flow.StartFlow(
        flow_cls=CallClientParentFlow,
        client_id=self.client_id,
        start_at=None,
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    client_flow_obj = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )[0]

    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.RUNNING)
    self.assertEqual(
        client_flow_obj.flow_state, flows_pb2.Flow.FlowState.RUNNING
    )

    # Terminate the parent flow.
    flow_base.TerminateFlow(self.client_id, flow_id, reason="Testing")

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    client_flow_obj = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )[0]

    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertEqual(client_flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)

  def testChildTerminationProto(self):
    flow_id = flow.StartFlow(
        flow_cls=CallClientProtoParentFlow,
        client_id=self.client_id,
        start_at=None,
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    client_flow_obj = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )[0]

    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.RUNNING)
    self.assertEqual(
        client_flow_obj.flow_state, flows_pb2.Flow.FlowState.RUNNING
    )

    # Terminate the parent flow.
    flow_base.TerminateFlow(self.client_id, flow_id, reason="Testing")

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    client_flow_obj = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )[0]

    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertEqual(client_flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)

  def testExceptionInStart(self):
    flow_id = flow.StartFlow(
        flow_cls=FlowWithBrokenStart,
        client_id=self.client_id,
        start_at=None,
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)

    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertEqual(flow_obj.error_message, "boo")
    self.assertIsNotNone(flow_obj.backtrace)

  @test_plugins.WithOutputPluginProto(OPPInitFails)
  def testStartFlowValidatesOutputPlugin(self):
    output_plugins = [
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name=OPPInitFails.__name__
        )
    ]
    with self.assertRaisesRegex(RuntimeError, "Oh no!"):
      flow.StartFlow(
          flow_cls=CallStateProtoFlow,
          client_id=self.client_id,
          output_plugins=output_plugins,
      )

  def testStartFlowWithRDFAndProtoOutputPluginsFails(self):
    rdf_op = [rdf_output_plugin.OutputPluginDescriptor(plugin_name="foo")]
    proto_op = [output_plugin_pb2.OutputPluginDescriptor(plugin_name="bar")]
    with self.assertRaisesRegex(ValueError, "Only one of"):
      flow.StartFlow(
          flow_cls=CallStateProtoFlow,
          client_id=self.client_id,
          output_plugins=rdf_op,
          proto_output_plugins=proto_op,
      )

  @test_plugins.WithOutputPluginProto(OPPWithArgs)
  def testStartFlowWithProtoOutputPlugin(self):
    args = jobs_pb2.LogMessage(data="args")
    any_args = any_pb2.Any()
    any_args.Pack(args)
    proto_op = [
        output_plugin_pb2.OutputPluginDescriptor(
            plugin_name=OPPWithArgs.__name__, args=any_args
        )
    ]

    flow_id = flow.StartFlow(
        flow_cls=CallStateProtoFlow,
        client_id=self.client_id,
        proto_output_plugins=proto_op,
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertLen(flow_obj.output_plugins, 1)
    self.assertEqual(
        flow_obj.output_plugins[0].plugin_name, OPPWithArgs.__name__
    )
    self.assertEqual(flow_obj.output_plugins[0].args.value, any_args.value)

  @test_plugins.WithOutputPluginProto(OPPInitFails)
  def testStartFlowValidatesProtoOutputPlugin(self):
    proto_output_plugins = [
        output_plugin_pb2.OutputPluginDescriptor(
            plugin_name=OPPInitFails.__name__
        )
    ]
    with self.assertRaisesRegex(RuntimeError, "Oh no!"):
      flow.StartFlow(
          flow_cls=CallStateProtoFlow,
          client_id=self.client_id,
          proto_output_plugins=proto_output_plugins,
      )


class GeneralFlowsTest(
    notification_test_lib.NotificationTestMixin,
    acl_test_lib.AclTestMixin,
    BasicFlowTest,
):
  """Tests some flows."""

  def testCallState(self):
    """Test the ability to chain flows."""
    CallStateFlow.success = False

    # Run the flow in the simulated way
    flow_test_lib.StartAndRunFlow(CallStateFlow, client_id=self.client_id)

    self.assertEqual(CallStateFlow.success, True)

  def testCallStateProto(self):
    """Test the ability to chain states."""
    CallStateProtoFlow.success = False
    # Run the flow in the simulated way
    flow_test_lib.StartAndRunFlow(CallStateProtoFlow, client_id=self.client_id)

    self.assertTrue(CallStateProtoFlow.success)

  def testCallStateWithResponses(self):
    """Test the ability to chain flows."""
    CallStateFlowWithResponses.success = False
    # Run the flow in the simulated way
    flow_test_lib.StartAndRunFlow(
        CallStateFlowWithResponses, client_id=self.client_id
    )
    self.assertTrue(CallStateFlowWithResponses.success)

  def testCallStateProtoWithResponsesMixed(self):
    """Test the ability to chain states."""
    CallStateProtoFlowWithResponsesMixed.success = False
    # Run the flow in the simulated way
    flow_test_lib.StartAndRunFlow(
        CallStateProtoFlowWithResponsesMixed, client_id=self.client_id
    )
    self.assertTrue(CallStateProtoFlowWithResponsesMixed.success)

  def testCallStateProtoWithResponsesOnlyProtos(self):
    """Test the ability to chain states."""
    CallStateProtoFlowWithResponsesOnlyProtos.success = False
    # Run the flow in the simulated way
    flow_test_lib.StartAndRunFlow(
        CallStateProtoFlowWithResponsesOnlyProtos, client_id=self.client_id
    )
    self.assertTrue(CallStateProtoFlowWithResponsesOnlyProtos.success)

  def testChainedFlow(self):
    """Test the ability to chain flows."""
    ParentFlow.success = False

    # Run the flow in the simulated way
    flow_test_lib.StartAndRunFlow(
        ParentFlow, client_mock=ClientMock(), client_id=self.client_id
    )

    self.assertEqual(ParentFlow.success, True)

  def testChainedFlowProto(self):
    class ParentCallFlowProto(flow_base.FlowBase):
      success = False

      def Start(self):
        self.CallFlowProto(
            "FlowWithSingleProtoResult", next_state="ParentReceiveHello"
        )

      def ParentReceiveHello(self, responses):
        responses = list(responses)
        if len(responses) != 1 or "Reply" not in str(responses[0]):
          raise RuntimeError("Messages not passed to parent")

        ParentCallFlowProto.success = True

    # Run the flow in the simulated way
    flow_test_lib.StartAndRunFlow(
        ParentCallFlowProto, client_mock=ClientMock(), client_id=self.client_id
    )

    self.assertEqual(ParentCallFlowProto.success, True)

  def testChainedFlowProto_WithFlowArgs(self):

    class ChildFlowTakesArgs(
        flow_base.FlowBase[
            flows_pb2.CollectFilesByKnownPathArgs,
            flows_pb2.DefaultFlowStore,
            flows_pb2.DefaultFlowProgress,
        ]
    ):
      args_type = rdf_file_finder.CollectFilesByKnownPathArgs
      proto_args_type = flows_pb2.CollectFilesByKnownPathArgs
      result_types = (rdf_client.LogMessage,)
      proto_result_types = (jobs_pb2.LogMessage,)
      banana = None
      batata = None

      def Start(self):
        ChildFlowTakesArgs.banana = self.args
        ChildFlowTakesArgs.batata = True
        assert self.args.paths == ["/foo"]
        self.SendReplyProto(jobs_pb2.LogMessage(data="foo"))

    class ParentCallFlowProtoWithArgs(flow_base.FlowBase):
      success = False

      def Start(self):
        self.CallFlowProto(
            ChildFlowTakesArgs.__name__,
            next_state="ParentReceiveHello",
            flow_args=flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]),
        )

      def ParentReceiveHello(
          self,
          responses: flow_responses.Responses[
              rdf_file_finder.CollectFilesByKnownPathArgs
          ],
      ):
        responses = list(responses)
        if len(responses) != 1 or "foo" not in str(responses[0]):
          raise RuntimeError(f"Messages not passed to parent: {responses}")

        ParentCallFlowProtoWithArgs.success = True

    # Run the flow in the simulated way
    flow_test_lib.StartAndRunFlow(
        ParentCallFlowProtoWithArgs,
        client_mock=ClientMock(),
        client_id=self.client_id,
    )

    self.assertEqual(ParentCallFlowProtoWithArgs.success, True)

  def testCallClientProto_WithCallback(self):

    class ActionSaysFoo(actions.ActionPlugin):
      in_proto = None
      out_rdfvalues = [rdf_client.LogMessage]

      def Run(self, _):
        self.SendReply(rdf_client.LogMessage(data="foo"))
        self.SendReply(rdf_client.LogMessage(data="bar"))

    action_registry.RegisterAdditionalTestClientAction(ActionSaysFoo)

    class ParentCallClientProtoWithCallback(flow_base.FlowBase):
      # Global class variables to track number of times called.
      callback_called_times = 0
      next_called_times = 0

      def Start(self):
        self.CallClientProto(
            ActionSaysFoo,
            callback_state=self.ParentReceiveOne.__name__,
            next_state="ParentReceiveAll",
        )

      @flow_base.UseProto2AnyResponsesCallback
      def ParentReceiveOne(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ):
        ParentCallClientProtoWithCallback.callback_called_times += 1
        res_text = str(list(responses))
        # Should contain EITHER "foo" or "bar".
        assert ("foo" in res_text) or ("bar" in res_text)

      @flow_base.UseProto2AnyResponsesCallback
      def ParentReceiveAll(
          self,
          responses: flow_responses.Responses[any_pb2.Any],
      ):
        ParentCallClientProtoWithCallback.next_called_times += 1
        res_text = str(list(responses))
        # Should contain BOTH "foo" and "bar".
        assert ("foo" in res_text) and ("bar" in res_text)

    # Run the flow in the simulated way
    flow_test_lib.StartAndRunFlow(
        ParentCallClientProtoWithCallback,
        client_mock=action_mocks.ActionMock.With(
            {"ActionSaysFoo": ActionSaysFoo}
        ),
        client_id=self.client_id,
    )

    self.assertEqual(ParentCallClientProtoWithCallback.callback_called_times, 2)
    self.assertEqual(ParentCallClientProtoWithCallback.next_called_times, 1)

  def testBrokenChainedFlow(self):
    BrokenParentFlow.success = False

    # Run the flow in the simulated way
    with test_lib.SuppressLogs():
      flow_test_lib.StartAndRunFlow(
          BrokenParentFlow,
          client_mock=ClientMock(),
          client_id=self.client_id,
          check_flow_errors=False,
      )

    self.assertEqual(BrokenParentFlow.success, True)

  def testBrokenChainedFlowProto(self):
    # TODO: Add child flow with arguments and check that they are
    # passed correctly from parent to child.
    class BrokenParentCallFlowProto(flow_base.FlowBase):
      """This flow will launch a broken child flow."""

      # This is a global flag which will be set when the flow runs.
      success = False

      def Start(self):
        # Call the child flow.
        self.CallFlowProto("BrokenChildFlow", next_state="ReceiveHello")

      def ReceiveHello(self, responses):
        if responses or responses.status.status == "OK":
          raise RuntimeError("Error not propagated to parent")

        BrokenParentCallFlowProto.success = True

    # The parent flow does not fail, just assert the child does.
    flow_test_lib.StartAndRunFlow(
        BrokenParentCallFlowProto,
        client_mock=ClientMock(),
        client_id=self.client_id,
        check_flow_errors=False,
    )

    self.assertEqual(BrokenParentCallFlowProto.success, True)

  def testCreatorPropagation(self):
    username = "original user"
    data_store.REL_DB.WriteGRRUser(username)

    client_mock = ClientMock()

    flow_id = flow_test_lib.StartAndRunFlow(
        flow_cls=ParentFlow,
        client_id=self.client_id,
        creator=username,
        client_mock=client_mock,
    )

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.creator, username)

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, flow_id
    )
    self.assertLen(child_flows, 1)
    child_flow = child_flows[0]

    self.assertEqual(child_flow.creator, username)

  def testLimitPropagation(self):
    """This tests that client actions are limited properly."""
    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[10],
        system_cpu_usage=[10],
        network_usage=[1000],
        runtime_us=[rdfvalue.Duration.From(1, rdfvalue.SECONDS)],
    )

    flow_test_lib.StartAndRunFlow(
        flow_test_lib.CPULimitFlow,
        client_mock=client_mock,
        client_id=self.client_id,
        cpu_limit=1000,
        network_bytes_limit=10000,
        runtime_limit=rdfvalue.Duration.From(5, rdfvalue.SECONDS),
    )

    self.assertEqual(client_mock.storage["cpulimit"], [1000, 980, 960])
    self.assertEqual(client_mock.storage["networklimit"], [10000, 9000, 8000])
    self.assertEqual(client_mock.storage["networklimit"], [10000, 9000, 8000])
    self.assertEqual(
        client_mock.storage["runtimelimit"],
        [
            rdfvalue.Duration.From(5, rdfvalue.SECONDS),
            rdfvalue.Duration.From(4, rdfvalue.SECONDS),
            rdfvalue.Duration.From(3, rdfvalue.SECONDS),
        ],
    )

  def testLimitPropagationProto(self):
    """This tests that client actions are limited properly."""
    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[10],
        system_cpu_usage=[10],
        network_usage=[1000],
        runtime_us=[rdfvalue.Duration.From(1, rdfvalue.SECONDS)],
    )

    flow_test_lib.StartAndRunFlow(
        flow_test_lib.CPULimitFlowProto,
        client_mock=client_mock,
        client_id=self.client_id,
        cpu_limit=1000,
        network_bytes_limit=10000,
        runtime_limit=rdfvalue.Duration.From(5, rdfvalue.SECONDS),
    )

    self.assertEqual(client_mock.storage["cpulimit"], [1000, 980, 960])
    self.assertEqual(client_mock.storage["networklimit"], [10000, 9000, 8000])
    self.assertEqual(client_mock.storage["networklimit"], [10000, 9000, 8000])
    self.assertEqual(
        client_mock.storage["runtimelimit"],
        [
            rdfvalue.Duration.From(5, rdfvalue.SECONDS),
            rdfvalue.Duration.From(4, rdfvalue.SECONDS),
            rdfvalue.Duration.From(3, rdfvalue.SECONDS),
        ],
    )

  def testCPULimitExceeded(self):
    """This tests that the cpu limit for flows is working."""
    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[10], system_cpu_usage=[10], network_usage=[1000]
    )

    with test_lib.SuppressLogs():
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_test_lib.CPULimitFlow,
          client_mock=client_mock,
          client_id=self.client_id,
          cpu_limit=30,
          network_bytes_limit=10000,
          check_flow_errors=False,
      )

    rdf_flow = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(rdf_flow.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertIn("CPU limit exceeded", rdf_flow.error_message)

  def testNetworkLimitExceeded(self):
    """This tests that the network limit for flows is working."""
    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[10], system_cpu_usage=[10], network_usage=[1000]
    )

    with test_lib.SuppressLogs():
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_test_lib.CPULimitFlow,
          client_mock=client_mock,
          client_id=self.client_id,
          cpu_limit=1000,
          network_bytes_limit=1500,
          check_flow_errors=False,
      )

    rdf_flow = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(rdf_flow.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertIn("bytes limit exceeded", rdf_flow.error_message)

  def testRuntimeLimitExceeded(self):
    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[1],
        system_cpu_usage=[1],
        network_usage=[1],
        runtime_us=[rdfvalue.Duration.From(4, rdfvalue.SECONDS)],
    )

    with test_lib.SuppressLogs():
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_test_lib.CPULimitFlow,
          client_mock=client_mock,
          client_id=self.client_id,
          runtime_limit=rdfvalue.Duration.From(9, rdfvalue.SECONDS),
          check_flow_errors=False,
      )

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertIn("Runtime limit exceeded", flow_obj.error_message)

  def testRuntimeLimitExceededProto(self):
    client_mock = action_mocks.CPULimitClientMock(
        user_cpu_usage=[1],
        system_cpu_usage=[1],
        network_usage=[1],
        runtime_us=[rdfvalue.Duration.From(4, rdfvalue.SECONDS)],
    )

    with test_lib.SuppressLogs():
      flow_id = flow_test_lib.StartAndRunFlow(
          flow_test_lib.CPULimitFlowProto,
          client_mock=client_mock,
          client_id=self.client_id,
          runtime_limit=rdfvalue.Duration.From(9, rdfvalue.SECONDS),
          check_flow_errors=False,
      )

    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.ERROR)
    self.assertIn("Runtime limit exceeded", flow_obj.error_message)

  def testUserGetsNotificationWithNumberOfResults(self):
    username = "notification_test_user"
    self.CreateUser(username)

    flow_test_lib.StartAndRunFlow(
        FlowWithMultipleResultTypes, client_id=self.client_id, creator=username
    )

    notifications = self.GetUserNotifications(username)

    self.assertIn(
        "FlowWithMultipleResultTypes completed with 6 results",
        notifications[0].message,
    )

  def testUserGetsNotificationWithNumberOfResultsProto(self):
    username = "notification_test_user"
    self.CreateUser(username)

    class FlowWithMultipleResultTypesProto(flow_base.FlowBase):
      """Flow with multiple result types."""

      proto_result_types = (
          jobs_pb2.LogMessage,
          jobs_pb2.PathSpec,
          jobs_pb2.ClientInformation,
      )

      def Start(self):
        self.SendReplyProto(jobs_pb2.LogMessage(data="foo"))
        self.SendReplyProto(jobs_pb2.PathSpec(path="bar.txt"))
        self.SendReplyProto(jobs_pb2.PathSpec(path="baz.txt"))
        self.SendReplyProto(jobs_pb2.ClientInformation(client_name="foo"))
        self.SendReplyProto(jobs_pb2.ClientInformation(client_name="bar"))
        self.SendReplyProto(jobs_pb2.ClientInformation(client_name="baz"))

    flow_test_lib.StartAndRunFlow(
        FlowWithMultipleResultTypesProto,
        client_id=self.client_id,
        creator=username,
    )

    notifications = self.GetUserNotifications(username)

    self.assertIn(
        "FlowWithMultipleResultTypesProto completed with 6 results",
        notifications[0].message,
    )

  def testNestedFlowsHaveTheirResultsSaved(self):
    # Run the flow in the simulated way
    parent_flow_id = flow_test_lib.StartAndRunFlow(
        ParentFlow, client_mock=ClientMock(), client_id=self.client_id
    )

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, parent_flow_id
    )
    self.assertLen(child_flows, 1)

    child_flow_results = flow_test_lib.GetFlowResults(
        self.client_id, child_flows[0].flow_id
    )
    self.assertNotEmpty(child_flow_results)

  def testNestedFlowsHaveTheirResultsSavedProtos(self):
    class ParentFlowProto(flow_base.FlowBase):
      success = False

      def Start(self):
        self.CallFlowProto("ChildFlowProto", next_state="ParentReceiveHello")

      @flow_base.UseProto2AnyResponses
      def ParentReceiveHello(self, responses):
        unpacked_responses = []
        for response_any in responses:
          r = jobs_pb2.LogMessage()
          response_any.Unpack(r)
          unpacked_responses.append(r)

        assert len(unpacked_responses) == 2
        assert "Child" in str(unpacked_responses[0])
        assert "Hello" in str(unpacked_responses[1])

        ParentFlowProto.success = True

    class ChildFlowProto(flow_base.FlowBase):
      success = False
      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        self.SendReplyProto(jobs_pb2.LogMessage(data="Child"))
        self.SendReplyProto(jobs_pb2.LogMessage(data="Hello"))
        ChildFlowProto.success = True

    # Run the flow in the simulated way
    parent_flow_id = flow_test_lib.StartAndRunFlow(
        ParentFlowProto, client_mock=ClientMock(), client_id=self.client_id
    )

    self.assertTrue(ParentFlowProto.success)
    self.assertTrue(ChildFlowProto.success)

    child_flows = data_store.REL_DB.ReadChildFlowObjects(
        self.client_id, parent_flow_id
    )
    self.assertLen(child_flows, 1)

    child_flow_results = flow_test_lib.GetFlowResults(
        self.client_id, child_flows[0].flow_id
    )
    self.assertLen(child_flow_results, 2)


class NoRequestChildFlow(flow_base.FlowBase):
  """This flow just returns and does not generate any requests."""

  def Start(self):
    return


class NoRequestParentFlow(flow_base.FlowBase):

  child_flow = "NoRequestChildFlow"

  def Start(self):
    self.CallFlow(
        self.child_flow,
        next_state=self._ProcessChildFlow.__name__,
    )

  def _ProcessChildFlow(self, responses) -> None:
    del responses  # Unused.


class FlowOutputPluginsTest(BasicFlowTest):

  def setUp(self):
    super().setUp()
    test_output_plugins.DummyFlowOutputPlugin.num_calls = 0
    test_output_plugins.DummyFlowOutputPlugin.num_responses = 0

  def RunFlow(
      self,
      flow_cls=None,
      output_plugins=None,
      flow_args=None,
      client_mock=None,
  ):
    flow_cls = flow_cls or file_finder.FileFinder

    if flow_args is None and flow_cls == file_finder.FileFinder:
      flow_args = rdf_file_finder.FileFinderArgs(paths=["/tmp/evil.txt"])

    if client_mock is None:
      client_mock = hunt_test_lib.SampleHuntMock(failrate=2)

    flow_urn = flow_test_lib.StartAndRunFlow(
        flow_cls,
        client_mock=client_mock,
        client_id=self.client_id,
        flow_args=flow_args,
        output_plugins=output_plugins,
    )

    return flow_urn

  def testFlowWithoutOutputPluginsCompletes(self):
    self.RunFlow()

  def testRDFFlow_RDFOutputPlugin_NoResultsCompletes(self):
    self.RunFlow(
        flow_cls=NoRequestParentFlow,
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin"
            )
        ],
    )
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 0)

  @test_plugins.WithOutputPluginProto(OPPProcessResultsIncrements)
  def testRDFFlow_ProtoOutputPlugin_NoResultsCompletes(self):
    OPPProcessResultsIncrements.num_calls = 0

    flow_test_lib.StartAndRunFlow(
        NoRequestParentFlow,
        client_mock=ClientMock(),
        client_id=self.client_id,
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsIncrements.__name__,
            )
        ],
    )

    self.assertEqual(OPPProcessResultsIncrements.num_calls, 0)

  def testFlowWithOutputPluginProcessesResultsSuccessfully(self):
    self.RunFlow(
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin"
            )
        ]
    )
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)

  @test_plugins.WithOutputPluginProto(OPPProcessResultsIncrements)
  def testProtoFlow_ProtoOutputPlugin_ProcessesResultsSuccessfully(self):
    OPPProcessResultsIncrements.num_calls = 0
    OPPProcessResultsIncrements.num_responses = 0

    self.RunFlow(
        flow_cls=FlowWithSingleProtoResult,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsIncrements.__name__
            )
        ],
    )
    self.assertEqual(OPPProcessResultsIncrements.num_calls, 1)
    self.assertEqual(OPPProcessResultsIncrements.num_responses, 1)

  def testProtoFlow_RDFOutputPlugin_ProcessesResultsSuccessfully(self):

    class FlowWithOutputPluginProtos(flow_base.FlowBase):
      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        self.SendReplyProto(jobs_pb2.LogMessage(data="To process 1"))
        self.SendReplyProto(jobs_pb2.LogMessage(data="To process 2"))

    self.RunFlow(
        flow_cls=FlowWithOutputPluginProtos,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin"
            )
        ],
    )
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 2)

  @test_plugins.WithOutputPluginProto(OPPProcessResultsIncrements)
  def testProtoFlow_ProtoOutputPlugin_ProcessesResultsSuccessfully2(self):
    OPPProcessResultsIncrements.num_calls = 0
    OPPProcessResultsIncrements.num_responses = 0
    OPPProcessResultsIncrements.got_results = []

    class FlowWithTwoSendReplyProto(flow_base.FlowBase):
      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        self.SendReplyProto(jobs_pb2.LogMessage(data="To process 1"))
        self.SendReplyProto(jobs_pb2.LogMessage(data="To process 2"))

    flow_id = self.RunFlow(
        flow_cls=FlowWithTwoSendReplyProto,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsIncrements.__name__
            )
        ],
    )
    self.assertEqual(OPPProcessResultsIncrements.num_calls, 1)
    self.assertEqual(OPPProcessResultsIncrements.num_responses, 2)

    res1 = flows_pb2.FlowResult(
        client_id=self.client_id, flow_id=flow_id, hunt_id=""
    )
    res1.payload.Pack(jobs_pb2.LogMessage(data="To process 1"))
    res2 = flows_pb2.FlowResult(
        client_id=self.client_id, flow_id=flow_id, hunt_id=""
    )
    res2.payload.Pack(jobs_pb2.LogMessage(data="To process 2"))

    self.assertEqual(
        OPPProcessResultsIncrements.got_results,
        [res1, res2],
    )

  def _RunFlowAndCollectLogs(self, output_plugins):
    log_lines = []
    with mock.patch.object(flow_base.FlowBase, "Log") as log_f:
      self.RunFlow(output_plugins=output_plugins)

      for args in log_f.call_args_list:
        log_lines.append(args[0][0] % args[0][1:])
    return log_lines

  def testFlowLogsSuccessfulOutputPluginProcessing(self):
    log_messages = self._RunFlowAndCollectLogs(
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin"
            )
        ]
    )

    self.assertIn(
        "Plugin"
        f" {rdf_output_plugin.OutputPluginDescriptor(plugin_name=test_output_plugins.DummyFlowOutputPlugin.__name__)} (id:"
        " 0) successfully processed 1 flow replies.",
        log_messages,
    )

  @test_plugins.WithOutputPluginProto(OPPProcessResultsIncrements)
  def testFlowLogsSuccessfulOutputPluginProcessing_OPProto(self):
    log_messages = self._RunFlowAndCollectLogs(
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsIncrements.__name__
            )
        ]
    )

    self.assertIn(
        "Plugin"
        f" <<{output_plugin_pb2.OutputPluginDescriptor(plugin_name=OPPProcessResultsIncrements.__name__)}>>"
        " (id: 0) successfully processed 1 flow replies.",
        log_messages,
    )

  def testFlowLogsSuccessfulOutputPluginProcessingProtos(self):
    flow_id = self.RunFlow(
        flow_cls=FlowWithSingleProtoResult,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin"
            )
        ],
    )

    flow_logs = data_store.REL_DB.ReadFlowLogEntries(
        self.client_id,
        flow_id,
        offset=0,
        count=10,
    )
    self.assertLen(flow_logs, 1)
    self.assertIn(
        "Plugin"
        f" {rdf_output_plugin.OutputPluginDescriptor(plugin_name=test_output_plugins.DummyFlowOutputPlugin.__name__)} (id:"
        " 0) successfully processed 1 flow replies.",
        flow_logs[0].message,
    )

  @test_plugins.WithOutputPluginProto(OPPProcessResultsIncrements)
  def testFlowLogsSuccessfulOutputPluginProcessingProtos_OPProtos(self):
    OPPProcessResultsIncrements.num_calls = 0
    OPPProcessResultsIncrements.num_responses = 0

    flow_id = self.RunFlow(
        flow_cls=FlowWithSingleProtoResult,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsIncrements.__name__
            )
        ],
    )

    flow_logs = data_store.REL_DB.ReadFlowLogEntries(
        self.client_id,
        flow_id,
        offset=0,
        count=10,
    )
    self.assertLen(flow_logs, 1)
    self.assertIn(
        "Plugin"
        f" <<{output_plugin_pb2.OutputPluginDescriptor(plugin_name=OPPProcessResultsIncrements.__name__)}>>"
        " (id: 0) successfully processed 1 flow replies.",
        flow_logs[0].message,
    )

  def testFlowLogsFailedOutputPluginProcessing(self):
    log_messages = self._RunFlowAndCollectLogs(
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="FailingDummyFlowOutputPlugin"
            )
        ]
    )
    self.assertIn(
        "Plugin FailingDummyFlowOutputPlugin failed to process 1 replies "
        "due to: Oh no!",
        log_messages,
    )

  @test_plugins.WithOutputPluginProto(OPPProcessResultsFails)
  def testFlowLogsFailedOutputPluginProcessingOPProtos(self):
    log_messages = self._RunFlowAndCollectLogs(
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsFails.__name__
            )
        ]
    )
    self.assertIn(
        "Plugin OPPProcessResultsFails failed to "
        "process 1 replies due to: Oh no!",
        log_messages,
    )

  def testFlowLogsFailedOutputPluginProcessingProtos(self):
    flow_id = self.RunFlow(
        flow_cls=FlowWithSingleProtoResult,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="FailingDummyFlowOutputPlugin"
            )
        ],
    )

    flow_logs = data_store.REL_DB.ReadFlowLogEntries(
        self.client_id,
        flow_id,
        offset=0,
        count=10,
    )
    self.assertLen(flow_logs, 1)
    self.assertIn(
        "Plugin FailingDummyFlowOutputPlugin failed to process 1 replies "
        "due to: Oh no!",
        flow_logs[0].message,
    )

  @test_plugins.WithOutputPluginProto(OPPProcessResultsFails)
  def testFlowLogsFailedOutputPluginProcessingProtos_OPProto(self):
    flow_id = self.RunFlow(
        flow_cls=FlowWithSingleProtoResult,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsFails.__name__
            )
        ],
    )

    flow_logs = data_store.REL_DB.ReadFlowLogEntries(
        self.client_id,
        flow_id,
        offset=0,
        count=10,
    )
    self.assertLen(flow_logs, 1)
    self.assertIn(
        "Plugin OPPProcessResultsFails failed to"
        " process 1 replies due to: Oh no!",
        flow_logs[0].message,
    )

  def testRDFFlowDoesNotFailWhenOutputPluginFails(self):
    flow_id = self.RunFlow(
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="FailingDummyFlowOutputPlugin"
            )
        ]
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @test_plugins.WithOutputPluginProto(OPPProcessResultsFails)
  def testRDFFlowDoesNotFailWhenProtoOutputPluginFails(self):
    flow_id = self.RunFlow(
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsFails.__name__
            )
        ]
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  def testProtoFlowDoesNotFailWhenOutputPluginFails(self):
    flow_id = self.RunFlow(
        flow_cls=FlowWithSingleProtoResult,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="FailingDummyFlowOutputPlugin"
            )
        ],
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  @test_plugins.WithOutputPluginProto(OPPProcessResultsFails)
  def testProtoFlowDoesNotFailWhenProtoOutputPluginFails(self):
    flow_id = self.RunFlow(
        flow_cls=FlowWithSingleProtoResult,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsFails.__name__
            )
        ],
    )
    flow_obj = data_store.REL_DB.ReadFlowObject(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FlowState.FINISHED)

  def testFailingPluginDoesNotImpactOtherPluginsRDFFlow(self):
    self.RunFlow(
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="FailingDummyFlowOutputPlugin"
            ),
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin"
            ),
        ]
    )

    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)

  def testFailingPluginDoesNotImpactOtherPluginsProtoFlow(self):
    self.RunFlow(
        flow_cls=FlowWithSingleProtoResult,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="FailingDummyFlowOutputPlugin"
            ),
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin"
            ),
        ],
    )

    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)

  @test_plugins.WithOutputPluginProto(OPPProcessResultsFails)
  @test_plugins.WithOutputPluginProto(OPPProcessResultsIncrements)
  def testFailingPluginDoesNotImpactOtherPluginsProtoFlow_ProtoPlugin(self):
    OPPProcessResultsIncrements.num_calls = 0
    OPPProcessResultsIncrements.num_responses = 0

    self.RunFlow(
        flow_cls=FlowWithSingleProtoResult,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsFails.__name__
            ),
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsIncrements.__name__
            ),
        ],
    )

    self.assertEqual(OPPProcessResultsIncrements.num_calls, 1)
    self.assertEqual(OPPProcessResultsIncrements.num_responses, 1)

  @test_plugins.WithOutputPluginProto(OPPWithArgs)
  def testProcessRepliesWithOutputPluginProtoWithArgs(self):
    OPPWithArgs.args_during_init = []

    args = jobs_pb2.LogMessage(data="args")
    any_args = any_pb2.Any()
    any_args.Pack(args)
    desc = output_plugin_pb2.OutputPluginDescriptor(
        plugin_name=OPPWithArgs.__name__,
        args=any_args,
    )
    self.RunFlow(
        flow_cls=FlowWithSingleProtoResult,
        client_mock=ClientMock(),
        output_plugins=[mig_output_plugin.ToRDFOutputPluginDescriptor(desc)],
    )

    # Init should be called twice, once when starting the flow in `flow.py` and
    # another when processing the replies in `flow_base.py`.
    self.assertCountEqual(
        OPPWithArgs.args_during_init,
        [jobs_pb2.LogMessage(data="args"), jobs_pb2.LogMessage(data="args")],
    )

  def testOutputPluginsOnlyRunInParentFlow_DoesNotForward(self):
    self.RunFlow(
        flow_cls=ParentFlowWithoutForwardingOutputPlugins,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin"
            )
        ],
    )

    # Parent calls once, and child doesn't call.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    # Parent has one response, child has two.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)

  @test_plugins.WithOutputPluginProto(OPPProcessResultsIncrements)
  def testOutputPluginsOnlyRunInParentFlow_DoesNotForward_OPProto(self):
    OPPProcessResultsIncrements.num_calls = 0
    OPPProcessResultsIncrements.num_responses = 0

    class ChildFlowProtoIgnored1(flow_base.FlowBase):
      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        self.SendReplyProto(jobs_pb2.LogMessage(data="IgnoredInParent"))

    class ParentFlowWithoutForwardingOutputPluginsProto1(flow_base.FlowBase):
      """This flow creates a Child without forwarding OutputPlugins."""

      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        # Call the child flow WITHOUT output plugins.
        self.CallFlowProto(
            ChildFlowProtoIgnored1.__name__, next_state="IgnoreChildReplies"
        )

      def IgnoreChildReplies(self, responses):
        del responses  # Unused
        self.SendReplyProto(jobs_pb2.LogMessage(data="Parent received"))

    self.RunFlow(
        flow_cls=ParentFlowWithoutForwardingOutputPluginsProto1,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsIncrements.__name__
            )
        ],
    )

    # Parent calls once, and child doesn't call.
    self.assertEqual(OPPProcessResultsIncrements.num_calls, 1)
    # Parent has one response, child has two.
    self.assertEqual(OPPProcessResultsIncrements.num_responses, 1)

  def testOutputPluginsOnlyRunInParentFlow_DoesNotForwardProto(self):
    class ChildFlowProtoIgnored(flow_base.FlowBase):
      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        self.SendReplyProto(jobs_pb2.LogMessage(data="IgnoredInParent"))

    class ParentFlowWithoutForwardingOutputPluginsProto(flow_base.FlowBase):
      """This flow creates a Child without forwarding OutputPlugins."""

      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        # Call the child flow WITHOUT output plugins.
        self.CallFlowProto(
            ChildFlowProtoIgnored.__name__, next_state="IgnoreChildReplies"
        )

      def IgnoreChildReplies(self, responses):
        del responses  # Unused
        self.SendReplyProto(jobs_pb2.LogMessage(data="Parent received"))

    self.RunFlow(
        flow_cls=ParentFlowWithoutForwardingOutputPluginsProto,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin"
            )
        ],
    )

    # Parent calls once, and child doesn't call.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    # Parent has one response, child has two.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)

  @test_plugins.WithOutputPluginProto(OPPProcessResultsIncrements)
  def testOutputPluginsOnlyRunInParentFlow_DoesNotForwardProto_OPProto(self):
    OPPProcessResultsIncrements.num_calls = 0
    OPPProcessResultsIncrements.num_responses = 0

    class ChildFlowProtoIgnored2(flow_base.FlowBase):
      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        self.SendReplyProto(jobs_pb2.LogMessage(data="IgnoredInParent"))

    class ParentFlowWithoutForwardingOutputPluginsProto2(flow_base.FlowBase):
      """This flow creates a Child without forwarding OutputPlugins."""

      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        # Call the child flow WITHOUT output plugins.
        self.CallFlowProto(
            ChildFlowProtoIgnored2.__name__, next_state="IgnoreChildReplies"
        )

      def IgnoreChildReplies(self, responses):
        del responses  # Unused
        self.SendReplyProto(jobs_pb2.LogMessage(data="Parent received"))

    self.RunFlow(
        flow_cls=ParentFlowWithoutForwardingOutputPluginsProto2,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsIncrements.__name__
            )
        ],
    )

    # Parent calls once, and child doesn't call.
    self.assertEqual(OPPProcessResultsIncrements.num_calls, 1)
    # Parent has one response, child has two.
    self.assertEqual(OPPProcessResultsIncrements.num_responses, 1)

  def testOutputPluginsOnlyRunInParentFlow_Forwards(self):
    self.RunFlow(
        flow_cls=ParentFlowWithForwardedOutputPlugins,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin"
            )
        ],
    )

    # Parent calls once, and child doesn't call.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    # Parent has one response, child has two.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)

  @test_plugins.WithOutputPluginProto(OPPProcessResultsIncrements)
  def testOutputPluginsOnlyRunInParentFlow_Forwards_OPProto(self):
    # This case documents the current behavior. Even if output plugins are
    # forwarded to the child flow, the child flow does NOT call the plugin.
    OPPProcessResultsIncrements.num_calls = 0
    OPPProcessResultsIncrements.num_responses = 0

    class ChildFlowProtoIgnored3(flow_base.FlowBase):
      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        self.SendReplyProto(jobs_pb2.LogMessage(data="IgnoredInParent"))
        self.SendReplyProto(jobs_pb2.LogMessage(data="IgnoredInParent_2"))

    class ParentFlowWithForwardedOutputPluginsProto3(flow_base.FlowBase):
      """This flow creates a Child with forwarding OutputPlugins."""

      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        # Call the child flow WITH output plugins.
        self.CallFlowProto(
            ChildFlowProtoIgnored3.__name__,
            output_plugins=self.rdf_flow.output_plugins,
            next_state="IgnoreChildReplies",
        )

      def IgnoreChildReplies(self, responses):
        del responses  # Unused
        self.SendReplyProto(jobs_pb2.LogMessage(data="Parent received"))

    self.RunFlow(
        flow_cls=ParentFlowWithForwardedOutputPluginsProto3,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name=OPPProcessResultsIncrements.__name__
            )
        ],
    )

    # Parent calls once, and child doesn't call.
    self.assertEqual(OPPProcessResultsIncrements.num_calls, 1)
    # Parent has one response, child has two.
    self.assertEqual(OPPProcessResultsIncrements.num_responses, 1)

  def testOutputPluginsOnlyRunInParentFlow_ForwardsProto(self):
    class ChildFlowProtoIgnored2Replies(flow_base.FlowBase):
      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        self.SendReplyProto(jobs_pb2.LogMessage(data="IgnoredInParent_1"))
        self.SendReplyProto(jobs_pb2.LogMessage(data="IgnoredInParent_2"))

    class ParentFlowWithForwardedOutputPluginsProto(flow_base.FlowBase):
      proto_result_types = (jobs_pb2.LogMessage,)

      def Start(self):
        # Calls the child flow WITH output plugins.
        self.CallFlowProto(
            ChildFlowProtoIgnored2Replies.__name__,
            output_plugins=self.rdf_flow.output_plugins,
            next_state="IgnoreChildReplies",
        )

      def IgnoreChildReplies(self, responses):
        del responses  # Unused
        self.SendReplyProto(jobs_pb2.LogMessage(data="Parent received"))

    self.RunFlow(
        flow_cls=ParentFlowWithForwardedOutputPluginsProto,
        client_mock=ClientMock(),
        output_plugins=[
            rdf_output_plugin.OutputPluginDescriptor(
                plugin_name="DummyFlowOutputPlugin"
            )
        ],
    )

    # Parent calls once, and child doesn't call.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_calls, 1)
    # Parent has one response, child has two.
    self.assertEqual(test_output_plugins.DummyFlowOutputPlugin.num_responses, 1)

  @test_plugins.WithOutputPluginProto(OPPProcessResultsIncrements)
  def testRDFAndProtoOutputPlugins(self):
    RDFOPIncrementsOnProcessing.num_calls = 0
    RDFOPIncrementsOnProcessing.num_responses = 0

    RDFOPIncrementsState.data = []
    RDFOPIncrementsState.num_calls = 0
    RDFOPIncrementsState.num_responses = 0

    OPPProcessResultsIncrements.num_calls = 0
    OPPProcessResultsIncrements.num_responses = 0
    OPPProcessResultsIncrements.got_results = []

    output_plugins = [
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name=RDFOPIncrementsOnProcessing.__name__
        ),
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name=RDFOPIncrementsState.__name__
        ),
        rdf_output_plugin.OutputPluginDescriptor(
            plugin_name=OPPProcessResultsIncrements.__name__
        ),
    ]

    flow_id = self.RunFlow(
        flow_cls=FlowWithSingleProtoResult,
        client_mock=ClientMock(),
        output_plugins=output_plugins,
    )

    self.assertEqual(RDFOPIncrementsOnProcessing.num_calls, 1)
    self.assertEqual(RDFOPIncrementsOnProcessing.num_responses, 1)
    self.assertEqual(RDFOPIncrementsState.num_calls, 1)
    self.assertEqual(RDFOPIncrementsState.num_responses, 1)
    self.assertEqual(RDFOPIncrementsState.data, [0])
    self.assertEqual(OPPProcessResultsIncrements.num_calls, 1)
    self.assertEqual(OPPProcessResultsIncrements.num_responses, 1)

    flow_logs = data_store.REL_DB.ReadFlowLogEntries(
        self.client_id,
        flow_id,
        offset=0,
        count=100,
    )
    flow_log_msgs = [l.message for l in flow_logs]
    self.assertIn(
        "Plugin"
        f" {rdf_output_plugin.OutputPluginDescriptor(plugin_name=RDFOPIncrementsOnProcessing.__name__)} (id:"
        " 0) successfully processed 1 flow replies.",
        flow_log_msgs,
    )
    self.assertIn(
        "Plugin"
        f" {rdf_output_plugin.OutputPluginDescriptor(plugin_name=RDFOPIncrementsState.__name__)} (id:"
        " 1) successfully processed 1 flow replies.",
        flow_log_msgs,
    )
    self.assertIn(
        "Plugin"
        f" <<{output_plugin_pb2.OutputPluginDescriptor(plugin_name=OPPProcessResultsIncrements.__name__)}>>"
        " (id: 2) successfully processed 1 flow replies.",
        flow_log_msgs,
    )

    plugin_logs = data_store.REL_DB.ReadAllFlowOutputPluginLogEntries(
        self.client_id, flow_id, offset=0, count=100
    )
    # We write 1 log entry for each plugin, and OPP should write an extra one.
    self.assertLen(plugin_logs, 4)
    logs_without_timestamps = []
    for log in plugin_logs:
      log_without_timestamp = flows_pb2.FlowOutputPluginLogEntry()
      log_without_timestamp.CopyFrom(log)
      log_without_timestamp.ClearField("timestamp")
      logs_without_timestamps.append(log_without_timestamp)
    self.assertCountEqual(
        logs_without_timestamps,
        [
            flows_pb2.FlowOutputPluginLogEntry(
                client_id=self.client_id,
                flow_id=flow_id,
                hunt_id="",
                output_plugin_id="0",
                log_entry_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
                message="Processed 1 replies.",
            ),
            flows_pb2.FlowOutputPluginLogEntry(
                client_id=self.client_id,
                flow_id=flow_id,
                hunt_id="",
                output_plugin_id="1",
                log_entry_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
                message="Processed 1 replies.",
            ),
            flows_pb2.FlowOutputPluginLogEntry(
                client_id=self.client_id,
                flow_id=flow_id,
                hunt_id="",
                output_plugin_id="2",
                log_entry_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
                message="Processed 1 replies.",
            ),
            flows_pb2.FlowOutputPluginLogEntry(
                client_id=self.client_id,
                flow_id=flow_id,
                hunt_id="",
                output_plugin_id="2",
                log_entry_type=flows_pb2.FlowOutputPluginLogEntry.LogEntryType.LOG,
                message="OPPProcessResultsIncrements: Processed 1 replies.",
            ),
        ],
    )


class ScheduleFlowTest(flow_test_lib.FlowTestsBaseclass):

  def SetupUser(self, username="u0"):
    data_store.REL_DB.WriteGRRUser(username)
    return username

  def ScheduleFlow(
      self,
      client_id: str,
      creator: str,
      flow_name: Optional[str] = None,
      flow_args: Optional[message_pb2.Message] = None,
      runner_args: Optional[flows_pb2.FlowRunnerArgs] = None,
  ) -> flows_pb2.ScheduledFlow:
    if flow_name is None:
      flow_name = file.CollectFilesByKnownPath.__name__

    if not flow_args:
      flow_args = flows_pb2.CollectFilesByKnownPathArgs(
          paths=["/foo{}".format(random.randint(0, 1000))]
      )

    if not runner_args:
      runner_args = flows_pb2.FlowRunnerArgs(cpu_limit=random.randint(0, 60))

    any_flow_args = any_pb2.Any()
    any_flow_args.Pack(flow_args)

    return flow.ScheduleFlow(
        client_id=client_id,
        creator=creator,
        flow_name=flow_name,
        flow_args=any_flow_args,
        runner_args=runner_args,
    )

  def testScheduleFlowCreatesMultipleScheduledFlows(self):
    client_id0 = self.SetupClient(0)
    client_id1 = self.SetupClient(1)
    username0 = self.SetupUser("u0")
    username1 = self.SetupUser("u1")

    self.ScheduleFlow(client_id=client_id0, creator=username0)
    self.ScheduleFlow(client_id=client_id0, creator=username0)
    self.ScheduleFlow(client_id=client_id1, creator=username0)
    self.ScheduleFlow(client_id=client_id0, creator=username1)

    results = flow.ListScheduledFlows(client_id0, username0)
    self.assertLen(results, 2)
    self.assertEqual(results[0].client_id, client_id0)
    self.assertEqual(results[1].client_id, client_id0)
    self.assertEqual(results[0].creator, username0)
    self.assertEqual(results[1].creator, username0)

    results = flow.ListScheduledFlows(client_id1, username0)
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id1)
    self.assertEqual(results[0].creator, username0)

    results = flow.ListScheduledFlows(client_id0, username1)
    self.assertLen(results, 1)
    self.assertEqual(results[0].client_id, client_id0)
    self.assertEqual(results[0].creator, username1)

  def testStartScheduledFlowsCreatesFlow(self):
    client_id = self.SetupClient(0)
    username = self.SetupUser("u0")

    self.ScheduleFlow(
        client_id=client_id,
        creator=username,
        flow_name=file.CollectFilesByKnownPath.__name__,
        flow_args=flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]),
        runner_args=flows_pb2.FlowRunnerArgs(cpu_limit=60),
    )

    flow.StartScheduledFlows(client_id, username)

    flows = data_store.REL_DB.ReadAllFlowObjects(client_id)
    self.assertLen(flows, 1)

    self.assertEqual(flows[0].client_id, client_id)
    self.assertEqual(flows[0].creator, username)
    self.assertEqual(
        flows[0].flow_class_name, file.CollectFilesByKnownPath.__name__
    )
    rdf_flow = mig_flow_objects.ToRDFFlow(flows[0])
    self.assertEqual(rdf_flow.args.paths, ["/foo"])
    self.assertEqual(
        flows[0].flow_state, rdf_flow_objects.Flow.FlowState.RUNNING
    )
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
        flow_name=file.CollectFilesByKnownPath.__name__,
        flow_args=flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]),
        runner_args=flows_pb2.FlowRunnerArgs(cpu_limit=60),
    )

    with mock.patch.object(
        file.CollectFilesByKnownPath,
        "__init__",
        side_effect=ValueError("foobazzle"),
    ):
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
        flow_name=file.CollectFilesByKnownPath.__name__,
        flow_args=flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]),
        runner_args=flows_pb2.FlowRunnerArgs(cpu_limit=60),
    )

    with mock.patch.object(
        rdf_file_finder.CollectFilesByKnownPathArgs,
        "Validate",
        side_effect=ValueError("foobazzle"),
    ):
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
        flow_name=file.CollectFilesByKnownPath.__name__,
        flow_args=flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]),
        runner_args=flows_pb2.FlowRunnerArgs(cpu_limit=60),
    )

    self.ScheduleFlow(
        client_id=client_id,
        creator=username,
        flow_name=file.CollectFilesByKnownPath.__name__,
        flow_args=flows_pb2.CollectFilesByKnownPathArgs(paths=["/foo"]),
        runner_args=flows_pb2.FlowRunnerArgs(cpu_limit=60),
    )

    with mock.patch.object(
        rdf_file_finder.CollectFilesByKnownPathArgs,
        "Validate",
        side_effect=[ValueError("foobazzle"), mock.DEFAULT],
    ):
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
        flow.random, "Id64", return_value=0xF0F1F2F3F4F5F6F7
    ):
      self.assertEqual(flow.RandomFlowId(), "F0F1F2F3F4F5F6F7")

    with mock.patch.object(flow.random, "Id64", return_value=0):
      self.assertEqual(flow.RandomFlowId(), "0000000000000000")

    with mock.patch.object(flow.random, "Id64", return_value=1):
      self.assertEqual(flow.RandomFlowId(), "0000000000000001")

    with mock.patch.object(
        flow.random, "Id64", return_value=0x0000000100000000
    ):
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
              name=message.name,
              response_id=i + 1,
              payload=r,
              type=rdf_flows.GrrMessage.Type.MESSAGE,
          )
      )

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
        next_state=self.ReceiveHello.__name__,
    )

  def ReceiveHelloCallback(self, responses):
    # Relay each message when it comes.
    for r in responses:
      self.SendReply(r)

  def ReceiveHello(self, responses):
    # Relay all incoming messages once more (but prefix the strings).
    for response in responses:
      self.SendReply(rdfvalue.RDFString("Final: " + str(response)))


class ReturnHelloLogClientAction(actions.ActionPlugin):
  """A test client action."""

  in_proto = None
  out_rdfvalues = [rdf_client.LogMessage]

  def Run(self, _):
    self.SendReply(rdf_client.LogMessage(data="Hello World"))


action_registry.RegisterAdditionalTestClientAction(ReturnHelloLogClientAction)


class ReturnHelloLogWithoutStatusClientMock(action_mocks.ActionMock):
  """A mock for testing resource limits."""

  NUM_INCREMENTAL_RESPONSES = 2

  def HandleMessage(self, message):
    responses = [
        rdf_client.LogMessage(data=f"Hello World {i}")
        for i in range(self.NUM_INCREMENTAL_RESPONSES)
    ]

    messages = []
    for i, r in enumerate(responses):
      messages.append(
          rdf_flows.GrrMessage(
              session_id=message.session_id,
              request_id=message.request_id,
              name=message.name,
              response_id=i + 1,
              payload=r,
              type=rdf_flows.GrrMessage.Type.MESSAGE,
          )
      )

    return messages


class FlowWithIncrementalCallbackProto(flow_base.FlowBase):
  """This flow will be called by our parent."""

  proto_result_types = [jobs_pb2.LogMessage]

  # These are global flags
  callback_state_called_times = 0
  next_state_called_times = 0

  def Start(self):
    self.CallClientProto(
        ReturnHelloLogClientAction,
        callback_state=self.ReceiveHelloCallback.__name__,
        next_state=self.ReceiveHello.__name__,
    )

  @flow_base.UseProto2AnyResponsesCallback
  def ReceiveHelloCallback(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ):
    FlowWithIncrementalCallbackProto.callback_state_called_times += 1
    # Relay each message when it comes.
    for response_any in responses:
      assert response_any.Is(jobs_pb2.LogMessage.DESCRIPTOR)
      response = jobs_pb2.LogMessage()
      response_any.Unpack(response)
      self.SendReplyProto(
          jobs_pb2.LogMessage(data=f"callback_state: {response.data}")
      )

  @flow_base.UseProto2AnyResponses
  def ReceiveHello(self, responses: flow_responses.Responses[any_pb2.Any]):
    FlowWithIncrementalCallbackProto.next_state_called_times += 1
    # Relay all incoming messages once more (but prefix the strings).
    for response_any in responses:
      assert response_any.Is(jobs_pb2.LogMessage.DESCRIPTOR)
      response = jobs_pb2.LogMessage()
      response_any.Unpack(response)
      self.SendReplyProto(
          jobs_pb2.LogMessage(data=f"next_state: {response.data}")
      )


class IncrementalResponseHandlingTest(BasicFlowTest):

  def testIncrementalCallbackReturnsResultsBeforeStatus_Proto(self):
    """Tests (callback state + proto responses - status message) works.

    This test case makes sure that the callback state is called independent
    of the status being sent. The class uses the proto annotations which should
    alter the response types sent, but not the callback behavior.
    """
    flow_id = flow_test_lib.StartAndRunFlow(
        FlowWithIncrementalCallbackProto,
        client_mock=ReturnHelloLogWithoutStatusClientMock(),
        client_id=self.client_id,
        # Set check_flow_errors to False, otherwise test runner will complain
        # that the flow has finished in the RUNNING state.
        check_flow_errors=False,
    )
    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.RUNNING)

    self.assertEqual(
        FlowWithIncrementalCallbackProto.callback_state_called_times,
        ReturnHelloLogWithoutStatusClientMock.NUM_INCREMENTAL_RESPONSES,
    )

    results = data_store.REL_DB.ReadFlowResults(self.client_id, flow_id, 0, 50)
    self.assertLen(
        results, ReturnHelloLogWithoutStatusClientMock.NUM_INCREMENTAL_RESPONSES
    )

    for i in range(
        ReturnHelloLogWithoutStatusClientMock.NUM_INCREMENTAL_RESPONSES
    ):
      result = jobs_pb2.LogMessage()
      results[i].payload.Unpack(result)

      self.assertEqual(result.data, f"callback_state: Hello World {i}")

  @mock.patch.object(FlowWithIncrementalCallback, "ReceiveHelloCallback")
  def testIncrementalCallbackReturnsResultsBeforeStatus(self, m):
    # Mocks don't have names by default.
    m.__name__ = "ReceiveHelloCallback"
    # Because mocks automagically create non-existing properties, we have to set
    # explicitly `_proto2_any_responses` to falsy value.
    m._proto2_any_responses = False
    m._proto2_any_responses_callback = False

    flow_id = flow_test_lib.StartAndRunFlow(
        FlowWithIncrementalCallback,
        client_mock=NotSendingStatusClientMock(),
        client_id=self.client_id,
        # Set check_flow_errors to False, otherwise test runner will complain
        # that the flow has finished in the RUNNING state.
        check_flow_errors=False,
    )
    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.RUNNING)

    self.assertEqual(
        m.call_count, NotSendingStatusClientMock.NUM_INCREMENTAL_RESPONSES
    )
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
        check_flow_errors=False,
    )

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
        check_flow_errors=False,
    )
    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.RUNNING)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertListEqual(
        results,
        [
            rdfvalue.RDFString(f"Hello World {i}")
            for i in range(NotSendingStatusClientMock.NUM_INCREMENTAL_RESPONSES)
        ],
    )

  def testIncrementalCallbackIsCalledWithResponsesInRightOrder(self):
    flow_id = flow_test_lib.StartAndRunFlow(
        FlowWithIncrementalCallback,
        client_mock=NotSendingStatusClientMock(shuffle=True),
        client_id=self.client_id,
        # Set check_flow_errors to False, otherwise test runner will complain
        # that the flow has finished in the RUNNING state.
        check_flow_errors=False,
    )

    flow_obj = flow_test_lib.GetFlowObj(self.client_id, flow_id)
    self.assertEqual(flow_obj.flow_state, flow_obj.FlowState.RUNNING)

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertListEqual(
        results,
        [
            rdfvalue.RDFString(f"Hello World {i}")
            for i in range(NotSendingStatusClientMock.NUM_INCREMENTAL_RESPONSES)
        ],
    )

  def testIncrementalCallbackIsCalledWhenAllResponsesArriveAtOnce(self):
    flow_id = flow_test_lib.StartAndRunFlow(
        FlowWithIncrementalCallback,
        client_mock=ClientMock(),
        client_id=self.client_id,
    )

    results = flow_test_lib.GetFlowResults(self.client_id, flow_id)
    self.assertListEqual(
        results,
        [
            rdfvalue.RDFString("Hello World"),
            rdfvalue.RDFString("Final: Hello World"),
        ],
    )


class WorkerTest(BasicFlowTest):

  def testRaisesIfFlowProcessingRequestDoesNotTriggerAnyProcessing(self):
    with flow_test_lib.TestWorker() as worker:
      flow_id = flow.StartFlow(
          flow_cls=CallClientParentFlow,
          client_id=self.client_id,
          start_at=None,
      )
      fpr = flows_pb2.FlowProcessingRequest(
          client_id=self.client_id, flow_id=flow_id
      )
      with self.assertRaises(worker_lib.FlowHasNothingToProcessError):
        worker.ProcessFlow(fpr)

  def testRaisesIfFlowProcessingRequestDoesNotTriggerAnyProcessingProto(self):
    with flow_test_lib.TestWorker() as worker:
      flow_id = flow.StartFlow(
          flow_cls=CallClientProtoParentFlow,
          client_id=self.client_id,
          start_at=None,
      )
      fpr = flows_pb2.FlowProcessingRequest(
          client_id=self.client_id, flow_id=flow_id
      )
      with self.assertRaises(worker_lib.FlowHasNothingToProcessError):
        worker.ProcessFlow(fpr)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
