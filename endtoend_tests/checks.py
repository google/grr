#!/usr/bin/env python
"""End to end tests for lib.flows.general.collectors."""


from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib.checks import checks as rdf_checks


class TestCheckRunner(base.AutomatedTest):
  """Test RunChecksFlow."""
  platforms = ["Linux"]
  flow = "CheckRunner"
  test_output_path = "analysis/CheckRunner/testing"
  check_ids = ["CIS-LOGIN-UNIX-HASH", "CIS-NET-SYNCOOKIES", "CIS-SSH-PROTOCOL",
               "CIS-NET-LOGMART"]
  args = {"output": test_output_path, "restrict_checks": check_ids}

  def CheckFlow(self):
    urn = self.client_id.Add(self.test_output_path)
    results = aff4.FACTORY.Open(urn, mode="r", token=self.token)
    self.assertIsInstance(results, aff4.RDFValueCollection)
    checks_run = [r.check_id for r in results
                  if isinstance(r, rdf_checks.CheckResult)]
    # Verify the expected checks were run.
    self.assertItemsEqual(self.check_ids, checks_run)
