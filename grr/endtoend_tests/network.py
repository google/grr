#!/usr/bin/env python
"""End to end tests for lib.flows.general.network."""


import logging
from grr.endtoend_tests import base
from grr.lib import aff4
from grr.lib.aff4_objects import network


class TestNetstat(base.AutomatedTest):
  """Test Netstat."""
  platforms = ["Linux", "Windows", "Darwin"]
  test_output_path = "network"
  flow = "Netstat"

  def CheckFlow(self):
    netstat = aff4.FACTORY.Open(
        self.client_id.Add(self.test_output_path),
        mode="r",
        token=self.token)
    self.assertIsInstance(netstat, network.Network)
    connections = netstat.Get(netstat.Schema.CONNECTIONS)
    self.assertGreater(len(connections), 5)
    # There should be at least two local IPs.
    num_ips = set([k.local_address.ip for k in connections])
    self.assertGreater(len(num_ips), 1)
    # There should be at least two different connection states.
    num_states = set([k.state for k in connections])
    # This is a known issue on CentOS so we just warn about it.
    if len(num_states) <= 1:
      logging.warning("Only received one distinct connection state!")
