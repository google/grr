#!/usr/bin/env python
"""Yara based client actions."""

import os
import re
import time

import psutil
import yara
import yara_procdump

from grr.client import actions
from grr.client.client_actions import tempfiles
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import paths as rdf_paths
from grr.lib.rdfvalues import rdf_yara


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

  def Run(self, args):
    result = rdf_yara.YaraProcessScanResponse()

    rules = args.yara_signature.GetRules()

    for p in ProcessIterator(args.pids, args.process_regex,
                             args.ignore_grr_process, result.errors):
      self.Progress()
      start_time = time.time()
      try:
        matches = rules.match(pid=p.pid, timeout=args.per_process_timeout)
        scan_time = time.time() - start_time
        scan_time_us = int(scan_time * 1e6)
      except yara.TimeoutError:
        result.errors.Append(
            rdf_yara.YaraProcessError(
                process=rdf_client.Process.FromPsutilProcess(p),
                error="Scanning timed out (%s seconds)." %
                (time.time() - start_time)))
        continue
      except Exception as e:  # pylint: disable=broad-except
        result.errors.Append(
            rdf_yara.YaraProcessError(
                process=rdf_client.Process.FromPsutilProcess(p), error=str(e)))
        continue

      rdf_process = rdf_client.Process.FromPsutilProcess(p)

      if matches:
        for match in matches:
          result.matches.Append(
              rdf_yara.YaraProcessScanMatch(
                  process=rdf_process,
                  match=rdf_yara.YaraMatch.FromLibYaraMatch(match),
                  scan_time_us=scan_time_us))
      else:
        result.misses.Append(
            rdf_yara.YaraProcessScanMiss(
                process=rdf_process, scan_time_us=scan_time_us))

    self.SendReply(result)


class YaraProcessDump(actions.ActionPlugin):
  """Dumps a process to disk and returns pathspecs for GRR to pick up."""
  in_rdfvalue = rdf_yara.YaraProcessDumpArgs
  out_rdfvalues = [rdf_yara.YaraProcessDumpResponse]

  def DumpProcess(self, psutil_process, bytes_limit):
    response = rdf_yara.YaraProcessDumpInformation()
    response.process = rdf_client.Process.FromPsutilProcess(psutil_process)

    iterator = yara_procdump.process_memory_iterator(pid=psutil_process.pid)
    name = psutil_process.name()

    with tempfiles.TemporaryDirectory(cleanup=False) as tmp_dir:
      for block in iterator:

        filename_template = "%s_%d_%x_%x.tmp"
        filename = os.path.join(tmp_dir.path, filename_template %
                                (name, psutil_process.pid, block.base,
                                 block.base + block.size))

        if bytes_limit and self.bytes_written + block.size > bytes_limit:
          response.error = ("Memory limit exceeded. Wrote %d bytes, "
                            "next block is %d bytes, limit is %d." %
                            (self.bytes_written, block.size, bytes_limit))
          return response

        with open(filename, "wb") as fd:
          fd.write(block)

        self.bytes_written += block.size

        response.dump_files.Append(
            rdf_paths.PathSpec(
                path=filename, pathtype=rdf_paths.PathSpec.PathType.TMPFILE))
    return response

  def Run(self, args):
    result = rdf_yara.YaraProcessDumpResponse()

    self.bytes_written = 0

    for p in ProcessIterator(args.pids, args.process_regex,
                             args.ignore_grr_process, result.errors):
      self.Progress()
      start_time = time.time()

      try:
        response = self.DumpProcess(p, args.size_limit)
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
