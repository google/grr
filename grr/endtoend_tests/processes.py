#!/usr/bin/env python
"""End to end tests for lib.flows.general.processes."""


from grr.endtoend_tests import base


class TestProcessListing(base.AutomatedTest):
  """Test ListProcesses."""
  platforms = ["Linux", "Windows", "Darwin"]

  flow = "ListProcesses"
  output_path = "analysis/ListProcesses/testing"

  def CheckFlow(self):
    procs = self.CheckResultCollectionNotEmptyWithRetry(self.session_id)
    self.assertGreater(len(procs), 5)
    expected_name = self.GetGRRBinaryName()
    for p in procs:
      if expected_name in p.exe:
        return
    self.fail("Process listing does not contain %s." % expected_name)
