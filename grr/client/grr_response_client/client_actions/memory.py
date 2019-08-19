#!/usr/bin/env python
"""Client actions dealing with memory."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import io
import os
import re
import shutil
import time

from future.builtins import str

import psutil
import yara

from grr_response_client import actions
from grr_response_client import client_utils
from grr_response_client import streaming
from grr_response_client.client_actions import tempfiles
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import memory as rdf_memory
from grr_response_core.lib.rdfvalues import paths as rdf_paths


def ProcessIterator(pids, process_regex_string, ignore_grr_process, error_list):
  """Yields all (psutil-) processes that match certain criteria.

  Args:
    pids: A list of pids. If given, only the processes with those pids are
      returned.
    process_regex_string: If given, only processes whose name matches the regex
      are returned.
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

      time_left = deadline - rdfvalue.RDFDatetime.Now()

      for m in rules.match(data=chunk.data, timeout=int(time_left)):
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
      deadline = rdfvalue.RDFDatetime.Now() + rdfvalue.DurationSeconds("1w")

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

    # TODO: Replace time.time() arithmetic with RDFDatetime
    # subtraction.
    start_time = time.time()
    try:
      matches = self._GetMatches(process, scan_request)
      scan_time = time.time() - start_time
      scan_time_us = int(scan_time * 1e6)
    except yara.TimeoutError:
      scan_response.errors.Append(
          rdf_memory.ProcessMemoryError(
              process=rdf_process,
              error="Scanning timed out (%s seconds)." %
              (time.time() - start_time)))
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

    yara_signature = self._SaveSignatureShard(args)
    if yara_signature is None:
      # We haven't received the whole signature yet.
      return

    scan_request = args.Copy()
    scan_request.yara_signature = yara_signature
    scan_response = rdf_memory.YaraProcessScanResponse()
    processes = ProcessIterator(scan_request.pids, scan_request.process_regex,
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

  def DumpProcess(self, psutil_process, args):
    response = rdf_memory.YaraProcessDumpInformation()
    response.process = rdf_client.Process.FromPsutilProcess(psutil_process)

    process = client_utils.OpenProcessForMemoryAccess(pid=psutil_process.pid)

    bytes_limit = args.size_limit

    with process:
      streamer = streaming.Streamer(chunk_size=args.chunk_size)

      with tempfiles.TemporaryDirectory(cleanup=False) as tmp_dir:
        for region in client_utils.MemoryRegions(process, args):

          if bytes_limit and self.bytes_written + region.size > bytes_limit:
            response.error = ("Byte limit exceeded. Wrote %d bytes, "
                              "next block is %d bytes, limit is %d." %
                              (self.bytes_written, region.size, bytes_limit))
            return response

          end = region.start + region.size

          # _ReplaceDumpPathspecsWithMultiGetFilePathspec in DumpProcessMemory
          # flow asserts that MemoryRegions can be uniquely identified by their
          # file's basename.
          filename = "%s_%d_%x_%x.tmp" % (psutil_process.name(),
                                          psutil_process.pid, region.start, end)
          filepath = os.path.join(tmp_dir.path, filename)

          chunks = streamer.StreamMemory(
              process, offset=region.start, amount=region.size)
          bytes_written = self._SaveMemDumpToFilePath(filepath, chunks)

          if not bytes_written:
            continue

          self.bytes_written += bytes_written

          # TODO: Remove workaround after client_utils are fixed.
          canonical_path = client_utils.LocalPathToCanonicalPath(filepath)
          if not canonical_path.startswith("/"):
            canonical_path = "/" + canonical_path

          region.file = rdf_paths.PathSpec(
              path=canonical_path, pathtype=rdf_paths.PathSpec.PathType.TMPFILE)

          response.memory_regions.Append(region)

    return response

  def Run(self, args):
    result = rdf_memory.YaraProcessDumpResponse()

    self.bytes_written = 0

    for p in ProcessIterator(args.pids, args.process_regex,
                             args.ignore_grr_process, result.errors):
      self.Progress()
      start_time = time.time()

      try:
        response = self.DumpProcess(p, args)
        response.dump_time_us = int((time.time() - start_time) * 1e6)
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
