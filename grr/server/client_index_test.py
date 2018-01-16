#!/usr/bin/env python
"""Tests for grr.lib.client_index."""

import socket

from grr.lib import flags
from grr.lib import ipv6_utils
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import objects
from grr.server import aff4
from grr.server import client_index
from grr.server import data_store
from grr.server.aff4_objects import aff4_grr
from grr.test_lib import aff4_test_lib
from grr.test_lib import test_lib

CLIENT_ID = "C.00aaeccbb45f33a3"


class AFF4ClientIndexTest(aff4_test_lib.AFF4ObjectTest):

  def testAnalyzeClient(self):
    index = client_index.CreateClientIndex(token=self.token)
    client = aff4.FACTORY.Create(
        "aff4:/" + CLIENT_ID,
        aff4_type=aff4_grr.VFSGRRClient,
        mode="rw",
        token=self.token)
    client.Set(client.Schema.SYSTEM("Windows"))
    client.Set(
        client.Schema.CLIENT_INFO(
            client_name="grr monitor", labels=["client-label-23"]))
    kb = rdf_client.KnowledgeBase()
    kb.users.Append(
        rdf_client.User(
            username="Bert",
            full_name="Eric (Bertrand ) 'Russell' \"Logician\" Jacobson"))
    kb.users.Append(
        rdf_client.User(username="Ernie", full_name="Steve O'Bryan"))
    client.Set(client.Schema.KNOWLEDGE_BASE(kb))
    _, keywords = index.AnalyzeClient(client)

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
    index = client_index.CreateClientIndex(token=self.token)
    client_urns = self.SetupClients(42)
    for urn in client_urns:
      client = aff4.FACTORY.Create(
          urn, aff4_type=aff4_grr.VFSGRRClient, mode="r", token=self.token)
      index.AddClient(client)

    # Check unique identifiers.
    self.assertEqual(
        index.LookupClients(["192.168.0.1"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000001")])
    self.assertEqual(
        index.LookupClients(["2001:aBcd::1"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000001")])
    self.assertEqual(
        index.LookupClients(["ip:192.168.0.1"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000001")])
    self.assertEqual(
        index.LookupClients(["ip:2001:abcd::1"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000001")])
    self.assertEqual(
        index.LookupClients(["host-2"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000002")])
    self.assertEqual(
        index.LookupClients(["C.1000000000000002"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000002")])
    self.assertEqual(
        index.LookupClients(["aabbccddee01"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000001")])
    self.assertEqual(
        index.LookupClients(["mac:aabbccddee01"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000001")])
    self.assertEqual(
        index.LookupClients(["aa:bb:cc:dd:ee:01"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000001")])
    self.assertEqual(
        index.LookupClients(["mac:aa:bb:cc:dd:ee:01"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000001")])

    # IP prefixes of octets should work:
    self.assertEqual(
        sorted(index.LookupClients(["192.168.0"])), sorted(client_urns))

    # Hostname prefixes of tokens should work.
    self.assertEqual(
        index.LookupClients(["host-5.example"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000005")])

    # Intersections should work.
    self.assertEqual(
        index.LookupClients(["192.168.0", "Host-2"]),
        [rdf_client.ClientURN("aff4:/C.1000000000000002")])

    # Universal keyword should find everything.
    self.assertEqual(len(index.LookupClients(["."])), 42)

  def testAddTimestamp(self):
    index = client_index.CreateClientIndex(token=self.token)

    client_urns = self.SetupClients(5)
    # 1413807132 = Mon, 20 Oct 2014 12:12:12 GMT
    with test_lib.FakeTime(1413807132):
      for urn in client_urns:
        client = aff4.FACTORY.Create(
            urn, aff4_type=aff4_grr.VFSGRRClient, mode="r", token=self.token)
        index.AddClient(client)

    self.assertEqual(
        len(index.LookupClients([".", "start_date:2014-10-20"])), 5)
    self.assertEqual(
        len(index.LookupClients([".", "start_date:2014-10-21"])), 0)
    self.assertEqual(
        len(
            index.LookupClients(
                [".", "start_date:2013-10-20", "end_date:2014-10-19"])), 0)
    self.assertEqual(
        len(
            index.LookupClients(
                [".", "start_date:2013-10-20", "end_date:2014-10-20"])), 5)

    # Ignore the keyword if the date is not readable.
    self.assertEqual(
        len(
            index.LookupClients([".", "start_date:2013-10-20",
                                 "end_date:XXXX"])), 5)

  def testUnversionedKeywords(self):
    index = client_index.CreateClientIndex(token=self.token)

    client_urns = self.SetupClients(5)

    with test_lib.FakeTime(1000000):
      for i in range(5):
        client = aff4.FACTORY.Create(
            client_urns[i],
            aff4_type=aff4_grr.VFSGRRClient,
            mode="rw",
            token=self.token)
        client.Set(client.Schema.HOST_IPS("10.1.0.%d" % i))
        client.Flush()
        index.AddClient(client)

    with test_lib.FakeTime(2000000):
      for i in range(5):
        client = aff4.FACTORY.Create(
            client_urns[i],
            aff4_type=aff4_grr.VFSGRRClient,
            mode="rw",
            token=self.token)
        client.Set(client.Schema.HOST_IPS("10.1.1.%d" % i))
        client.Flush()
        index.AddClient(client)
    with test_lib.FakeTime(3000000):
      self.assertEqual(
          index.LookupClients(["10.1.0", "Host-2"]),
          [rdf_client.ClientURN("aff4:/C.1000000000000002")])
      self.assertEqual(index.LookupClients(["+10.1.0", "Host-2"]), [])
      self.assertEqual(
          index.LookupClients(["+10.1.1", "Host-2"]),
          [rdf_client.ClientURN("aff4:/C.1000000000000002")])

  def testRemoveLabels(self):
    client = aff4.FACTORY.Create(
        CLIENT_ID, aff4_type=aff4_grr.VFSGRRClient, mode="rw", token=self.token)
    client.AddLabel("testlabel_1")
    client.AddLabel("testlabel_2")
    client.Flush()
    index = client_index.CreateClientIndex(token=self.token)
    index.AddClient(client)

    client_list = [rdf_client.ClientURN(CLIENT_ID)]
    self.assertEqual(index.LookupClients(["testlabel_1"]), client_list)
    self.assertEqual(index.LookupClients(["testlabel_2"]), client_list)

    # Now delete one label.
    index.RemoveClientLabels(client)
    client.RemoveLabel("testlabel_1")
    index.AddClient(client)

    self.assertEqual(index.LookupClients(["testlabel_1"]), [])
    self.assertEqual(index.LookupClients(["testlabel_2"]), client_list)

  def _HostsHaveLabel(self, hosts, label, index):
    urns = index.LookupClients(["+label:%s" % label])
    result = [
        utils.SmartStr(c.Get("Host")).lower()
        for c in aff4.FACTORY.MultiOpen(urns, token=self.token)
    ]
    self.assertItemsEqual(hosts, result)

  def testBulkLabelClients(self):
    index = client_index.CreateClientIndex(token=self.token)

    client_urns = self.SetupClients(2)
    for urn in client_urns:
      client = aff4.FACTORY.Create(
          urn, aff4_type=aff4_grr.VFSGRRClient, mode="rw", token=self.token)
      client.AddLabel("test_client")
      client.Flush()
      index.AddClient(client)

    # Maps hostnames used in the test to client urns.
    m = {"host-0": client_urns[0], "host-1": client_urns[1]}

    # No hostname.
    client_index.BulkLabel(
        "label-0", ["host-3"], token=self.token, client_index=index)
    self._HostsHaveLabel([], "label-0", index)

    # Add label.
    hosts = ["host-0", "host-1"]
    client_index.BulkLabel(
        "label-0", hosts, token=self.token, client_index=index)
    # host-0: label-0
    # host-1: label-0
    self._HostsHaveLabel(hosts, "label-0", index)
    self.assertItemsEqual(
        index.LookupClients(["label-0"]), [m[host] for host in hosts])

    # Add another label only changes the new host.
    hosts = ["host-1"]
    client_index.BulkLabel(
        "label-1", hosts, token=self.token, client_index=index)
    # host-0: label-0
    # host-1: label-0, label-1
    self._HostsHaveLabel(hosts, "label-1", index)
    self.assertItemsEqual(
        index.LookupClients(["label-1"]), [m[host] for host in hosts])
    # and other labels remain unchanged.
    hosts = ["host-0", "host-1"]
    self._HostsHaveLabel(hosts, "label-0", index)
    self.assertItemsEqual(
        index.LookupClients(["label-0"]), [m[host] for host in hosts])

    # Relabeling updates the label on already labeled hosts.
    hosts = ["host-0"]
    client_index.BulkLabel(
        "label-0", hosts, token=self.token, client_index=index)
    # host-0: label-0
    # host-1: label-1
    self._HostsHaveLabel(hosts, "label-0", index)
    self.assertItemsEqual(
        index.LookupClients(["label-0"]), [m[host] for host in hosts])
    # and other labels remain unchanged.
    hosts = ["host-1"]
    self._HostsHaveLabel(hosts, "label-1", index)
    self.assertItemsEqual(
        index.LookupClients(["label-1"]), [m[host] for host in hosts])


class ClientIndexTest(aff4_test_lib.AFF4ObjectTest):

  def testAnalyzeClient(self):
    index = client_index.ClientIndex()

    client = objects.Client()
    client.system = "Windows"
    client.client_info.client_name = "grr monitor"
    client.client_info.labels = ["client-label-23"]
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
      client = objects.Client()
      client.system = "Windows"
      client.hostname = "host-%d" % i
      client.fqdn = "host-%d.example.com" % i

      client.interfaces = [
          rdf_client.Interface(
              addresses=[
                  rdf_client.NetworkAddress(
                      address_type=rdf_client.NetworkAddress.Family.INET,
                      packed_bytes=ipv6_utils.InetPtoN(socket.AF_INET,
                                                       "192.168.0.%d" % i)),
                  rdf_client.NetworkAddress(
                      address_type=rdf_client.NetworkAddress.Family.INET6,
                      packed_bytes=ipv6_utils.InetPtoN(socket.AF_INET6,
                                                       "2001:abcd::%d" % i))
              ],
              mac_address=("aabbccddee0%d" % i).decode("hex"))
      ]
      res[client_id] = client
    return res

  def testAddLookupClients(self):
    index = client_index.ClientIndex()

    clients = self._SetupClients(2)
    for client_id, client in clients.items():
      data_store.REL_DB.WriteClientMetadata(client_id, fleetspeak_enabled=False)
      index.AddClient(client_id, client)

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
    self.assertItemsEqual(index.LookupClients(["192.168.0"]), list(clients))

    # Hostname prefixes of tokens should work.
    self.assertEqual(
        index.LookupClients(["host-2.example"]), ["C.1000000000000002"])

    # Intersections should work.
    self.assertEqual(
        index.LookupClients(["192.168.0", "Host-2"]), ["C.1000000000000002"])

    # Universal keyword should find everything.
    self.assertItemsEqual(index.LookupClients(["."]), list(clients))

  def testAddTimestamp(self):
    index = client_index.ClientIndex()

    clients = self._SetupClients(5)

    # 1413807132 = Mon, 20 Oct 2014 12:12:12 GMT
    with test_lib.FakeTime(1413807132):
      for client_id, client in clients.items():
        data_store.REL_DB.WriteClientMetadata(
            client_id, fleetspeak_enabled=False)
        index.AddClient(client_id, client)

    self.assertEqual(
        len(index.LookupClients([".", "start_date:2014-10-20"])), 5)
    self.assertEqual(
        len(index.LookupClients([".", "start_date:2014-10-21"])), 0)

    # Ignore the keyword if the date is not readable.
    self.assertEqual(len(index.LookupClients([".", "start_date:XXX"])), 0)

  def testRemoveLabels(self):
    client_id, _ = self._SetupClients(1).items()[0]
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
    client_data = data_store.REL_DB.ReadClients(client_ids)
    labelled_hosts = []

    for client_id in client_ids:
      data = client_data[client_id]
      if not data:
        continue
      labelled_hosts.append(data.hostname)
    self.assertItemsEqual(expected_hosts, labelled_hosts)


def main(argv):
  test_lib.main(argv)


if __name__ == "__main__":
  flags.StartMain(main)
