#!/usr/bin/env python
"""Flows related to process memory."""

import collections
import logging
import re
from typing import Iterable, Union

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.util import compatibility
from grr_response_server import data_store
from grr_response_server import flow_base
from grr_response_server import flow_responses
from grr_response_server import server_stubs
from grr_response_server.flows.general import transfer
from grr_response_server.rdfvalues import objects as rdf_objects

_YARA_SIGNATURE_SHARD_SIZE = 500 << 10  # 500 KiB


class YaraProcessScan(flow_base.FlowBase):
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

  def _ValidateFlowArgs(self):
    if self.args.yara_signature and self.args.yara_signature_blob_id:
      message = ("`yara_signature` can't be used together with "
                 "`yara_signature_blob_id")
      raise flow_base.FlowError(message)
    elif self.args.yara_signature:
      rules = self.args.yara_signature.GetRules()
      if not list(rules):
        raise flow_base.FlowError(
            "No rules found in the signature specification.")
    elif self.args.yara_signature_blob_id:
      blob_id = rdf_objects.BlobID(self.args.yara_signature_blob_id)
      if not data_store.REL_DB.VerifyYaraSignatureReference(blob_id):
        message = "Incorrect YARA signature reference: {}".format(blob_id)
        raise flow_base.FlowError(message)
    else:
      raise flow_base.FlowError(
          "Flow args contain neither yara_signature nor yara_signature_blob_id."
          " Provide a yara_signature for scanning.")

    if self.args.process_regex and self.args.cmdline_regex:
      raise flow_base.FlowError(
          "Use either process_regex to match process names"
          "or cmdline_regex to match the process cmdline.")

    if self.args.process_regex:
      re.compile(self.args.process_regex)

    if self.args.cmdline_regex:
      re.compile(self.args.cmdline_regex)

  def Start(self):
    """See base class."""
    self._ValidateFlowArgs()
    if self.client_version < 3306:
      # TODO(user): Remove when support ends for old clients (Jan 1 2022).
      self.CallClient(
          server_stubs.YaraProcessScan,
          request=self.args,
          next_state=compatibility.GetName(self.ProcessScanResults))
      return

    if self.args.scan_runtime_limit_us:
      # Back up original runtime limit. Override it for YaraProcessScan action
      # only.
      request_data = {"runtime_limit_us": self.rdf_flow.runtime_limit_us}
      self.rdf_flow.runtime_limit_us = self.args.scan_runtime_limit_us
    else:
      request_data = None

    if self.args.yara_signature:
      signature_bytes = str(self.args.yara_signature).encode("utf-8")
    elif self.args.yara_signature_blob_id:
      blob_id = rdf_objects.BlobID(self.args.yara_signature_blob_id)
      signature_bytes = data_store.BLOBS.ReadBlob(blob_id)

    offsets = range(0, len(signature_bytes), _YARA_SIGNATURE_SHARD_SIZE)
    for i, offset in enumerate(offsets):
      client_request = self.args.Copy()
      # We do not want to send the whole signature to the client, so we clear
      # the field.
      client_request.yara_signature = None
      client_request.signature_shard = rdf_memory.YaraSignatureShard(
          index=i,
          payload=signature_bytes[offset:offset + _YARA_SIGNATURE_SHARD_SIZE])
      client_request.num_signature_shards = len(offsets)
      self.CallClient(
          server_stubs.YaraProcessScan,
          request=client_request,
          request_data=request_data,
          next_state=compatibility.GetName(self.ProcessScanResults))

  def ProcessScanResults(
      self,
      responses: flow_responses.Responses[rdf_memory.YaraProcessScanResponse]):
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
          "runtime_limit_us"]

    regions_to_dump = collections.defaultdict(set)

    for response in responses:
      for match in response.matches:
        self.SendReply(match)
        rules = set([m.rule_name for m in match.match])
        rules_string = ",".join(sorted(rules))
        logging.debug("YaraScan match in pid %d (%s) for rules %s.",
                      match.process.pid, match.process.exe, rules_string)

        if self.args.dump_process_on_match:
          for process_match in match.match:
            for string_match in process_match.string_matches:
              regions_to_dump[match.process.pid].add(string_match.offset)

      for error in response.errors:
        if self._ShouldIncludeError(error):
          self.SendReply(error)

      if self.args.include_misses_in_results:
        for miss in response.misses:
          self.SendReply(miss)

    for pid, offsets in regions_to_dump.items():
      self.CallFlow(
          DumpProcessMemory.__name__,
          pids=[pid],
          prioritize_offsets=list(sorted(offsets)),
          size_limit=self.args.process_dump_size_limit,
          skip_special_regions=self.args.skip_special_regions,
          skip_mapped_files=self.args.skip_mapped_files,
          skip_shared_regions=self.args.skip_shared_regions,
          skip_executable_regions=self.args.skip_executable_regions,
          skip_readonly_regions=self.args.skip_readonly_regions,
          next_state=compatibility.GetName(self.CheckDumpProcessMemoryResults))

  def CheckDumpProcessMemoryResults(self, responses: flow_responses.Responses[
      Union[rdf_client_fs.StatEntry, rdf_memory.YaraProcessDumpResponse]]):
    # First send responses to parent Flow, then indicate potential errors, to
    # increase robustness.
    for response in responses:
      self.SendReply(response)

    if not responses.success:
      raise flow_base.FlowError(responses.status)

  def _ShouldIncludeError(self, error: rdf_memory.ProcessMemoryError) -> bool:
    ErrorPolicy = self.args.ErrorPolicy  # pylint: disable=invalid-name

    if self.args.include_errors_in_results == ErrorPolicy.NO_ERRORS:
      return False

    if self.args.include_errors_in_results == ErrorPolicy.CRITICAL_ERRORS:
      msg = error.error.lower()
      return ("failed to open process" not in msg and
              "access denied" not in msg)

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


def _MigrateLegacyDumpFilesToMemoryAreas(
    response: rdf_memory.YaraProcessDumpResponse):
  """Migrates a YPDR from dump_files to memory_regions inplace."""
  for info in response.dumped_processes:
    for dump_file in info.dump_files:
      # filename = "%s_%d_%x_%x.tmp" % (process.name, pid, start, end)
      # process.name can contain underscores. Split exactly 3 _ from the right.
      path_without_ext, _ = dump_file.Basename().rsplit(".", 1)
      _, _, start, end = path_without_ext.rsplit("_", 3)
      start = int(start, 16)
      end = int(end, 16)

      info.memory_regions.Append(
          rdf_memory.ProcessMemoryRegion(
              file=_CanonicalizeLegacyWindowsPathSpec(dump_file),
              start=start,
              size=end - start,
          ))
    # Remove dump_files, since new clients do not set it anymore.
    info.dump_files = None


def _ReplaceDumpPathspecsWithMultiGetFilePathspec(
    dump_response: rdf_memory.YaraProcessDumpResponse,
    stat_entries: Iterable[rdf_client_fs.StatEntry]):
  """Replaces a dump's PathSpecs based on their Basename."""
  memory_regions = {}
  for dumped_process in dump_response.dumped_processes:
    for memory_region in dumped_process.memory_regions:
      memory_regions[memory_region.file.Basename()] = memory_region

  for stat_entry in stat_entries:
    memory_regions[stat_entry.pathspec.Basename()].file = rdf_paths.PathSpec(
        stat_entry.pathspec)


class DumpProcessMemory(flow_base.FlowBase):
  """Acquires memory for a given list of processes."""

  category = "/Memory/"
  friendly_name = "Process Dump"

  args_type = rdf_memory.YaraProcessDumpArgs
  result_types = (rdf_client_fs.StatEntry, rdf_memory.YaraProcessDumpResponse)
  behaviours = flow_base.BEHAVIOUR_BASIC

  def Start(self):
    # Catch regex errors early.
    if self.args.process_regex:
      re.compile(self.args.process_regex)

    if not (self.args.dump_all_processes or self.args.pids or
            self.args.process_regex):
      raise ValueError("No processes to dump specified.")

    if self.args.prioritize_offsets and len(self.args.pids) != 1:
      raise ValueError(
          "Supplied prioritize_offsets {} for PIDs {} in YaraProcessDump. "
          "Required exactly one PID.".format(self.args.prioritize_offsets,
                                             self.args.pids))

    self.CallClient(
        server_stubs.YaraProcessDump,
        request=self.args,
        next_state=compatibility.GetName(self.ProcessResults))

  def ProcessResults(
      self,
      responses: flow_responses.Responses[rdf_memory.YaraProcessDumpResponse]):
    """Processes the results of the dump."""
    if not responses.success:
      raise flow_base.FlowError(responses.status)

    response = responses.First()
    _MigrateLegacyDumpFilesToMemoryAreas(response)

    for error in response.errors:
      p = error.process
      self.Log("Error dumping process %s (pid %d): %s" %
               (p.name, p.pid, error.error))

    dump_files_to_get = []
    for dumped_process in response.dumped_processes:
      p = dumped_process.process
      self.Log("Getting %d dump files for process %s (pid %d)." %
               (len(dumped_process.memory_regions), p.name, p.pid))
      for region in dumped_process.memory_regions:
        dump_files_to_get.append(region.file)

    if not dump_files_to_get:
      self.SendReply(response)
      self.Log("No memory dumped, exiting.")
      return

    self.CallFlow(
        transfer.MultiGetFile.__name__,
        pathspecs=dump_files_to_get,
        file_size=1024 * 1024 * 1024,
        use_external_stores=False,
        next_state=compatibility.GetName(self.ProcessMemoryRegions),
        request_data={"YaraProcessDumpResponse": response})

  def ProcessMemoryRegions(
      self, responses: flow_responses.Responses[rdf_client_fs.StatEntry]):
    if not responses.success:
      raise flow_base.FlowError(responses.status)

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
      _ReplaceDumpPathspecsWithMultiGetFilePathspec(dump_response, responses)
      self.SendReply(dump_response)

    for response in responses:
      self.SendReply(response)

      self.CallClient(
          server_stubs.DeleteGRRTempFiles,
          response.pathspec,
          next_state=compatibility.GetName(self.LogDeleteFiles))

  def LogDeleteFiles(
      self, responses: flow_responses.Responses[rdf_client.LogMessage]):
    # Check that the DeleteFiles flow worked.
    if not responses.success:
      raise flow_base.FlowError("Could not delete file: %s" % responses.status)
