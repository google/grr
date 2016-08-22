#!/usr/bin/env python
"""These are network related flows."""


from grr.lib import aff4
from grr.lib import flow
from grr.lib.aff4_objects import network


class Netstat(flow.GRRFlow):
  """List running processes on a system."""

  category = "/Network/"
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  @flow.StateHandler()
  def Start(self):
    """Start processing."""
    self.CallClient("Netstat", next_state="StoreNetstat")

  @flow.StateHandler()
  def StoreNetstat(self, responses):
    """Collect the connections and store in the datastore.

    Args:
      responses: A list of rdf_client.NetworkConnection objects.

    Raises:
      flow.FlowError: On failure to get retrieve the connections.
    """
    if not responses.success:
      raise flow.FlowError("Failed to get connections. Err: {0}".format(
          responses.status))

    self.state.urn = self.client_id.Add("network")
    net_fd = aff4.FACTORY.Create(
        self.state.urn, network.Network, token=self.token)
    conns = net_fd.Schema.CONNECTIONS()
    for response in responses:
      self.SendReply(response)
      conns.Append(response)

    self.state.conn_count = len(conns)

    net_fd.Set(conns)
    net_fd.Close()

  @flow.StateHandler()
  def End(self):
    self.Log("Successfully wrote %d connections.", self.state.conn_count)
    self.Notify("ViewObject", self.state.urn, "Listed Connections")
