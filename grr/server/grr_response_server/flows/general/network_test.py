#!/usr/bin/env python
"""Test the connections listing module."""

import ipaddress

from absl import app

from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_proto import flows_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_test_utils
from grr_response_server.flows.general import network
from grr.test_lib import action_mocks
from grr.test_lib import db_test_lib
from grr.test_lib import flow_test_lib
from grr.test_lib import rrg_test_lib
from grr.test_lib import test_lib
from grr_response_proto import rrg_pb2
from grr_response_proto.rrg import net_pb2 as rrg_net_pb2
from grr_response_proto.rrg.action import list_connections_pb2 as rrg_list_connections_pb2


class ClientMock(action_mocks.ActionMock):

  def ListNetworkConnections(self, _):
    """Returns fake connections."""
    conn1 = rdf_client_network.NetworkConnection(
        state=rdf_client_network.NetworkConnection.State.CLOSED,
        type=rdf_client_network.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=22),
        remote_address=rdf_client_network.NetworkEndpoint(ip="0.0.0.0", port=0),
        pid=2136,
        ctime=0,
    )
    conn2 = rdf_client_network.NetworkConnection(
        state=rdf_client_network.NetworkConnection.State.LISTEN,
        type=rdf_client_network.NetworkConnection.Type.SOCK_STREAM,
        local_address=rdf_client_network.NetworkEndpoint(
            ip="192.168.1.1", port=31337
        ),
        remote_address=rdf_client_network.NetworkEndpoint(
            ip="1.2.3.4", port=6667
        ),
        pid=1,
        ctime=0,
    )

    return [conn1, conn2]


class NetstatFlowTest(flow_test_lib.FlowTestsBaseclass):
  """Test the process listing flow."""

  def testNetstat(self):
    """Test that the Netstat flow works."""
    client_id = self.SetupClient(0)
    session_id = flow_test_lib.StartAndRunFlow(
        network.Netstat,
        ClientMock(),
        client_id=client_id,
        creator=self.test_username,
    )

    # Check the results are correct.
    conns = flow_test_lib.GetUnpackedFlowResults(
        client_id, session_id, sysinfo_pb2.NetworkConnection
    )
    self.assertLen(conns, 2)
    self.assertEqual(conns[0].local_address.ip, "0.0.0.0")
    self.assertEqual(conns[0].local_address.port, 22)
    self.assertEqual(conns[1].local_address.ip, "192.168.1.1")
    self.assertEqual(conns[1].pid, 1)
    self.assertEqual(conns[1].remote_address.port, 6667)

  def testNetstatFilter(self):
    client_id = self.SetupClient(0)
    session_id = flow_test_lib.StartAndRunFlow(
        network.Netstat,
        ClientMock(),
        client_id=client_id,
        creator=self.test_username,
        flow_args=flows_pb2.NetstatArgs(
            listening_only=True,
        ),
    )

    # Check the results are correct.
    conns = flow_test_lib.GetUnpackedFlowResults(
        client_id, session_id, sysinfo_pb2.NetworkConnection
    )
    self.assertLen(conns, 1)
    self.assertEqual(conns[0].local_address.ip, "192.168.1.1")
    self.assertEqual(conns[0].pid, 1)
    self.assertEqual(conns[0].remote_address.port, 6667)
    self.assertEqual(conns[0].state, sysinfo_pb2.NetworkConnection.State.LISTEN)

  @db_test_lib.WithDatabase
  def testRRG(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def ListConnectionsHandler(session: rrg_test_lib.Session) -> None:
      result_v4 = rrg_list_connections_pb2.Result()
      result_v4_tcp = result_v4.connection.tcp
      result_v4_tcp.pid = 1337
      result_v4_tcp.state = rrg_net_pb2.ESTABLISHED
      result_v4_tcp.local_address.ip_address.octets = ipaddress.ip_address(
          "0.0.0.0",
      ).packed
      result_v4_tcp.local_address.port = 162342
      result_v4_tcp.remote_address.ip_address.octets = ipaddress.ip_address(
          "172.217.208.101",
      ).packed
      result_v4_tcp.remote_address.port = 80
      session.Reply(result_v4)

      result_v6 = rrg_list_connections_pb2.Result()
      result_v6_tcp = result_v6.connection.tcp
      result_v6_tcp.pid = 1338
      result_v6_tcp.state = rrg_net_pb2.LISTEN
      result_v6_tcp.local_address.ip_address.octets = ipaddress.ip_address(
          "::",
      ).packed
      result_v6_tcp.local_address.port = 481516
      result_v6_tcp.remote_address.ip_address.octets = ipaddress.ip_address(
          "2a00:1450:40::8a",
      ).packed
      result_v6_tcp.remote_address.port = 443
      session.Reply(result_v6)

      result_v4 = rrg_list_connections_pb2.Result()
      result_v4_udp = result_v4.connection.udp
      result_v4_udp.pid = 1339
      result_v4_udp.local_address.ip_address.octets = ipaddress.ip_address(
          "8.8.8.8",
      ).packed
      result_v4_udp.local_address.port = 53
      session.Reply(result_v4)

      result_v6 = rrg_list_connections_pb2.Result()
      result_v6_udp = result_v6.connection.udp
      result_v6_udp.pid = 1333
      result_v6_udp.local_address.ip_address.octets = ipaddress.ip_address(
          "21:60:4860::8888",
      ).packed
      result_v6_udp.local_address.port = 53
      session.Reply(result_v6)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=network.Netstat,
        flow_args=flows_pb2.NetstatArgs(),
        handlers={
            rrg_pb2.LIST_CONNECTIONS: ListConnectionsHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id,
        flow_id,
        sysinfo_pb2.NetworkConnection,
    )
    self.assertLen(results, 4)

    results_by_pid = {result.pid: result for result in results}

    self.assertEqual(
        results_by_pid[1337].family,
        sysinfo_pb2.NetworkConnection.INET,
    )
    self.assertEqual(
        results_by_pid[1337].type,
        sysinfo_pb2.NetworkConnection.SOCK_STREAM,
    )
    self.assertEqual(
        results_by_pid[1337].state,
        sysinfo_pb2.NetworkConnection.ESTABLISHED,
    )
    self.assertEqual(results_by_pid[1337].local_address.ip, "0.0.0.0")
    self.assertEqual(results_by_pid[1337].local_address.port, 162342)
    self.assertEqual(results_by_pid[1337].remote_address.ip, "172.217.208.101")
    self.assertEqual(results_by_pid[1337].remote_address.port, 80)

    self.assertEqual(
        results_by_pid[1338].family,
        sysinfo_pb2.NetworkConnection.INET6,
    )
    self.assertEqual(
        results_by_pid[1338].type,
        sysinfo_pb2.NetworkConnection.SOCK_STREAM,
    )
    self.assertEqual(
        results_by_pid[1338].state,
        sysinfo_pb2.NetworkConnection.LISTEN,
    )
    self.assertEqual(results_by_pid[1338].local_address.ip, "::")
    self.assertEqual(results_by_pid[1338].local_address.port, 481516)
    self.assertEqual(results_by_pid[1338].remote_address.ip, "2a00:1450:40::8a")
    self.assertEqual(results_by_pid[1338].remote_address.port, 443)

    self.assertEqual(
        results_by_pid[1339].family,
        sysinfo_pb2.NetworkConnection.INET,
    )
    self.assertEqual(
        results_by_pid[1339].type,
        sysinfo_pb2.NetworkConnection.SOCK_DGRAM,
    )
    self.assertEqual(results_by_pid[1339].local_address.ip, "8.8.8.8")
    self.assertEqual(results_by_pid[1339].local_address.port, 53)

    self.assertEqual(
        results_by_pid[1333].family,
        sysinfo_pb2.NetworkConnection.INET6,
    )
    self.assertEqual(
        results_by_pid[1333].type,
        sysinfo_pb2.NetworkConnection.SOCK_DGRAM,
    )
    self.assertEqual(results_by_pid[1333].local_address.ip, "21:60:4860::8888")
    self.assertEqual(results_by_pid[1333].local_address.port, 53)

  @db_test_lib.WithDatabase
  def testRRG_ListeningOnly(self, db: abstract_db.Database):
    client_id = db_test_utils.InitializeRRGClient(db)

    def ListConnectionsHandler(session: rrg_test_lib.Session) -> None:
      result_closed = rrg_list_connections_pb2.Result()
      result_closed_tcp = result_closed.connection.tcp
      result_closed_tcp.pid = 1337
      result_closed_tcp.state = rrg_net_pb2.CLOSED
      result_closed_tcp.local_address.ip_address.octets = ipaddress.ip_address(
          "0.0.0.0",
      ).packed
      result_closed_tcp.local_address.port = 162342
      result_closed_tcp.remote_address.ip_address.octets = ipaddress.ip_address(
          "172.217.208.101",
      ).packed
      result_closed_tcp.remote_address.port = 80
      session.Reply(result_closed)

      result_listen = rrg_list_connections_pb2.Result()
      result_listen_tcp = result_listen.connection.tcp
      result_listen_tcp.pid = 1338
      result_listen_tcp.state = rrg_net_pb2.LISTEN
      result_listen_tcp.local_address.ip_address.octets = ipaddress.ip_address(
          "::",
      ).packed
      result_listen_tcp.local_address.port = 481516
      result_listen_tcp.remote_address.ip_address.octets = ipaddress.ip_address(
          "2a00:1450:40::8a",
      ).packed
      result_listen_tcp.remote_address.port = 443
      session.Reply(result_listen)

    flow_id = rrg_test_lib.ExecuteFlow(
        client_id=client_id,
        flow_cls=network.Netstat,
        flow_args=flows_pb2.NetstatArgs(listening_only=True),
        handlers={
            rrg_pb2.LIST_CONNECTIONS: ListConnectionsHandler,
        },
    )

    flow_obj = db.ReadFlowObject(client_id, flow_id)
    self.assertEqual(flow_obj.backtrace, "")
    self.assertEqual(flow_obj.error_message, "")
    self.assertEqual(flow_obj.flow_state, flows_pb2.Flow.FINISHED)

    results = flow_test_lib.GetUnpackedFlowResults(
        client_id,
        flow_id,
        sysinfo_pb2.NetworkConnection,
    )
    self.assertLen(results, 1)
    self.assertEqual(results[0].family, sysinfo_pb2.NetworkConnection.INET6)
    self.assertEqual(results[0].type, sysinfo_pb2.NetworkConnection.SOCK_STREAM)
    self.assertEqual(results[0].state, sysinfo_pb2.NetworkConnection.LISTEN)
    self.assertEqual(results[0].local_address.ip, "::")
    self.assertEqual(results[0].local_address.port, 481516)
    self.assertEqual(results[0].remote_address.ip, "2a00:1450:40::8a")
    self.assertEqual(results[0].remote_address.port, 443)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
