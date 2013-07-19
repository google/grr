#!/usr/bin/env python
"""Tests the search library."""


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import flags
from grr.lib import search
from grr.lib import test_lib


class SearchTest(test_lib.FlowTestsBaseclass):
  """Test the search handling."""

  def setUp(self):
    super(SearchTest, self).setUp()
    self.clients = self.SetupClients(5)

  def testSearch(self):
    """Test the ability to search for clients."""
    client_ids = self.SetupClients(10)
    client1 = aff4.FACTORY.Open(client_ids[0], token=self.token, mode="rw")
    client2 = aff4.FACTORY.Open(client_ids[1], token=self.token, mode="rw")
    client1.Set(client1.Schema.FQDN("lmao.example.com"))
    client2.Set(client2.Schema.FQDN("lmao.example.com"))
    macs = client1.Get(client1.Schema.MAC_ADDRESS)
    client1.Flush()
    client2.Flush()

    # Search for something indexed on two clients.
    results = list(search.SearchClients("lmao.example.com", token=self.token))
    results.sort()
    self.assertEqual(results[0].urn, client1.urn)
    self.assertEqual(len(results), 2)

    # Search for something indexed on many clients.
    results = list(search.SearchClients("example.com", token=self.token,
                                        max_results=4))
    self.assertEqual(len(results), 4)

    results = list(search.SearchClients("example.com", token=self.token,
                                        max_results=1))
    self.assertEqual(len(results), 1)

    # Check we can search mac addresses with or without index.
    mac_addr = str(macs).split()[0]
    results = list(search.SearchClients("mac:%s" % mac_addr, token=self.token))
    self.assertEqual(results[0].urn, client1.urn)
    self.assertEqual(len(results), 1)
    results = list(search.SearchClients("%s" % mac_addr, token=self.token))
    self.assertEqual(results[0].urn, client1.urn)
    self.assertEqual(len(results), 1)

    # Check we handle mac addresses in : format.
    mac_addr = ":".join(mac_addr[i:i+2] for i in range(0, len(mac_addr), 2))
    results = list(search.SearchClients(mac_addr.upper(), token=self.token))
    self.assertEqual(len(results), 1)
    # Check we handle mac addresses in : format with prefix.
    results = list(search.SearchClients("mac:%s" % mac_addr, token=self.token))
    self.assertEqual(len(results), 1)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
