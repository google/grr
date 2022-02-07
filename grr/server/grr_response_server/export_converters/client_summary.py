#!/usr/bin/env python
"""Classes for exporting ClientSummary."""

from typing import Iterator, List

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_server.export_converters import base
from grr_response_server.export_converters import network


class ExportedClient(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedClient
  rdf_deps = [
      base.ExportedMetadata,
  ]


class ClientSummaryToExportedNetworkInterfaceConverter(
    network.InterfaceToExportedNetworkInterfaceConverter):
  """Converts a ClientSummary to ExportedNetworkInterfaces."""

  input_rdf_type = rdf_client.ClientSummary

  def Convert(
      self, metadata: base.ExportedMetadata,
      client_summary: rdf_client.ClientSummary
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
      self, metadata: base.ExportedMetadata,
      unused_client_summary: rdf_client.ClientSummary) -> List[ExportedClient]:
    """Returns an ExportedClient using the ExportedMetadata.

    Args:
      metadata: ExportedMetadata to be added to the ExportedClient.
      unused_client_summary: UNUSED ClientSummary.

    Returns:
      A list containing an ExportedClient with the converted ClientSummary.
    """

    return [ExportedClient(metadata=metadata)]
