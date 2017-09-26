#!/usr/bin/env python
"""Yara based client actions."""

import os
import re

import psutil
import yara

from grr.client import actions
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import rdf_yara


class YaraProcessScan(actions.ActionPlugin):
  """Scans the memory of a number of processes using Yara."""
  in_rdfvalue = rdf_yara.YaraProcessScanRequest
  out_rdfvalues = [rdf_yara.YaraProcessScanResponse]

  def Run(self, args):
    result = rdf_yara.YaraProcessScanResponse()

    rules = args.yara_signature.GetRules()
    pids = set(args.pids)
    process_regex_string = args.process_regex
    grr_pid = os.getpid()

    if process_regex_string:
      process_regex = re.compile(process_regex_string)
    else:
      process_regex = None

    for p in psutil.process_iter():
      self.Progress()

      if pids and p.pid not in pids:
        continue

      if process_regex and not process_regex.search(p.name()):
        continue

      if args.ignore_grr_process and p.pid == grr_pid:
        continue

      try:
        matches = rules.match(pid=p.pid, timeout=args.per_process_timeout)
      except yara.TimeoutError:
        result.errors.Append(
            rdf_yara.YaraProcessScanError(
                process=rdf_client.Process.FromPsutilProcess(p),
                error="Scanning timed out."))
        continue
      except Exception as e:  # pylint: disable=broad-except
        result.errors.Append(
            rdf_yara.YaraProcessScanError(
                process=rdf_client.Process.FromPsutilProcess(p), error=str(e)))
        continue

      rdf_process = rdf_client.Process.FromPsutilProcess(p)

      if matches:
        for match in matches:
          result.matches.Append(
              rdf_yara.YaraProcessScanMatch(
                  process=rdf_process,
                  match=rdf_yara.YaraMatch.FromLibYaraMatch(match)))
      else:
        result.misses.Append(rdf_process)

    self.SendReply(result)
