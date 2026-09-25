#!/usr/bin/env python
"""These are network related flows."""

import ipaddress

from google.protobuf import any_pb2
from grr_response_proto import flows_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_proto.rrg import net_pb2 as rrg_net_pb2
from grr_response_proto.rrg.action import list_connections_pb2 as rrg_list_connections_pb2


class Netstat(
    flow_base.FlowBase[
        flows_pb2.NetstatArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """List active network connections on a system."""

  category = "/Network/"
  behaviours = flow_base.BEHAVIOUR_BASIC

  proto_args_type = flows_pb2.NetstatArgs
  proto_result_types = (sysinfo_pb2.NetworkConnection,)

  def Start(self):
    """Start processing."""
    if (
        # Enum comparison in RRG filters is supported since version 0.0.11.
        self.rrg_version >= (0, 0, 11)
        or (self.rrg_support and not self.proto_args.listening_only)
    ):
      list_connections = rrg_stubs.ListConnections()

      if self.proto_args.listening_only:
        tcp_state_listen_cond = list_connections.AddFilter().conditions.add()
        tcp_state_listen_cond.int64_equal = rrg_net_pb2.LISTEN
        tcp_state_listen_cond.field.extend([
            rrg_list_connections_pb2.Result.CONNECTION_FIELD_NUMBER,
            rrg_net_pb2.Connection.TCP_FIELD_NUMBER,
            rrg_net_pb2.TcpConnection.STATE_FIELD_NUMBER,
        ])

      list_connections.Call(self._ProcessListConnections)
      return

    self.CallClientProto(
        server_stubs.ListNetworkConnections,
        flows_pb2.ListNetworkConnectionsArgs(
            listening_only=self.proto_args.listening_only,
        ),
        next_state=self.StoreNetstat.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessListConnections(
      self,
      responses_any: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses_any.success:
      raise flow_base.FlowError(
          f"Failed to list connections: {responses_any.status}",
      )

    for response_any in responses_any:
      response = rrg_list_connections_pb2.Result()
      response.ParseFromString(response_any.value)

      result = sysinfo_pb2.NetworkConnection()

      if response.connection.HasField("tcp"):
        tcp = response.connection.tcp

        result.pid = tcp.pid
        result.type = sysinfo_pb2.NetworkConnection.SOCK_STREAM

        ip_local = ipaddress.ip_address(tcp.local_address.ip_address.octets)
        ip_remote = ipaddress.ip_address(tcp.remote_address.ip_address.octets)

        result.local_address.ip = str(ip_local)
        result.local_address.port = tcp.local_address.port
        result.remote_address.ip = str(ip_remote)
        result.remote_address.port = tcp.remote_address.port

        if isinstance(ip_local, ipaddress.IPv4Address):
          result.family = sysinfo_pb2.NetworkConnection.INET
        elif isinstance(ip_local, ipaddress.IPv6Address):
          result.family = sysinfo_pb2.NetworkConnection.INET6
        else:
          raise ValueError(f"Unexpected TCP local IP address: {ip_local}")

        result.state = {
            rrg_net_pb2.ESTABLISHED: sysinfo_pb2.NetworkConnection.ESTABLISHED,
            rrg_net_pb2.SYN_SENT: sysinfo_pb2.NetworkConnection.SYN_SENT,
            rrg_net_pb2.SYN_RECEIVED: sysinfo_pb2.NetworkConnection.SYN_RECV,
            rrg_net_pb2.FIN_WAIT_1: sysinfo_pb2.NetworkConnection.FIN_WAIT1,
            rrg_net_pb2.FIN_WAIT_2: sysinfo_pb2.NetworkConnection.FIN_WAIT2,
            rrg_net_pb2.TIME_WAIT: sysinfo_pb2.NetworkConnection.TIME_WAIT,
            rrg_net_pb2.CLOSED: sysinfo_pb2.NetworkConnection.CLOSED,
            rrg_net_pb2.CLOSE_WAIT: sysinfo_pb2.NetworkConnection.CLOSE_WAIT,
            rrg_net_pb2.LAST_ACK: sysinfo_pb2.NetworkConnection.LAST_ACK,
            rrg_net_pb2.LISTEN: sysinfo_pb2.NetworkConnection.LISTEN,
            rrg_net_pb2.CLOSING: sysinfo_pb2.NetworkConnection.CLOSING,
        }[tcp.state]
      elif response.connection.HasField("udp"):
        udp = response.connection.udp

        result.pid = udp.pid
        result.type = sysinfo_pb2.NetworkConnection.SOCK_DGRAM

        ip_local = ipaddress.ip_address(udp.local_address.ip_address.octets)

        result.local_address.ip = str(ip_local)
        result.local_address.port = udp.local_address.port

        if isinstance(ip_local, ipaddress.IPv4Address):
          result.family = sysinfo_pb2.NetworkConnection.INET
        elif isinstance(ip_local, ipaddress.IPv6Address):
          result.family = sysinfo_pb2.NetworkConnection.INET6
        else:
          raise ValueError(f"Unexpected UDP local IP address: {ip_local}")
      else:
        raise ValueError(f"Unexpected connection: {response.connection}")

      self.SendReplyProto(result)

  @flow_base.UseProto2AnyResponses
  def StoreNetstat(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    """Collects the connections.

    Args:
      responses: A list of rdf_client_network.NetworkConnection objects.

    Raises:
      flow_base.FlowError: On failure to get retrieve the connections.
    """
    if not responses.success:
      raise flow_base.FlowError(
          "Failed to get connections. Err: {0}".format(responses.status)
      )

    for response_any in responses:
      response = sysinfo_pb2.NetworkConnection()
      response_any.Unpack(response)
      if (
          self.proto_args.listening_only
          and response.state != sysinfo_pb2.NetworkConnection.State.LISTEN
      ):
        continue
      self.SendReplyProto(response)

    self.Log("Successfully wrote %d connections.", len(responses))
