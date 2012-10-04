#!/usr/bin/env python
# Copyright 2011 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""These are network related flows."""


from grr.lib import aff4
from grr.lib import flow
from grr.proto import sysinfo_pb2


class Netstat(flow.GRRFlow):
  """List running processes on a system."""

  category = "/Network/"

  @flow.StateHandler(next_state=["StoreNetstat"])
  def Start(self):
    """Start processing."""
    self.CallClient("Netstat", next_state="StoreNetstat")

  @flow.StateHandler(sysinfo_pb2.NetworkConnection)
  def StoreNetstat(self, responses):
    """Collect the connections and store in the datastore.

    Args:
      responses: A list of sysinfo_pb2.NetworkConnection objects.

    Raises:
      flow.FlowError: On failure to get retrieve the connections.
    """
    self.urn = aff4.ROOT_URN.Add(self.client_id).Add("network")
    net_fd = aff4.FACTORY.Create(self.urn, "Network", token=self.token)
    if responses.success:
      conns = net_fd.Schema.CONNECTIONS()
      for response in responses:
        conns.Append(response)
    else:
      raise flow.FlowError("Failed to get connections. Err: {0}".format(
          responses.status))
    self.conn_count = len(conns)

    net_fd.Set(conns)
    net_fd.Close()

  def End(self):
    self.Log("Successfully wrote %d connections.", self.conn_count)
    self.Notify("ViewObject", self.urn, "Listed Connections")
