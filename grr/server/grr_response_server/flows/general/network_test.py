#!/usr/bin/env python
"""Test the connections listing module."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from grr_response_core.lib import flags
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_server.flows.general import network
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ClientMock(action_mocks.ActionMock):

  def ListNetworkConnections(self, _):
    """Returns fake connections."""
    conn1 = rdf_client_network.NetworkConnection(
        state=rdf_client_network.NetworkConnection.State.CLOSED,
        type=rdf_client_network.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=22),
        remote_address=rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=0),
        pid=2136,
        ctime=0)
    conn2 = rdf_client_network.NetworkConnection(
        state=rdf_client_network.NetworkConnection.State.LISTEN,
        type=rdf_client_network.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client_network.NetworkEndpoint(
            ip="192.168.1.1", port=31337),
        remote_address=rdf_client_network.NetworkEndpoint(
            ip="1.2.3.4", port=6667),
        pid=1,
        ctime=0)

    return [conn1, conn2]


@db_test_lib.DualDBTest
class NetstatFlowTest(flow_test_lib.FlowTestsBaseclass):
  """Test the process listing flow."""

  def testNetstat(self):
    """Test that the Netstat flow works."""
    client_id = self.SetupClient(0)
    session_id = flow_test_lib.TestFlowHelper(
        network.Netstat.__name__,
        ClientMock(),
        client_id=client_id,
        token=self.token)

    # Check the results are correct.
    conns = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(conns, 2)
    self.assertEqual(conns[0].local_address.ip, "0.0.0.0")
    self.assertEqual(conns[0].local_address.port, 22)
    self.assertEqual(conns[1].local_address.ip, "192.168.1.1")
    self.assertEqual(conns[1].pid, 1)
    self.assertEqual(conns[1].remote_address.port, 6667)

  def testNetstatFilter(self):
    client_id = self.SetupClient(0)
    session_id = flow_test_lib.TestFlowHelper(
        network.Netstat.__name__,
        ClientMock(),
        client_id=client_id,
        listening_only=True,
        token=self.token)

    # Check the results are correct.
    conns = flow_test_lib.GetFlowResults(client_id, session_id)
    self.assertLen(conns, 1)
    self.assertEqual(conns[0].local_address.ip, "192.168.1.1")
    self.assertEqual(conns[0].pid, 1)
    self.assertEqual(conns[0].remote_address.port, 6667)
    self.assertEqual(conns[0].state, "LISTEN")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
