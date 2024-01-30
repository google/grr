#!/usr/bin/env python
"""End to end tests for lib.flows.general.processes."""

from grr_response_test.end_to_end_tests import test_base


class TestProcessListing(test_base.EndToEndTest):
  """Test ListProcesses."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def runTest(self):
    f = self.RunFlowAndWait("ListProcesses")

    results = list(f.ListResults())
    self.assertNotEmpty(results)

    # TODO(user): add a check for a GRR process (probably need to query
    # the server for the configuration option containing GRR agent name
    # to do that).
