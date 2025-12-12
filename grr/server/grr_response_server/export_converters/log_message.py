#!/usr/bin/env python
"""Export converters for protobuf wrapper types."""

from typing import Iterable

from grr_response_proto import export_pb2
from grr_response_proto import jobs_pb2
from grr_response_server.export_converters import base


class LogMessageToExportedStringConverter(
    base.ExportConverterProto[jobs_pb2.LogMessage]
):
  """Converts LogMessage to ExportedString."""

  input_proto_type = jobs_pb2.LogMessage
  output_proto_types = (export_pb2.ExportedString,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      log_message: jobs_pb2.LogMessage,
  ) -> Iterable[export_pb2.ExportedString]:
    """Converts a LogMessage into an ExportedString."""
    yield export_pb2.ExportedString(metadata=metadata, data=log_message.data)
