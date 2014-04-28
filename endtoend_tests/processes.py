#!/usr/bin/env python
"""End to end tests for lib.flows.general.processes."""



from grr.endtoend_tests import base
from grr.lib import aff4


class TestProcessListing(base.ClientTestBase):
  """Test ListProcesses."""
  platforms = ["linux", "windows", "darwin"]

  flow = "ListProcesses"

  args = {"output": "analysis/ListProcesses/testing"}

  def setUp(self):
    super(TestProcessListing, self).setUp()
    self.process_urn = self.client_id.Add(self.args["output"])
    self.DeleteUrn(self.process_urn)

    self.assertRaises(AssertionError, self.CheckFlow)

  def CheckFlow(self):
    procs = aff4.FACTORY.Open(self.process_urn, mode="r", token=self.token)
    self.assertIsInstance(procs, aff4.RDFValueCollection)
    process_list = list(procs)
    # Make sure there are at least some results.
    self.assertGreater(len(process_list), 5)

    expected_name = self.GetGRRBinaryName()
    for p in process_list:
      if expected_name in p.exe:
        return
    self.fail("Process listing does not contain %s." % expected_name)

