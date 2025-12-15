#!/usr/bin/env python
"""These are network related flows."""

from google.protobuf import any_pb2
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs


class NetstatArgs(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.NetstatArgs


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
  args_type = NetstatArgs
  result_types = (rdf_client_network.NetworkConnection,)

  proto_args_type = flows_pb2.NetstatArgs
  proto_result_types = (sysinfo_pb2.NetworkConnection,)
  only_protos_allowed = True

  def Start(self):
    """Start processing."""
    self.CallClientProto(
        server_stubs.ListNetworkConnections,
        flows_pb2.ListNetworkConnectionsArgs(
            listening_only=self.proto_args.listening_only,
        ),
        next_state=self.StoreNetstat.__name__,
    )

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
