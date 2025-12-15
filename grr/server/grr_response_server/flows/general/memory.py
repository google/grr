#!/usr/bin/env python
"""Flows related to process memory."""

import collections
from collections.abc import Iterable
import logging
import re

import yara

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_core.lib.rdfvalues import mig_memory
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.flows.general import transfer
from grr_response_server.models import blobs as models_blobs

_YARA_SIGNATURE_SHARD_SIZE = 500 << 10  # 500 KiB


class YaraProcessScan(
    flow_base.FlowBase[
        flows_pb2.YaraProcessScanRequest,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """Scans process memory using Yara."""

  category = "/Memory/"
  friendly_name = "Yara Process Scan"

  args_type = rdf_memory.YaraProcessScanRequest
  behaviours = flow_base.BEHAVIOUR_BASIC
  result_types = (
      rdf_client_fs.StatEntry,
      rdf_memory.YaraProcessDumpResponse,
      rdf_memory.ProcessMemoryError,
      rdf_memory.YaraProcessScanMatch,
      rdf_memory.YaraProcessScanMiss,
  )

  proto_args_type = flows_pb2.YaraProcessScanRequest
  proto_result_types = [
      jobs_pb2.StatEntry,
      flows_pb2.YaraProcessDumpResponse,
      flows_pb2.ProcessMemoryError,
      flows_pb2.YaraProcessScanMatch,
      flows_pb2.YaraProcessScanMiss,
  ]
  only_protos_allowed = True

  def _ValidateFlowArgs(self):
    if (
        self.proto_args.yara_signature
        and self.proto_args.yara_signature_blob_id
    ):
      message = (
          "`yara_signature` can't be used together with `yara_signature_blob_id"
      )
      raise flow_base.FlowError(message)
    elif self.proto_args.yara_signature:
      # Make sure the rules compile and are not empty before we move forward.
      rules = yara.compile(source=str(self.proto_args.yara_signature))
      if not list(rules):
        raise flow_base.FlowError(
            "No rules found in the signature specification."
        )
    elif self.proto_args.yara_signature_blob_id:
      blob_id = models_blobs.BlobID(self.proto_args.yara_signature_blob_id)
      if not data_store.REL_DB.VerifyYaraSignatureReference(blob_id):
        message = "Incorrect YARA signature reference: {}".format(blob_id)
        raise flow_base.FlowError(message)
    else:
      raise flow_base.FlowError(
          "Flow args contain neither yara_signature nor yara_signature_blob_id."
          " Provide a yara_signature for scanning."
      )

    if self.proto_args.process_regex and self.proto_args.cmdline_regex:
      raise flow_base.FlowError(
          "Use either process_regex to match process names"
          "or cmdline_regex to match the process cmdline."
      )

    if self.proto_args.process_regex:
      re.compile(self.proto_args.process_regex)

    if self.proto_args.cmdline_regex:
      re.compile(self.proto_args.cmdline_regex)

  def Start(self):
    """See base class."""
    self._ValidateFlowArgs()

    if self.proto_args.scan_runtime_limit_us:
      # We use the runtime limit on the args to override the runtime limit on
      # the current flow object temporarily. This is because we want to use it
      # while we're doing the YaraProcessScan action, but we want to restore the
      # original runtime limit afterwards in case we do the dumping.
      request_data = {"runtime_limit_us": self.rdf_flow.runtime_limit_us}
      self.rdf_flow.runtime_limit_us = rdfvalue.Duration.From(
          self.proto_args.scan_runtime_limit_us, rdfvalue.MICROSECONDS
      )
    else:
      request_data = None

    if self.proto_args.yara_signature:
      signature_bytes = str(self.proto_args.yara_signature).encode("utf-8")
    elif self.proto_args.yara_signature_blob_id:
      blob_id = models_blobs.BlobID(self.proto_args.yara_signature_blob_id)
      signature_bytes = data_store.BLOBS.ReadBlob(blob_id)
    else:
      raise flow_base.FlowError(
          "We should have one or the other set _ValidateFlowArgs should have"
          " caught this."
      )

    offsets = range(0, len(signature_bytes), _YARA_SIGNATURE_SHARD_SIZE)
    for i, offset in enumerate(offsets):
      client_request = flows_pb2.YaraProcessScanRequest()
      client_request.CopyFrom(self.proto_args)
      # We do not want to send the whole signature to the client, so we clear
      # the field.
      client_request.ClearField("yara_signature")
      client_request.signature_shard.CopyFrom(
          flows_pb2.YaraSignatureShard(
              index=i,
              payload=signature_bytes[
                  offset : offset + _YARA_SIGNATURE_SHARD_SIZE
              ],
          )
      )
      client_request.num_signature_shards = len(offsets)
      self.CallClientProto(
          server_stubs.YaraProcessScan,
          client_request,
          request_data=request_data,
          next_state=self.ProcessScanResults.__name__,
      )

  @flow_base.UseProto2AnyResponses
  def ProcessScanResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    """Processes the results of the scan."""
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    if not responses:
      # Clients (versions 3306 and above) only send back responses when
      # the full signature has been received.
      return

    # Restore original runtime limit in case it was overridden.
    if "runtime_limit_us" in responses.request_data:
      self.rdf_flow.runtime_limit_us = responses.request_data[
          "runtime_limit_us"
      ]

    # Maps PIDs to the offsets of the memory regions to dump for that PID.
    regions_to_dump = collections.defaultdict(set)

    for response_any in responses:
      response = flows_pb2.YaraProcessScanResponse()
      response.ParseFromString(response_any.value)

      for match in response.matches:
        self.SendReplyProto(match)
        rules = set([m.rule_name for m in match.match])
        rules_string = ",".join(sorted(rules))
        logging.debug(
            "YaraScan match in pid %d (%s) for rules %s.",
            match.process.pid,
            match.process.exe,
            rules_string,
        )

        if self.proto_args.dump_process_on_match:
          for process_match in match.match:
            for string_match in process_match.string_matches:
              regions_to_dump[match.process.pid].add(string_match.offset)

      for error in response.errors:
        # TODO: Remove server side filtering for errors after
        # clients adopted to the new version.
        if self._ShouldIncludeError(error):
          self.SendReplyProto(error)

      if self.proto_args.include_misses_in_results:
        for miss in response.misses:
          self.SendReplyProto(miss)

    for pid, offsets in regions_to_dump.items():
      self.CallFlowProto(
          DumpProcessMemory.__name__,
          flow_args=flows_pb2.YaraProcessDumpArgs(
              pids=[pid],
              prioritize_offsets=list(sorted(offsets)),
              size_limit=self.proto_args.process_dump_size_limit,
              skip_special_regions=self.proto_args.skip_special_regions,
              skip_mapped_files=self.proto_args.skip_mapped_files,
              skip_shared_regions=self.proto_args.skip_shared_regions,
              skip_executable_regions=self.proto_args.skip_executable_regions,
              skip_readonly_regions=self.proto_args.skip_readonly_regions,
          ),
          next_state=self.CheckDumpProcessMemoryResults.__name__,
      )

  @flow_base.UseProto2AnyResponses
  def CheckDumpProcessMemoryResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    # First send responses to parent Flow, then indicate potential errors, to
    # increase robustness.
    for response_any in responses:
      if response_any.Is(jobs_pb2.StatEntry.DESCRIPTOR):
        response = jobs_pb2.StatEntry()
        response_any.Unpack(response)
        self.SendReplyProto(response)
      elif response_any.Is(flows_pb2.YaraProcessDumpResponse.DESCRIPTOR):
        response = flows_pb2.YaraProcessDumpResponse()
        response_any.Unpack(response)
        self.SendReplyProto(response)
      else:
        raise flow_base.FlowError(
            f"Unexpected response type being dropped: {response_any.type_url}"
        )

    if not responses.success:
      raise flow_base.FlowError(responses.status)

  def _ShouldIncludeError(self, error: flows_pb2.ProcessMemoryError) -> bool:

    if (
        self.proto_args.include_errors_in_results
        == flows_pb2.YaraProcessScanRequest.ErrorPolicy.NO_ERRORS
    ):
      return False

    if (
        self.proto_args.include_errors_in_results
        == flows_pb2.YaraProcessScanRequest.ErrorPolicy.CRITICAL_ERRORS
    ):
      msg = error.error.lower()
      return "failed to open process" not in msg and "access denied" not in msg

    # Fall back to including all errors.
    return True


def _CanonicalizeLegacyWindowsPathSpec(ps: rdf_paths.PathSpec):
  """Canonicalize simple PathSpecs that might be from Windows legacy clients."""
  canonicalized = rdf_paths.PathSpec(ps)
  # Detect a path like C:\\Windows\\System32\\GRR.
  if ps.path[1:3] == ":\\" and "/" not in ps.path:
    # Canonicalize the path to /C:/Windows/System32/GRR.
    canonicalized.path = "/" + "/".join(ps.path.split("\\"))
  return canonicalized


def _ReplaceDumpPathspecsWithMultiGetFilePathspec(
    dump_response: flows_pb2.YaraProcessDumpResponse,
    stat_entries: Iterable[jobs_pb2.StatEntry],
):
  """Replaces a dump's PathSpecs based on their Basename."""
  memory_regions = {}
  for dumped_process in dump_response.dumped_processes:
    for memory_region in dumped_process.memory_regions:
      pathspec = mig_paths.ToRDFPathSpec(memory_region.file)
      memory_regions[pathspec.Basename()] = memory_region

  for stat_entry in stat_entries:
    pathspec = mig_paths.ToRDFPathSpec(stat_entry.pathspec)
    memory_regions[pathspec.Basename()].file.CopyFrom(stat_entry.pathspec)


class DumpProcessMemory(
    flow_base.FlowBase[
        flows_pb2.YaraProcessDumpArgs,
        flows_pb2.DefaultFlowStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """Acquires memory for a given list of processes."""

  category = "/Memory/"
  friendly_name = "Process Dump"

  args_type = rdf_memory.YaraProcessDumpArgs
  result_types = (rdf_client_fs.StatEntry, rdf_memory.YaraProcessDumpResponse)
  behaviours = flow_base.BEHAVIOUR_BASIC

  proto_args_type = flows_pb2.YaraProcessDumpArgs
  proto_result_types = [
      jobs_pb2.StatEntry,
      flows_pb2.YaraProcessDumpResponse,
  ]
  only_protos_allowed = True

  def Start(self):
    # Catch regex errors early.
    if self.args.process_regex:
      re.compile(self.args.process_regex)

    if not (
        self.proto_args.dump_all_processes
        or self.proto_args.pids
        or self.proto_args.process_regex
    ):
      raise ValueError("No processes to dump specified.")

    if self.proto_args.prioritize_offsets and len(self.proto_args.pids) != 1:
      raise ValueError(
          "Supplied prioritize_offsets {} for PIDs {} in YaraProcessDump. "
          "Required exactly one PID.".format(
              self.proto_args.prioritize_offsets, self.proto_args.pids
          )
      )

    self.CallClientProto(
        server_stubs.YaraProcessDump,
        self.proto_args,
        next_state=self.ProcessResults.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def ProcessResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ):
    """Processes the results of the dump."""
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    if len(list(responses)) < 1:
      raise flow_base.FlowError("No responses from client.")

    response = flows_pb2.YaraProcessDumpResponse()
    response.ParseFromString(list(responses)[0].value)

    for error in response.errors:
      p = error.process
      self.Log(
          "Error dumping process %s (pid %d): %s" % (p.name, p.pid, error.error)
      )

    dump_files_to_get = []
    for dumped_process in response.dumped_processes:
      p = dumped_process.process
      self.Log(
          "Getting %d dump files for process %s (pid %d)."
          % (len(dumped_process.memory_regions), p.name, p.pid)
      )
      for region in dumped_process.memory_regions:
        dump_files_to_get.append(region.file)

    if not dump_files_to_get:
      self.SendReplyProto(response)
      self.Log("No memory dumped, exiting.")
      return

    self.CallFlowProto(
        transfer.MultiGetFile.__name__,
        flow_args=flows_pb2.MultiGetFileArgs(
            pathspecs=dump_files_to_get,
            file_size=1024 * 1024 * 1024,
            use_external_stores=False,
        ),
        next_state=self.ProcessMemoryRegions.__name__,
        # `request_data` dict does not support proto messages.
        request_data={
            "YaraProcessDumpResponse": mig_memory.ToRDFYaraProcessDumpResponse(
                response
            )
        },
    )

  @flow_base.UseProto2AnyResponses
  def ProcessMemoryRegions(
      self, responses: flow_responses.Responses[any_pb2.Any]
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    stat_entries = []
    for response_any in responses:
      stat_entry = jobs_pb2.StatEntry()
      stat_entry.ParseFromString(response_any.value)
      stat_entries.append(stat_entry)

    # request_data is not present
    if "YaraProcessDumpResponse" in responses.request_data:
      # On case-sensitive filesystems, the requested PathSpecs (located in
      # YaraProcessDumpResponse.dumped_processes[*].memory_regions[*]file) might
      # differ from the real location of the received MemoryRegion (located in
      # StatEntry.pathspec). Since MemoryRegions are later identified
      # case-sensitive by their filename in file_store.OpenFile(), we need to
      # align both PathSpecs to make sure we can actually find MemoryRegions in
      # file_store again.
      dump_response = responses.request_data["YaraProcessDumpResponse"]
      dump_response = mig_memory.ToProtoYaraProcessDumpResponse(dump_response)
      _ReplaceDumpPathspecsWithMultiGetFilePathspec(dump_response, stat_entries)
      self.SendReplyProto(dump_response)

    for stat_entry in stat_entries:
      self.SendReplyProto(stat_entry)

      self.CallClientProto(
          server_stubs.DeleteGRRTempFiles,
          stat_entry.pathspec,
          next_state=self.LogDeleteFiles.__name__,
      )

  @flow_base.UseProto2AnyResponses
  def LogDeleteFiles(self, responses: flow_responses.Responses[any_pb2.Any]):
    # Check that the DeleteFiles flow worked.
    if not responses.success:
      raise flow_base.FlowError("Could not delete file: %s" % responses.status)
