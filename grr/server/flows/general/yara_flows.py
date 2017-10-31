#!/usr/bin/env python
"""Flows that utilize the Yara library."""

import re

from grr.lib.rdfvalues import rdf_yara
from grr.server import flow
from grr.server import server_stubs
from grr.server.flows.general import transfer


class YaraProcessScan(flow.GRRFlow):
  """Scans process memory using Yara.

  Note that accessing process memory with Yara on Linux causes
  processes to pause. This can impact the client machines when doing
  large scans.
  """

  category = "/Yara/"
  friendly_name = "Yara Process Scan"

  args_type = rdf_yara.YaraProcessScanRequest

  @flow.StateHandler()
  def Start(self):

    # Catch signature issues early.
    self.args.yara_signature.GetRules()

    # Same for regex errors.
    if self.args.process_regex:
      re.compile(self.args.process_regex)

    self.CallClient(
        server_stubs.YaraProcessScan,
        request=self.args,
        next_state="ProcessScanResults")

  @flow.StateHandler()
  def ProcessScanResults(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    for response in responses:
      self.SendReply(response)


class YaraDumpProcessMemory(flow.GRRFlow):
  """Acquires memory for a given list of processes.

  Note that accessing process memory with Yara on Linux causes
  processes to pause. This can impact the client machines when dumping
  large processes.
  """

  category = "/Yara/"
  friendly_name = "Yara Process Dump"

  args_type = rdf_yara.YaraProcessDumpArgs

  @flow.StateHandler()
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

  @flow.StateHandler()
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
      self.Log("Getting %d dump files for process %s (pid %d)." %
               (len(dumped_process.dump_files), p.name, p.pid))
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

  @flow.StateHandler()
  def DeleteFiles(self, responses):
    if not responses.success:
      raise flow.FlowError(responses.status)

    for response in responses:
      self.SendReply(response)

      self.CallClient(
          server_stubs.DeleteGRRTempFiles,
          response.pathspec,
          next_state="LogDeleteFiles")

  @flow.StateHandler()
  def LogDeleteFiles(self, responses):
    # Check that the DeleteFiles flow worked.
    if not responses.success:
      raise flow.FlowError("Could not delete file: %s" % responses.status)
