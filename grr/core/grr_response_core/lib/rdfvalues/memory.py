#!/usr/bin/env python
"""RDFValues used with Yara."""

import yara

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_proto import flows_pb2


class YaraSignature(rdfvalue.RDFString):

  def GetRules(self):
    return yara.compile(source=str(self))


class YaraSignatureShard(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraSignatureShard
  rdf_deps = []


class YaraProcessScanRequest(rdf_structs.RDFProtoStruct):
  """Args for YaraProcessScan flow and client action."""
  protobuf = flows_pb2.YaraProcessScanRequest
  rdf_deps = [
      YaraSignature,
      YaraSignatureShard,
      rdfvalue.ByteSize,
      rdfvalue.Duration,
  ]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # These default values were migrated from the Protobuf definition.
    if not self.HasField("include_errors_in_results"):
      self.include_errors_in_results = YaraProcessScanRequest.ErrorPolicy.NO_ERRORS
    if not self.HasField("include_misses_in_results"):
      self.include_misses_in_results = False
    if not self.HasField("ignore_grr_process"):
      self.ignore_grr_process = True
    if not self.HasField("chunk_size"):
      self.chunk_size = 100 * 1024 * 1024  # 100 MiB
    if not self.HasField("overlap_size"):
      self.overlap_size = 10 * 1024 * 1024  # 10 MiB
    if not self.HasField("skip_special_regions"):
      self.skip_special_regions = False
    if not self.HasField("skip_mapped_files"):
      self.skip_mapped_files = True
    if not self.HasField("skip_shared_regions"):
      self.skip_shared_regions = False
    if not self.HasField("skip_executable_regions"):
      self.skip_executable_regions = False
    if not self.HasField("skip_readonly_regions"):
      self.skip_readonly_regions = False
    if not self.HasField("dump_process_on_match"):
      self.dump_process_on_match = False
    if not self.HasField("process_dump_size_limit"):
      self.process_dump_size_limit = 0


class ProcessMemoryError(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ProcessMemoryError
  rdf_deps = [rdf_client.Process]


class YaraStringMatch(rdf_structs.RDFProtoStruct):
  """A result of Yara string matching."""
  protobuf = flows_pb2.YaraStringMatch
  rdf_deps = []

  @classmethod
  def FromLibYaraStringMatch(cls, yara_string_match):
    # Format is described in
    # http://yara.readthedocs.io/en/v3.5.0/yarapython.html
    res = cls()
    res.offset, res.string_id, res.data = yara_string_match
    return res


class YaraMatch(rdf_structs.RDFProtoStruct):
  """A result of Yara matching."""
  protobuf = flows_pb2.YaraMatch
  rdf_deps = [YaraStringMatch]

  @classmethod
  def FromLibYaraMatch(cls, yara_match):
    res = cls()
    res.rule_name = yara_match.rule
    res.string_matches = [
        YaraStringMatch.FromLibYaraStringMatch(sm) for sm in yara_match.strings
    ]
    return res


class YaraProcessScanMatch(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessScanMatch
  rdf_deps = [rdf_client.Process, YaraMatch]


class YaraProcessScanMiss(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessScanMiss
  rdf_deps = [rdf_client.Process]


class YaraProcessScanResponse(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessScanResponse
  rdf_deps = [YaraProcessScanMatch, YaraProcessScanMiss, ProcessMemoryError]


class YaraProcessDumpArgs(rdf_structs.RDFProtoStruct):
  """Args for DumpProcessMemory flow and YaraProcessDump client action."""
  protobuf = flows_pb2.YaraProcessDumpArgs
  rdf_deps = [rdfvalue.ByteSize]

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # These default values were migrated from the Protobuf definition.
    if not self.HasField("ignore_grr_process"):
      self.ignore_grr_process = True
    if not self.HasField("dump_all_processes"):
      self.dump_all_processes = False
    if not self.HasField("size_limit"):
      self.size_limit = 0
    if not self.HasField("chunk_size"):
      self.chunk_size = 100 * 1024 * 1024  # 100 MiB
    if not self.HasField("skip_special_regions"):
      self.skip_special_regions = False
    if not self.HasField("skip_mapped_files"):
      self.skip_mapped_files = True
    if not self.HasField("skip_shared_regions"):
      self.skip_shared_regions = False
    if not self.HasField("skip_executable_regions"):
      self.skip_executable_regions = False
    if not self.HasField("skip_readonly_regions"):
      self.skip_readonly_regions = False


class ProcessMemoryRegion(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.ProcessMemoryRegion
  rdf_deps = [rdf_paths.PathSpec]


class YaraProcessDumpInformation(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessDumpInformation
  rdf_deps = [rdf_client.Process, rdf_paths.PathSpec, ProcessMemoryRegion]


class YaraProcessDumpResponse(rdf_structs.RDFProtoStruct):
  protobuf = flows_pb2.YaraProcessDumpResponse
  rdf_deps = [YaraProcessDumpInformation, ProcessMemoryError]
