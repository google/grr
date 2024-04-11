#!/usr/bin/env python
"""Provides conversion functions to be used during RDFProtoStruct migration."""

from grr_response_proto import export_pb2
from grr_response_server.export_converters import network


def ToProtoExportedNetworkConnection(
    rdf: network.ExportedNetworkConnection,
) -> export_pb2.ExportedNetworkConnection:
  return rdf.AsPrimitiveProto()


def ToRDFExportedNetworkConnection(
    proto: export_pb2.ExportedNetworkConnection,
) -> network.ExportedNetworkConnection:
  return network.ExportedNetworkConnection.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExportedDNSClientConfiguration(
    rdf: network.ExportedDNSClientConfiguration,
) -> export_pb2.ExportedDNSClientConfiguration:
  return rdf.AsPrimitiveProto()


def ToRDFExportedDNSClientConfiguration(
    proto: export_pb2.ExportedDNSClientConfiguration,
) -> network.ExportedDNSClientConfiguration:
  return network.ExportedDNSClientConfiguration.FromSerializedBytes(
      proto.SerializeToString()
  )


def ToProtoExportedNetworkInterface(
    rdf: network.ExportedNetworkInterface,
) -> export_pb2.ExportedNetworkInterface:
  return rdf.AsPrimitiveProto()


def ToRDFExportedNetworkInterface(
    proto: export_pb2.ExportedNetworkInterface,
) -> network.ExportedNetworkInterface:
  return network.ExportedNetworkInterface.FromSerializedBytes(
      proto.SerializeToString()
  )
