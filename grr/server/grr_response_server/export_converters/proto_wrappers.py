#!/usr/bin/env python
"""Export converters for protobuf wrapper types."""

from typing import Iterable

from google.protobuf import wrappers_pb2
from grr_response_proto import export_pb2
from grr_response_server.export_converters import base


class StringValueToExportedStringConverter(
    base.ExportConverterProto[wrappers_pb2.StringValue]
):
  """Converts StringValue to ExportedString."""

  input_proto_type = wrappers_pb2.StringValue
  output_proto_types = (export_pb2.ExportedString,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      value: wrappers_pb2.StringValue,
  ) -> Iterable[export_pb2.ExportedString]:
    """Converts a StringValue into an ExportedString."""
    yield export_pb2.ExportedString(metadata=metadata, data=value.value)


class BytesValueToExportedBytesConverter(
    base.ExportConverterProto[wrappers_pb2.BytesValue]
):
  """Converts BytesValue to ExportedBytes."""

  input_proto_type = wrappers_pb2.BytesValue
  output_proto_types = (export_pb2.ExportedBytes,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      value: wrappers_pb2.BytesValue,
  ) -> Iterable[export_pb2.ExportedBytes]:
    """Converts a BytesValue into an ExportedBytes."""
    yield export_pb2.ExportedBytes(
        metadata=metadata, data=value.value, length=len(value.value)
    )
