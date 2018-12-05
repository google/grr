#!/usr/bin/env python
"""End to end tests for lib.flows.general.network."""
from __future__ import absolute_import
from __future__ import division

from grr_response_test.end_to_end_tests import test_base


class TestNetstat(test_base.EndToEndTest):
  """Test Netstat."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def runTest(self):
    f = self.RunFlowAndWait("Netstat")

    results = list(f.ListResults())
    self.assertGreater(len(results), 5)

    num_ips = set()
    for r in results:
      netstat = r.payload
      num_ips.add(netstat.local_address.ip)

    # There should be at least two local IPs.
    self.assertGreater(len(num_ips), 1)
