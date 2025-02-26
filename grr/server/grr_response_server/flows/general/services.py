#!/usr/bin/env python
"""Flows for listing running services."""

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs


class ListRunningServices(flow_base.FlowBase):
  """Flow that lists services (launchd jobs) running on the endpoint."""

  category = "/Processes/"
  behaviours = flow_base.BEHAVIOUR_BASIC
  result_types = (rdf_client.OSXServiceInformation,)

  def Start(self):
    if self.client_os != "Darwin":
      raise flow_base.FlowError(f"Unsupported platform: {self.client_os}")

    self.CallClient(
        server_stubs.OSXEnumerateRunningServices,
        next_state=self._ProcessOSXEnumerateRunningServices.__name__,
    )

  def _ProcessOSXEnumerateRunningServices(
      self,
      responses: flow_responses.Responses[rdf_client.OSXServiceInformation],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(f"Failed to list services: {responses.status}")

    for response in responses:
      self.SendReply(response)
