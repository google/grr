#!/usr/bin/env python
"""Classes for exporting memory-related data."""

from collections.abc import Iterator

from grr_response_proto import export_pb2
from grr_response_proto import flows_pb2
from grr_response_server.export_converters import base
from grr_response_server.export_converters import process


class YaraProcessScanMatchConverterProto(
    base.ExportConverterProto[flows_pb2.YaraProcessScanMatch]
):
  """Converter for YaraProcessScanMatch."""

  input_proto_type = flows_pb2.YaraProcessScanMatch
  output_proto_types = (export_pb2.ExportedYaraProcessScanMatch,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      value: flows_pb2.YaraProcessScanMatch,
  ) -> Iterator[export_pb2.ExportedYaraProcessScanMatch]:
    conv = process.ProcessToExportedProcessConverterProto()
    proc = list(conv.Convert(metadata, value.process))
    if not proc:
      return []

    assert len(proc) == 1, f"Expected exactly one process, got {len(proc)}"
    proc = proc[0]

    yara_matches = value.match or [flows_pb2.YaraMatch()]
    for yara_match in yara_matches:
      sm = yara_match.string_matches or [flows_pb2.YaraStringMatch()]
      for yara_string_match in sm:
        yield export_pb2.ExportedYaraProcessScanMatch(
            metadata=metadata,
            process=proc,
            rule_name=yara_match.rule_name,
            process_scan_time_us=value.scan_time_us,
            string_id=yara_string_match.string_id,
            offset=yara_string_match.offset,
            context=yara_string_match.context,
        )


class ProcessMemoryErrorConverterProto(
    base.ExportConverterProto[flows_pb2.ProcessMemoryError]
):
  """Converter for ProcessMemoryError."""

  input_proto_type = flows_pb2.ProcessMemoryError
  output_proto_types = (export_pb2.ExportedProcessMemoryError,)

  def Convert(
      self,
      metadata: export_pb2.ExportedMetadata,
      value: flows_pb2.ProcessMemoryError,
  ) -> Iterator[export_pb2.ExportedProcessMemoryError]:
    """See base class."""

    conv = process.ProcessToExportedProcessConverterProto()
    proc = list(conv.Convert(metadata, value.process))
    if not proc:
      return []

    assert len(proc) == 1, f"Expected exactly one process, got {len(proc)}"
    proc = proc[0]

    yield export_pb2.ExportedProcessMemoryError(
        metadata=metadata, process=proc, error=value.error
    )
