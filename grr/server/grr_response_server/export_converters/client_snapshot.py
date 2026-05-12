#!/usr/bin/env python
"""Classes for exporting ClientSnapshot."""

from collections.abc import Iterator

from grr_response_proto import export_pb2
from grr_response_proto import objects_pb2
from grr_response_server.export_converters import base


class ClientSnapshotToExportedClientConverterProto(
    base.ExportConverterProto[objects_pb2.ClientSnapshot]
):
  """Converts a ClientSnapshot to ExportedClient."""

  input_proto_type = objects_pb2.ClientSnapshot
  output_proto_types = (export_pb2.ExportedClient,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      unused_client_snapshot: objects_pb2.ClientSnapshot,
  ) -> Iterator[export_pb2.ExportedClient]:
    """Yields an ExportedClient using the ExportedMetadata.

    Args:
      metadata: ExportedMetadata to be added to the ExportedClient.
      unused_client_snapshot: UNUSED ClientSnapshot.

    Yields:
      An ExportedClient with the converted ClientSnapshot.
    """

    yield export_pb2.ExportedClient(metadata=metadata)
