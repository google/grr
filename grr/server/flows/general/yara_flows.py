#!/usr/bin/env python
"""Flows that utilize the Yara library."""

import re

from grr.lib.rdfvalues import rdf_yara
from grr.server import flow
from grr.server import server_stubs


class YaraProcessScan(flow.GRRFlow):
  """Scans process memory using Yara."""

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
