#!/usr/bin/env python
"""End to end tests for lib.flows.general.processes."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib import flow_runner


class TestProcessListing(base.AutomatedTest):
  """Test ListProcesses."""
  platforms = ["Linux", "Windows", "Darwin"]

  flow = "ListProcesses"
  output_path = "analysis/ListProcesses/testing"

  def CheckFlow(self):
    procs = aff4.FACTORY.Open(
        self.session_id.Add(flow_runner.RESULTS_SUFFIX),
        mode="r",
        token=self.token)

    # Make sure there are at least some results.
    self.assertGreater(len(procs), 5)

    expected_name = self.GetGRRBinaryName()
    for p in procs:
      if expected_name in p.exe:
        return
    self.fail("Process listing does not contain %s." % expected_name)
