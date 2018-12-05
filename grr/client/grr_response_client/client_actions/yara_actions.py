#!/usr/bin/env python
"""Yara based client actions."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os
import re
import time

import psutil
import yara

from grr_response_client import actions
from grr_response_client import client_utils
from grr_response_client import streaming
from grr_response_client.client_actions import tempfiles
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import rdf_yara


def ProcessIterator(pids, process_regex_string, ignore_grr_process, error_list):
  """Yields all (psutil-) processes that match certain criteria.

  Args:
    pids: A list of pids. If given, only the processes with those pids are
          returned.
    process_regex_string: If given, only processes whose name matches the regex
          are returned.
    ignore_grr_process: If True, the grr process itself will not be returned.
    error_list: All errors while handling processes are appended to this
                list. Type is repeated YaraProcessError.

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
            rdf_yara.YaraProcessError(
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
  in_rdfvalue = rdf_yara.YaraProcessScanRequest
  out_rdfvalues = [rdf_yara.YaraProcessScanResponse]

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
            rdf_match = rdf_yara.YaraMatch.FromLibYaraMatch(m)
            for s in rdf_match.string_matches:
              s.offset += chunk.offset
            yield rdf_match
            break

  def _ScanProcess(self, psutil_process, args):
    if args.per_process_timeout:
      deadline = rdfvalue.RDFDatetime.Now() + args.per_process_timeout
    else:
      deadline = rdfvalue.RDFDatetime.Now() + rdfvalue.Duration("1w")

    rules = args.yara_signature.GetRules()

    process = client_utils.OpenProcessForMemoryAccess(pid=psutil_process.pid)
    with process:
      streamer = streaming.Streamer(
          chunk_size=args.chunk_size, overlap_size=args.overlap_size)
      matches = []

      try:
        for start, length in client_utils.MemoryRegions(process, args):
          chunks = streamer.StreamMemory(process, offset=start, amount=length)
          for m in self._ScanRegion(rules, chunks, deadline):
            matches.append(m)
            if (args.max_results_per_process > 0 and
                len(matches) >= args.max_results_per_process):
              return matches
      except yara.Error as e:
        # Yara internal error 30 is too many hits (obviously...). We
        # need to report this as a hit, not an error.
        if e.message == "internal error: 30":
          return matches
        raise

    return matches

  def Run(self, args):
    result = rdf_yara.YaraProcessScanResponse()
    for p in ProcessIterator(args.pids, args.process_regex,
                             args.ignore_grr_process, result.errors):
      self.Progress()
      rdf_process = rdf_client.Process.FromPsutilProcess(p)

      start_time = time.time()
      try:
        matches = self._ScanProcess(p, args)
        scan_time = time.time() - start_time
        scan_time_us = int(scan_time * 1e6)
      except yara.TimeoutError:
        result.errors.Append(
            rdf_yara.YaraProcessError(
                process=rdf_process,
                error="Scanning timed out (%s seconds)." %
                (time.time() - start_time)))
        continue
      except Exception as e:  # pylint: disable=broad-except
        result.errors.Append(
            rdf_yara.YaraProcessError(process=rdf_process, error=str(e)))
        continue

      if matches:
        result.matches.Append(
            rdf_yara.YaraProcessScanMatch(
                process=rdf_process, match=matches, scan_time_us=scan_time_us))
      else:
        result.misses.Append(
            rdf_yara.YaraProcessScanMiss(
                process=rdf_process, scan_time_us=scan_time_us))

    self.SendReply(result)


class YaraProcessDump(actions.ActionPlugin):
  """Dumps a process to disk and returns pathspecs for GRR to pick up."""
  in_rdfvalue = rdf_yara.YaraProcessDumpArgs
  out_rdfvalues = [rdf_yara.YaraProcessDumpResponse]

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
    response = rdf_yara.YaraProcessDumpInformation()
    response.process = rdf_client.Process.FromPsutilProcess(psutil_process)

    process = client_utils.OpenProcessForMemoryAccess(pid=psutil_process.pid)

    bytes_limit = args.size_limit

    with process:
      streamer = streaming.Streamer(chunk_size=args.chunk_size)

      with tempfiles.TemporaryDirectory(cleanup=False) as tmp_dir:
        for start, length in client_utils.MemoryRegions(process, args):

          if bytes_limit and self.bytes_written + length > bytes_limit:
            response.error = ("Byte limit exceeded. Wrote %d bytes, "
                              "next block is %d bytes, limit is %d." %
                              (self.bytes_written, length, bytes_limit))
            return response

          end = start + length
          filename = "%s_%d_%x_%x.tmp" % (psutil_process.name(),
                                          psutil_process.pid, start, end)
          filepath = os.path.join(tmp_dir.path, filename)

          chunks = streamer.StreamMemory(process, offset=start, amount=length)
          bytes_written = self._SaveMemDumpToFilePath(filepath, chunks)

          if not bytes_written:
            continue

          self.bytes_written += bytes_written
          response.dump_files.Append(
              rdf_paths.PathSpec(
                  path=filepath, pathtype=rdf_paths.PathSpec.PathType.TMPFILE))

    return response

  def Run(self, args):
    result = rdf_yara.YaraProcessDumpResponse()

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
            rdf_yara.YaraProcessError(
                process=rdf_client.Process.FromPsutilProcess(p), error=str(e)))
        continue

    self.SendReply(result)
