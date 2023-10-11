#!/usr/bin/env python
"""Flow that sends a message to the client and back as example."""

from grr_response_core.lib.rdfvalues import dummy as rdf_dummy
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import dummy_pb2
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


class Dummy(flow_base.FlowBase):
  """A mechanism to send a string to the client and back.

  Returns to parent flow:
    A DummyFlowResult with a modified string.
  """

  friendly_name = "Dummy Example Flow"
  category = "/Administrative/"
  behaviours = flow_base.BEHAVIOUR_DEBUG

  args_type = DummyArgs
  result_types = (DummyFlowResult,)

  def Start(self):
    """Schedules the action in the client (Dummy ClientAction)."""

    if not self.args.flow_input:
      raise ValueError("args.flow_input is empty, cannot proceed!")

    request = rdf_dummy.DummyRequest(
        action_input=f"args.flow_input: '{self.args.flow_input}'"
    )
    self.CallClient(
        server_stubs.Dummy,
        request,
        next_state=self.ReceiveActionOutput.__name__,
    )

    self.Log("Finished Start.")

  def ReceiveActionOutput(
      self, responses: flow_responses.Responses[rdf_dummy.DummyResult]
  ):
    """Receives the action output and processes it."""
    # Checks the "Status" of the action, attaching information to the flow.A
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    if len(responses) != 1:
      raise flow_base.FlowError(
          "Oops, something weird happened. Expected a single response, but"
          f" got {list(responses)}"
      )

    result = DummyFlowResult(
        flow_output=(
            f"responses.action_output: '{list(responses)[0].action_output}'"
        )
    )
    self.SendReply(result)

    self.Log("Finished ReceiveActionOutput.")
