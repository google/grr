#!/usr/bin/env python
# Lint as: python3
# -*- encoding: utf-8 -*-
"""Tests for grr.lib.client_index."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import binascii
import ipaddress

from absl import app

from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_core.lib.rdfvalues import client_network as rdf_client_network
from grr_response_server import client_index
from grr_response_server import data_store
from grr_response_server.rdfvalues import objects as rdf_objects
from grr.test_lib import test_lib

CLIENT_ID = "C.00aaeccbb45f33a3"


class ClientIndexTest(test_lib.GRRBaseTest):

  def testAnalyzeClient(self):
    index = client_index.ClientIndex()

    client = rdf_objects.ClientSnapshot(client_id="C.0000000000000000")
    client.knowledge_base.os = "Windows"
    client.startup_info.client_info.client_name = "grr monitor"
    client.startup_info.client_info.labels = ["client-label-23"]
    kb = client.knowledge_base
    kb.users = [
        rdf_client.User(
            username="Bert",
            full_name="Eric (Bertrand ) 'Russell' \"Logician\" Jacobson"),
        rdf_client.User(username="Ernie", full_name="Steve O'Bryan")
    ]
    keywords = index.AnalyzeClient(client)

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

  def _SetupClients(self, n):
    res = {}
    for i in range(1, n + 1):
      client_id = "C.100000000000000%d" % i
      client = rdf_objects.ClientSnapshot(client_id=client_id)
      client.knowledge_base.os = "Windows"
      client.knowledge_base.fqdn = "host-%d.example.com" % i

      ipv4_addr = rdf_client_network.NetworkAddress(
          address_type=rdf_client_network.NetworkAddress.Family.INET,
          packed_bytes=ipaddress.IPv4Address("192.168.0.%d" % i).packed)
      ipv6_addr = rdf_client_network.NetworkAddress(
          address_type=rdf_client_network.NetworkAddress.Family.INET6,
          packed_bytes=ipaddress.IPv6Address("2001:abcd::%d" % i).packed)

      client.interfaces = [
          rdf_client_network.Interface(
              addresses=[ipv4_addr, ipv6_addr],
              mac_address=binascii.unhexlify("aabbccddee0%d" % i))
      ]
      res[client_id] = client
    return res

  def testAddLookupClients(self):
    index = client_index.ClientIndex()

    clients = self._SetupClients(2)
    for client_id, client in clients.items():
      data_store.REL_DB.WriteClientMetadata(client_id, fleetspeak_enabled=False)
      index.AddClient(client)

    # Check unique identifiers.
    self.assertEqual(
        index.LookupClients(["192.168.0.1"]), ["C.1000000000000001"])
    self.assertEqual(
        index.LookupClients(["2001:aBcd::1"]), ["C.1000000000000001"])
    self.assertEqual(
        index.LookupClients(["ip:192.168.0.1"]), ["C.1000000000000001"])
    self.assertEqual(
        index.LookupClients(["ip:2001:abcd::1"]), ["C.1000000000000001"])
    self.assertEqual(index.LookupClients(["host-2"]), ["C.1000000000000002"])
    self.assertEqual(
        index.LookupClients(["C.1000000000000002"]), ["C.1000000000000002"])
    self.assertEqual(
        index.LookupClients(["aabbccddee01"]), ["C.1000000000000001"])
    self.assertEqual(
        index.LookupClients(["mac:aabbccddee01"]), ["C.1000000000000001"])
    self.assertEqual(
        index.LookupClients(["aa:bb:cc:dd:ee:01"]), ["C.1000000000000001"])
    self.assertEqual(
        index.LookupClients(["mac:aa:bb:cc:dd:ee:01"]), ["C.1000000000000001"])

    # IP prefixes of octets should work:
    self.assertCountEqual(index.LookupClients(["192.168.0"]), list(clients))

    # Hostname prefixes of tokens should work.
    self.assertEqual(
        index.LookupClients(["host-2.example"]), ["C.1000000000000002"])

    # Intersections should work.
    self.assertEqual(
        index.LookupClients(["192.168.0", "Host-2"]), ["C.1000000000000002"])

    # Universal keyword should find everything.
    self.assertCountEqual(index.LookupClients(["."]), list(clients))

  def testAddTimestamp(self):
    index = client_index.ClientIndex()

    clients = self._SetupClients(5)

    # 1413807132 = Mon, 20 Oct 2014 12:12:12 GMT
    with test_lib.FakeTime(1413807132):
      for client_id, client in clients.items():
        data_store.REL_DB.WriteClientMetadata(
            client_id, fleetspeak_enabled=False)
        index.AddClient(client)

    self.assertEqual(
        len(index.LookupClients([".", "start_date:2014-10-20"])), 5)
    self.assertEqual(
        len(index.LookupClients([".", "start_date:2014-10-21"])), 0)

    # Ignore the keyword if the date is not readable.
    self.assertEmpty(index.LookupClients([".", "start_date:XXX"]))

  def testRemoveLabels(self):
    client_id = next(iter(self._SetupClients(1).keys()))
    data_store.REL_DB.WriteClientMetadata(client_id, fleetspeak_enabled=False)
    data_store.REL_DB.AddClientLabels(client_id, "owner",
                                      ["testlabel_1", "testlabel_2"])

    index = client_index.ClientIndex()
    index.AddClientLabels(client_id, ["testlabel_1", "testlabel_2"])

    self.assertEqual(index.LookupClients(["testlabel_1"]), [client_id])
    self.assertEqual(index.LookupClients(["testlabel_2"]), [client_id])

    # Now delete one label.
    index.RemoveClientLabels(client_id, ["testlabel_1"])

    self.assertEqual(index.LookupClients(["testlabel_1"]), [])
    self.assertEqual(index.LookupClients(["testlabel_2"]), [client_id])

    # Remove them all.
    index.RemoveAllClientLabels(client_id)

    self.assertEqual(index.LookupClients(["testlabel_1"]), [])
    self.assertEqual(index.LookupClients(["testlabel_2"]), [])

  def _HostsHaveLabel(self, expected_hosts, label, index):
    client_ids = index.LookupClients(["label:%s" % label])
    client_data = data_store.REL_DB.MultiReadClientSnapshot(client_ids)
    labelled_hosts = []

    for client_id in client_ids:
      data = client_data[client_id]
      if not data:
        continue
      labelled_hosts.append(data.hostname)
    self.assertCountEqual(expected_hosts, labelled_hosts)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
