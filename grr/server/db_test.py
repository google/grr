#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
import abc

import unittest
from grr.lib import rdfvalue
from grr.lib import utils
from grr.lib.rdfvalues import client as rdf_client
from grr.lib.rdfvalues import crypto
from grr.lib.rdfvalues import objects
from grr.server import db


class DatabaseTest(unittest.TestCase):
  """An abstract class for testing db.Database implementations.

  Implementations should override CreateDatabase in order to produce
  a test suite for a particular implementation of db.Database.
  """
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def CreateDatabase(self):
    """Create a test database.

    Returns:
      A db.Database, suitable for testing.
    """

  def testDatabaseType(self):
    d = self.CreateDatabase()
    self.assertIsInstance(d, db.Database)

  def testClientMetadataInitialWrite(self):
    d = self.CreateDatabase()

    client_id_1 = "C.fc413187fefa1dcf"
    # Typical initial FS enabled write
    d.WriteClientMetadata(client_id_1, fleetspeak_enabled=True)

    client_id_2 = "C.00413187fefa1dcf"
    # Typical initial non-FS write
    d.WriteClientMetadata(
        client_id_2, certificate=CERT, fleetspeak_enabled=False)

    res = d.ReadClientMetadatas([client_id_1, client_id_2])
    self.assertEqual(len(res), 2)

    m1 = res[client_id_1]
    self.assertIsInstance(m1, objects.ClientMetadata)
    self.assertTrue(m1.fleetspeak_enabled)

    m2 = res[client_id_2]
    self.assertIsInstance(m2, objects.ClientMetadata)
    self.assertFalse(m2.fleetspeak_enabled)
    self.assertEqual(m2.certificate, CERT)

  def testClientMetadataPing(self):
    d = self.CreateDatabase()

    client_id_1 = "C.fc413187fefa1dcf"
    # Typical initial FS enabled write
    d.WriteClientMetadata(client_id_1, fleetspeak_enabled=True)

    # Typical update on client ping.
    d.WriteClientMetadata(
        client_id_1,
        last_ping=rdfvalue.RDFDatetime(200000),
        last_clock=rdfvalue.RDFDatetime(210000),
        last_ip=rdf_client.NetworkAddress(human_readable_address="8.8.8.8"),
        last_foreman=rdfvalue.RDFDatetime(220000))

    res = d.ReadClientMetadatas([client_id_1])
    self.assertEqual(len(res), 1)
    m1 = res[client_id_1]
    self.assertIsInstance(m1, objects.ClientMetadata)
    self.assertTrue(m1.fleetspeak_enabled)
    self.assertEqual(m1.ping, rdfvalue.RDFDatetime(200000))
    self.assertEqual(m1.clock, rdfvalue.RDFDatetime(210000))
    self.assertEqual(
        m1.ip, rdf_client.NetworkAddress(human_readable_address="8.8.8.8"))
    self.assertEqual(m1.last_foreman_time, rdfvalue.RDFDatetime(220000))

  def testClientMetadataCrash(self):
    d = self.CreateDatabase()

    client_id_1 = "C.fc413187fefa1dcf"
    # Typical initial FS enabled write
    d.WriteClientMetadata(client_id_1, fleetspeak_enabled=True)

    # Typical update on client crash.
    d.WriteClientMetadata(
        client_id_1,
        last_crash=rdf_client.ClientCrash(crash_message="Et tu, Brute?"))
    res = d.ReadClientMetadatas([client_id_1])
    self.assertEqual(len(res), 1)
    m1 = res[client_id_1]
    self.assertEqual(
        m1.last_crash, rdf_client.ClientCrash(crash_message="Et tu, Brute?"))

  def testClientMetadataValidatesIP(self):
    d = self.CreateDatabase()
    client_id = "C.fc413187fefa1dcf"
    with self.assertRaises(ValueError):
      d.WriteClientMetadata(
          client_id, fleetspeak_enabled=True, last_ip="127.0.0.1")

  def testClientMetadataValidatesCrash(self):
    d = self.CreateDatabase()
    client_id = "C.fc413187fefa1dcf"
    with self.assertRaises(ValueError):
      d.WriteClientMetadata(
          client_id, fleetspeak_enabled=True, last_crash="Et tu, Brute?")

  def testClientHistory(self):
    d = self.CreateDatabase()

    client_id = "C.fc413187fefa1dcf"
    d.WriteClientMetadata(client_id, fleetspeak_enabled=True)

    client = objects.Client(hostname="test1234.examples.com", kernel="12.3")
    d.WriteClient(client_id, client)
    client = objects.Client(hostname="test1234.examples.com", kernel="12.4")
    d.WriteClient(client_id, client)

    hist = d.ReadClientHistory(client_id)
    self.assertEqual(len(hist), 2)
    self.assertIsInstance(hist[0], objects.Client)
    self.assertIsInstance(hist[1], objects.Client)
    self.assertGreater(hist[0].timestamp, hist[1].timestamp)
    self.assertEqual(hist[0].kernel, "12.4")
    self.assertEqual(hist[1].kernel, "12.3")

  def testClientSummary(self):
    d = self.CreateDatabase()

    client_id_1 = "C.0000000000000001"
    client_id_2 = "C.0000000000000002"
    client_id_3 = "C.0000000000000003"
    d.WriteClientMetadata(client_id_1, fleetspeak_enabled=True)
    d.WriteClientMetadata(client_id_2, fleetspeak_enabled=True)
    d.WriteClientMetadata(client_id_3, fleetspeak_enabled=True)

    d.WriteClient(client_id_1,
                  objects.Client(
                      hostname="test1234.examples.com", kernel="12.3"))
    d.WriteClient(client_id_1,
                  objects.Client(
                      hostname="test1234.examples.com", kernel="12.4"))

    d.WriteClient(client_id_2,
                  objects.Client(
                      hostname="test1235.examples.com", kernel="12.4"))

    hist = d.ReadClientHistory(client_id_1)
    self.assertEqual(len(hist), 2)

    # client_3 should be excluded - no snapshot yet
    res = d.ReadClients([client_id_1, client_id_2, client_id_3])
    self.assertEqual(len(res), 3)
    self.assertIsInstance(res[client_id_1], objects.Client)
    self.assertIsInstance(res[client_id_2], objects.Client)
    self.assertIsNotNone(res[client_id_1].timestamp)
    self.assertIsNotNone(res[client_id_2].timestamp)
    self.assertEqual(res[client_id_1].hostname, "test1234.examples.com")
    self.assertEqual(res[client_id_1].kernel, "12.4")
    self.assertEqual(res[client_id_2].hostname, "test1235.examples.com")
    self.assertFalse(res[client_id_3])

  def testClientValidates(self):
    d = self.CreateDatabase()

    # Write some metadata so the client write would otherwise succeed.
    client_id = "C.fc413187fefa1dcf"
    d.WriteClientMetadata(client_id, fleetspeak_enabled=True)
    with self.assertRaises(ValueError):
      d.WriteClient(client_id, "test1235.examples.com")

  def testClientKeywords(self):
    d = self.CreateDatabase()
    client_id_1 = "C.0000000000000001"
    client_id_2 = "C.0000000000000002"
    client_id_3 = "C.0000000000000003"
    for cid in [client_id_1, client_id_2, client_id_3]:
      d.WriteClientMetadata(cid, fleetspeak_enabled=True)

    # Typical keywords are usernames and prefixes of hostnames.
    d.WriteClientKeywords(client_id_1, [
        "joe", "machine.test.example1.com", "machine.test.example1",
        "machine.test", "machine", u"⊙_ʘ"
    ])
    d.WriteClientKeywords(client_id_2, [
        "fred", "machine.test.example2.com", "machine.test.example2",
        "machine.test", "machine", u"ಠ_ಠ"
    ])
    res = d.ListClientsForKeywords(["fred", "machine", "missing"])
    self.assertEqual(res["fred"], [client_id_2])
    self.assertEqual(sorted(res["machine"]), [client_id_1, client_id_2])
    self.assertEqual(res["missing"], [])

    for kw, client_id in [(u"⊙_ʘ", client_id_1), (u"ಠ_ಠ", client_id_2),
                          (utils.SmartStr(u"⊙_ʘ"), client_id_1)]:
      res = d.ListClientsForKeywords([kw])
      self.assertEqual(res[kw], [client_id],
                       "Expected [%s] when reading keyword %s, got %s" %
                       (client_id, kw, res[kw]))

  def testClientKeywordsTimeRanges(self):
    d = self.CreateDatabase()
    client_id = "C.0000000000000001"
    d.WriteClientMetadata(client_id, fleetspeak_enabled=True)

    d.WriteClientKeywords(client_id, ["hostname1"])
    change_time = rdfvalue.RDFDatetime.Now()
    d.WriteClientKeywords(client_id, ["hostname2"])

    res = d.ListClientsForKeywords(
        ["hostname1", "hostname2"], start_time=change_time)
    self.assertEqual(res["hostname1"], [])
    self.assertEqual(res["hostname2"], [client_id])

  def testDeleteClientKeyword(self):
    d = self.CreateDatabase()
    client_id = "C.0000000000000001"
    temporary_kw = "investigation42"
    d.WriteClientMetadata(client_id, fleetspeak_enabled=True)
    d.WriteClientKeywords(client_id, [
        "joe", "machine.test.example.com", "machine.test.example",
        "machine.test", temporary_kw
    ])
    self.assertEqual(
        d.ListClientsForKeywords([temporary_kw])[temporary_kw], [client_id])
    d.DeleteClientKeyword(client_id, temporary_kw)
    self.assertEqual(d.ListClientsForKeywords([temporary_kw])[temporary_kw], [])
    self.assertEqual(d.ListClientsForKeywords(["joe"])["joe"], [client_id])

  def testClientLabels(self):
    d = self.CreateDatabase()
    client_id = "C.0000000000000001"
    d.WriteClientMetadata(client_id, fleetspeak_enabled=True)

    self.assertEqual(d.GetClientLabels(client_id), set())

    d.AddClientLabels(client_id, "owner1", ["label1"])
    d.AddClientLabels(client_id, "owner2", ["label2", "label3"])

    all_labels = set(["label1", "label2", "label3"])

    self.assertEqual(d.GetClientLabels(client_id), all_labels)

    # Can't hurt to insert this one again.
    d.AddClientLabels(client_id, "owner1", ["label1"])
    self.assertEqual(d.GetClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner1", ["does not exist"])
    self.assertEqual(d.GetClientLabels(client_id), all_labels)

    # Label3 is actually owned by owner2.
    d.RemoveClientLabels(client_id, "owner1", ["label3"])
    self.assertEqual(d.GetClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner2", ["label3"])
    self.assertEqual(d.GetClientLabels(client_id), set(["label1", "label2"]))

  def testClientLabelsUnicode(self):
    d = self.CreateDatabase()
    client_id = "C.0000000000000001"
    d.WriteClientMetadata(client_id, fleetspeak_enabled=True)

    self.assertEqual(d.GetClientLabels(client_id), set())

    d.AddClientLabels(client_id, "owner1", [u"⛄࿄1"])
    d.AddClientLabels(client_id, "owner2", [u"⛄࿄2"])
    d.AddClientLabels(client_id, "owner2", [utils.SmartStr(u"⛄࿄3")])

    all_labels = set([u"⛄࿄1", u"⛄࿄2", u"⛄࿄3"])

    self.assertEqual(d.GetClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner1", ["does not exist"])
    self.assertEqual(d.GetClientLabels(client_id), all_labels)

    # This label is actually owned by owner2.
    d.RemoveClientLabels(client_id, "owner1", [u"⛄࿄3"])
    self.assertEqual(d.GetClientLabels(client_id), all_labels)

    d.RemoveClientLabels(client_id, "owner2", [u"⛄࿄3"])
    self.assertEqual(d.GetClientLabels(client_id), set([u"⛄࿄1", u"⛄࿄2"]))


CERT = crypto.RDFX509Cert("""-----BEGIN CERTIFICATE-----
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
-----END CERTIFICATE-----""")
