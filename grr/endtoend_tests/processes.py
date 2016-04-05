#!/usr/bin/env python
"""End to end tests for lib.flows.general.processes."""



from grr.endtoend_tests import base
from grr.lib import aff4


class TestProcessListing(base.AutomatedTest):
  """Test ListProcesses."""
  platforms = ["Linux", "Windows", "Darwin"]

  flow = "ListProcesses"
  output_path = "analysis/ListProcesses/testing"
  args = {"output": output_path}

  def CheckFlow(self):
    procs = aff4.FACTORY.Open(self.client_id.Add(self.output_path), mode="r",
                              token=self.token)
    self.assertIsInstance(procs, aff4.RDFValueCollection)
    process_list = list(procs)
    # Make sure there are at least some results.
    self.assertGreater(len(process_list), 5)

    expected_name = self.GetGRRBinaryName()
    for p in process_list:
      if expected_name in p.exe:
        return
    self.fail("Process listing does not contain %s." % expected_name)
