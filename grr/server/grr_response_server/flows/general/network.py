#!/usr/bin/env python
"""These are network related flows."""

from grr.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr.server.grr_response_server import flow
from grr.server.grr_response_server import server_stubs


class NetstatArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.NetstatArgs


class Netstat(flow.GRRFlow):
  """List active network connections on a system."""

  category = "/Network/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"
  args_type = NetstatArgs

  @flow.StateHandler()
  def Start(self):
    """Start processing."""
    self.CallClient(
        server_stubs.ListNetworkConnections,
        listening_only=self.args.listening_only,
        next_state="ValidateListNetworkConnections")

  @flow.StateHandler()
  def ValidateListNetworkConnections(self, responses):
    if not responses.success:
      # Most likely the client is old and doesn't have ListNetworkConnections.
      self.Log(responses.status)

      # Fallback to Netstat.
      self.CallClient(server_stubs.Netstat, next_state="StoreNetstat")
    else:
      self.CallStateInline(next_state="StoreNetstat", responses=responses)

  @flow.StateHandler()
  def StoreNetstat(self, responses):
    """Collects the connections.

    Args:
      responses: A list of rdf_client.NetworkConnection objects.

    Raises:
      flow.FlowError: On failure to get retrieve the connections.
    """
    if not responses.success:
      raise flow.FlowError("Failed to get connections. Err: {0}".format(
          responses.status))

    for response in responses:
      if self.args.listening_only and response.state != "LISTEN":
        continue
      self.SendReply(response)

    self.state.conn_count = len(responses)

  @flow.StateHandler()
  def End(self):
    self.Log("Successfully wrote %d connections.", self.state.conn_count)
