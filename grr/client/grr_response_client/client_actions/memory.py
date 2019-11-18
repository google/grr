#!/usr/bin/env python
"""Client actions dealing with memory."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import collections
import io
import os
import re
import shutil

from future.builtins import str

import psutil

from typing import Iterable
from typing import List

import yara

from grr_response_client import actions
from grr_response_client import client_utils
from grr_response_client import streaming
from grr_response_client.client_actions import tempfiles
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_core.lib.rdfvalues import paths as rdf_paths


def ProcessIterator(pids, process_regex_string, cmdline_regex_string,
                    ignore_grr_process, error_list):
  """Yields all (psutil-) processes that match certain criteria.

  Args:
    pids: A list of pids. If given, only the processes with those pids are
      returned.
    process_regex_string: If given, only processes whose name matches the regex
      are returned.
    cmdline_regex_string: If given, only processes whose cmdline matches the
      regex are returned.
    ignore_grr_process: If True, the grr process itself will not be returned.
    error_list: All errors while handling processes are appended to this list.
      Type is repeated ProcessMemoryError.

  Yields:
    psutils.Process objects matching all criteria.
  """
  pids = set(pids)
  if ignore_grr_process:
    grr_pid = psutil.Process().pid
  else:
    grr_pid = -1

  if process_regex_string:
    process_regex = re.compile(process_regex_string)
  else:
    process_regex = None

  if cmdline_regex_string:
    cmdline_regex = re.compile(cmdline_regex_string)
  else:
    cmdline_regex = None

  if pids:
    process_iterator = []
    for pid in pids:
      try:
        process_iterator.append(psutil.Process(pid=pid))
      except Exception as e:  # pylint: disable=broad-except
        error_list.Append(
            rdf_memory.ProcessMemoryError(
                process=rdf_client.Process(pid=pid), error=str(e)))
  else:
    process_iterator = psutil.process_iter()

  for p in process_iterator:
    if process_regex and not process_regex.search(p.name()):
      continue

    if cmdline_regex and not cmdline_regex.search(" ".join(p.cmdline())):
      continue

    if p.pid == grr_pid:
      continue

    yield p


class YaraProcessScan(actions.ActionPlugin):
  """Scans the memory of a number of processes using Yara."""
  in_rdfvalue = rdf_memory.YaraProcessScanRequest
  out_rdfvalues = [rdf_memory.YaraProcessScanResponse]

  def _ScanRegion(self, rules, chunks, deadline):
    for chunk in chunks:
      if not chunk.data:
        break

      self.Progress()

      time_left = (deadline - rdfvalue.RDFDatetime.Now()).ToInt(
          rdfvalue.SECONDS)

      for m in rules.match(data=chunk.data, timeout=time_left):
        # Note that for regexps in general it might be possible to
        # specify characters at the end of the string that are not
        # part of the returned match. In that case, this algorithm
        # might miss results in unlikely scenarios. We doubt that the
        # Yara library even allows such constructs but it's good to be
        # aware that this can happen.
        for offset, _, s in m.strings:
          if offset + len(s) > chunk.overlap:
            # We haven't seen this match before.
            rdf_match = rdf_memory.YaraMatch.FromLibYaraMatch(m)
            for string_match in rdf_match.string_matches:
              string_match.offset += chunk.offset
            yield rdf_match
            break

  def _GetMatches(self, psutil_process, scan_request):
    if scan_request.per_process_timeout:
      deadline = rdfvalue.RDFDatetime.Now() + scan_request.per_process_timeout
    else:
      deadline = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration.From(
          1, rdfvalue.WEEKS)

    rules = scan_request.yara_signature.GetRules()

    process = client_utils.OpenProcessForMemoryAccess(pid=psutil_process.pid)
    with process:
      streamer = streaming.Streamer(
          chunk_size=scan_request.chunk_size,
          overlap_size=scan_request.overlap_size)
      matches = []

      try:
        for region in client_utils.MemoryRegions(process, scan_request):
          chunks = streamer.StreamMemory(
              process, offset=region.start, amount=region.size)
          for m in self._ScanRegion(rules, chunks, deadline):
            matches.append(m)
            if 0 < scan_request.max_results_per_process <= len(matches):
              return matches
      except yara.Error as e:
        # Yara internal error 30 is too many hits (obviously...). We
        # need to report this as a hit, not an error.
        if "internal error: 30" in str(e):
          return matches
        raise

    return matches

  # We don't want individual response messages to get too big so we send
  # multiple responses for 100 processes each.
  _RESULTS_PER_RESPONSE = 100

  def _ScanProcess(self, process, scan_request, scan_response):
    rdf_process = rdf_client.Process.FromPsutilProcess(process)

    start_time = rdfvalue.RDFDatetime.Now()
    try:
      matches = self._GetMatches(process, scan_request)
      scan_time = rdfvalue.RDFDatetime.Now() - start_time
      scan_time_us = scan_time.ToInt(rdfvalue.MICROSECONDS)
    except yara.TimeoutError:
      scan_response.errors.Append(
          rdf_memory.ProcessMemoryError(
              process=rdf_process,
              error="Scanning timed out (%s)." %
              (rdfvalue.RDFDatetime.Now() - start_time)))
      return
    except Exception as e:  # pylint: disable=broad-except
      scan_response.errors.Append(
          rdf_memory.ProcessMemoryError(process=rdf_process, error=str(e)))
      return

    if matches:
      scan_response.matches.Append(
          rdf_memory.YaraProcessScanMatch(
              process=rdf_process, match=matches, scan_time_us=scan_time_us))
    else:
      scan_response.misses.Append(
          rdf_memory.YaraProcessScanMiss(
              process=rdf_process, scan_time_us=scan_time_us))

  def _SaveSignatureShard(self, scan_request):
    """Writes a YaraSignatureShard received from the server to disk.

    Args:
      scan_request: The YaraProcessScanRequest sent by the server.

    Returns:
      The full Yara signature, if all shards have been received. Otherwise,
      None is returned.
    """

    def GetShardName(shard_index, num_shards):
      return "shard_%02d_of_%02d" % (shard_index, num_shards)

    signature_dir = os.path.join(tempfiles.GetDefaultGRRTempDirectory(),
                                 "Sig_%s" % self.session_id.Basename())
    # Create the temporary directory and set permissions, if it does not exist.
    tempfiles.EnsureTempDirIsSane(signature_dir)
    shard_path = os.path.join(
        signature_dir,
        GetShardName(scan_request.signature_shard.index,
                     scan_request.num_signature_shards))
    with io.open(shard_path, "wb") as f:
      f.write(scan_request.signature_shard.payload)

    dir_contents = set(os.listdir(signature_dir))
    all_shards = [
        GetShardName(i, scan_request.num_signature_shards)
        for i in range(scan_request.num_signature_shards)
    ]
    if dir_contents.issuperset(all_shards):
      # All shards have been received; delete the temporary directory and
      # return the full signature.
      full_signature = io.BytesIO()
      for shard in all_shards:
        with io.open(os.path.join(signature_dir, shard), "rb") as f:
          full_signature.write(f.read())
      shutil.rmtree(signature_dir, ignore_errors=True)
      return full_signature.getvalue().decode("utf-8")
    else:
      return None

  def Run(self, args):
    if args.yara_signature or not args.signature_shard.payload:
      raise ValueError(
          "A Yara signature shard is required, and not the full signature.")

    if args.num_signature_shards == 1:
      # Skip saving to disk if there is just one shard.
      yara_signature = args.signature_shard.payload.decode("utf-8")
    else:
      yara_signature = self._SaveSignatureShard(args)
      if yara_signature is None:
        # We haven't received the whole signature yet.
        return

    scan_request = args.Copy()
    scan_request.yara_signature = yara_signature
    scan_response = rdf_memory.YaraProcessScanResponse()
    processes = ProcessIterator(scan_request.pids, scan_request.process_regex,
                                scan_request.cmdline_regex,
                                scan_request.ignore_grr_process,
                                scan_response.errors)

    for process in processes:
      self.Progress()
      num_results = (
          len(scan_response.errors) + len(scan_response.matches) +
          len(scan_response.misses))
      if num_results >= self._RESULTS_PER_RESPONSE:
        self.SendReply(scan_response)
        scan_response = rdf_memory.YaraProcessScanResponse()
      self._ScanProcess(process, scan_request, scan_response)

    self.SendReply(scan_response)


def _PrioritizeRegions(
    regions,
    prioritize_offsets
):
  """Returns reordered `regions` to prioritize regions containing offsets.

  Args:
    regions: Iterable of ProcessMemoryRegions.
    prioritize_offsets: List of integers containing prioritized offsets.  Pass
      pre-sorted regions and offsets to improve this functions performance from
      O(n * log n) to O(n) respectively.

  Returns:
    An iterable of first all ProcessMemoryRegions that contain a prioritized
    offset, followed by all regions that do not contain a prioritized offset.
    All prioritized regions and all unprioritized regions are sorted by their
    starting address.
  """

  # Sort regions and offsets to be mononotically increasing and insert sentinel.
  all_regions = collections.deque(sorted(regions, key=lambda r: r.start))
  all_regions.append(None)
  region = all_regions.popleft()

  all_offsets = collections.deque(sorted(prioritize_offsets))
  all_offsets.append(None)
  offset = all_offsets.popleft()

  prio_regions = []
  nonprio_regions = []

  # This loop runs in O(max(|regions|, |offsets|)) with use of invariants:
  # - offset is increasing monotonically.
  # - region[n+1] end >= region[n+1] start >= region[n] start
  # Because memory regions could theoretically overlap, no relationship exists
  # between the end of region[n+1] and region[n].

  while region is not None and offset is not None:
    if offset < region.start:
      # Offset is before the first region, thus cannot be contained in any
      # region. This could happen when some memory regions are unreadable.
      offset = all_offsets.popleft()
    elif offset >= region.start + region.size:
      # Offset comes after the first region. The first region can not contain
      # any following offsets, because offsets increase monotonically.
      nonprio_regions.append(region)
      region = all_regions.popleft()
    else:
      # The first region contains the offset. Mark it as prioritized and
      # proceed with the next offset. All following offsets that are contained
      # in the current region are skipped with the first if-branch.
      prio_regions.append(region)
      region = all_regions.popleft()
      offset = all_offsets.popleft()

  all_regions.appendleft(region)  # Put back the current region or sentinel.
  all_regions.pop()  # Remove sentinel.

  # When there are fewer offsets than regions, remaining regions can be present
  # in `all_regions`.
  return prio_regions + nonprio_regions + list(all_regions)


def _ApplySizeLimit(regions,
                    size_limit):
  """Truncates regions so that the total size stays in size_limit."""
  total_size = 0
  regions_in_limit = []
  for region in regions:
    total_size += region.size
    if total_size > size_limit:
      break
    regions_in_limit.append(region)
  return regions_in_limit


class YaraProcessDump(actions.ActionPlugin):
  """Dumps a process to disk and returns pathspecs for GRR to pick up."""
  in_rdfvalue = rdf_memory.YaraProcessDumpArgs
  out_rdfvalues = [rdf_memory.YaraProcessDumpResponse]

  def _SaveMemDumpToFile(self, fd, chunks):
    bytes_written = 0

    for chunk in chunks:
      if not chunk.data:
        return 0

      fd.write(chunk.data)
      bytes_written += len(chunk.data)

    return bytes_written

  def _SaveMemDumpToFilePath(self, filename, chunks):
    with open(filename, "wb") as fd:
      bytes_written = self._SaveMemDumpToFile(fd, chunks)

    # When getting read errors, we just delete the file and move on.
    if not bytes_written:
      try:
        os.remove(filename)
      except OSError:
        pass

    return bytes_written

  def _SaveRegionToDirectory(self, psutil_process, process, region, tmp_dir,
                             streamer):
    end = region.start + region.size

    # _ReplaceDumpPathspecsWithMultiGetFilePathspec in DumpProcessMemory
    # flow asserts that MemoryRegions can be uniquely identified by their
    # file's basename.
    filename = "%s_%d_%x_%x.tmp" % (psutil_process.name(), psutil_process.pid,
                                    region.start, end)
    filepath = os.path.join(tmp_dir.path, filename)

    chunks = streamer.StreamMemory(
        process, offset=region.start, amount=region.size)
    bytes_written = self._SaveMemDumpToFilePath(filepath, chunks)

    if not bytes_written:
      return None

    # TODO: Remove workaround after client_utils are fixed.
    canonical_path = client_utils.LocalPathToCanonicalPath(filepath)
    if not canonical_path.startswith("/"):
      canonical_path = "/" + canonical_path

    return rdf_paths.PathSpec(
        path=canonical_path, pathtype=rdf_paths.PathSpec.PathType.TMPFILE)

  def DumpProcess(self, psutil_process, args):
    response = rdf_memory.YaraProcessDumpInformation()
    response.process = rdf_client.Process.FromPsutilProcess(psutil_process)
    streamer = streaming.Streamer(chunk_size=args.chunk_size)

    with client_utils.OpenProcessForMemoryAccess(psutil_process.pid) as process:
      regions = list(client_utils.MemoryRegions(process, args))

      if args.prioritize_offsets:
        regions = _PrioritizeRegions(regions, args.prioritize_offsets)

      if args.size_limit:
        total_regions = len(regions)
        regions = _ApplySizeLimit(regions, args.size_limit)
        if len(regions) < total_regions:
          response.error = ("Byte limit exceeded. Writing {} of {} "
                            "regions.").format(len(regions), total_regions)

      regions = sorted(regions, key=lambda r: r.start)

      with tempfiles.TemporaryDirectory(cleanup=False) as tmp_dir:
        for region in regions:
          self.Progress()
          pathspec = self._SaveRegionToDirectory(psutil_process, process,
                                                 region, tmp_dir, streamer)
          if pathspec is not None:
            region.file = pathspec
            response.memory_regions.Append(region)

    return response

  def Run(self, args):
    if args.prioritize_offsets and len(args.pids) != 1:
      raise ValueError(
          "Supplied prioritize_offsets {} for PIDs {} in YaraProcessDump. "
          "Required exactly one PID.".format(args.prioritize_offsets,
                                             args.pids))

    result = rdf_memory.YaraProcessDumpResponse()

    for p in ProcessIterator(args.pids, args.process_regex, None,
                             args.ignore_grr_process, result.errors):
      self.Progress()
      start = rdfvalue.RDFDatetime.Now()

      try:
        response = self.DumpProcess(p, args)
        now = rdfvalue.RDFDatetime.Now()
        response.dump_time_us = (now - start).ToInt(rdfvalue.MICROSECONDS)
        result.dumped_processes.Append(response)
        if response.error:
          # Limit exceeded, we bail out early.
          break
      except Exception as e:  # pylint: disable=broad-except
        result.errors.Append(
            rdf_memory.ProcessMemoryError(
                process=rdf_client.Process.FromPsutilProcess(p), error=str(e)))
        continue

    self.SendReply(result)
