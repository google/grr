#!/usr/bin/env python
"""Flows for listing running services."""

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import sysinfo_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs


class ListRunningServices(flow_base.FlowBase):
  """Flow that lists services (launchd jobs) running on the endpoint."""

  category = "/Processes/"
  behaviours = flow_base.BEHAVIOUR_BASIC
  result_types = (rdf_client.OSXServiceInformation,)

  proto_result_types = (sysinfo_pb2.OSXServiceInformation,)
  only_protos_allowed = True

  def Start(self):
    if self.client_os != "Darwin":
      raise flow_base.FlowError(f"Unsupported platform: {self.client_os}")

    self.CallClientProto(
        server_stubs.OSXEnumerateRunningServices,
        next_state=self._ProcessOSXEnumerateRunningServices.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessOSXEnumerateRunningServices(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(f"Failed to list services: {responses.status}")

    for response_any in responses:
      response = sysinfo_pb2.OSXServiceInformation()
      response.ParseFromString(response_any.value)
      self.SendReplyProto(response)
