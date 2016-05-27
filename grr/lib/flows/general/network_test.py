#!/usr/bin/env python
"""Test the connections listing module."""

from grr.lib import aff4
from grr.lib import flags
from grr.lib import test_lib
from grr.lib.aff4_objects import aff4_grr
# pylint: disable=unused-import
from grr.lib.flows.general import network
# pylint: enable=unused-import
from grr.lib.rdfvalues import client as rdf_client


class NetstatTest(test_lib.FlowTestsBaseclass):
  """Test the process listing flow."""

  def testNetstat(self):
    """Test that the Netstat flow works."""

    class ClientMock(object):

      def Netstat(self, _):
        """Returns fake connections."""
        conn1 = rdf_client.NetworkConnection(
            state=rdf_client.NetworkConnection.State.LISTEN,
            type=rdf_client.NetworkConnection.Type.SOCK_STREAM,
            local_address=rdf_client.NetworkEndpoint(ip="0.0.0.0",
                                                     port=22),
            remote_address=rdf_client.NetworkEndpoint(ip="0.0.0.0",
                                                      port=0),
            pid=2136,
            ctime=0)
        conn2 = rdf_client.NetworkConnection(
            state=rdf_client.NetworkConnection.State.LISTEN,
            type=rdf_client.NetworkConnection.Type.SOCK_STREAM,
            local_address=rdf_client.NetworkEndpoint(ip="192.168.1.1",
                                                     port=31337),
            remote_address=rdf_client.NetworkEndpoint(ip="1.2.3.4",
                                                      port=6667),
            pid=1,
            ctime=0)

        return [conn1, conn2]

    # Set the system to Windows so the netstat flow will run as its the only
    # one that works at the moment.
    fd = aff4.FACTORY.Create(self.client_id,
                             aff4_grr.VFSGRRClient,
                             token=self.token)
    fd.Set(fd.Schema.SYSTEM("Windows"))
    fd.Close()

    for _ in test_lib.TestFlowHelper("Netstat",
                                     ClientMock(),
                                     client_id=self.client_id,
                                     token=self.token):
      pass

    # Check the output file is created
    fd = aff4.FACTORY.Open(self.client_id.Add("network"), token=self.token)
    conns = fd.Get(fd.Schema.CONNECTIONS)

    self.assertEqual(len(conns), 2)
    self.assertEqual(conns[0].local_address.ip, "0.0.0.0")
    self.assertEqual(conns[0].local_address.port, 22)
    self.assertEqual(conns[1].local_address.ip, "192.168.1.1")
    self.assertEqual(conns[1].pid, 1)
    self.assertEqual(conns[1].remote_address.port, 6667)


def main(argv):
  # Run the full test suite
  test_lib.GrrTestProgram(argv=argv)


if __name__ == "__main__":
  flags.StartMain(main)
