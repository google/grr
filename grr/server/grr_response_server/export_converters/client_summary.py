#!/usr/bin/env python
"""Classes for exporting ClientSummary."""

from collections.abc import Iterator

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.export_converters import base
from grr_response_server.export_converters import network


class ExportedClient(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedClient
  rdf_deps = [
      base.ExportedMetadata,
  ]


class ClientSummaryToExportedNetworkInterfaceConverter(
    network.InterfaceToExportedNetworkInterfaceConverter
):
  """Converts a ClientSummary to ExportedNetworkInterfaces."""

  input_rdf_type = rdf_client.ClientSummary

  def Convert(
      self,
      metadata: base.ExportedMetadata,
      client_summary: rdf_client.ClientSummary,
  ) -> Iterator[network.ExportedNetworkInterface]:
    """Converts a ClientSummary into ExportedNetworkInterfaces.

    Args:
      metadata: ExportedMetadata to be added to the ExportedNetworkInterface.
      client_summary: ClientSummary to be converted.

    Yields:
      An ExportedNetworkInterface containing the converted ClientSummary.
    """

    sup = super()

    for interface in client_summary.interfaces:
      yield next(sup.Convert(metadata, interface))


class ClientSummaryToExportedClientConverter(base.ExportConverter):
  """Converts a ClientSummary to ExportedClient."""

  input_rdf_type = rdf_client.ClientSummary

  def Convert(
      self,
      metadata: base.ExportedMetadata,
      unused_client_summary: rdf_client.ClientSummary,
  ) -> list[ExportedClient]:
    """Returns an ExportedClient using the ExportedMetadata.

    Args:
      metadata: ExportedMetadata to be added to the ExportedClient.
      unused_client_summary: UNUSED ClientSummary.

    Returns:
      A list containing an ExportedClient with the converted ClientSummary.
    """

    return [ExportedClient(metadata=metadata)]


class ClientSummaryToExportedClientConverterProto(
    base.ExportConverterProto[jobs_pb2.ClientSummary]
):
  """Converts a ClientSummary to ExportedClient."""

  input_proto_type = jobs_pb2.ClientSummary
  output_proto_types = (export_pb2.ExportedClient,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      unused_client_summary: jobs_pb2.ClientSummary,
  ) -> Iterator[export_pb2.ExportedClient]:
    """Yields an ExportedClient using the ExportedMetadata.

    Args:
      metadata: ExportedMetadata to be added to the ExportedClient.
      unused_client_summary: UNUSED ClientSummary.

    Yields:
      An ExportedClient with the converted ClientSummary.
    """

    yield export_pb2.ExportedClient(metadata=metadata)


class ClientSummaryToExportedNetworkInterfaceConverterProto(
    base.ExportConverterProto[jobs_pb2.ClientSummary]
):
  """Converts a ClientSummary to ExportedNetworkInterfaces."""

  input_proto_type = jobs_pb2.ClientSummary
  output_proto_types = (export_pb2.ExportedNetworkInterface,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      client_summary: jobs_pb2.ClientSummary,
  ) -> Iterator[export_pb2.ExportedNetworkInterface]:
    """Converts a ClientSummary into ExportedNetworkInterfaces.

    Args:
      metadata: ExportedMetadata to be added to the ExportedNetworkInterface.
      client_summary: ClientSummary to be converted.

    Yields:
      An ExportedNetworkInterface containing the converted ClientSummary.
    """

    converter = network.InterfaceToExportedNetworkInterfaceConverterProto()

    for interface in client_summary.interfaces:
      yield from converter.Convert(metadata, interface)
