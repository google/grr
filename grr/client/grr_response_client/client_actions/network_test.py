#!/usr/bin/env python
"""Tests the Netstat client action."""

from absl import app

from grr_response_client.client_actions import network
from grr_response_core.lib.rdfvalues import client_action as rdf_client_action
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


class NetstatActionTest(client_test_lib.EmptyActionTest):
  """Tests the Netstat client action."""

  def testListNetworkConnections(self):
    result = self.RunAction(
        network.ListNetworkConnections,
        arg=rdf_client_action.ListNetworkConnectionsArgs(),
    )
    for r in result:
      self.assertTrue(r.process_name)
      self.assertTrue(r.local_address)

  def testListNetworkConnectionsFilter(self):
    result = self.RunAction(
        network.ListNetworkConnections,
        arg=rdf_client_action.ListNetworkConnectionsArgs(listening_only=True),
    )
    for r in result:
      self.assertTrue(r.process_name)
      self.assertTrue(r.local_address)
      self.assertEqual(r.state, "LISTEN")


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
