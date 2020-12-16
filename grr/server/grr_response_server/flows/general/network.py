#!/usr/bin/env python
# Lint as: python3
"""These are network related flows."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import compatibility
from grr_response_proto import flows_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs


class NetstatArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.NetstatArgs


class Netstat(flow_base.FlowBase):
  """List active network connections on a system."""

  category = "/Network/"
  behaviours = flow_base.BEHAVIOUR_BASIC
  args_type = NetstatArgs

  def Start(self):
    """Start processing."""
    self.CallClient(
        server_stubs.ListNetworkConnections,
        listening_only=self.args.listening_only,
        next_state=compatibility.GetName(self.ValidateListNetworkConnections))

  def ValidateListNetworkConnections(
      self,
      responses: flow_responses.Responses,
  ) -> None:
    if not responses.success:
      # Most likely the client is old and doesn't have ListNetworkConnections.
      self.Log("%s", responses.status)

      # Fallback to Netstat.
      self.CallClient(
          server_stubs.Netstat,
          next_state=compatibility.GetName(self.StoreNetstat))
    else:
      self.CallStateInline(
          next_state=compatibility.GetName(self.StoreNetstat),
          responses=responses)

  def StoreNetstat(self, responses):
    """Collects the connections.

    Args:
      responses: A list of rdf_client_network.NetworkConnection objects.

    Raises:
      flow_base.FlowError: On failure to get retrieve the connections.
    """
    if not responses.success:
      raise flow_base.FlowError("Failed to get connections. Err: {0}".format(
          responses.status))

    for response in responses:
      if self.args.listening_only and response.state != "LISTEN":
        continue
      self.SendReply(response)

    self.state.conn_count = len(responses)

  def End(self, responses):
    del responses
    self.Log("Successfully wrote %d connections.", self.state.conn_count)
