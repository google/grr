#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2


def ToProtoNetworkEndpoint(
    rdf: rdf_client_network.NetworkEndpoint,
) -> sysinfo_pb2.NetworkEndpoint:
  return rdf.AsPrimitiveProto()


def ToRDFNetworkEndpoint(
    proto: sysinfo_pb2.NetworkEndpoint,
) -> rdf_client_network.NetworkEndpoint:
  return rdf_client_network.NetworkEndpoint.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoNetworkConnection(
    rdf: rdf_client_network.NetworkConnection,
) -> sysinfo_pb2.NetworkConnection:
  return rdf.AsPrimitiveProto()


def ToRDFNetworkConnection(
    proto: sysinfo_pb2.NetworkConnection,
) -> rdf_client_network.NetworkConnection:
  return rdf_client_network.NetworkConnection.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoNetworkAddress(
    rdf: rdf_client_network.NetworkAddress,
) -> jobs_pb2.NetworkAddress:
  return rdf.AsPrimitiveProto()


def ToRDFNetworkAddress(
    proto: jobs_pb2.NetworkAddress,
) -> rdf_client_network.NetworkAddress:
  return rdf_client_network.NetworkAddress.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoDNSClientConfiguration(
    rdf: rdf_client_network.DNSClientConfiguration,
) -> sysinfo_pb2.DNSClientConfiguration:
  return rdf.AsPrimitiveProto()


def ToRDFDNSClientConfiguration(
    proto: sysinfo_pb2.DNSClientConfiguration,
) -> rdf_client_network.DNSClientConfiguration:
  return rdf_client_network.DNSClientConfiguration.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoInterface(rdf: rdf_client_network.Interface) -> jobs_pb2.Interface:
  return rdf.AsPrimitiveProto()


def ToRDFInterface(proto: jobs_pb2.Interface) -> rdf_client_network.Interface:
  return rdf_client_network.Interface.FromSerializedBytes(
      proto.SerializeToString()
  )
