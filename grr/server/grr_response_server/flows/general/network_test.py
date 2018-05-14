#!/usr/bin/env python
"""Test the connections listing module."""

from grr.lib import flags
from grr.lib.rdfvalues import client as rdf_client
from grr.server.grr_response_server import flow
from grr.server.grr_response_server.flows.general import network
from grr.test_lib import flow_test_lib
from grr.test_lib import test_lib


class ClientMock(object):

  def ListNetworkConnections(self, _):
    """Returns fake connections."""
    conn1 = rdf_client.NetworkConnection(
        state=rdf_client.NetworkConnection.State.CLOSED,
        type=rdf_client.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client.NetworkEndpoint(ip="0.0.0.0", port=22),
        remote_address=rdf_client.NetworkEndpoint(ip="0.0.0.0", port=0),
        pid=2136,
        ctime=0)
    conn2 = rdf_client.NetworkConnection(
        state=rdf_client.NetworkConnection.State.LISTEN,
        type=rdf_client.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client.NetworkEndpoint(ip="192.168.1.1", port=31337),
        remote_address=rdf_client.NetworkEndpoint(ip="1.2.3.4", port=6667),
        pid=1,
        ctime=0)

    return [conn1, conn2]


class NetstatFlowTest(flow_test_lib.FlowTestsBaseclass):
  """Test the process listing flow."""

  def testNetstat(self):
    """Test that the Netstat flow works."""
    session_id = flow_test_lib.TestFlowHelper(
        network.Netstat.__name__,
        ClientMock(),
        client_id=test_lib.TEST_CLIENT_ID,
        token=self.token)

    # Check the results are correct.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)
    conns = list(fd)
    self.assertEqual(len(conns), 2)
    self.assertEqual(conns[0].local_address.ip, "0.0.0.0")
    self.assertEqual(conns[0].local_address.port, 22)
    self.assertEqual(conns[1].local_address.ip, "192.168.1.1")
    self.assertEqual(conns[1].pid, 1)
    self.assertEqual(conns[1].remote_address.port, 6667)

  def testNetstatFilter(self):
    session_id = flow_test_lib.TestFlowHelper(
        network.Netstat.__name__,
        ClientMock(),
        client_id=test_lib.TEST_CLIENT_ID,
        listening_only=True,
        token=self.token)

    # Check the results are correct.
    fd = flow.GRRFlow.ResultCollectionForFID(session_id)
    conns = list(fd)
    self.assertEqual(len(conns), 1)
    self.assertEqual(conns[0].local_address.ip, "192.168.1.1")
    self.assertEqual(conns[0].pid, 1)
    self.assertEqual(conns[0].remote_address.port, 6667)
    self.assertEqual(conns[0].state, "LISTEN")


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
