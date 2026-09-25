#!/usr/bin/env python
"""Flows related to process memory."""

import collections
from collections.abc import Iterable
import hashlib
import logging
import re

import yara

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import mig_memory
from grr_response_core.lib.rdfvalues import mig_paths
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_proto import sysinfo_pb2
from grr_response_server import data_store
from grr_response_server import file_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import rrg_stubs
from grr_response_server import server_stubs
from grr_response_server.databases import db
from grr_response_server.flows.general import processes
from grr_response_server.flows.general import transfer
from grr_response_server.models import blobs as models_blobs
from grr_response_proto.rrg.action import dump_process_memory_pb2 as rrg_dump_process_memory_pb2
from grr_response_proto.rrg.action import scan_memory_yara_pb2 as rrg_scan_memory_yara_pb2
from grr_response_proto.rrg.action import store_filestore_part_pb2 as rrg_store_filestore_part_pb2


_YARA_SIGNATURE_SHARD_SIZE = 500 << 10  # 500 KiB


class YaraProcessScan(
    flow_base.FlowBase[
        flows_pb2.YaraProcessScanRequest,
        flows_pb2.YaraProcessScanStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """Scans process memory using Yara."""

  category = "/Memory/"
  friendly_name = "Yara Process Scan"
  behaviours = flow_base.BEHAVIOUR_BASIC

  proto_args_type = flows_pb2.YaraProcessScanRequest
  proto_store_type = flows_pb2.YaraProcessScanStore
  proto_result_types = [
      jobs_pb2.StatEntry,
      flows_pb2.YaraProcessDumpResponse,
      flows_pb2.ProcessMemoryError,
      flows_pb2.YaraProcessScanMatch,
      flows_pb2.YaraProcessScanMiss,
  ]

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

    if self.rrg_version >= (0, 0, 8):
      self._StartRRG()
      return

    if self.proto_args.scan_runtime_limit_us:
      # We use the runtime limit on the args to override the runtime limit on
      # the current flow object temporarily. This is because we want to use it
      # while we're doing the YaraProcessScan action, but we want to restore the
      # original runtime limit afterwards in case we do the dumping.
      request_data = {"runtime_limit_us": self.runtime_limit_us}
      self.runtime_limit_us = rdfvalue.Duration.From(
          self.proto_args.scan_runtime_limit_us, rdfvalue.MICROSECONDS
      ).SerializeToWireFormat()
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
      self.runtime_limit_us = responses.request_data["runtime_limit_us"]

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
        # TODO - Remove server side filtering for errors after
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

  def _GetRRGClientAction(
      self,
  ) -> rrg_stubs.Action[rrg_scan_memory_yara_pb2.Args]:
    action = rrg_stubs.ScanProcessMemoryYara()
    pids = set(self.store.processes.keys())
    if self.proto_args.pids:
      # If specific PIDs were specified, also include those,
      # even if no process with that PID is running on the client.
      # This way the client can send back an error for that PID.
      pids = pids.union(self.proto_args.pids)
    action.args.pids.extend(pids)
    if self.proto_args.per_process_timeout:
      action.args.timeout.FromSeconds(self.proto_args.per_process_timeout)
    if self.proto_args.chunk_size:
      action.args.chunk_size = self.proto_args.chunk_size
    if self.proto_args.overlap_size:
      action.args.chunk_overlap = self.proto_args.overlap_size
    if self.proto_args.skip_special_regions:
      self.Log(
          "skip_special_regions is no longer supported in the client, ignoring."
      )
    action.args.skip_mapped_files = self.proto_args.skip_mapped_files
    action.args.skip_shared_regions = self.proto_args.skip_shared_regions
    action.args.skip_executable_regions = (
        self.proto_args.skip_executable_regions
    )
    action.args.skip_readonly_regions = self.proto_args.skip_readonly_regions
    if self.proto_args.max_matches_per_pattern:
      action.args.max_matches_per_pattern = (
          self.proto_args.max_matches_per_pattern
      )
    elif self.proto_args.max_results_per_process:
      # TODO - Remove this once the clients have adopted
      # the new parameter.
      self.Log(
          "max_results_per_process is deprecated, automatically converting it"
          " to max_matches_per_pattern instead."
      )
      action.args.max_matches_per_pattern = (
          self.proto_args.max_results_per_process
      )
    return action

  def _StartRRG(self):
    self.CallFlowProto(
        processes.ListProcesses.__name__,
        flow_args=flows_pb2.ListProcessesArgs(
            pids=self.proto_args.pids,
            process_name_regex=self.proto_args.process_regex,
            cmdline_regex=self.proto_args.cmdline_regex,
        ),
        next_state=self._ProcessListProcesses.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessListProcesses(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to invoke list_processes: {responses.status}",
      )

    for response in responses:
      process = sysinfo_pb2.Process()
      process.ParseFromString(response.value)
      self.store.processes[process.pid].CopyFrom(process)

    if self.proto_args.yara_signature:
      signature_bytes = self.proto_args.yara_signature.encode("utf-8")
    elif self.proto_args.yara_signature_blob_id:
      signature_bytes = data_store.BLOBS.ReadBlob(
          models_blobs.BlobID(self.proto_args.yara_signature_blob_id)
      )
    else:
      raise flow_base.FlowError("No YARA signature provided.")

    if len(signature_bytes) <= _YARA_SIGNATURE_SHARD_SIZE:
      # If the signature is smaller than the shard size, we can just send it to
      # the client inline.
      action = self._GetRRGClientAction()
      action.args.signature_inline = signature_bytes.decode("utf-8")
      action.Call(next_state=self._ProcessScanResults)
    else:
      # Otherwise, we first need to upload the signature to the client
      # filestore.
      signature_sha256 = hashlib.sha256(signature_bytes).digest()
      for offset in range(0, len(signature_bytes), _YARA_SIGNATURE_SHARD_SIZE):
        action = rrg_stubs.StoreFilestorePart()
        action.args.file_sha256 = signature_sha256
        action.args.file_size = len(signature_bytes)
        action.args.part_offset = offset
        action.args.part_content = signature_bytes[
            offset : offset + _YARA_SIGNATURE_SHARD_SIZE
        ]
        action.Call(next_state=self._ProcessUploadedSignaturePart)

  @flow_base.UseProto2AnyResponses
  def _ProcessUploadedSignaturePart(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to invoke store_filestore_part: {responses.status}",
      )
    response = rrg_store_filestore_part_pb2.Result()
    response.ParseFromString(list(responses)[0].value)
    if response.status != rrg_store_filestore_part_pb2.COMPLETE:
      # Only proceed once the client has received the complete signature.
      return
    action = self._GetRRGClientAction()
    action.args.signature_file_sha256 = response.file_sha256
    action.Call(next_state=self._ProcessScanResults)

  @flow_base.UseProto2AnyResponses
  def _ProcessScanResults(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to invoke scan_process_memory_yara: {responses.status}",
      )

    for response in responses:
      result = rrg_scan_memory_yara_pb2.Result()
      result.ParseFromString(response.value)

      process = self.store.processes.get(result.pid, None)
      if process is None:
        # If there was no process with one of the given PIDs running on the
        # client at the time ListProcesses ran, we won't have its details in
        # the store. The client will still send an (error) result for it,
        # so we create a dummy process here with only the PID set for context.
        self.Log(f"No process found for PID {result.pid} in store.")
        process = sysinfo_pb2.Process(pid=result.pid)

      if result.error:
        if (
            self.proto_args.include_errors_in_results
            != flows_pb2.YaraProcessScanRequest.ErrorPolicy.NO_ERRORS
        ):
          # RRG already filters out non-critical errors, so ALL_ERRORS is
          # equivalent to CRITICAL_ERRORS.
          self.SendReplyProto(
              flows_pb2.ProcessMemoryError(
                  process=process,
                  error=result.error,
              )
          )
        continue
      if not result.matching_rules:
        if self.proto_args.include_misses_in_results:
          self.SendReplyProto(flows_pb2.YaraProcessScanMiss(process=process))
        continue

      scan_match = flows_pb2.YaraProcessScanMatch(process=process)
      match_offsets = []
      for rule in result.matching_rules:
        matching_rule = scan_match.match.add(
            rule_name=rule.identifier,
        )
        for pattern in rule.patterns:
          for pattern_match in pattern.matches:
            data = data_store.BLOBS.ReadBlob(
                models_blobs.BlobID(pattern_match.data_sha256)
            )
            matching_rule.string_matches.add(
                string_id=pattern.identifier,
                offset=pattern_match.offset,
                data=data,
                # TODO - Populate context parameter.
            )
            match_offsets.append(pattern_match.offset)

      self.SendReplyProto(scan_match)
      if self.proto_args.dump_process_on_match:
        self.CallFlowProto(
            DumpProcessMemory.__name__,
            flow_args=flows_pb2.YaraProcessDumpArgs(
                pids=[process.pid],
                prioritize_offsets=match_offsets,
                size_limit=self.proto_args.process_dump_size_limit,
                skip_mapped_files=self.proto_args.skip_mapped_files,
                skip_shared_regions=self.proto_args.skip_shared_regions,
                skip_executable_regions=self.proto_args.skip_executable_regions,
                skip_readonly_regions=self.proto_args.skip_readonly_regions,
                skip_special_regions=self.proto_args.skip_special_regions,
            ),
            next_state=self.CheckDumpProcessMemoryResults.__name__,
        )


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
        flows_pb2.DumpProcessMemoryStore,
        flows_pb2.DefaultFlowProgress,
    ]
):
  """Acquires memory for a given list of processes."""

  category = "/Memory/"
  friendly_name = "Process Dump"
  behaviours = flow_base.BEHAVIOUR_BASIC

  proto_args_type = flows_pb2.YaraProcessDumpArgs
  proto_store_type = flows_pb2.DumpProcessMemoryStore
  proto_result_types = [
      jobs_pb2.StatEntry,
      flows_pb2.YaraProcessDumpResponse,
  ]

  def Start(self):
    # Catch regex errors early.
    if self.proto_args.process_regex:
      re.compile(self.proto_args.process_regex)

    if self.proto_args.dump_all_processes:
      raise ValueError(
          "dump_all_processes has been deprecated. Please specify individual"
          " pids or a process_regex."
      )

    if not (self.proto_args.pids or self.proto_args.process_regex):
      raise ValueError("No processes to dump specified.")

    if self.proto_args.prioritize_offsets and len(self.proto_args.pids) != 1:
      raise ValueError(
          "Supplied prioritize_offsets {} for PIDs {} in YaraProcessDump. "
          "Required exactly one PID.".format(
              self.proto_args.prioritize_offsets, self.proto_args.pids
          )
      )

    if self.rrg_support:
      self._StartRRG()
      return

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

  def _StartRRG(self):
    self.CallFlowProto(
        processes.ListProcesses.__name__,
        flow_args=flows_pb2.ListProcessesArgs(
            pids=self.proto_args.pids,
            process_name_regex=self.proto_args.process_regex,
        ),
        next_state=self._ProcessListProcesses.__name__,
    )

  @flow_base.UseProto2AnyResponses
  def _ProcessListProcesses(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to invoke list_processes: {responses.status}",
      )

    for response in responses:
      process = sysinfo_pb2.Process()
      process.ParseFromString(response.value)
      self.store.processes[process.pid].CopyFrom(process)

    pids = set(self.store.processes.keys())
    if self.proto_args.pids:
      # If specific PIDs were specified, also include those,
      # even if no process with that PID is running on the client.
      # This way the client can send back an error for that PID.
      pids = pids.union(self.proto_args.pids)

    action = rrg_stubs.DumpProcessMemory()
    action.args.pids.extend(pids)
    action.args.priority_offsets.extend(self.proto_args.prioritize_offsets)
    if self.proto_args.size_limit:
      action.args.total_size_limit = self.proto_args.size_limit
    if self.proto_args.skip_special_regions:
      self.Log(
          "skip_special_regions is no longer supported in the client, ignoring."
      )
    action.args.skip_mapped_files = self.proto_args.skip_mapped_files
    action.args.skip_shared_regions = self.proto_args.skip_shared_regions
    action.args.skip_executable_regions = (
        self.proto_args.skip_executable_regions
    )
    action.args.skip_readonly_regions = self.proto_args.skip_readonly_regions
    action.Call(self._ProcessRegions)

  @flow_base.UseProto2AnyResponses
  def _ProcessRegions(
      self,
      responses: flow_responses.Responses[any_pb2.Any],
  ) -> None:
    if not responses.success:
      raise flow_base.FlowError(
          f"Failed to invoke dump_process_memory: {responses.status}",
      )

    results_by_pid: collections.defaultdict[
        int, list[rrg_dump_process_memory_pb2.Result]
    ] = collections.defaultdict(list)
    for response_any in responses:
      result = rrg_dump_process_memory_pb2.Result()
      result.ParseFromString(response_any.value)
      results_by_pid[result.pid].append(result)

    response = flows_pb2.YaraProcessDumpResponse()
    for pid, results in results_by_pid.items():
      # It's possible that ListProcesses was not able to retrieve
      # information for this process, so we only set the PID in that case.
      process = self.store.processes.get(pid, sysinfo_pb2.Process(pid=pid))
      if len(results) == 1 and results[0].error:
        # Only propagate process-level errors.
        response.errors.add(
            process=process,
            error=results[0].error,
        )
        continue

      results.sort(key=lambda result: result.region_start)

      dumped_process = response.dumped_processes.add(process=process)
      current_region: flows_pb2.ProcessMemoryRegion | None = None
      current_region_blobs = []
      for result in results:
        if result.error:
          # Ignore individual region dump errors for now.
          continue
        blob = objects_pb2.BlobReference(
            offset=result.offset,
            size=result.size,
            blob_id=result.blob_sha256,
        )
        if current_region is not None:
          if result.region_start == current_region.start:
            # This is a continuation of the current region.
            current_region_blobs.append(blob)
            current_region.dumped_size += result.size
            if current_region.dumped_size == current_region.size:
              # dumped_size should be unset when the whole region was dumped.
              current_region.ClearField("dumped_size")
            continue
          # This is a new region, so write the contents of the previous region.
          self._WriteRegionContents(current_region_blobs, current_region.file)
        current_region = dumped_process.memory_regions.add(
            start=result.region_start,
            size=(result.region_end - result.region_start),
            file=jobs_pb2.PathSpec(
                path=f"{self.flow_id}_{pid}_{hex(result.region_start)}",
                pathtype=jobs_pb2.PathSpec.PathType.TMPFILE,
            ),
            is_executable=result.permissions.execute,
            is_writable=result.permissions.write,
            is_readable=result.permissions.read,
            dumped_size=result.size,
        )
        current_region_blobs = [blob]

      if current_region is not None:
        self._WriteRegionContents(current_region_blobs, current_region.file)

    self.SendReplyProto(response)

  def _WriteRegionContents(
      self,
      blobs: list[objects_pb2.BlobReference],
      pathspec: jobs_pb2.PathSpec,
  ):
    """Writes a list of blobs into a temporary file in the file store."""
    path_info = objects_pb2.PathInfo(
        components=[pathspec.path],
        path_type=pathspec.pathtype,
    )
    hash_id = file_store.AddFileWithUnknownHash(
        db.ClientPath.FromPathInfo(self.client_id, path_info),
        blobs,
    )
    path_info.hash_entry.sha256 = hash_id.AsBytes()
    path_info.hash_entry.num_bytes = sum(b.size for b in blobs)
    path_info.hash_entry.source_offset = min(b.offset for b in blobs)
    data_store.REL_DB.WritePathInfos(self.client_id, [path_info])
