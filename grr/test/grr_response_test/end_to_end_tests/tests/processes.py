#!/usr/bin/env python
"""End to end tests for lib.flows.general.processes."""
from __future__ import absolute_import
from __future__ import division

from grr_response_test.end_to_end_tests import test_base


class TestProcessListing(test_base.EndToEndTest):
  """Test ListProcesses."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def runTest(self):
    f = self.RunFlowAndWait("Netstat")

    results = list(f.ListResults())
    self.assertGreater(len(results), 5)

    # TODO(user): add a check for a GRR process (probably need to query
    # the server for the configuration option containing GRR agent name
    # to do that).
