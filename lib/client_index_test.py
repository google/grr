#!/usr/bin/env python
"""Tests for grr.lib.client_index."""


# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
from grr.lib import client_index
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import aff4
from grr.lib import flags
from grr.lib import rdfvalue
from grr.lib import test_lib


CLIENT_ID = "C.00aaeccbb45f33a3"


class ClientIndexTest(test_lib.AFF4ObjectTest):

  def testClientIdToFromURN(self):
    index = aff4.FACTORY.Create("aff4:/client-index/",
                                aff4_type="ClientIndex",
                                mode="rw",
                                token=self.token)
    # Capitilzation is fixed if necessary.
    self.assertEqual(
        CLIENT_ID,
        index._ClientIdFromURN(
            rdfvalue.ClientURN("aff4:/C.00AAeccbb45f33a3")))
    self.assertEqual(rdfvalue.ClientURN("aff4:/C.00aaeccbb45f33a3"),
                     index._URNFromClientID(CLIENT_ID))

  def testAnalyzeClient(self):
    index = aff4.FACTORY.Create("aff4:/client-index/",
                                aff4_type="ClientIndex",
                                mode="rw",
                                token=self.token)
    test_lib.ClientFixture("aff4:/" + CLIENT_ID, token=self.token)
    client = aff4.FACTORY.Create("aff4:/" + CLIENT_ID,
                                 aff4_type="VFSGRRClient",
                                 mode="rw",
                                 token=self.token)
    client_id, keywords = index.AnalyzeClient(client)

    # Should contain the client id.
    self.assertEqual(client_id, CLIENT_ID)
    self.assertIn(CLIENT_ID, keywords)

    # Should not contain an empty string.
    self.assertNotIn("", keywords)

    # OS of the client
    self.assertIn("windows", keywords)

    # Users of the client.
    self.assertIn("bert", keywords)
    self.assertIn("bertrand", keywords)
    self.assertNotIn(")", keywords)
    self.assertIn("russell", keywords)
    self.assertIn("logician", keywords)
    self.assertIn("ernie", keywords)
    self.assertIn("eric", keywords)
    self.assertIn("jacobson", keywords)
    self.assertIn("steve o'bryan", keywords)
    self.assertIn("o'bryan", keywords)

    # Client information.
    self.assertIn("grr monitor", keywords)
    self.assertIn("client-label-23", keywords)

  def testAddLookupClients(self):
    index = aff4.FACTORY.Create("aff4:/client-index/",
                                aff4_type="ClientIndex",
                                mode="rw",
                                token=self.token)
    client_urns = self.SetupClients(42)
    for urn in client_urns:
      client = aff4.FACTORY.Create(urn,
                                   aff4_type="VFSGRRClient",
                                   mode="r",
                                   token=self.token)
      index.AddClient(client)

    # Check unique identifiers.
    self.assertEqual(
        index.LookupClients(["192.168.0.1"]),
        [rdfvalue.ClientURN("aff4:/C.1000000000000001")])
    self.assertEqual(
        index.LookupClients(["2001:aBcd::1"]),
        [rdfvalue.ClientURN("aff4:/C.1000000000000001")])
    self.assertEqual(
        index.LookupClients(["ip:192.168.0.1"]),
        [rdfvalue.ClientURN("aff4:/C.1000000000000001")])
    self.assertEqual(
        index.LookupClients(["ip:2001:abcd::1"]),
        [rdfvalue.ClientURN("aff4:/C.1000000000000001")])
    self.assertEqual(
        index.LookupClients(["host-2"]),
        [rdfvalue.ClientURN("aff4:/C.1000000000000002")])

    # IP prefixes of octets should work:
    self.assertEqual(
        sorted(index.LookupClients(["192.168.0"])), sorted(client_urns))

    # Intersections should work.
    self.assertEqual(index.LookupClients(["192.168.0", "Host-2"]),
                     [rdfvalue.ClientURN("aff4:/C.1000000000000002")])


def main(argv):
  test_lib.main(argv)

if __name__ == "__main__":
  flags.StartMain(main)
