#!/usr/bin/env python
"""Classes for exporting network-related data."""

from collections.abc import Iterator
import ipaddress

from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server.export_converters import base


class ExportedNetworkConnection(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedNetworkConnection
  rdf_deps = [
      base.ExportedMetadata,
      rdf_client_network.NetworkEndpoint,
  ]


class ExportedDNSClientConfiguration(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedDNSClientConfiguration
  rdf_deps = [
      base.ExportedMetadata,
  ]


class ExportedNetworkInterface(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedNetworkInterface
  rdf_deps = [
      base.ExportedMetadata,
  ]


class NetworkConnectionToExportedNetworkConnectionConverter(
    base.ExportConverter
):
  """Converts NetworkConnection to ExportedNetworkConnection."""

  input_rdf_type = rdf_client_network.NetworkConnection

  def Convert(
      self,
      metadata: base.ExportedMetadata,
      conn: rdf_client_network.NetworkConnection,
  ) -> list[ExportedNetworkConnection]:
    """Converts a NetworkConnection into a ExportedNetworkConnection.

    Args:
      metadata: ExportedMetadata to be added to the ExportedNetworkConnection.
      conn: NetworkConnection to be converted.

    Returns:
      A list with a single ExportedNetworkConnection containing the converted
      NetworkConnection.
    """

    result = ExportedNetworkConnection(
        metadata=metadata,
        family=conn.family,
        type=conn.type,
        local_address=conn.local_address,
        remote_address=conn.remote_address,
        state=conn.state,
        pid=conn.pid,
        ctime=conn.ctime,
    )
    return [result]


class NetworkConnectionToExportedNetworkConnectionConverterProto(
    base.ExportConverterProto[sysinfo_pb2.NetworkConnection]
):
  """Converts NetworkConnection to ExportedNetworkConnection."""

  input_proto_type = sysinfo_pb2.NetworkConnection
  output_proto_types = (export_pb2.ExportedNetworkConnection,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      conn: sysinfo_pb2.NetworkConnection,
  ) -> list[export_pb2.ExportedNetworkConnection]:
    """Converts a NetworkConnection into a ExportedNetworkConnection.

    Args:
      metadata: ExportedMetadata to be added to the ExportedNetworkConnection.
      conn: NetworkConnection to be converted.

    Returns:
      A list with a single ExportedNetworkConnection containing the converted
      NetworkConnection.
    """

    result = export_pb2.ExportedNetworkConnection(
        metadata=metadata,
        family=conn.family,
        type=conn.type,
        local_address=conn.local_address,
        remote_address=conn.remote_address,
        state=conn.state,
        pid=conn.pid,
        ctime=conn.ctime,
    )
    return [result]


class InterfaceToExportedNetworkInterfaceConverter(base.ExportConverter):
  """Converts Interface to ExportedNetworkInterface."""

  input_rdf_type = rdf_client_network.Interface

  def Convert(
      self,
      metadata: base.ExportedMetadata,
      interface: rdf_client_network.Interface,
  ) -> Iterator[ExportedNetworkInterface]:
    """Converts a Interface into ExportedNetworkInterfaces.

    Args:
      metadata: ExportedMetadata to be added to the ExportedNetworkInterface.
      interface: (Network) Interface to be converted.

    Yields:
      An ExportedNetworkInterface containing the converted Interface.
    """

    ip4_addresses = []
    ip6_addresses = []
    for addr in interface.addresses:
      if addr.address_type == addr.Family.INET:
        ip4_addresses.append(addr.human_readable_address)
      elif addr.address_type == addr.Family.INET6:
        ip6_addresses.append(addr.human_readable_address)
      else:
        raise ValueError("Invalid address type: %s" % addr.address_type)

    result = ExportedNetworkInterface(
        metadata=metadata,
        ifname=interface.ifname,
        ip4_addresses=" ".join(ip4_addresses),
        ip6_addresses=" ".join(ip6_addresses),
    )

    if interface.mac_address:
      result.mac_address = interface.mac_address.human_readable_address

    yield result


class InterfaceToExportedNetworkInterfaceConverterProto(
    base.ExportConverterProto[jobs_pb2.Interface]
):
  """Converts Interface to ExportedNetworkInterface."""

  input_proto_type = jobs_pb2.Interface
  output_proto_types = (export_pb2.ExportedNetworkInterface,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      interface: jobs_pb2.Interface,
  ) -> Iterator[export_pb2.ExportedNetworkInterface]:
    """Converts a Interface into ExportedNetworkInterfaces.

    Args:
      metadata: ExportedMetadata to be added to the ExportedNetworkInterface.
      interface: (Network) Interface to be converted.

    Yields:
      An ExportedNetworkInterface containing the converted Interface.
    """

    ip4_addresses = []
    ip6_addresses = []
    for addr in interface.addresses:
      if addr.address_type == jobs_pb2.NetworkAddress.Family.INET:
        ip4_addresses.append(str(ipaddress.IPv4Address(addr.packed_bytes)))
      elif addr.address_type == jobs_pb2.NetworkAddress.Family.INET6:
        ip6_addresses.append(str(ipaddress.IPv6Address(addr.packed_bytes)))
      else:
        raise ValueError("Invalid address type: %s" % addr.address_type)

    result = export_pb2.ExportedNetworkInterface(
        metadata=metadata,
        ifname=interface.ifname,
        ip4_addresses=" ".join(ip4_addresses),
        ip6_addresses=" ".join(ip6_addresses),
    )

    if interface.mac_address:
      result.mac_address = rdf_client_network.MacAddress(
          interface.mac_address
      ).human_readable_address

    yield result


class DNSClientConfigurationToExportedDNSClientConfiguration(
    base.ExportConverter
):
  """Converts DNSClientConfiguration to ExportedDNSClientConfiguration."""

  input_rdf_type = rdf_client_network.DNSClientConfiguration

  def Convert(
      self,
      metadata: base.ExportedMetadata,
      config: rdf_client_network.DNSClientConfiguration,
  ) -> Iterator[ExportedDNSClientConfiguration]:
    """Converts a DNSClientConfiguration into a ExportedDNSClientConfiguration.

    Args:
      metadata: ExportedMetadata to be added to the
        ExportedDNSClientConfiguration.
      config: DNSClientConfiguration to be converted.

    Yields:
      An ExportedDNSClientConfiguration containing the DNSClientConfiguration.
    """

    result = ExportedDNSClientConfiguration(
        metadata=metadata,
        dns_servers=" ".join(config.dns_server),
        dns_suffixes=" ".join(config.dns_suffix),
    )
    yield result


class DNSClientConfigurationToExportedDNSClientConfigurationProto(
    base.ExportConverterProto[sysinfo_pb2.DNSClientConfiguration]
):
  """Converts DNSClientConfiguration to ExportedDNSClientConfiguration."""

  input_proto_type = sysinfo_pb2.DNSClientConfiguration
  output_proto_types = (export_pb2.ExportedDNSClientConfiguration,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      config: sysinfo_pb2.DNSClientConfiguration,
  ) -> Iterator[export_pb2.ExportedDNSClientConfiguration]:
    """Converts a DNSClientConfiguration into a ExportedDNSClientConfiguration.

    Args:
      metadata: ExportedMetadata to be added to the
        ExportedDNSClientConfiguration.
      config: DNSClientConfiguration to be converted.

    Yields:
      An ExportedDNSClientConfiguration containing the DNSClientConfiguration.
    """

    result = export_pb2.ExportedDNSClientConfiguration(
        metadata=metadata,
        dns_servers=" ".join(config.dns_server),
        dns_suffixes=" ".join(config.dns_suffix),
    )
    yield result
