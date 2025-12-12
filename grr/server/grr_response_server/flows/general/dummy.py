#!/usr/bin/env python
"""Flow that sends a message to the client and back as example."""

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import dummy_pb2
from grr_response_proto import flows_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs


class DummyArgs(rdf_structs.RDFProtoStruct):
  """Request for Dummy action."""

  protobuf = dummy_pb2.DummyArgs
  rdf_deps = []


class DummyFlowResult(rdf_structs.RDFProtoStruct):
  """Result for Dummy action."""

  protobuf = dummy_pb2.DummyFlowResult
  rdf_deps = []


class Dummy(
    flow_base.FlowBase[
        dummy_pb2.DummyArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """A mechanism to send a string to the client and back.

  Returns to parent flow:
    A DummyFlowResult with a modified string.
  """

  friendly_name = "Dummy Example Flow"
  category = "/Administrative/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  args_type = DummyArgs
  result_types = (DummyFlowResult,)

  proto_args_type = dummy_pb2.DummyArgs
  proto_result_types = (dummy_pb2.DummyFlowResult,)
  only_protos_allowed = True

  def Start(self):
    """Schedules the action in the client (Dummy ClientAction)."""

    if not self.proto_args.flow_input:
      raise ValueError("proto_args.flow_input is empty, cannot proceed!")

    request = dummy_pb2.DummyRequest(
        action_input=f"proto_args.flow_input: '{self.proto_args.flow_input}'"
    )
    self.CallClientProto(
        server_stubs.Dummy,
        request,
        next_state=self.ReceiveActionOutput.__name__,
    )

    self.Log("Finished Start.")

  @flow_base.UseProto2AnyResponses
  def ReceiveActionOutput(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    """Receives the action output and processes it."""
    # Checks the "Status" of the action, attaching information to the flow.A
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    if len(responses) != 1:
      raise flow_base.FlowError(
          "Oops, something weird happened. Expected a single response, but"
          f" got {list(responses)}"
      )

    response_any: any_pb2.Any = list(responses)[0]
    if not response_any.Is(dummy_pb2.DummyResult.DESCRIPTOR):
      raise flow_base.FlowError(
          f"Unexpected response type: '{response_any.type_url}'"
      )

    response = dummy_pb2.DummyResult()
    response.ParseFromString(response_any.value)

    result = dummy_pb2.DummyFlowResult(
        flow_output=f"responses.action_output: '{response.action_output}'"
    )
    self.SendReplyProto(result)

    self.Log("Finished ReceiveActionOutput.")
