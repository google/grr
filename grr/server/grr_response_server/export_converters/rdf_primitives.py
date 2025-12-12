#!/usr/bin/env python
"""Classes for exporting rdf primitives data."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_server.export_converters import base


class ExportedBytes(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedBytes
  rdf_deps = [
      base.ExportedMetadata,
  ]


class ExportedString(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedString
  rdf_deps = [
      base.ExportedMetadata,
  ]


class RDFBytesToExportedBytesConverter(base.ExportConverter):
  """Converts RDFBytes to ExportedBytes."""

  input_rdf_type = rdfvalue.RDFBytes

  def Convert(
      self, metadata: base.ExportedMetadata, data: rdfvalue.RDFBytes
  ) -> list[ExportedBytes]:
    """Converts a RDFBytes into a ExportedNetworkConnection.

    Args:
      metadata: ExportedMetadata to be added to the ExportedBytes.
      data: RDFBytes to be converted.

    Returns:
      A list with a single ExportedBytes containing the converted RDFBytes.
    """

    result = ExportedBytes(
        metadata=metadata, data=data.SerializeToBytes(), length=len(data)
    )
    return [result]


class RDFStringToExportedStringConverter(base.ExportConverter):
  """Converts RDFString to ExportedString."""

  input_rdf_type = rdfvalue.RDFString

  def Convert(
      self, metadata: base.ExportedMetadata, data: rdfvalue.RDFString
  ) -> list[ExportedString]:
    """Converts a RDFString into a ExportedString.

    Args:
      metadata: ExportedMetadata to be added to the ExportedString.
      data: RDFString to be converted.

    Returns:
      A list with a single ExportedString containing the converted RDFString.
    """

    return [ExportedString(metadata=metadata, data=data.SerializeToBytes())]
