#!/usr/bin/env python
"""Tests the Netstat client action."""


from grr.client.client_actions import network
from grr.lib import flags
from grr.test_lib import client_test_lib
from grr.test_lib import test_lib


class NetstatActionTest(client_test_lib.EmptyActionTest):
  """Tests the Netstat client action."""

  def testNetstat(self):

    result = self.RunAction(network.Netstat)
    # TODO(user|user): Turn this into an e2e test.
    # self.assertGreater(len(result), 0)
    for r in result:
      self.assertTrue(r.process_name)
      self.assertTrue(r.local_address)
      self.assertTrue(r.local_address.port)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
