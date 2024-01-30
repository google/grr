#!/usr/bin/env python
"""End to end tests for lib.flows.general.network."""

from grr_response_test.end_to_end_tests import test_base


class TestNetstat(test_base.EndToEndTest):
  """Test Netstat."""

  platforms = test_base.EndToEndTest.Platform.ALL

  def runTest(self):
    f = self.RunFlowAndWait("Netstat")

    results = list(f.ListResults())
    self.assertNotEmpty(results)

    ips = set()
    for r in results:
      netstat = r.payload
      ips.add(netstat.local_address.ip)

    # There should be at least one local IP.
    self.assertNotEmpty(ips)
