#!/usr/bin/env python
"""Flows that utilize the Yara library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import re

from grr_response_core.lib.rdfvalues import rdf_yara
from grr_response_server import flow
from grr_response_server import flow_base
from grr_response_server import server_stubs
from grr_response_server.flows.general import transfer


@flow_base.DualDBFlow
class YaraProcessScanMixin(object):
  """Scans process memory using Yara.

  Note that accessing process memory with Yara on Linux causes
  processes to pause. This can impact the client machines when doing
  large scans.
  """

  category = "/Yara/"
  friendly_name = "Yara Process Scan"

  args_type = rdf_yara.YaraProcessScanRequest
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  def Start(self):

    # Catch signature issues early.
    rules = self.args.yara_signature.GetRules()
    if not list(rules):
      raise flow.FlowError("No rules found in the signature specification.")

    # Same for regex errors.
    if self.args.process_regex:
      re.compile(self.args.process_regex)

    self.CallClient(
        server_stubs.YaraProcessScan,
        request=self.args,
        next_state="ProcessScanResults")

  def ProcessScanResults(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    pids_to_dump = set()

    for response in responses:
      for match in response.matches:
        self.SendReply(match)
        rules = set([m.rule_name for m in match.match])
        rules_string = ",".join(sorted(rules))
        logging.debug("YaraScan match in pid %d (%s) for rules %s.",
                      match.process.pid, match.process.exe, rules_string)
        if self.args.dump_process_on_match:
          pids_to_dump.add(match.process.pid)

      if self.args.include_errors_in_results:
        for error in response.errors:
          self.SendReply(error)

      if self.args.include_misses_in_results:
        for miss in response.misses:
          self.SendReply(miss)

    if pids_to_dump:
      self.CallFlow(
          YaraDumpProcessMemory.__name__,  # pylint: disable=undefined-variable
          pids=list(pids_to_dump),
          skip_special_regions=self.args.skip_special_regions,
          skip_mapped_files=self.args.skip_mapped_files,
          skip_shared_regions=self.args.skip_shared_regions,
          skip_executable_regions=self.args.skip_executable_regions,
          skip_readonly_regions=self.args.skip_readonly_regions,
          next_state="CheckDumpProcessMemoryResults")

  def CheckDumpProcessMemoryResults(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    for response in responses:
      self.SendReply(response)


@flow_base.DualDBFlow
class YaraDumpProcessMemoryMixin(object):
  """Acquires memory for a given list of processes.

  Note that accessing process memory with Yara on Linux causes
  processes to pause. This can impact the client machines when dumping
  large processes.
  """

  category = "/Yara/"
  friendly_name = "Yara Process Dump"

  args_type = rdf_yara.YaraProcessDumpArgs
  behaviours = flow.GRRFlow.behaviours + "BASIC"

  def Start(self):
    # Catch regex errors early.
    if self.args.process_regex:
      re.compile(self.args.process_regex)

    if not (self.args.dump_all_processes or self.args.pids or
            self.args.process_regex):
      raise ValueError("No processes to dump specified.")

    self.CallClient(
        server_stubs.YaraProcessDump,
        request=self.args,
        next_state="ProcessResults")

  def ProcessResults(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    response = responses.First()

    self.SendReply(response)

    for error in response.errors:
      p = error.process
      self.Log("Error dumping process %s (pid %d): %s" % (p.name, p.pid,
                                                          error.error))

    dump_files_to_get = []
    for dumped_process in response.dumped_processes:
      p = dumped_process.process
      self.Log("Getting %d dump files for process %s (pid %d)." % (len(
          dumped_process.dump_files), p.name, p.pid))
      for pathspec in dumped_process.dump_files:
        dump_files_to_get.append(pathspec)

    if not dump_files_to_get:
      self.Log("No memory dumped, exiting.")
      return

    self.CallFlow(
        transfer.MultiGetFile.__name__,
        pathspecs=dump_files_to_get,
        file_size=1024 * 1024 * 1024,
        next_state="DeleteFiles")

  def DeleteFiles(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    for response in responses:
      self.SendReply(response)

      self.CallClient(
          server_stubs.DeleteGRRTempFiles,
          response.pathspec,
          next_state="LogDeleteFiles")

  def LogDeleteFiles(self, responses):
    # Check that the DeleteFiles flow worked.
    if not responses.success:
      raise flow.FlowError("Could not delete file: %s" % responses.status)
