#!/usr/bin/env python
"""Classes for exporting memory-related data."""

from typing import Iterator

from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import export_pb2
from grr_response_server.export_converters import base
from grr_response_server.export_converters import process


class ExportedYaraProcessScanMatch(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedYaraProcessScanMatch
  rdf_deps = [process.ExportedProcess, base.ExportedMetadata]


class ExportedProcessMemoryError(rdf_structs.RDFProtoStruct):
  protobuf = export_pb2.ExportedProcessMemoryError
  rdf_deps = [process.ExportedProcess, base.ExportedMetadata]


class YaraProcessScanMatchConverter(base.ExportConverter):
  """Converter for YaraProcessScanMatch."""
  input_rdf_type = rdf_memory.YaraProcessScanMatch

  def Convert(
      self, metadata: base.ExportedMetadata,
      value: rdf_memory.YaraProcessScanMatch
  ) -> Iterator[ExportedYaraProcessScanMatch]:
    """See base class."""

    conv = process.ProcessToExportedProcessConverter(options=self.options)
    proc = list(conv.Convert(metadata, value.process))[0]

    yara_matches = value.match or [rdf_memory.YaraMatch()]
    for yara_match in yara_matches:
      sm = yara_match.string_matches or [rdf_memory.YaraStringMatch()]
      for yara_string_match in sm:
        yield ExportedYaraProcessScanMatch(
            metadata=metadata,
            process=proc,
            rule_name=yara_match.rule_name,
            process_scan_time_us=value.scan_time_us,
            string_id=yara_string_match.string_id,
            offset=yara_string_match.offset)


class ProcessMemoryErrorConverter(base.ExportConverter):
  """Converter for ProcessMemoryError."""
  input_rdf_type = rdf_memory.ProcessMemoryError

  def Convert(
      self,
      metadata: base.ExportedMetadata,
      value: rdf_memory.ProcessMemoryError,
  ) -> Iterator[ExportedProcessMemoryError]:
    """See base class."""

    conv = process.ProcessToExportedProcessConverter(options=self.options)
    proc = next(iter(conv.Convert(metadata, value.process)))
    yield ExportedProcessMemoryError(
        metadata=metadata, process=proc, error=value.error)
