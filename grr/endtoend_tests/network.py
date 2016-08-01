#!/usr/bin/env python
"""End to end tests for lib.flows.general.network."""


from grr.endtoend_tests import base
from grr.lib import flow_runner
from grr.lib.rdfvalues import client as rdf_client


class TestNetstat(base.AutomatedTest):
  """Test Netstat."""
  platforms = ["Linux", "Windows", "Darwin"]
  flow = "Netstat"

  def CheckFlow(self):
    netstat_list = self.CheckCollectionNotEmptyWithRetry(
        self.session_id.Add(flow_runner.RESULTS_SUFFIX), self.token)
    self.assertGreater(len(netstat_list), 5)
    num_ips = set()
    for netstat in netstat_list:
      self.assertIsInstance(netstat, rdf_client.NetworkConnection)
      num_ips.add(netstat.local_address.ip)
      if len(num_ips) > 1:
        break

    # There should be at least two local IPs.
    self.assertGreater(len(num_ips), 1)
